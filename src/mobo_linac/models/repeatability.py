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
    min_relative_std: float = 1.0e-6,
) -> Dict[str, float]:
    """
    Measured variance of each configured objective from repeated evaluations.

    The variance floor is relative to each objective's reporting scale,
    ``(min_relative_std * scale)**2``, so it is negligible for objectives of any
    magnitude (an absolute floor of 1e-8 would exceed the squared emittance itself).

    Args:
        results: EvaluationResult instances evaluated at identical or near-identical inputs.
        config: MoboConfig or ResultSchema defining the objective order, names and scales.
        min_relative_std: Floor standard deviation as a fraction of the reporting scale.

    Returns:
        Dict mapping configured physical objective column -> measured variance value.
    """
    schema = ResultSchema.from_config(config)
    floors = [(min_relative_std * scale) ** 2 for scale in schema.scales]
    valid_objs = [r.objectives_physical for r in results if r.simulation_valid and r.objectives_physical]
    if len(valid_objs) < 2:
        return dict(zip(schema.physical_columns, floors))

    variances = np.var(np.array(valid_objs), axis=0, ddof=1)
    return {name: float(max(value, floor)) for name, value, floor in zip(schema.physical_columns, variances, floors)}


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
