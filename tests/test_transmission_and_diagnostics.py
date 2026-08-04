"""
Tests for Transmission Computation, Diagnostic Integrity, and Range Validation (Task 02).
"""

import math
import pytest
import numpy as np
import pandas as pd

from mobo_linac.config import load_config
from mobo_linac.constraints import ConstraintEvaluator
from mobo_linac.evaluation import (
    EvaluationResult,
    FailureCategory,
    create_evaluation_result,
)
from mobo_linac.io.results import results_to_dataframe


def get_valid_raw_output():
    return {
        "status": "success",
        "eval_id": "eval_000001",
        "run_id": "test_run",
        "parameters": [0.194, 1.28, -2.88, 35.6, -39.5, 310.0],
        "objectives": {
            "norm_emit_x": 1.0e-6,
            "norm_emit_y": 1.0e-6,
            "sigma_energy": 0.5e6,
        },
        "diagnostics": {
            "sigma_x_m": 0.5e-3,
            "sigma_y_m": 0.5e-3,
            "sigma_xp_rad": 0.5e-3,
            "sigma_yp_rad": 0.5e-3,
            "sigma_z_m": 0.5e-3,
            "mean_kinetic_energy_eV": 200.0e6,
            "sigma_energy_eV": 0.5e6,
            "n_particles_initial": 10000,
            "n_particles_final": 10000,
            "transmission_fraction": 1.0,
        },
        "timestamps": {"duration_sec": 1.5},
        "eval_dir": "/tmp/mock_eval",
    }


def test_transmission_full():
    """Verify 100% transmission fraction evaluation."""
    config = load_config()
    raw = get_valid_raw_output()
    raw["diagnostics"]["n_particles_initial"] = 10000
    raw["diagnostics"]["n_particles_final"] = 10000
    raw["diagnostics"]["transmission_fraction"] = 1.0

    res = create_evaluation_result(raw, config)
    assert res.simulation_valid is True
    assert res.physically_feasible is True
    assert res.failure_category == FailureCategory.SUCCESS.value
    assert res.diagnostics["transmission_fraction"] == 1.0


def test_transmission_partial():
    """Verify partial transmission fraction evaluation (e.g. 95% passing, 85% failing threshold)."""
    config = load_config()
    raw = get_valid_raw_output()

    # 95% transmission -> meets 90% threshold
    raw["diagnostics"]["n_particles_initial"] = 10000
    raw["diagnostics"]["n_particles_final"] = 9500
    raw["diagnostics"]["transmission_fraction"] = 0.95
    res_pass = create_evaluation_result(raw, config)
    assert res_pass.simulation_valid is True
    assert res_pass.physically_feasible is True
    assert res_pass.failure_category == FailureCategory.SUCCESS.value

    # 85% transmission -> valid simulation, but fails physical feasibility (min 90%)
    raw["diagnostics"]["n_particles_final"] = 8500
    raw["diagnostics"]["transmission_fraction"] = 0.85
    res_fail = create_evaluation_result(raw, config)
    assert res_fail.simulation_valid is True
    assert res_fail.physically_feasible is False
    assert res_fail.failure_category == FailureCategory.INVALID_TRANSMISSION.value


def test_transmission_missing():
    """Verify that missing transmission diagnostic cannot pass feasibility and fails validation."""
    config = load_config()
    raw = get_valid_raw_output()
    del raw["diagnostics"]["transmission_fraction"]
    if "transmission" in raw["diagnostics"]:
        del raw["diagnostics"]["transmission"]

    res = create_evaluation_result(raw, config)
    assert res.simulation_valid is False
    assert res.physically_feasible is False
    assert res.failure_category == FailureCategory.MISSING_OUTPUT.value


def test_diagnostic_units():
    """Verify export of explicit unit-bearing diagnostic names and dataframe columns."""
    config = load_config()
    raw = get_valid_raw_output()
    res = create_evaluation_result(raw, config)

    diags = res.diagnostics
    assert "sigma_x_m" in diags
    assert "sigma_y_m" in diags
    assert "sigma_xp_rad" in diags
    assert "sigma_yp_rad" in diags
    assert "sigma_z_m" in diags
    assert "mean_kinetic_energy_eV" in diags
    assert "sigma_energy_eV" in diags
    assert "n_particles_initial" in diags
    assert "n_particles_final" in diags
    assert "transmission_fraction" in diags

    df = results_to_dataframe([res])
    for col in [
        "sigma_x_m",
        "sigma_y_m",
        "sigma_xp_rad",
        "sigma_yp_rad",
        "sigma_z_m",
        "mean_kinetic_energy_eV",
        "sigma_energy_eV",
        "n_particles_initial",
        "n_particles_final",
        "transmission_fraction",
    ]:
        assert col in df.columns
        assert not pd.isna(df[col].iloc[0])


def test_nonfinite_diagnostics():
    """Verify rejection of NaN/Inf or negative RMS beam diagnostic parameters."""
    config = load_config()

    # 1. NaN diagnostic
    raw_nan = get_valid_raw_output()
    raw_nan["diagnostics"]["sigma_x_m"] = float("nan")
    res_nan = create_evaluation_result(raw_nan, config)
    assert res_nan.simulation_valid is False
    assert res_nan.failure_category == FailureCategory.NAN_INF_DIAGNOSTICS.value

    # 2. Inf diagnostic
    raw_inf = get_valid_raw_output()
    raw_inf["diagnostics"]["mean_kinetic_energy_eV"] = float("inf")
    res_inf = create_evaluation_result(raw_inf, config)
    assert res_inf.simulation_valid is False
    assert res_inf.failure_category == FailureCategory.NAN_INF_DIAGNOSTICS.value

    # 3. Negative RMS quantity
    raw_neg = get_valid_raw_output()
    raw_neg["diagnostics"]["sigma_z_m"] = -0.001
    res_neg = create_evaluation_result(raw_neg, config)
    assert res_neg.simulation_valid is False
    assert res_neg.failure_category == FailureCategory.NAN_INF_DIAGNOSTICS.value

    # 4. Out of bounds transmission (> 1.0 or < 0.0)
    raw_oob = get_valid_raw_output()
    raw_oob["diagnostics"]["transmission_fraction"] = 1.5
    res_oob = create_evaluation_result(raw_oob, config)
    assert res_oob.simulation_valid is False
    assert res_oob.failure_category == FailureCategory.INVALID_TRANSMISSION.value


def test_transmission_zero():
    """Verify zero transmission evaluation (valid simulation, physically infeasible)."""
    config = load_config()
    raw = get_valid_raw_output()
    raw["diagnostics"]["n_particles_initial"] = 10000
    raw["diagnostics"]["n_particles_final"] = 0
    raw["diagnostics"]["transmission_fraction"] = 0.0

    res = create_evaluation_result(raw, config)
    assert res.simulation_valid is True
    assert res.physically_feasible is False
    assert res.failure_category == FailureCategory.INVALID_TRANSMISSION.value


def test_invalid_particle_counts():
    """Verify invalid initial particle counts (<= 0) fail validation."""
    config = load_config()
    raw = get_valid_raw_output()
    raw["diagnostics"]["n_particles_initial"] = 0
    raw["diagnostics"]["n_particles_final"] = 0
    del raw["diagnostics"]["transmission_fraction"]
    if "transmission" in raw["diagnostics"]:
        del raw["diagnostics"]["transmission"]

    res = create_evaluation_result(raw, config)
    assert res.simulation_valid is False
    assert res.physically_feasible is False
    assert res.failure_category == FailureCategory.MISSING_OUTPUT.value

