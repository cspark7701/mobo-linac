"""Proposal strategies independent of simulator initialization and run storage.

A strategy turns the identity-ordered training observations of a campaign into the next
batch of candidates (physical units) plus the proposal metadata recorded with it.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

import torch
from botorch.acquisition.logei import qLogNoisyExpectedImprovement
from botorch.models import ModelListGP

from mobo_linac.acquisition.mobo import SliceObjective, build_acquisition_function, generate_next_candidates
from mobo_linac.config import ExecutionConfig, MoboConfig
from mobo_linac.constraints import get_botorch_constraint_functions
from mobo_linac.metrics.hypervolume import compute_reference_point
from mobo_linac.models.gp import build_scalarized_gp_model, fit_gp_models
from mobo_linac.models.pipeline import SurrogatePipeline
from mobo_linac.result_schema import ResultSchema

Proposal = Tuple[List[List[float]], Optional[Dict[str, Any]]]
# persist_model(model, iteration, training, pipeline=...) records the fitted surrogate.
PersistModel = Callable[..., None]


class ProposalStrategy(Protocol):
    def propose(self, training, iteration: int, batch_size: int, sobol_engine) -> Proposal:
        ...


@dataclass(frozen=True)
class AcquisitionSettings:
    """Multi-start acquisition optimizer budget (from ``execution``)."""

    num_restarts: int
    raw_samples: int
    maxiter: int
    batch_limit: int

    @classmethod
    def from_execution(cls, execution: ExecutionConfig, batch_limit: Optional[int] = None) -> "AcquisitionSettings":
        return cls(execution.acqf_num_restarts, execution.acqf_raw_samples, execution.acqf_maxiter,
                   execution.acqf_batch_limit if batch_limit is None else batch_limit)


def _optimize(acq_func, bounds, batch_size, settings: AcquisitionSettings, device, sobol_engine):
    result = generate_next_candidates(acq_func=acq_func, bounds=bounds, batch_size=batch_size,
                                      num_restarts=settings.num_restarts, raw_samples=settings.raw_samples,
                                      maxiter=settings.maxiter, batch_limit=settings.batch_limit,
                                      device=device, sobol_engine=sobol_engine)
    candidates, _ = result
    return candidates.detach().cpu().tolist(), getattr(result, "metadata", None)


@dataclass
class ScalarizedProposal:
    """Weighted sum of scale-normalized objectives, one GP and qLogNEI."""

    config: MoboConfig
    device: torch.device
    scalar_weights: torch.Tensor
    bounds: torch.Tensor
    persist_model: PersistModel

    def propose(self, training, iteration, batch_size, sobol_engine) -> Proposal:
        device = self.device
        train_X = training.train_X.to(dtype=torch.double, device=device)
        scales = torch.tensor(ResultSchema.from_config(self.config).scales, dtype=torch.double, device=device)
        # Configured scales make objective weights dimensionless.
        scalar_Y = ((training.train_Y.to(dtype=torch.double, device=device) / scales)
                    * self.scalar_weights.to(dtype=torch.double, device=device)).sum(dim=-1, keepdim=True)
        bounds = self.bounds.to(device=device, dtype=torch.double)
        model = self.config.model
        gp = build_scalarized_gp_model(
            train_X=train_X, train_Y=scalar_Y, bounds=bounds, covar_type=model.covar_type,
            noise_mode=model.noise_mode, fixed_noise_val=model.fixed_noise_variance,
            relative_noise_ratio=model.relative_noise_ratio, min_noise_variance=model.min_noise_variance,
            device=device,
        )
        fit_gp_models(gp)
        self.persist_model(gp, iteration, training)
        if device.type == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        acq_func = qLogNoisyExpectedImprovement(model=gp, X_baseline=train_X, prune_baseline=True)
        settings = AcquisitionSettings.from_execution(self.config.execution,
                                                      batch_limit=1 if device.type == "cuda" else None)
        return _optimize(acq_func, bounds, batch_size, settings, device, sobol_engine)


@dataclass
class MultiObjectiveProposal:
    """Independent objective GPs (and constraint GPs when constrained) with an EHVI-family acquisition."""

    config: MoboConfig
    device: torch.device
    constrained: bool
    acq_type: str
    bounds: torch.Tensor
    persist_model: PersistModel

    def _surrogate(self, training):
        model = self.config.model
        pipeline = SurrogatePipeline(
            bounds=self.bounds, covar_type=model.covar_type, noise_mode=model.noise_mode,
            fixed_noise_val=model.fixed_noise_variance, relative_noise_ratio=model.relative_noise_ratio,
            min_noise_variance=model.min_noise_variance, objective_noise_variances=model.objective_noise_variances,
            constraints_config=self.config.constraints, device=self.device,
        )
        if not self.constrained:
            pipeline.fit(training.train_X, training.train_Y)
            return pipeline, pipeline.objective_model, None, None
        pipeline.fit(training.train_X, training.train_Y, training.constraints)
        if pipeline.constraint_model is None:
            return pipeline, pipeline.objective_model, None, None
        count = training.train_Y.shape[-1]
        model = ModelListGP(*pipeline.objective_model.models, *pipeline.constraint_model.models).to(
            device=self.device, dtype=torch.double)
        return (pipeline, model, get_botorch_constraint_functions(self.config, num_objectives=count),
                SliceObjective(num_objectives=count))

    def propose(self, training, iteration, batch_size, sobol_engine) -> Proposal:
        pipeline, gp_model, constraints, objective = self._surrogate(training)
        self.persist_model(pipeline, iteration, training, pipeline=True)
        execution = self.config.execution
        basis_Y = training.train_Y
        if execution.acquisition_reference_basis == "feasible" and bool(training.feasible.any()):
            basis_Y = training.train_Y[training.feasible]
        reference = compute_reference_point(basis_Y, offset_ratio=execution.acquisition_reference_offset,
                                            config=self.config)
        acq_func = build_acquisition_function(
            model=gp_model, train_X=training.train_X, train_Y=training.train_Y, ref_point=reference,
            train_feas_mask=training.feasible, acq_type=self.acq_type, constraints=constraints, objective=objective,
        )
        candidates, metadata = _optimize(acq_func, self.bounds, batch_size,
                                         AcquisitionSettings.from_execution(execution), self.device, sobol_engine)
        if metadata is not None:
            metadata = dict(metadata, acquisition_reference={
                "point_model": reference.detach().cpu().tolist(),
                "offset": execution.acquisition_reference_offset,
                "basis": execution.acquisition_reference_basis})
        return candidates, metadata


def make_strategy(optimization_mode: str, *, config: MoboConfig, device: torch.device, scalar_weights: torch.Tensor,
                  constrained: bool, acq_type: str, bounds: torch.Tensor, persist_model: PersistModel) -> ProposalStrategy:
    if optimization_mode == "scalarized_bo":
        return ScalarizedProposal(config, device, scalar_weights, bounds, persist_model)
    return MultiObjectiveProposal(config, device, constrained, acq_type, bounds, persist_model)
