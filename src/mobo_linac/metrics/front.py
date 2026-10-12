"""The single Pareto-front, hypervolume and normalization implementation.

All values are in BoTorch model space (maximization). A point contributes to a
hypervolume only when it strictly dominates the reference point in every objective.
"""

from typing import Sequence, Union

import torch
from botorch.utils.multi_objective.hypervolume import Hypervolume
from botorch.utils.multi_objective.pareto import is_non_dominated

TensorLike = Union[Sequence[Sequence[float]], torch.Tensor]


def as_double(values, like: torch.Tensor = None) -> torch.Tensor:
    if like is not None:
        return torch.as_tensor(values, dtype=like.dtype, device=like.device)
    if isinstance(values, torch.Tensor):
        return values if values.is_floating_point() else values.to(dtype=torch.double)
    return torch.as_tensor(values, dtype=torch.double)


def normalize(values: TensorLike, scales: Sequence[float]) -> torch.Tensor:
    """Divide each objective by its configured reporting scale, preserving placement and dtype."""
    tensor = as_double(values)
    return tensor / torch.as_tensor(scales, dtype=tensor.dtype, device=tensor.device)


def pareto_mask(values: TensorLike) -> torch.Tensor:
    """Boolean mask of non-dominated rows (maximization)."""
    tensor = as_double(values)
    if tensor.shape[0] == 0:
        return torch.zeros(0, dtype=torch.bool, device=tensor.device)
    return is_non_dominated(tensor)


def dominating_front(values: TensorLike, reference: TensorLike) -> torch.Tensor:
    """Non-dominated rows that strictly dominate the reference point."""
    tensor = as_double(values)
    ref = as_double(reference, like=tensor)
    if tensor.shape[0] == 0:
        return tensor
    better = tensor[(tensor > ref).all(dim=-1)]
    return better[pareto_mask(better)] if better.shape[0] else better


def hypervolume(values: TensorLike, reference: TensorLike) -> float:
    """Exact hypervolume dominated by ``values`` relative to ``reference`` (non-negative)."""
    tensor = as_double(values)
    ref = as_double(reference, like=tensor)
    front = dominating_front(tensor, ref)
    if front.shape[0] == 0:
        return 0.0
    return max(0.0, float(Hypervolume(ref_point=ref).compute(front)))


def front_size(values: TensorLike, reference: TensorLike) -> int:
    """Number of non-dominated rows that strictly dominate the reference point."""
    return int(dominating_front(values, reference).shape[0])
