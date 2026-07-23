"""
Fixed Reporting Reference Point and Hypervolume Audit Module for mobo_linac.

Provides robust hypervolume calculation, reference point generation, and
HypervolumeTracker to ensure hypervolume curves are strictly comparable across
iterations and optimization runs.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd
import torch
from botorch.utils.multi_objective.hypervolume import Hypervolume
from botorch.utils.multi_objective.pareto import is_non_dominated

from mobo_linac.config import MoboConfig, load_config


def compute_reference_point(
    train_Y: torch.Tensor,
    offset_ratio: float = 0.10,
    default_ref_point: Optional[Sequence[float]] = None,
) -> torch.Tensor:
    """
    Computes a model-space reference point (maximization space) from initial candidate evaluations.

    For model space (where objectives are negated physical values), the reference point
    must be strictly below (worse than) observed model-space values.

    Args:
        train_Y: (N, D) PyTorch double tensor of model-space objectives.
        offset_ratio: Fraction of objective range to subtract as safety offset.
        default_ref_point: Fallback reference point if train_Y is empty.

    Returns:
        1D PyTorch double tensor of reference point values in model space.
    """
    if default_ref_point is not None:
        return torch.tensor(default_ref_point, dtype=torch.double)

    if train_Y is None or train_Y.shape[0] == 0:
        # Default fallback for 3D linac objectives (-emit_x, -emit_y, -sigma_energy)
        return torch.tensor([-1.0e-4, -1.0e-4, -1.0e7], dtype=torch.double)

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
    """
    Computes exact non-dominated hypervolume w.r.t a specified model-space reference point.

    Args:
        train_Y: (N, D) PyTorch double tensor of model-space objectives.
        ref_point: Reference point tensor or sequence in model space.

    Returns:
        Non-negative float hypervolume value.
    """
    if not isinstance(ref_point, torch.Tensor):
        ref_tensor = torch.tensor(ref_point, dtype=torch.double)
    else:
        ref_tensor = ref_point.to(dtype=torch.double)

    if train_Y is None or train_Y.shape[0] == 0:
        return 0.0

    Y_double = train_Y.to(dtype=torch.double)

    # Filter candidates that strictly dominate the reference point in model space (Y > ref_point)
    strictly_better = (Y_double > ref_tensor).all(dim=-1)
    Y_valid = Y_double[strictly_better]

    if Y_valid.shape[0] == 0:
        return 0.0

    pareto_mask = is_non_dominated(Y_valid)
    pareto_Y = Y_valid[pareto_mask]

    hv_calc = Hypervolume(ref_point=ref_tensor)
    volume = hv_calc.compute(pareto_Y)
    return max(0.0, float(volume))


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
        config: Optional[MoboConfig] = None,
    ):
        if not isinstance(reporting_ref_point, torch.Tensor):
            self._reporting_ref_point = torch.tensor(reporting_ref_point, dtype=torch.double)
        else:
            self._reporting_ref_point = reporting_ref_point.to(dtype=torch.double)

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

        # Compute all-point hypervolume (valid simulations)
        all_hv = compute_hypervolume(train_Y, self._reporting_ref_point)

        # Compute feasible-only hypervolume
        pareto_size = 0
        if train_Y is not None and train_feas_mask is not None and num_feasible > 0:
            feasible_Y = train_Y[train_feas_mask]
            feas_hv = compute_hypervolume(feasible_Y, self._reporting_ref_point)

            # Compute Pareto front size on feasible set
            strictly_better = (feasible_Y > self._reporting_ref_point).all(dim=-1)
            feas_valid = feasible_Y[strictly_better]
            if feas_valid.shape[0] > 0:
                pareto_mask = is_non_dominated(feas_valid)
                pareto_size = int(pareto_mask.sum().item())
        else:
            feas_hv = 0.0

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
            "reporting_ref_point_physical": (-self._reporting_ref_point).tolist(),
            "acquisition_ref_point_model": acq_ref_list,
            "all_point_hypervolume": all_hv,
            "feasible_hypervolume": feas_hv,
            "num_valid_points": num_valid,
            "num_feasible_points": num_feasible,
            "pareto_size": pareto_size,
        }

        self.history.append(record)
        return record

    def to_dataframe(self) -> pd.DataFrame:
        """Returns hypervolume tracking history as a Pandas DataFrame."""
        return pd.DataFrame(self.history)

    def save_csv(self, output_path: Union[str, Path]) -> Path:
        """Saves hypervolume history to CSV file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = self.to_dataframe()
        df.to_csv(path, index=False)
        return path

    @classmethod
    def load_history(cls, history_path: Union[str, Path]) -> pd.DataFrame:
        """Loads hypervolume tracking history from CSV."""
        path = Path(history_path)
        if not path.exists():
            raise FileNotFoundError(f"Hypervolume history file not found: {path}")
        return pd.read_csv(path)
