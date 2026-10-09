"""
Canonical Objectives Module for mobo_linac.

Handles objective transformations between physical space and BoTorch model space
(maximization), using each configured objective's direction.
"""

from typing import Any, Dict

import torch

from mobo_linac.result_schema import ResultSchema


def transform_to_model_space(physical_objectives, config) -> torch.Tensor:
    """Transform physical objective values into model space (maximization for BoTorch).

    ``config`` is a MoboConfig or ResultSchema; minimized objectives are negated.
    """
    return ResultSchema.from_config(config).transform(physical_objectives)


def transform_to_physical_space(model_objectives, config) -> torch.Tensor:
    """Restore physical values with each configured objective's direction."""
    return ResultSchema.from_config(config).transform(model_objectives)


def extract_physical_objectives(stats: Dict[str, Any], config) -> Dict[str, float]:
    """Extract final observed statistics using configured names and aliases."""
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
