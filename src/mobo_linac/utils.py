"""
Device helper module for mobo_linac.

Provides dynamic GPU/CPU device resolution for PyTorch/BoTorch tensor calculations.
"""

import os
from typing import Optional, Union
import torch


def get_device(device_str: Optional[str] = None) -> torch.device:
    """
    Selects PyTorch device.
    
    If device_str is provided (e.g. 'cuda', 'cuda:0', 'cpu'), parses it.
    If 'auto' or None, automatically selects CUDA GPU if torch.cuda.is_available()
    else CPU.
    
    Args:
        device_str: Optional device string ('auto', 'cuda', 'cuda:0', 'cpu').
        
    Returns:
        torch.device instance.
    """
    if device_str is None or device_str.lower() in ("auto", ""):
        if torch.cuda.is_available():
            device = torch.device("cuda")
        else:
            device = torch.device("cpu")
    else:
        req_dev = device_str.lower().strip()
        if req_dev.startswith("cuda") and not torch.cuda.is_available():
            print(f"[Warning] Requested device '{device_str}' but CUDA is not available. Falling back to CPU.")
            device = torch.device("cpu")
        else:
            device = torch.device(req_dev)

    return device
