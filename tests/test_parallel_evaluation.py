"""
Unit and Integration Tests for Process-Safe Parallel ASTRA Evaluation (Task 03).
"""

import json
from pathlib import Path
import pytest
import numpy as np

from mobo_linac.execution.parallel import (
    BatchEvaluator,
    evaluate_candidates_parallel,
    _worker_eval_task,
)


@pytest.fixture
def temp_project(tmp_path):
    """
    Creates a temporary project environment with mock input/field files.
    """
    template_dir = tmp_path / "template"
    template_dir.mkdir()

    (template_dir / "gun.dat").write_text("GUN DATA MOCK")
    (template_dir / "PAL_SOL_A.dat").write_text("SOLENOID DATA MOCK")
    (template_dir / "TWS_Sband.dat").write_text("TWS DATA MOCK")
    (template_dir / "pal_photo2.ini").write_text("PARTICLE DIST MOCK")

    astra_in_content = (
        "&INPUT\n"
        "  solenoid:maxb(1) = 0.20,\n"
        "  quadrupole:q_grad(1) = 1.5,\n"
        "  quadrupole:q_grad(2) = -1.5,\n"
        "  cavity:phi(1) = 0.0,\n"
        "  cavity:phi(2) = 0.0,\n"
        "  cavity:phi(3) = 0.0,\n"
        "  cavity:phi(4) = 0.0,\n"
        "  cavity:phi(5) = 0.0\n"
        "/\n"
    )
    (template_dir / "astra.in").write_text(astra_in_content)

    results_dir = tmp_path / "results"
    results_dir.mkdir()

    return {
        "template_dir": template_dir,
        "results_dir": results_dir,
        "base_dir": tmp_path,
    }


def test_worker_eval_task_mock_failure(temp_project, monkeypatch):
    """Test worker handles failure gracefully and returns structured dict."""
    task = {
        "candidate_idx": 0,
        "parameters": [0.2, 1.0, -1.0, 0.0, 0.0, 0.0],
        "run_id": "test_run",
        "eval_id": 1,
        "base_results_dir": str(temp_project["results_dir"]),
        "template_dir": str(temp_project["template_dir"]),
        "template_in": "astra.in",
        "timeout": 5,
        "retries": 1,
    }

    # Mock run_astra_eval to simulate failure
    def mock_run_astra_eval(**kwargs):
        return {
            "status": "failed",
            "objectives": None,
            "diagnostics": None,
            "eval_dir": str(temp_project["results_dir"] / "test_run" / "work" / "eval_000001"),
            "manifest_path": None,
            "error": "Simulated ASTRA failure",
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    res = _worker_eval_task(task)

    assert res["candidate_idx"] == 0
    assert res["status"] == "failed"
    assert res["error"] == "Simulated ASTRA failure"
    assert res["retries_attempted"] == 1


def test_parallel_deterministic_order_and_alignment(temp_project, monkeypatch):
    """Verify that results order strictly matches candidate input order regardless of worker finish time."""
    candidates = [
        [0.20, 1.0, -1.0, 0.0, 0.0, 0.0],
        [0.22, 1.2, -1.2, 5.0, 2.0, 2.0],
        [0.25, 1.5, -1.5, 10.0, 5.0, 5.0],
        [0.28, 1.8, -1.8, 15.0, 8.0, 8.0],
    ]

    def mock_run_astra_eval(parameters, run_id, eval_id, base_results_dir, **kwargs):
        cand_val = parameters[0]
        eval_path = Path(base_results_dir) / run_id / "work" / str(eval_id)
        eval_path.mkdir(parents=True, exist_ok=True)
        return {
            "status": "success",
            "objectives": {"norm_emit_x": cand_val * 1e-6, "norm_emit_y": cand_val * 1e-6, "sigma_energy": 0.01},
            "diagnostics": {"emit_x": cand_val * 1e-6},
            "eval_dir": str(eval_path),
            "manifest_path": str(eval_path / "manifest.json"),
            "error": None,
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    results = evaluate_candidates_parallel(
        candidates=candidates,
        run_id="order_test",
        max_workers=4,
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
    )

    assert len(results) == 4
    for i, res in enumerate(results):
        assert res["candidate_idx"] == i
        assert res["manifest"] is not None if "manifest" in res else True
        assert res["objectives"]["norm_emit_x"] == pytest.approx(candidates[i][0] * 1e-6)


def test_partial_failure_resilience(temp_project, monkeypatch):
    """Ensure a single failed candidate does not crash or cancel remaining batch candidates."""
    candidates = [
        [0.20, 1.0, -1.0, 0.0, 0.0, 0.0],  # Success
        [0.99, 9.9, -9.9, 0.0, 0.0, 0.0],  # Fail
        [0.25, 1.5, -1.5, 10.0, 5.0, 5.0], # Success
    ]

    def mock_run_astra_eval(parameters, **kwargs):
        if parameters[0] == 0.99:
            return {
                "status": "failed",
                "objectives": None,
                "diagnostics": None,
                "eval_dir": "/tmp/dummy",
                "manifest_path": None,
                "error": "Simulated divergence error",
            }
        return {
            "status": "success",
            "objectives": {"norm_emit_x": 1e-6, "norm_emit_y": 1e-6, "sigma_energy": 0.01},
            "diagnostics": {"emit_x": 1e-6},
            "eval_dir": "/tmp/dummy",
            "manifest_path": None,
            "error": None,
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    results = evaluate_candidates_parallel(
        candidates=candidates,
        run_id="resilience_test",
        max_workers=2,
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
    )

    assert len(results) == 3
    assert results[0]["status"] == "success"
    assert results[1]["status"] == "failed"
    assert results[1]["error"] == "Simulated divergence error"
    assert results[2]["status"] == "success"


def test_serial_and_parallel_agreement(temp_project, monkeypatch):
    """Verify that serial execution (max_workers=1) and parallel execution return identical results."""
    candidates = [
        [0.20, 1.0, -1.0, 0.0, 0.0, 0.0],
        [0.22, 1.2, -1.2, 5.0, 2.0, 2.0],
    ]

    def mock_run_astra_eval(parameters, eval_id, **kwargs):
        return {
            "status": "success",
            "objectives": {"norm_emit_x": parameters[0], "norm_emit_y": parameters[1], "sigma_energy": 0.01},
            "diagnostics": {},
            "eval_dir": f"/tmp/eval_{eval_id}",
            "manifest_path": None,
            "error": None,
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    serial_res = evaluate_candidates_parallel(
        candidates=candidates,
        run_id="test_serial",
        max_workers=1,
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
    )

    parallel_res = evaluate_candidates_parallel(
        candidates=candidates,
        run_id="test_parallel",
        max_workers=2,
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
    )

    assert len(serial_res) == len(parallel_res)
    for s, p in zip(serial_res, parallel_res):
        assert s["status"] == p["status"]
        assert s["objectives"] == p["objectives"]
        assert s["candidate_idx"] == p["candidate_idx"]


def test_batch_evaluator_class(temp_project, monkeypatch):
    """Test BatchEvaluator class encapsulation."""
    evaluator = BatchEvaluator(
        base_results_dir=temp_project["results_dir"],
        template_dir=temp_project["template_dir"],
        max_workers=2,
        timeout=15,
    )

    def mock_run_astra_eval(parameters, **kwargs):
        return {
            "status": "success",
            "objectives": {"norm_emit_x": 1.0, "norm_emit_y": 1.0, "sigma_energy": 0.01},
            "diagnostics": {},
            "eval_dir": "/tmp/dummy",
            "manifest_path": None,
            "error": None,
        }

    monkeypatch.setattr("mobo_linac.execution.parallel.run_astra_eval", mock_run_astra_eval)

    candidates = [[0.20, 1.0, -1.0, 0.0, 0.0, 0.0]]
    results = evaluator.evaluate_batch(candidates, run_id="batch_class_test")
    assert len(results) == 1
    assert results[0]["status"] == "success"


@pytest.mark.integration
def test_real_parallel_astra_evaluations():
    """
    Integration test executing multiple real ASTRA simulations in parallel processes.
    """
    root_dir = Path(__file__).resolve().parents[1]
    if not (root_dir / "gun.dat").exists() or not (root_dir / "astra.in").exists():
        pytest.skip("Root ASTRA files not present")

    candidates = [
        [0.21, 1.1, -1.1, 0.0, 0.0, 0.0],
        [0.24, 1.3, -1.3, 4.0, 1.0, 1.0],
    ]

    evaluator = BatchEvaluator(
        base_results_dir="results",
        template_dir=root_dir,
        max_workers=2,
        timeout=30,
    )

    results = evaluator.evaluate_batch(candidates, run_id="integration_parallel_run")

    assert len(results) == 2
    for idx, res in enumerate(results):
        assert res["candidate_idx"] == idx
        assert res["status"] == "success"
        assert res["objectives"] is not None
        assert "norm_emit_x" in res["objectives"]
        assert Path(res["manifest_path"]).exists()
