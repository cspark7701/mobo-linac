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
from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS

from mobo_linac.config import load_config as _load_test_config
TEST_CONFIG = _load_test_config("configs/mobo_200MeV.yaml")


@pytest.mark.parametrize("channel", DIAGNOSTIC_CHANNELS, ids=lambda c: c.name)
def test_missing_diagnostic_invalidates_new_evaluation_without_imputation(channel):
    from mobo_linac.io.results import get_constraint_tensors, get_train_tensors

    raw = get_valid_raw_output()
    del raw["diagnostics"][channel.name]
    result = create_evaluation_result(raw, load_config())
    assert not result.simulation_valid
    assert result.failure_category == FailureCategory.MISSING_OUTPUT.value
    assert channel.name not in result.diagnostics
    assert get_constraint_tensors([result], config=TEST_CONFIG).shape == (0, 7)
    assert get_train_tensors([result], config=TEST_CONFIG)[0].shape[0] == 0


@pytest.mark.parametrize("value", [None, "unmeasured", float("nan"), float("inf")])
def test_invalid_channel_values_are_recorded_without_factory_crashes(value):
    raw = get_valid_raw_output()
    raw["diagnostics"]["sigma_x_m"] = value
    result = create_evaluation_result(raw, load_config())
    assert not result.simulation_valid
    assert result.failure_category == FailureCategory.NAN_INF_DIAGNOSTICS.value
    assert not math.isfinite(result.diagnostics["sigma_x_m"])


def test_factory_normalizes_complete_legacy_aliases_once():
    raw = get_valid_raw_output()
    for channel in DIAGNOSTIC_CHANNELS:
        raw["diagnostics"][channel.aliases[0]] = raw["diagnostics"].pop(channel.name)
    result = create_evaluation_result(raw, load_config())
    assert result.simulation_valid and result.physically_feasible
    for channel in DIAGNOSTIC_CHANNELS:
        assert channel.name in result.diagnostics
        assert channel.aliases[0] not in result.diagnostics


def test_numpy_real_measurements_are_valid_observations():
    raw = get_valid_raw_output()
    raw["diagnostics"] = {key: np.float64(value) for key, value in raw["diagnostics"].items()}
    raw["diagnostics"]["n_particles_final"] = np.int64(10000)
    raw["objectives"]["norm_emit_x"] = np.float32(1e-6)
    result = create_evaluation_result(raw, load_config())
    assert result.simulation_valid and result.physically_feasible
    # Particle counts are telemetry, kept apart from constraint channels.
    assert result.telemetry["n_particles_final"] == 10000.0
    assert "n_particles_final" not in result.diagnostics


def test_filtered_constraint_rows_retain_design_objective_identity():
    from mobo_linac.io.results import get_training_observations, get_constraint_tensors

    records = []
    for index in range(5):
        raw = get_valid_raw_output()
        raw["eval_id"] = f"eval_{index + 1:06d}"
        raw["parameters"][0] += index * 0.001
        raw["objectives"]["norm_emit_x"] += index * 1e-7
        if index == 3:
            raw["diagnostics"]["sigma_x_m"] = 1.2e-3  # Measured infeasibility is still training data.
        records.append(create_evaluation_result(raw, load_config()))
    # Archived records can carry a valid flag despite incomplete diagnostic dictionaries.
    del records[1].diagnostics["sigma_y_m"]
    records[2].diagnostics["mean_kinetic_energy_eV"] = float("inf")
    records[4].objectives_model[0] = float("nan")
    observed = get_training_observations(records, require_diagnostics=True, config=TEST_CONFIG)
    assert observed.evaluation_ids == (("test_run", "eval_000001"), ("test_run", "eval_000004"))
    assert observed.train_X.tolist() == [records[i].x_physical for i in (0, 3)]
    assert observed.train_Y.tolist() == [records[i].objectives_model for i in (0, 3)]
    assert observed.constraints[:, 0].tolist() == [0.5e-3, 1.2e-3]
    assert observed.feasible.tolist() == [True, False]
    assert get_constraint_tensors(records, config=TEST_CONFIG).tolist() == observed.constraints.tolist()
    objective_only = get_training_observations(records, config=TEST_CONFIG)
    assert len(objective_only.evaluation_ids) == 4


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
    # Below-threshold transmission is ordinary infeasibility, not an unphysical value.
    assert res_fail.failure_category == FailureCategory.INFEASIBLE_BEAM.value
    assert "transmission" in res_fail.failure_reason


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
    assert "transmission_fraction" in diags
    # Objective copies and particle counts are not diagnostics.
    assert "sigma_energy_eV" not in diags
    assert {"n_particles_initial", "n_particles_final"} <= set(res.telemetry)

    df = results_to_dataframe([res], config=TEST_CONFIG)
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
    assert res.failure_category == FailureCategory.INFEASIBLE_BEAM.value


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


def test_premature_beam_loss_exit_plane_rejection():
    """Verify rejection of premature beam termination before reaching exit plane (Task 03)."""
    config = load_config()
    raw = get_valid_raw_output()

    # 1. Premature stop at 12.0 m (linac exit plane is 16.2 m)
    raw["diagnostics"]["z_final_m"] = 12.0
    res_premature = create_evaluation_result(raw, config)
    assert res_premature.simulation_valid is False
    assert res_premature.physically_feasible is False
    assert res_premature.failure_category == FailureCategory.PREMATURE_BEAM_LOSS.value

    # 2. Target exit plane achieved at 16.2 m
    raw["diagnostics"]["z_final_m"] = 16.2
    res_valid = create_evaluation_result(raw, config)
    assert res_valid.simulation_valid is True
    assert res_valid.physically_feasible is True
    assert res_valid.failure_category == FailureCategory.SUCCESS.value
