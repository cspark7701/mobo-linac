"""
Canonical Objectives Module for mobo_linac.

Handles objective transformations between physical space (minimization: smaller is better)
and model space (maximization in BoTorch: larger/less negative is better).
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import torch

from mobo_linac.config import MoboConfig, load_config

DEFAULT_OBJECTIVE_NAMES = ["norm_emit_x", "norm_emit_y", "sigma_energy"]
EXPLICIT_OBJECTIVE_NAMES = ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]


def transform_to_model_space(
    physical_objectives: Union[Sequence[float], np.ndarray, torch.Tensor],
    config: Optional[MoboConfig] = None,
) -> torch.Tensor:
    """
    Transforms physical objective values (minimization) into model space (maximization for BoTorch).

    For physical minimization (smaller is better), multiplies by -1 so that higher values
    in model space correspond to better physical solutions.

    Args:
        physical_objectives: Tensor, array, or list of physical objective values.
        config: Optional MoboConfig instance.

    Returns:
        PyTorch double tensor of model-space objectives.
    """
    if config is not None:
        signs = torch.tensor([obj.model_sign for obj in config.objectives], dtype=torch.double)
    else:
        # Default: -1 for all 3 minimization objectives
        signs = torch.tensor([-1.0, -1.0, -1.0], dtype=torch.double)

    if not isinstance(physical_objectives, torch.Tensor):
        obj_tensor = torch.tensor(physical_objectives, dtype=torch.double)
    else:
        obj_tensor = physical_objectives.to(dtype=torch.double)

    return obj_tensor * signs


def transform_to_physical_space(
    model_objectives: Union[Sequence[float], np.ndarray, torch.Tensor],
    config: Optional[MoboConfig] = None,
) -> torch.Tensor:
    """
    Restores model-space objective values (maximization) back to physical values (minimization).

    Args:
        model_objectives: Tensor, array, or list of model-space objective values.
        config: Optional MoboConfig instance.

    Returns:
        PyTorch double tensor of physical objective values.
    """
    if config is not None:
        signs = torch.tensor([obj.model_sign for obj in config.objectives], dtype=torch.double)
    else:
        signs = torch.tensor([-1.0, -1.0, -1.0], dtype=torch.double)

    if not isinstance(model_objectives, torch.Tensor):
        obj_tensor = torch.tensor(model_objectives, dtype=torch.double)
    else:
        obj_tensor = model_objectives.to(dtype=torch.double)

    return obj_tensor * signs


def extract_physical_objectives(stats: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract physical objective values from ASTRA statistics dictionary with explicit names.

    Args:
        stats: Output stats dictionary from ASTRA simulation.

    Returns:
        Dictionary mapping objective names (both standard and explicit) to final physical values.
    """
    norm_emit_x = float(stats["norm_emit_x"][-1])
    norm_emit_y = float(stats["norm_emit_y"][-1])
    sigma_energy = float(stats["sigma_energy"][-1])

    return {
        "norm_emit_x": norm_emit_x,
        "norm_emit_y": norm_emit_y,
        "sigma_energy": sigma_energy,
        "norm_emit_x_m_rad": norm_emit_x,
        "norm_emit_y_m_rad": norm_emit_y,
        "sigma_energy_eV": sigma_energy,
    }
