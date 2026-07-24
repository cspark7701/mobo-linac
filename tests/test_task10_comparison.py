import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Ensure repo root is in sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from scripts.run_comparison_and_verification import (
    compute_target_distance,
    generate_comparison_report,
    verify_pareto_candidates,
    TARGET_EMIT_X_M_RAD,
    TARGET_EMIT_Y_M_RAD,
    TARGET_SIGMA_E_EV,
)

from mobo_linac.config import load_config
from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.metrics.hypervolume import HypervolumeTracker
import torch


def test_compute_target_distance():
    """Verify engineering target distance calculation."""
    dist_at_target = compute_target_distance(
        TARGET_EMIT_X_M_RAD,
        TARGET_EMIT_Y_M_RAD,
        TARGET_SIGMA_E_EV,
    )
    assert dist_at_target == pytest.approx(np.sqrt(3.0), rel=1e-5)
    assert compute_target_distance(0.0, 0.0, 0.0) == 0.0


def test_verify_pareto_candidates_mock(tmp_path, monkeypatch):
    """Test Pareto candidate selection and relative difference verification with mocked run_astra_eval."""
    config = load_config("configs/mobo_200mev.yaml")

    mock_results = []
    for i in range(1, 10):
        res = EvaluationResult(
            evaluation_id=f"eval_00000{i}",
            run_id="mock_run",
            x_physical=[0.20 + 0.01 * i, 1.0, -1.0, 0.0, 0.0, 0.0],
            objectives_physical=[1e-6 * i, 1e-6 * i, 0.1e6 * i],
            objectives_model=[-1e-6 * i, -1e-6 * i, -0.1e6 * i],
            diagnostics={
                "sigma_x": 0.5e-3,
                "sigma_y": 0.5e-3,
                "sigma_xp": 0.5e-3,
                "sigma_yp": 0.5e-3,
                "sigma_z": 0.5e-3,
                "mean_kinetic_energy": 200e6,
                "transmission": 1.0,
            },
            simulation_valid=True,
            physically_feasible=True,
            failure_category=FailureCategory.SUCCESS.value,
        )
        mock_results.append(res)

    def mock_run_astra_eval(parameters, **kwargs):
        i = round((parameters[0] - 0.20) / 0.01)
        return {
            "status": "success",
            "objectives": {"norm_emit_x": 1e-6 * i, "norm_emit_y": 1e-6 * i, "sigma_energy": 0.1e6 * i},
            "diagnostics": {},
            "eval_dir": str(tmp_path / "mock_workdir"),
            "manifest_path": None,
            "error": None,
        }

    monkeypatch.setattr("scripts.run_comparison_and_verification.run_astra_eval", mock_run_astra_eval)

    records = verify_pareto_candidates(mock_results, config, tmp_path)

    assert len(records) == 5
    for rec in records:
        assert rec["status"] == "VERIFIED"
        assert rec["max_diff_pct"] < 1.0e-3


def test_generate_comparison_report(tmp_path):
    """Test generating mobo_validation_report.md."""
    config = load_config("configs/mobo_200mev.yaml")
    ref_point = torch.tensor([-5.0e-6, -5.0e-6, -2.0e6], dtype=torch.double)

    tracker_p2 = HypervolumeTracker(reporting_ref_point=ref_point, config=config)
    tracker_p3 = HypervolumeTracker(reporting_ref_point=ref_point, config=config)

    train_Y = torch.tensor([[-1.0e-6, -1.0e-6, -0.5e6]], dtype=torch.double)
    feas_mask = torch.tensor([True])

    tracker_p2.track_iteration(0, train_Y, feas_mask)
    tracker_p3.track_iteration(0, train_Y, feas_mask)

    mock_results = [
        EvaluationResult(
            evaluation_id="eval_000001",
            run_id="mock_run",
            x_physical=[0.20, 1.0, -1.0, 0.0, 0.0, 0.0],
            objectives_physical=[1.0e-6, 1.0e-6, 0.5e6],
            objectives_model=[-1.0e-6, -1.0e-6, -0.5e6],
            diagnostics={
                "sigma_x": 0.5e-3,
                "sigma_y": 0.5e-3,
                "sigma_xp": 0.5e-3,
                "sigma_yp": 0.5e-3,
                "sigma_z": 0.5e-3,
                "mean_kinetic_energy": 200e6,
                "transmission": 1.0,
            },
            simulation_valid=True,
            physically_feasible=True,
            failure_category=FailureCategory.SUCCESS.value,
        )
    ]

    verification_records = [
        {
            "role": "knee_point",
            "original_eval_id": "eval_000001",
            "stored_emit_x_m_rad": 1.0e-6,
            "rerun_emit_x_m_rad": 1.0e-6,
            "stored_emit_y_m_rad": 1.0e-6,
            "rerun_emit_y_m_rad": 1.0e-6,
            "stored_sigma_energy_eV": 0.5e6,
            "rerun_sigma_energy_eV": 0.5e6,
            "max_diff_pct": 0.0,
            "status": "VERIFIED",
        }
    ]

    report_path = tmp_path / "docs" / "results" / "mobo_validation_report.md"

    generate_comparison_report(
        run_dir_p2=tmp_path / "run_p2",
        results_p2=mock_results,
        tracker_p2=tracker_p2,
        wall_sec_p2=12.34,
        run_dir_p3=tmp_path / "run_p3",
        results_p3=mock_results,
        tracker_p3=tracker_p3,
        wall_sec_p3=15.67,
        verification_records=verification_records,
        report_path=report_path,
    )

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Multi-Objective Bayesian Optimization Validation & Comparison Report" in content
    assert "Phase 2 (Unconstrained MOBO)" in content
    assert "Phase 3 (Constrained MOBO)" in content
    assert "VERIFIED" in content
