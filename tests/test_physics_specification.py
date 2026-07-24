"""
Unit tests for Publication Physics Specification, Parameter Bounds, and Sensitivity Profiles (Task 03).
"""

import pytest
import torch
from mobo_linac.config import load_config, MoboConfig, DesignVariableConfig
from mobo_linac.objectives import transform_to_model_space, transform_to_physical_space


def test_publication_config_loading():
    """Verify loading of canonical publication_200mev.yaml configuration."""
    config = load_config("configs/publication_200mev.yaml")
    assert config.version == "1.0"
    assert len(config.design_variables) == 6
    assert len(config.objectives) == 3


def test_design_variable_bounds_and_negative_ordering():
    """Verify design variable bounds ordering, especially for negative quadrupole gradients."""
    config = load_config("configs/publication_200mev.yaml")

    for dv in config.design_variables:
        assert dv.lower_bound <= dv.upper_bound, f"Variable {dv.name} lower_bound > upper_bound"

    # Check Quad 2 negative bounds specifically
    quad2 = [dv for dv in config.design_variables if dv.name == "quad_2_gradient_T_m"][0]
    assert quad2.lower_bound == -4.330027545
    assert quad2.upper_bound == -1.443342515
    assert quad2.lower_bound < quad2.upper_bound

    # Check PyTorch bounds tensor
    bounds = config.get_parameter_bounds_tensor()
    assert bounds.shape == (2, 6)
    assert torch.all(bounds[0] <= bounds[1])


def test_coupled_phase_configurations():
    """Verify coupled RF phase declarations."""
    config = load_config("configs/publication_200mev.yaml")

    coupled_vars = [dv for dv in config.design_variables if dv.is_coupled]
    assert len(coupled_vars) == 2

    acc1_2 = [dv for dv in coupled_vars if dv.name == "acc1_acc2_phase_deg"][0]
    assert acc1_2.coupled_targets == ["cavity:phi(2)", "cavity:phi(3)"]

    acc3_4 = [dv for dv in coupled_vars if dv.name == "acc3_acc4_phase_deg"][0]
    assert acc3_4.coupled_targets == ["cavity:phi(4)", "cavity:phi(5)"]


def test_objective_transformations():
    """Verify minimization <-> maximization transformation roundtrips."""
    config = load_config("configs/publication_200mev.yaml")
    phys_objs = [1.2e-6, 1.5e-6, 4.0e5]

    model_tensor = transform_to_model_space(phys_objs, config)
    assert model_tensor.tolist() == [-1.2e-6, -1.5e-6, -4.0e5]

    restored_tensor = transform_to_physical_space(model_tensor, config)
    assert restored_tensor.tolist() == phys_objs


def test_sensitivity_profiles():
    """Verify loading and retrieval of stringent, nominal, and relaxed constraint profiles."""
    config = load_config("configs/publication_200mev.yaml")

    stringent = config.get_constraint_profile("stringent")
    assert stringent.max_sigma_x_m == pytest.approx(0.3e-3)
    assert stringent.min_transmission == pytest.approx(0.9999)

    nominal = config.get_constraint_profile("nominal")
    assert nominal.max_sigma_x_m == pytest.approx(1.0e-3)
    assert nominal.min_transmission == pytest.approx(0.90)

    relaxed = config.get_constraint_profile("relaxed")
    assert relaxed.max_sigma_x_m == pytest.approx(2.0e-3)
    assert relaxed.min_transmission == pytest.approx(0.80)
