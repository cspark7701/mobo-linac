"""
Repeatability and Measured Noise Variance Utility for Linac Optimizations (Task 07).

Provides tools for evaluating observation noise variance from repeated ASTRA evaluations
or sensitivity profiling around a nominal candidate vector.
"""

from typing import Dict, List, Optional, Sequence, Union
import numpy as np
import torch

from mobo_linac.evaluation import EvaluationResult


def compute_measured_noise_variance(
    results: List[EvaluationResult],
    min_variance: float = 1.0e-8,
) -> Dict[str, float]:
    """
    Computes measured variance across objective columns from repeated evaluation runs.

    Args:
        results: List of EvaluationResult instances evaluated at identical or near-identical inputs.
        min_variance: Floor for calculated variance.

    Returns:
        Dict mapping objective name -> measured variance value.
    """
    valid_objs = [r.objectives_physical for r in results if r.simulation_valid and r.objectives_physical]
    if len(valid_objs) < 2:
        return {
            "norm_emit_x_m_rad": min_variance,
            "norm_emit_y_m_rad": min_variance,
            "sigma_energy_eV": min_variance,
        }

    arr = np.array(valid_objs)
    variances = np.var(arr, axis=0, ddof=1)

    return {
        "norm_emit_x_m_rad": float(max(variances[0], min_variance)),
        "norm_emit_y_m_rad": float(max(variances[1], min_variance)),
        "sigma_energy_eV": float(max(variances[2], min_variance)),
    }


def create_measured_yvar_tensor(
    num_samples: int,
    variances: Union[Sequence[float], Dict[str, float]],
) -> torch.Tensor:
    """
    Creates an (N, M) PyTorch double tensor of observation variances.

    Args:
        num_samples: Number of sample evaluations (N).
        variances: List or dict of objective variances.

    Returns:
        (N, M) PyTorch double tensor.
    """
    if isinstance(variances, dict):
        var_list = [
            variances.get("norm_emit_x_m_rad", 1e-8),
            variances.get("norm_emit_y_m_rad", 1e-8),
            variances.get("sigma_energy_eV", 1e-8),
        ]
    else:
        var_list = list(variances)

    var_tensor = torch.tensor(var_list, dtype=torch.double).unsqueeze(0)
    return var_tensor.repeat(num_samples, 1)
