"""
Unit tests for Objectives and Sign Transformations (Task 04).
"""

import numpy as np
import pytest
import torch

from mobo_linac.config import load_config
from mobo_linac.objectives import (
    extract_physical_objectives,
    transform_to_model_space,
    transform_to_physical_space,
)


def test_transform_to_model_space_and_back():
    """Verify objective negation for minimization and restoration idempotency."""
    config = load_config("configs/mobo_200MeV.yaml")
    phys_objs = [1.5e-6, 1.2e-6, 5.0e4]  # emit_x, emit_y, sigma_energy

    # Model space should negate minimization objectives
    model_tensor = transform_to_model_space(phys_objs, config)
    assert torch.allclose(model_tensor, torch.tensor([-1.5e-6, -1.2e-6, -5.0e4], dtype=torch.double))

    # Restoring to physical space should return exact physical values
    restored_tensor = transform_to_physical_space(model_tensor, config)
    assert torch.allclose(restored_tensor, torch.tensor(phys_objs, dtype=torch.double))


def test_transform_input_types():
    """Test transform works with list, numpy array, and torch tensor."""
    phys_list = [1.0e-6, 2.0e-6, 3.0e4]
    phys_np = np.array(phys_list)
    phys_torch = torch.tensor(phys_list, dtype=torch.double)

    res_list = transform_to_model_space(phys_list)
    res_np = transform_to_model_space(phys_np)
    res_torch = transform_to_model_space(phys_torch)

    assert torch.allclose(res_list, res_np)
    assert torch.allclose(res_np, res_torch)


def test_extract_physical_objectives():
    """Verify extraction of objectives with explicit naming."""
    mock_stats = {
        "norm_emit_x": [1.0e-6, 1.2e-6],
        "norm_emit_y": [2.0e-6, 2.2e-6],
        "sigma_energy": [10.0, 50.0],
    }

    objs = extract_physical_objectives(mock_stats)
    assert objs["norm_emit_x"] == 1.2e-6
    assert objs["norm_emit_y_m_rad"] == 2.2e-6
    assert objs["sigma_energy_eV"] == 50.0
