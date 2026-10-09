"""Acquisition names, optimization modes and campaign option helpers.

This leaf module is the single list of supported acquisition functions; the CLI,
configuration schema, checkpoint validation and acquisition factory all use it.
"""

from dataclasses import asdict
from enum import Enum

import torch


class Acquisition(str, Enum):
    qLogNEHVI = "qLogNEHVI"
    qLogEHVI = "qLogEHVI"
    qEHVI = "qEHVI"
    qNEHVI = "qNEHVI"
    qLogNEI = "qLogNEI"  # single-objective acquisition of scalarized BO


MULTIOBJECTIVE_ACQUISITIONS = tuple(item.value for item in Acquisition if item is not Acquisition.qLogNEI)
OPTIMIZATION_MODES = ("scalarized_bo", "constrained_mobo", "unconstrained_mobo")
# Checkpoints of scalarized campaigns record this alias of qLogNEI.
_LEGACY_ALIASES = {"scalarized_qLogNEI": Acquisition.qLogNEI}


def decode_acquisition(name) -> Acquisition:
    """Resolve an acquisition name (or legacy checkpoint alias); unknown names raise ValueError."""
    if isinstance(name, Acquisition):
        return name
    if name in _LEGACY_ALIASES:
        return _LEGACY_ALIASES[name]
    try:
        return Acquisition(name)
    except ValueError:
        raise ValueError(f"Unsupported acquisition: {name}") from None


def normalize_scalar_weights(weights, objective_count):
    """Validate dimensions/finite weights and normalize without sum overflow."""
    if type(objective_count) is not int or objective_count < 1:
        raise ValueError("Scalar weights require at least one objective.")
    if weights is None:
        return torch.full((objective_count,), 1.0 / objective_count, dtype=torch.double)
    if any(isinstance(value, bool) for value in weights):
        raise ValueError("Scalar weights must be numeric, not boolean.")
    values = torch.as_tensor(weights, dtype=torch.double)
    if (values.shape != (objective_count,) or not torch.isfinite(values).all()
            or (values < 0).any() or not (values > 0).any()):
        raise ValueError("Scalar weights must match objectives and be finite, nonnegative, with positive sum.")
    scaled = values / values.max()
    return scaled / scaled.sum()


def resolve_campaign_options(config, **requested):
    """Fill omitted (None) campaign options from the configuration, the single default source."""
    defaults = asdict(config.campaign)
    resolved = {name: requested.get(name) if requested.get(name) is not None else value
                for name, value in defaults.items()}
    workers = requested.get("num_workers")
    resolved["num_workers"] = workers if workers is not None else config.execution.max_workers
    return resolved


def validate_campaign_options(*, num_initial_samples, num_batches, batch_size, num_workers=None,
                              seed=42, acq_type="qLogNEHVI", optimization_mode="unconstrained_mobo",
                              total_eval_budget=None):
    """Validate orchestration options before any campaign side effects."""
    for name, value, minimum in (("num_initial_samples", num_initial_samples, 1),
                                 ("num_batches", num_batches, 0), ("batch_size", batch_size, 1),
                                 ("seed", seed, 0)):
        if type(value) is not int or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}.")
    if seed >= 2**32:
        raise ValueError("seed must be less than 2**32.")
    if num_workers is not None and (type(num_workers) is not int or num_workers < 1):
        raise ValueError("num_workers must be a positive integer.")
    if total_eval_budget is not None and (type(total_eval_budget) is not int or total_eval_budget <= num_initial_samples):
        raise ValueError("total_eval_budget must exceed positive initial samples.")
    if optimization_mode not in OPTIMIZATION_MODES:
        raise ValueError(f"Unsupported optimization_mode: {optimization_mode}")
    acquisition = decode_acquisition(acq_type)
    if optimization_mode == "scalarized_bo" and acquisition is not Acquisition.qLogNEI:
        raise ValueError("scalarized_bo uses qLogNEI; multi-objective acquisitions are unsupported.")
    if acquisition is Acquisition.qLogNEI and optimization_mode != "scalarized_bo":
        raise ValueError("qLogNEI requires scalarized_bo optimization mode.")
