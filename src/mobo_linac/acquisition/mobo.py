"""
Multi-Objective Bayesian Optimization Acquisition Functions.

Constructs and optimizes qLogNEHVI and qEHVI acquisition functions.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
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
from botorch.optim import optimize_acqf
from botorch.utils.multi_objective.box_decompositions.non_dominated import (
    FastNondominatedPartitioning,
)

from botorch.acquisition.multi_objective.objective import IdentityMCMultiOutputObjective
from mobo_linac.campaign_options import MULTIOBJECTIVE_ACQUISITIONS, Acquisition, decode_acquisition
from mobo_linac.metrics.hypervolume import compute_reference_point

from mobo_linac.utils import get_device, get_logger
from mobo_linac.utils.device import module_device

logger = get_logger(__name__)


class SliceObjective(IdentityMCMultiOutputObjective):
    """
    Slices the first num_objectives outputs from posterior samples for multi-objective evaluation.
    """

    def __init__(self, num_objectives: int):
        super().__init__()
        if type(num_objectives) is not int or num_objectives < 1:
            raise ValueError("num_objectives must be a positive integer.")
        self.num_objectives = num_objectives

    def forward(self, samples: torch.Tensor, X: Optional[torch.Tensor] = None) -> torch.Tensor:
        return samples[..., :self.num_objectives]


# Acquisition -> (BoTorch constructor, uses a noisy observed baseline).
_MULTIOBJECTIVE_FACTORY = {
    Acquisition.qLogEHVI: (qLogExpectedHypervolumeImprovement, False),
    Acquisition.qEHVI: (qExpectedHypervolumeImprovement, False),
    Acquisition.qLogNEHVI: (qLogNoisyExpectedHypervolumeImprovement, True),
    Acquisition.qNEHVI: (qNoisyExpectedHypervolumeImprovement, True),
}


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
    model_device = module_device(model, train_X.device)

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

    try:
        constructor, noisy = _MULTIOBJECTIVE_FACTORY[decode_acquisition(acq_type)]
    except (ValueError, KeyError):
        raise ValueError(f"Unsupported acquisition type: '{acq_type}'. "
                         f"Choose one of {list(MULTIOBJECTIVE_ACQUISITIONS)}.") from None
    if noisy:  # noisy variants integrate over the observed baseline
        kw_args.update(X_baseline=train_X_dbl, prune_baseline=True)
    else:
        kw_args["partitioning"] = FastNondominatedPartitioning(ref_point=ref_point_dbl, Y=feas_Y)
    acq_func = constructor(model=model, ref_point=ref_point_dbl, sampler=sampler, **kw_args)
    return acq_func



@dataclass
class ProposalResult:
    """Validated proposal and audit metadata."""

    candidates: torch.Tensor
    acq_values: torch.Tensor
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class FallbackPolicy:
    """Reduced budgets of the retry/CPU tiers and the CUDA batch limit (from ``execution``)."""

    retry_maxiter: int = 100
    retry_restart_divisor: int = 2
    retry_min_restarts: int = 2
    retry_raw_samples_divisor: int = 4
    retry_min_raw_samples: int = 32
    cuda_batch_limit: int = 1

    @classmethod
    def from_execution(cls, execution) -> "FallbackPolicy":
        return cls(execution.acqf_retry_maxiter, execution.acqf_retry_restart_divisor,
                   execution.acqf_retry_min_restarts, execution.acqf_retry_raw_samples_divisor,
                   execution.acqf_retry_min_raw_samples, execution.acqf_cuda_batch_limit)


def _validate_proposal(candidates, acq_values, bounds, batch_size):
    if (not isinstance(candidates, torch.Tensor) or candidates.shape != (batch_size, bounds.shape[1])
            or not torch.isfinite(candidates).all()):
        raise ValueError("Optimizer candidates must have finite (q, D) shape.")
    candidates = candidates.to(bounds)
    if (candidates < bounds[0]).any() or (candidates > bounds[1]).any():
        raise ValueError("Optimizer candidates exceed parameter bounds.")
    values = torch.as_tensor(acq_values, dtype=bounds.dtype, device=bounds.device)
    if not values.numel() or not torch.isfinite(values).all():
        raise ValueError("Optimizer acquisition values must be finite and nonempty.")
    return candidates, values


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
    sobol_engine: Optional[torch.quasirandom.SobolEngine] = None,
    fallback_seed: int = 0,
    policy: FallbackPolicy = FallbackPolicy(),
) -> ProposalResult:
    """Propose with primary, reduced-budget, isolated CPU, then seeded Sobol tiers.

    Metadata records every attempt and effective budget. Campaigns supply their owned
    Sobol engine; standalone calls use an explicit deterministic fallback seed. The
    supplied module is never moved for CPU fallback. Invalid optimizer output counts
    as a failed attempt. retry_on_failure=False propagates the primary failure.
    """
    for name, value in (("batch_size", batch_size), ("num_restarts", num_restarts),
                        ("raw_samples", raw_samples), ("maxiter", maxiter), ("batch_limit", batch_limit)):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer.")
    if (bounds.ndim != 2 or bounds.shape[0] != 2 or bounds.shape[1] < 1
            or not torch.isfinite(bounds).all() or not (bounds[1] > bounds[0]).all()):
        raise ValueError("Bounds must be a finite, strictly increasing (2, D) matrix.")
    if sobol_engine is not None and sobol_engine.dimension != bounds.shape[1]:
        raise ValueError("Fallback Sobol dimension does not match parameter bounds.")
    if type(fallback_seed) is not int or fallback_seed < 0 or fallback_seed >= 2**32:
        raise ValueError("fallback_seed must be an integer in [0, 2**32).")
    placement = {tensor.device for tensor in (*acq_func.parameters(), *acq_func.buffers())} if isinstance(acq_func, torch.nn.Module) else set()
    if len(placement) > 1:
        raise ValueError("Acquisition parameters/buffers must have one device before proposal.")
    original_device = next(iter(placement), bounds.device)
    target_device = get_device(device) if device is not None else original_device
    if placement and target_device != original_device:
        raise ValueError("Requested proposal device differs from acquisition placement; move the model at the campaign boundary.")
    bounds_dbl = bounds.to(device=target_device, dtype=torch.double)
    opt_options = {"batch_limit": policy.cuda_batch_limit if target_device.type == "cuda" else batch_limit,
                   "maxiter": maxiter}
    opt_options.update(options or {})
    for name in ("batch_limit", "maxiter"):
        if type(opt_options[name]) is not int or opt_options[name] < 1:
            raise ValueError(f"Optimizer option {name} must be a positive integer.")
    attempts = []
    start = sobol_engine.num_generated if sobol_engine is not None else 0
    reduced_options = {"batch_limit": 1, "maxiter": min(opt_options["maxiter"], policy.retry_maxiter)}
    reduced_restarts = max(policy.retry_min_restarts, num_restarts // policy.retry_restart_divisor)
    reduced_raw = max(policy.retry_min_raw_samples, raw_samples // policy.retry_raw_samples_divisor)
    tiers = [("primary", target_device, num_restarts, raw_samples, opt_options),
             ("retry", target_device, reduced_restarts, reduced_raw, reduced_options),
             ("cpu", torch.device("cpu"), reduced_restarts, reduced_raw, reduced_options)]
    for tier, attempt_device, restarts, samples, budget in tiers:
        record = {"tier": tier, "device": str(attempt_device), "num_restarts": restarts,
                  "raw_samples": samples, "options": deepcopy(budget)}
        try:
            # deepcopy may itself fail (e.g. unsupported custom caches); record and
            # proceed to the owned Sobol stream without mutating the supplied model.
            module = deepcopy(acq_func).to("cpu") if tier == "cpu" else acq_func
            attempt_bounds = bounds_dbl.to(attempt_device)
            candidates, values = optimize_acqf(acq_function=module, bounds=attempt_bounds,
                                               q=batch_size, num_restarts=restarts,
                                               raw_samples=samples, options=budget)
            candidates, values = _validate_proposal(candidates, values, attempt_bounds, batch_size)
            record["status"] = "success"
            attempts.append(record)
            logger.debug(f"Acquisition proposal succeeded via {tier} on {attempt_device}.")
            return ProposalResult(candidates.to(bounds_dbl), values.to(bounds_dbl), {
                "method": tier, "device": str(target_device), "optimizer_device": str(attempt_device),
                "attempts": attempts, "fallback_reason": attempts[-2].get("error") if len(attempts) > 1 else None,
                "sobol": {"start": start, "end": start}, "fallback_policy": asdict(policy),
            })
        except Exception as error:
            record.update(status="failed", error=f"{type(error).__name__}: {error}")
            attempts.append(record)
            if not retry_on_failure:
                raise
            logger.warning(f"Acquisition {tier} failed on {attempt_device}: {error}")
    if sobol_engine is None:
        sobol_engine = torch.quasirandom.SobolEngine(bounds.shape[1], scramble=True, seed=fallback_seed)
    samples = sobol_engine.draw(batch_size).to(bounds_dbl)
    candidates = bounds_dbl[0] + (bounds_dbl[1] - bounds_dbl[0]) * samples
    values = torch.zeros(batch_size, dtype=bounds_dbl.dtype, device=bounds_dbl.device)
    candidates, values = _validate_proposal(candidates, values, bounds_dbl, batch_size)
    logger.warning("Acquisition optimizers exhausted; using seeded Sobol exploration.")
    return ProposalResult(candidates, values, {
        "method": "sobol", "device": str(target_device), "optimizer_device": None,
        "attempts": attempts, "fallback_reason": attempts[-1]["error"],
        "sobol": {"seed": sobol_engine.seed, "start": start, "end": sobol_engine.num_generated},
        "fallback_policy": asdict(policy),
    })
