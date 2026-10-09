"""Shared CPU/CUDA resolution for campaigns and standalone tensor operations."""

from typing import Optional, Union
import torch
from mobo_linac.utils.logger import get_logger

logger = get_logger(__name__)


def get_device(device_str: Optional[Union[str, torch.device]] = None, *, allow_cpu_fallback: bool = True) -> torch.device:
    """Resolve auto/CPU/CUDA consistently; explicit unavailable CUDA can fall back.

    CUDA indices are validated when CUDA is available. Resume uses strict resolution
    after checking checkpoint placement, so it never silently changes devices.
    """
    automatic = device_str is None or (isinstance(device_str, str) and device_str.strip().lower() in ("auto", ""))
    if automatic:
        return torch.device("cuda", torch.cuda.current_device()) if torch.cuda.is_available() else torch.device("cpu")
    try:
        device = torch.device(device_str.strip().lower() if isinstance(device_str, str) else device_str)
    except (TypeError, RuntimeError) as error:
        raise ValueError(f"Invalid device: {device_str}") from error
    if device.type == "cpu":
        return torch.device("cpu")
    if device.type != "cuda":
        raise ValueError("Supported devices are cpu, auto, cuda, and indexed cuda devices.")
    if not torch.cuda.is_available():
        if not allow_cpu_fallback:
            raise ValueError(f"Requested CUDA device {device} is unavailable.")
        logger.warning(f"Requested device '{device}' but CUDA is unavailable; using CPU.")
        return torch.device("cpu")
    index = device.index if device.index is not None else torch.cuda.current_device()
    if index >= torch.cuda.device_count():
        raise ValueError(f"Requested CUDA index {index} is unavailable.")
    return torch.device("cuda", index)


def module_device(module, default: torch.device) -> torch.device:
    """Device of a module's parameters (``default`` for parameter-free or non-module objects)."""
    try:
        return next(module.parameters()).device
    except (StopIteration, AttributeError):
        return default
