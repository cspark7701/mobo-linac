"""
Multi-Objective Bayesian Optimization Acquisition Functions.

Constructs and optimizes qLogNEHVI and qEHVI acquisition functions.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
from botorch.acquisition.multi_objective.logei import (
    qLogExpectedHypervolumeImprovement,
    qLogNoisyExpectedHypervolumeImprovement,
)
from botorch.acquisition.multi_objective.monte_carlo import (
    qExpectedHypervolumeImprovement,
    qNoisyExpectedHypervolumeImprovement,
)
from botorch.models import ModelListGP
from botorch.optim import optimize_acqf
from botorch.utils.multi_objective.box_decompositions.non_dominated import (
    FastNondominatedPartitioning,
)

from botorch.acquisition.multi_objective.objective import IdentityMCMultiOutputObjective
from mobo_linac.metrics.hypervolume import compute_reference_point

logger = logging.getLogger(__name__)


class SliceObjective(IdentityMCMultiOutputObjective):
    """
    Slices the first num_objectives outputs from posterior samples for multi-objective evaluation.
    """

    def __init__(self, num_objectives: int = 3):
        super().__init__()
        self.num_objectives = num_objectives

    def forward(self, samples: torch.Tensor, X: Optional[torch.Tensor] = None) -> torch.Tensor:
        return samples[..., :self.num_objectives]


def build_acquisition_function(
    model: Any,
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    ref_point: torch.Tensor,
    train_feas_mask: Optional[torch.Tensor] = None,
    acq_type: str = "qLogNEHVI",
    sampler: Optional[Any] = None,
    constraints: Optional[List[Any]] = None,
    objective: Optional[Any] = None,
) -> Any:
    """
    Constructs a multi-objective acquisition function (qLogNEHVI, qLogEHVI, qEHVI, or qNEHVI).

    Args:
        model: Fitted ModelListGP surrogate model.
        train_X: (N, D) PyTorch double tensor of design variables.
        train_Y: (N, M) PyTorch double tensor of model-space objectives.
        ref_point: 1D PyTorch double tensor reference point in model space.
        train_feas_mask: Optional boolean feasibility mask.
        acq_type: Acquisition function type ('qLogNEHVI', 'qLogEHVI', 'qEHVI', 'qNEHVI').
        sampler: Optional Monte Carlo sampler.
        constraints: Optional list of BoTorch tensor constraint functions c_i(Y) <= 0.
        objective: Optional MCMultiOutputObjective for slicing model outputs.

    Returns:
        Instantiated acquisition function.
    """
    try:
        model_device = next(model.parameters()).device
    except (StopIteration, AttributeError):
        model_device = train_X.device

    ref_point_dbl = ref_point.to(device=model_device, dtype=torch.double)
    train_X_dbl = train_X.to(device=model_device, dtype=torch.double)
    train_Y_dbl = train_Y.to(device=model_device, dtype=torch.double)

    feasible_mask = train_feas_mask if train_feas_mask is not None else torch.ones(train_Y_dbl.shape[0], dtype=torch.bool, device=model_device)
    if feasible_mask.device != model_device:
        feasible_mask = feasible_mask.to(device=model_device)
    if feasible_mask.sum().item() > 0:
        feas_Y = train_Y_dbl[feasible_mask]
    else:
        feas_Y = train_Y_dbl

    kw_args = {}
    if constraints is not None:
        kw_args["constraints"] = constraints
    if objective is not None:
        kw_args["objective"] = objective

    if acq_type in ("qLogEHVI", "qEHVI"):
        partitioning = FastNondominatedPartitioning(ref_point=ref_point_dbl, Y=feas_Y)
        if acq_type == "qLogEHVI":
            acq_func = qLogExpectedHypervolumeImprovement(
                model=model,
                ref_point=ref_point_dbl,
                partitioning=partitioning,
                sampler=sampler,
                **kw_args,
            )
        else:
            acq_func = qExpectedHypervolumeImprovement(
                model=model,
                ref_point=ref_point_dbl,
                partitioning=partitioning,
                sampler=sampler,
                **kw_args,
            )
    elif acq_type in ("qLogNEHVI", "qNEHVI"):
        if acq_type == "qLogNEHVI":
            acq_func = qLogNoisyExpectedHypervolumeImprovement(
                model=model,
                ref_point=ref_point_dbl,
                X_baseline=train_X_dbl,
                prune_baseline=True,
                sampler=sampler,
                **kw_args,
            )
        else:
            acq_func = qNoisyExpectedHypervolumeImprovement(
                model=model,
                ref_point=ref_point_dbl,
                X_baseline=train_X_dbl,
                prune_baseline=True,
                sampler=sampler,
                **kw_args,
            )
    else:
        raise ValueError(f"Unsupported acquisition type: '{acq_type}'. Choose 'qLogNEHVI', 'qLogEHVI', 'qEHVI', or 'qNEHVI'.")

    return acq_func



def generate_next_candidates(
    acq_func: Any,
    bounds: torch.Tensor,
    batch_size: int = 8,
    num_restarts: int = 20,
    raw_samples: int = 1024,
    maxiter: int = 200,
    batch_limit: int = 5,
    options: Optional[Dict[str, Any]] = None,
    device: Optional[Union[torch.device, str]] = None,
    retry_on_failure: bool = True,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Optimizes the acquisition function over parameter bounds to generate next candidate batch.
    Includes adaptive retry and fallback mechanisms against numerical convergence issues.

    Args:
        acq_func: Instantiated acquisition function.
        bounds: (2, D) PyTorch double tensor of design variable bounds.
        batch_size: Number of candidates q to suggest.
        num_restarts: Number of optimization restarts.
        raw_samples: Number of raw samples for initialization heuristic.
        maxiter: Maximum L-BFGS optimization iterations per restart.
        batch_limit: Batch limit for parallel restart optimization in BoTorch.
        options: Optional dict of extra optimizer options overriding maxiter/batch_limit.
        device: Optional torch device (e.g. 'cpu' or 'cuda').
        retry_on_failure: Whether to retry with reduced budget or fallback to Sobol sampling.

    Returns:
        Tuple of (candidates_tensor, acq_values_tensor).
    """
    if device is not None:
        target_device = torch.device(device) if isinstance(device, str) else device
    else:
        try:
            if hasattr(acq_func, "model"):
                target_device = next(acq_func.model.parameters()).device
            else:
                target_device = bounds.device
        except Exception:
            target_device = bounds.device

    bounds_dbl = bounds.to(device=target_device, dtype=torch.double)

    opt_options: Dict[str, Any] = {"batch_limit": batch_limit, "maxiter": maxiter}
    if options:
        opt_options.update(options)

    try:
        candidates, acq_values = optimize_acqf(
            acq_function=acq_func,
            bounds=bounds_dbl,
            q=batch_size,
            num_restarts=num_restarts,
            raw_samples=raw_samples,
            options=opt_options,
        )
        return candidates, acq_values
    except Exception as e:
        if not retry_on_failure:
            raise

        logger.warning(
            f"Primary acquisition optimization failed with error: {e}. Retrying with reduced restart budget..."
        )

        reduced_restarts = max(2, num_restarts // 2)
        reduced_raw = max(32, raw_samples // 2)
        reduced_batch_limit = max(1, batch_limit // 2)
        reduced_options = {"batch_limit": reduced_batch_limit, "maxiter": min(maxiter, 100)}

        try:
            candidates, acq_values = optimize_acqf(
                acq_function=acq_func,
                bounds=bounds_dbl,
                q=batch_size,
                num_restarts=reduced_restarts,
                raw_samples=reduced_raw,
                options=reduced_options,
            )
            logger.info("Acquisition optimization succeeded with reduced restart budget.")
            return candidates, acq_values
        except Exception as retry_err:
            logger.error(
                f"Acquisition retry also failed: {retry_err}. Falling back to quasi-random Sobol exploration."
            )
            dim = bounds_dbl.shape[1]
            sobol_engine = torch.quasirandom.SobolEngine(dimension=dim, scramble=True)
            samples = sobol_engine.draw(batch_size).to(device=target_device, dtype=torch.double)
            candidates = bounds_dbl[0] + (bounds_dbl[1] - bounds_dbl[0]) * samples
            acq_values = torch.zeros(batch_size, dtype=torch.double, device=target_device)
            return candidates, acq_values
