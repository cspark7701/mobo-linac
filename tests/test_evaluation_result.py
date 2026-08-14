"""
Unit tests for Structured Evaluation Results and Failure Semantics (Task 05).
"""

import math
import pytest
import torch

from mobo_linac.config import load_config
from mobo_linac.evaluation import (
    EvaluationResult,
    FailureCategory,
    create_evaluation_result,
)
from mobo_linac.io.results import get_train_tensors


@pytest.fixture
def sample_config():
    return load_config("configs/mobo_200MeV.yaml")


def test_success_evaluation_result(sample_config):
    """Test creation of EvaluationResult for a successful, feasible simulation."""
    raw_res = {
        "eval_id": "eval_000001",
        "run_id": "test_run",
        "parameters": [0.20, 1.2, -1.2, 0.0, 0.0, 0.0],
        "status": "success",
        "objectives": {"norm_emit_x": 1.2e-6, "norm_emit_y": 1.2e-6, "sigma_energy": 5.0e4},
        "diagnostics": {
            "sigma_x": 0.8e-3,
            "sigma_y": 0.8e-3,
            "sigma_xp": 0.8e-3,
            "sigma_yp": 0.8e-3,
            "sigma_z": 0.8e-3,
            "mean_kinetic_energy": 200.0e6,
            "transmission": 1.0,
        },
        "eval_dir": "/tmp/eval_000001",
        "execution_time_sec": 2.5,
    }

    res = create_evaluation_result(raw_res, config=sample_config)

    assert res.evaluation_id == "eval_000001"
    assert res.simulation_valid is True
    assert res.physically_feasible is True
    assert res.failure_category == FailureCategory.SUCCESS.value
    assert res.objectives_physical == [1.2e-6, 1.2e-6, 5.0e4]
    assert res.objectives_model == [-1.2e-6, -1.2e-6, -5.0e4]


def test_infeasible_beam_result(sample_config):
    """Test result where simulation is valid but beam is physically infeasible (sigma_x > 1mm)."""
    raw_res = {
        "eval_id": "eval_000002",
        "run_id": "test_run",
        "parameters": [0.20, 1.2, -1.2, 0.0, 0.0, 0.0],
        "status": "success",
        "objectives": {"norm_emit_x": 2.0e-6, "norm_emit_y": 2.0e-6, "sigma_energy": 5.0e4},
        "diagnostics": {
            "sigma_x": 1.5e-3,  # Infeasible > 1mm
            "sigma_y": 0.8e-3,
            "sigma_xp": 0.8e-3,
            "sigma_yp": 0.8e-3,
            "sigma_z": 0.8e-3,
            "mean_kinetic_energy": 200.0e6,
            "transmission": 1.0,
        },
    }

    res = create_evaluation_result(raw_res, config=sample_config)

    assert res.simulation_valid is True
    assert res.physically_feasible is False
    assert res.failure_category == FailureCategory.INFEASIBLE_BEAM.value


def test_timeout_failure_result(sample_config):
    """Test result for ASTRA simulation timeout failure."""
    raw_res = {
        "eval_id": "eval_000003",
        "run_id": "test_run",
        "parameters": [0.20, 1.2, -1.2, 0.0, 0.0, 0.0],
        "status": "timeout",
        "error": "ASTRA execution timed out after 30 seconds",
    }

    res = create_evaluation_result(raw_res, config=sample_config)

    assert res.simulation_valid is False
    assert res.physically_feasible is False
    assert res.failure_category == FailureCategory.ASTRA_TIMEOUT.value


def test_nan_inf_failure_result(sample_config):
    """Test result when output contains NaN or Inf."""
    raw_res = {
        "eval_id": "eval_000004",
        "run_id": "test_run",
        "parameters": [0.20, 1.2, -1.2, 0.0, 0.0, 0.0],
        "status": "success",
        "objectives": {"norm_emit_x": math.nan, "norm_emit_y": 1.2e-6, "sigma_energy": 5.0e4},
        "diagnostics": {"sigma_x": 0.8e-3, "mean_kinetic_energy": 200e6, "transmission": 1.0},
    }

    res = create_evaluation_result(raw_res, config=sample_config)

    assert res.simulation_valid is False
    assert res.physically_feasible is False
    assert res.failure_category == FailureCategory.NAN_INF_DIAGNOSTICS.value


def test_premature_beam_loss_detection(sample_config):
    """Test detection of premature beam loss along the linac (Task 03)."""
    # 1. Premature loss at z = 5.0 m (linac exit plane is 16.2 m)
    raw_premature = {
        "eval_id": "eval_000005",
        "run_id": "test_run",
        "parameters": [0.20, 1.2, -1.2, 0.0, 0.0, 0.0],
        "status": "success",
        "objectives": {"norm_emit_x": 0.5e-6, "norm_emit_y": 0.5e-6, "sigma_energy": 1.0e4},
        "diagnostics": {
            "sigma_x": 0.5e-3,
            "sigma_y": 0.5e-3,
            "sigma_xp": 0.5e-3,
            "sigma_yp": 0.5e-3,
            "sigma_z": 0.5e-3,
            "mean_kinetic_energy": 30.0e6,
            "transmission": 1.0,
            "z_final_m": 5.0,  # Premature stop
        },
    }
    res_premature = create_evaluation_result(raw_premature, config=sample_config)
    assert res_premature.simulation_valid is False
    assert res_premature.physically_feasible is False
    assert res_premature.failure_category == FailureCategory.PREMATURE_BEAM_LOSS.value
    assert "Premature tracking termination" in res_premature.failure_reason

    # 2. Complete tracking to exit plane z = 16.2 m
    raw_complete = {
        "eval_id": "eval_000006",
        "run_id": "test_run",
        "parameters": [0.20, 1.2, -1.2, 0.0, 0.0, 0.0],
        "status": "success",
        "objectives": {"norm_emit_x": 1.2e-6, "norm_emit_y": 1.2e-6, "sigma_energy": 5.0e4},
        "diagnostics": {
            "sigma_x": 0.8e-3,
            "sigma_y": 0.8e-3,
            "sigma_xp": 0.8e-3,
            "sigma_yp": 0.8e-3,
            "sigma_z": 0.8e-3,
            "mean_kinetic_energy": 200.0e6,
            "transmission": 1.0,
            "z_final_m": 16.2,  # Full tracking
        },
    }
    res_complete = create_evaluation_result(raw_complete, config=sample_config)
    assert res_complete.simulation_valid is True
    assert res_complete.physically_feasible is True
    assert res_complete.failure_category == FailureCategory.SUCCESS.value


def test_exclude_invalid_from_gp_train_tensors():
    """Verify that invalid simulations including premature beam loss are excluded from GP training tensors."""
    valid_feasible = EvaluationResult(
        evaluation_id="1", run_id="r", x_physical=[0.2, 1.0, -1.0, 0.0, 0.0, 0.0],
        objectives_physical=[1e-6, 1e-6, 1e4], objectives_model=[-1e-6, -1e-6, -1e4],
        simulation_valid=True, physically_feasible=True, failure_category="SUCCESS"
    )
    valid_infeasible = EvaluationResult(
        evaluation_id="2", run_id="r", x_physical=[0.3, 1.5, -1.5, 0.0, 0.0, 0.0],
        objectives_physical=[2e-6, 2e-6, 2e4], objectives_model=[-2e-6, -2e-6, -2e4],
        simulation_valid=True, physically_feasible=False, failure_category="INFEASIBLE_BEAM"
    )
    invalid_timeout = EvaluationResult(
        evaluation_id="3", run_id="r", x_physical=[0.4, 2.0, -2.0, 0.0, 0.0, 0.0],
        objectives_physical=None, objectives_model=None,
        simulation_valid=False, physically_feasible=False, failure_category="ASTRA_TIMEOUT"
    )
    invalid_premature = EvaluationResult(
        evaluation_id="4", run_id="r", x_physical=[0.5, 2.5, -2.5, 0.0, 0.0, 0.0],
        objectives_physical=[0.5e-6, 0.5e-6, 1e4], objectives_model=[-0.5e-6, -0.5e-6, -1e4],
        simulation_valid=False, physically_feasible=False, failure_category="PREMATURE_BEAM_LOSS"
    )

    results = [valid_feasible, valid_infeasible, invalid_timeout, invalid_premature]

    train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)

    # Only 2 valid samples should be in GP training tensors (invalid and premature beam loss excluded)
    assert train_X.shape[0] == 2
    assert train_Y.shape[0] == 2
    assert train_feas_mask.shape[0] == 2
    assert train_feas_mask[0].item() is True
    assert train_feas_mask[1].item() is False
