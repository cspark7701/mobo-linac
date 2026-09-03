"""
Unit tests for Canonical Mock Evaluator Infrastructure (Task 19).
"""

from pathlib import Path
import pytest

from mobo_linac.execution.mock import MockBatchEvaluator


def test_mock_batch_evaluator_callable(tmp_path):
    """Verify MockBatchEvaluator callable interface produces valid dictionary."""
    evaluator = MockBatchEvaluator(run_dir=tmp_path)
    res = evaluator([0.2, 1.0, -1.0, 0.0, 0.0, 0.0], run_id="test_run", eval_id=1)

    assert res["status"] == "success"
    assert res["eval_id"] == "eval_000001"
    assert res["run_id"] == "test_run"
    assert "norm_emit_x" in res["objectives"]
    assert "sigma_energy" in res["objectives"]
    assert res["diagnostics"]["transmission_fraction"] == 1.0
    assert res["diagnostics"]["mean_kinetic_energy_eV"] == 200.0e6


def test_mock_batch_evaluator_batch_and_callback(tmp_path):
    """Verify batch evaluation and real-time streaming callback triggering."""
    evaluator = MockBatchEvaluator(run_dir=tmp_path)
    cands = [
        [0.2, 1.0, -1.0, 0.0, 0.0, 0.0],
        [0.25, 0.9, -0.9, 1.0, 1.0, 0.0],
        [0.18, 1.1, -1.1, -1.0, -1.0, 0.0],
    ]

    callback_records = []

    def on_done(res):
        callback_records.append(res["eval_id"])

    results = evaluator.evaluate_batch(
        cands,
        run_id="stream_test",
        eval_ids=[10, 20, 30],
        on_evaluation_complete=on_done,
    )

    assert len(results) == 3
    assert len(callback_records) == 3
    assert results[0]["eval_id"] == "eval_000010"
    assert results[1]["eval_id"] == "eval_000020"
    assert results[2]["eval_id"] == "eval_000030"
    assert callback_records == ["eval_000010", "eval_000020", "eval_000030"]


def test_mock_batch_evaluator_failure_injection(tmp_path):
    """Verify targeted failure injection on specific evaluation IDs."""
    evaluator = MockBatchEvaluator(run_dir=tmp_path, fail_eval_ids=["eval_000002"])
    results = evaluator.evaluate_batch(
        [[0.2, 1.0, -1.0, 0.0, 0.0, 0.0], [0.25, 0.9, -0.9, 1.0, 1.0, 0.0]],
        run_id="fail_test",
        eval_ids=[1, 2],
    )

    assert results[0]["status"] == "success"
    assert results[1]["status"] == "failed"
    assert results[1]["error"] is not None
