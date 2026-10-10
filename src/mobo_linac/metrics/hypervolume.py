"""
Fixed Reporting Reference Point and Hypervolume Audit Module for mobo_linac.

Provides robust hypervolume calculation, reference point generation, and
HypervolumeTracker to ensure hypervolume curves are strictly comparable across
iterations and optimization runs.
"""

from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd
import torch
from mobo_linac.metrics.front import front_size, hypervolume

from mobo_linac.config import MoboConfig
from mobo_linac.objectives import transform_to_physical_space
from mobo_linac.result_schema import ResultSchema


def compute_reference_point(
    train_Y: torch.Tensor,
    offset_ratio: float = 0.10,
    default_ref_point: Optional[Sequence[float]] = None,
    config=None,
) -> torch.Tensor:
    """
    Computes a model-space reference point (maximization space) from initial candidate evaluations.

    For model space (where objectives are negated physical values), the reference point
    must be strictly below (worse than) observed model-space values.

    Args:
        train_Y: (N, D) PyTorch double tensor of model-space objectives.
        offset_ratio: Fraction of objective range to subtract as safety offset.
        default_ref_point: Explicit reference point; returned unchanged when supplied.
        config: MoboConfig or ResultSchema; required when no observation is available.

    Returns:
        1D PyTorch double tensor of reference point values in model space.
    """
    if default_ref_point is not None:
        return torch.tensor(default_ref_point, dtype=torch.double)

    if train_Y is None or train_Y.shape[0] == 0:
        # The configured schema defines the empty-data reference; there is no implicit layout.
        if config is None:
            raise ValueError("An empty objective tensor requires a configuration or explicit reference point.")
        return torch.tensor(ResultSchema.from_config(config).empty_reference, dtype=torch.double)

    train_Y_double = train_Y.to(dtype=torch.double)
    min_vals = train_Y_double.min(dim=0).values
    max_vals = train_Y_double.max(dim=0).values

    ranges = max_vals - min_vals
    epsilon = 1.0e-8
    offset = offset_ratio * (ranges + epsilon)

    ref_point = min_vals - offset
    return ref_point


def compute_hypervolume(
    train_Y: torch.Tensor,
    ref_point: Union[Sequence[float], torch.Tensor],
) -> float:
    """Exact hypervolume of model-space objectives w.r.t. a model-space reference point."""
    if train_Y is None:
        return 0.0
    return hypervolume(train_Y, ref_point)


def validate_reference_point_compatibility(
    ref_point_a: Union[Sequence[float], torch.Tensor],
    ref_point_b: Union[Sequence[float], torch.Tensor],
    atol: float = 1.0e-6,
    raise_on_incompatible: bool = True,
) -> bool:
    """
    Validates that two reference points are identical within a specified tolerance.

    Args:
        ref_point_a: First reference point.
        ref_point_b: Second reference point.
        atol: Absolute tolerance for floating-point comparison.
        raise_on_incompatible: If True, raise ValueError on mismatch.

    Returns:
        True if compatible, False otherwise.
    """
    a = np.asarray(ref_point_a, dtype=np.float64)
    b = np.asarray(ref_point_b, dtype=np.float64)

    if a.shape != b.shape:
        if raise_on_incompatible:
            raise ValueError(f"Reference point dimension mismatch: {a.shape} vs {b.shape}")
        return False

    is_compat = np.allclose(a, b, atol=atol)
    if not is_compat and raise_on_incompatible:
        raise ValueError(
            f"Incompatible reporting reference points! Run A: {a.tolist()}, Run B: {b.tolist()}"
        )
    return is_compat


class HypervolumeTracker:
    """
    Stateful hypervolume metric tracker using a FIXED reporting reference point.
    """

    def __init__(
        self,
        reporting_ref_point: Union[Sequence[float], torch.Tensor],
        config: MoboConfig,
    ):
        if not isinstance(reporting_ref_point, torch.Tensor):
            self._reporting_ref_point = torch.tensor(reporting_ref_point, dtype=torch.double)
        else:
            self._reporting_ref_point = reporting_ref_point.to(dtype=torch.double)

        self.schema = ResultSchema.from_config(config)
        if self._reporting_ref_point.shape != (len(self.schema.signs),):
            raise ValueError("Reporting reference must match configured objectives.")
        self.config = config
        self.history: List[Dict[str, Any]] = []

    @property
    def reporting_ref_point(self) -> torch.Tensor:
        """Fixed reporting reference point tensor in model space."""
        return self._reporting_ref_point

    def track_iteration(
        self,
        iteration: int,
        train_Y: torch.Tensor,
        train_feas_mask: torch.Tensor,
        acq_ref_point: Optional[Union[Sequence[float], torch.Tensor]] = None,
    ) -> Dict[str, Any]:
        """
        Track metrics for a single optimization iteration.

        Args:
            iteration: Iteration index.
            train_Y: (N, D) PyTorch tensor of all model-space objectives evaluated so far.
            train_feas_mask: (N,) PyTorch bool tensor indicating physical beam feasibility.
            acq_ref_point: Optional acquisition function reference point.

        Returns:
            Metric dictionary record.
        """
        num_valid = train_Y.shape[0] if train_Y is not None else 0
        num_feasible = int(train_feas_mask.sum().item()) if train_feas_mask is not None else 0

        all_hv = compute_hypervolume(train_Y, self._reporting_ref_point)
        if train_Y is not None and train_feas_mask is not None and num_feasible > 0:
            feasible_Y = train_Y[train_feas_mask]
            feas_hv = hypervolume(feasible_Y, self._reporting_ref_point)
            pareto_size = front_size(feasible_Y, self._reporting_ref_point)
        else:
            feas_hv, pareto_size = 0.0, 0

        if acq_ref_point is not None:
            if isinstance(acq_ref_point, torch.Tensor):
                acq_ref_list = acq_ref_point.detach().tolist()
            else:
                acq_ref_list = list(acq_ref_point)
        else:
            acq_ref_list = self._reporting_ref_point.tolist()

        record = {
            "iteration": iteration,
            "reporting_ref_point_model": self._reporting_ref_point.tolist(),
            "reporting_ref_point_physical": transform_to_physical_space(self._reporting_ref_point, self.schema).tolist(),
            "acquisition_ref_point_model": acq_ref_list,
            "all_point_hypervolume": all_hv,
            "feasible_hypervolume": feas_hv,
            "num_valid_points": num_valid,
            "num_feasible_points": num_feasible,
            "pareto_size": pareto_size,
        }

        self.history.append(record)
        return record

    # Reference points live in reporting_metadata.json; the CSV holds measurements only.
    CSV_COLUMNS = ["iteration", "all_point_hypervolume", "feasible_hypervolume",
                   "num_valid_points", "num_feasible_points", "pareto_size"]

    def to_dataframe(self) -> pd.DataFrame:
        """Returns hypervolume tracking history as a Pandas DataFrame."""
        return pd.DataFrame(self.history, columns=self.CSV_COLUMNS)
