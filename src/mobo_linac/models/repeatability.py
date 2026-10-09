"""
Repeatability and Measured Noise Variance Utility for Linac Optimizations.

Provides tools for evaluating observation noise variance from repeated ASTRA evaluations
or sensitivity profiling around a nominal candidate vector.
"""

from typing import Dict, List, Sequence, Union
import numpy as np
import torch

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.result_schema import ResultSchema


def compute_measured_noise_variance(
    results: List[EvaluationResult],
    config,
    min_variance: float = 1.0e-8,
) -> Dict[str, float]:
    """
    Computes measured variance across configured objective columns from repeated runs.

    Args:
        results: EvaluationResult instances evaluated at identical or near-identical inputs.
        config: MoboConfig or ResultSchema defining the objective order and names.
        min_variance: Floor for calculated variance.

    Returns:
        Dict mapping configured physical objective column -> measured variance value.
    """
    schema = ResultSchema.from_config(config)
    valid_objs = [r.objectives_physical for r in results if r.simulation_valid and r.objectives_physical]
    if len(valid_objs) < 2:
        return {name: min_variance for name in schema.physical_columns}

    variances = np.var(np.array(valid_objs), axis=0, ddof=1)
    return {name: float(max(value, min_variance)) for name, value in zip(schema.physical_columns, variances)}


def create_measured_yvar_tensor(
    num_samples: int,
    variances: Union[Sequence[float], Dict[str, float]],
    config=None,
) -> torch.Tensor:
    """
    Creates an (N, M) PyTorch double tensor of observation variances.

    Args:
        num_samples: Number of sample evaluations (N).
        variances: Ordered variances, or a mapping keyed by configured objective columns
            (which then requires ``config``).

    Returns:
        (N, M) PyTorch double tensor.
    """
    if isinstance(variances, dict):
        if config is None:
            raise TypeError("A configuration is required to order variance mappings.")
        columns = ResultSchema.from_config(config).physical_columns
        missing = [name for name in columns if name not in variances]
        if missing:
            raise ValueError(f"Missing measured variances: {missing}")
        var_list = [variances[name] for name in columns]
    else:
        var_list = list(variances)

    var_tensor = torch.tensor(var_list, dtype=torch.double).unsqueeze(0)
    return var_tensor.repeat(num_samples, 1)
