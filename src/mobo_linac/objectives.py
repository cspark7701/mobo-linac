"""
Canonical Objectives Module for mobo_linac.

Handles objective transformations between physical space (minimization: smaller is better)
and model space (maximization in BoTorch: larger/less negative is better).
"""

from typing import Any, Dict, Optional, Sequence, Union
import numpy as np
import torch

from mobo_linac.config import MoboConfig

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
    from mobo_linac.result_schema import ResultSchema
    return ResultSchema.from_config(config).transform(physical_objectives)


def transform_to_physical_space(model_objectives, config=None) -> torch.Tensor:
    """Restore physical values with each configured objective's direction."""
    from mobo_linac.result_schema import ResultSchema
    return ResultSchema.from_config(config).transform(model_objectives)


def extract_physical_objectives(stats: Dict[str, Any], config=None) -> Dict[str, float]:
    """Extract final observed statistics using configured names and aliases."""
    from mobo_linac.result_schema import ResultSchema
    schema = ResultSchema.from_config(config)
    final = {}
    for names in schema.objective_aliases:
        for name in names:
            if name in stats:
                values = stats[name]
                try:
                    final[name] = values[-1] if len(values) else float("nan")
                except (TypeError, KeyError, IndexError):
                    final[name] = float("nan")
    ordered = schema.extract(final)
    if ordered is None:
        raise KeyError("Required objective statistics missing")
    return {name: value for names, value in zip(schema.objective_aliases, ordered) for name in names}
