"""
Multi-Objective Bayesian Optimization Acquisition Functions.

Constructs and optimizes qLogNEHVI and qEHVI acquisition functions.
"""

from typing import Any, Dict, Optional, Tuple, Union
import torch
from botorch.acquisition.multi_objective.logei import (
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

from mobo_linac.metrics.hypervolume import compute_reference_point


def build_acquisition_function(
    model: Any,
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    ref_point: torch.Tensor,
    train_feas_mask: Optional[torch.Tensor] = None,
    acq_type: str = "qLogNEHVI",
    sampler: Optional[Any] = None,
) -> Any:
    """
    Constructs a multi-objective acquisition function (qLogNEHVI or qEHVI).

    Args:
        model: Fitted ModelListGP surrogate model.
        train_X: (N, D) PyTorch double tensor of design variables.
        train_Y: (N, M) PyTorch double tensor of model-space objectives.
        ref_point: 1D PyTorch double tensor reference point in model space.
        train_feas_mask: Optional boolean feasibility mask.
        acq_type: Acquisition function type ('qLogNEHVI' or 'qEHVI').
        sampler: Optional Monte Carlo sampler.

    Returns:
        Instantiated acquisition function.
    """
    ref_point_dbl = ref_point.to(dtype=torch.double)
    train_X_dbl = train_X.to(dtype=torch.double)
    train_Y_dbl = train_Y.to(dtype=torch.double)

    if acq_type == "qLogNEHVI":
        acq_func = qLogNoisyExpectedHypervolumeImprovement(
            model=model,
            ref_point=ref_point_dbl,
            X_baseline=train_X_dbl,
            prune_baseline=True,
            sampler=sampler,
        )
    elif acq_type == "qEHVI":
        # Partition non-dominated set for qEHVI
        feasible_mask = train_feas_mask if train_feas_mask is not None else torch.ones(train_Y_dbl.shape[0], dtype=torch.bool)
        if feasible_mask.sum().item() > 0:
            feas_Y = train_Y_dbl[feasible_mask]
            partitioning = FastNondominatedPartitioning(ref_point=ref_point_dbl, Y=feas_Y)
        else:
            partitioning = FastNondominatedPartitioning(ref_point=ref_point_dbl, Y=train_Y_dbl)

        acq_func = qExpectedHypervolumeImprovement(
            model=model,
            ref_point=ref_point_dbl,
            partitioning=partitioning,
            sampler=sampler,
        )
    else:
        raise ValueError(f"Unsupported acquisition type: '{acq_type}'. Choose 'qLogNEHVI' or 'qEHVI'.")

    return acq_func


def generate_next_candidates(
    acq_func: Any,
    bounds: torch.Tensor,
    batch_size: int = 8,
    num_restarts: int = 20,
    raw_samples: int = 1024,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Optimizes the acquisition function over parameter bounds to generate next candidate batch.

    Args:
        acq_func: Instantiated acquisition function.
        bounds: (2, D) PyTorch double tensor of design variable bounds.
        batch_size: Number of candidates q to suggest.
        num_restarts: Number of optimization restarts.
        raw_samples: Number of raw samples for initialization heuristic.

    Returns:
        Tuple of (candidates_tensor, acq_values_tensor).
    """
    bounds_dbl = bounds.to(dtype=torch.double)

    candidates, acq_values = optimize_acqf(
        acq_function=acq_func,
        bounds=bounds_dbl,
        q=batch_size,
        num_restarts=num_restarts,
        raw_samples=raw_samples,
        options={"batch_limit": 5, "maxiter": 200},
    )
    return candidates, acq_values
