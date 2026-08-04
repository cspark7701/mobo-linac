"""
Unit tests for Diagnostic Constraints and Feasibility (Task 04).
"""

import pytest
from mobo_linac.config import ConstraintsConfig
from mobo_linac.constraints import ConstraintEvaluator


def test_feasibility_boundary_conditions():
    """Test constraint feasibility evaluation at exact boundary thresholds."""
    evaluator = ConstraintEvaluator(
        ConstraintsConfig(
            max_sigma_x_m=1.0e-3,
            max_sigma_y_m=1.0e-3,
            max_sigma_xp_rad=1.0e-3,
            max_sigma_yp_rad=1.0e-3,
            max_sigma_z_m=1.0e-3,
            min_mean_kinetic_energy_eV=195.0e6,
            max_mean_kinetic_energy_eV=205.0e6,
            min_transmission=0.90,
        )
    )

    feasible_diags = {
        "sigma_x": 1.0e-3,
        "sigma_y": 1.0e-3,
        "sigma_xp": 1.0e-3,
        "sigma_yp": 1.0e-3,
        "sigma_z": 1.0e-3,
        "mean_kinetic_energy": 200.0e6,
        "transmission": 1.0,
    }
    assert evaluator.check_feasibility(feasible_diags) is True

    # Infeasible: sigma_x too large
    infeasible_sigma_x = dict(feasible_diags, sigma_x=1.001e-3)
    assert evaluator.check_feasibility(infeasible_sigma_x) is False

    # Infeasible: energy too low
    infeasible_energy_low = dict(feasible_diags, mean_kinetic_energy=194.9e6)
    assert evaluator.check_feasibility(infeasible_energy_low) is False

    # Infeasible: energy too high
    infeasible_energy_high = dict(feasible_diags, mean_kinetic_energy=205.1e6)
    assert evaluator.check_feasibility(infeasible_energy_high) is False


def test_compute_constraint_violations():
    """Test computation of constraint violation magnitudes."""
    evaluator = ConstraintEvaluator()

    diags = {
        "sigma_x": 1.2e-3,  # Violated by 0.2e-3
        "sigma_y": 0.8e-3,  # Satisfied (violation 0.0)
        "sigma_xp": 1.0e-3,
        "sigma_yp": 1.0e-3,
        "sigma_z": 1.0e-3,
        "mean_kinetic_energy": 190.0e6,  # Violated by 5.0e6 below min
    }

    violations = evaluator.compute_violations(diags)

    assert violations["sigma_x_m"] == pytest.approx(0.2e-3)
    assert violations["sigma_y_m"] == 0.0
    assert violations["energy_lower_eV"] == pytest.approx(5.0e6)
    assert violations["energy_upper_eV"] == 0.0


def test_get_botorch_constraint_functions():
    """Test dynamic generation of BoTorch tensor constraint functions."""
    import torch
    from mobo_linac.constraints import get_botorch_constraint_functions

    c_funcs = get_botorch_constraint_functions()
    assert len(c_funcs) == 8

    # Dummy outcome tensor Y (batch size 1, 10 outcome metrics)
    # Objectives: Y[0..2], Constraints: Y[3..9]
    Y_feasible = torch.tensor([[0.0, 0.0, 0.0, 0.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 200.0e6, 1.0]], dtype=torch.double)
    for c_func in c_funcs:
        val = c_func(Y_feasible)
        assert val.item() <= 0.0  # All <= 0 means feasible

    # Test infeasible tensor (sigma_x = 1.5e-3 > 1.0e-3 threshold)
    Y_infeasible_x = torch.tensor([[0.0, 0.0, 0.0, 1.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 200.0e6, 1.0]], dtype=torch.double)
    assert c_funcs[0](Y_infeasible_x).item() > 0.0

    # Test infeasible transmission tensor (transmission = 0.80 < 0.90 threshold)
    Y_infeasible_trans = torch.tensor([[0.0, 0.0, 0.0, 0.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 200.0e6, 0.80]], dtype=torch.double)
    assert c_funcs[7](Y_infeasible_trans).item() > 0.0


