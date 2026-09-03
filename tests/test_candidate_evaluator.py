"""
Unit tests for CandidateEvaluatorBase, RobustnessEvaluator, and ParetoVerifier.
"""

from pathlib import Path
import numpy as np
import pytest

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution.candidate_evaluator import (
    CandidateEvaluatorBase,
    EvaluationOutcome,
    EvaluationTask,
    compute_metric_deltas,
)
from mobo_linac.robustness.evaluator import RobustnessEvaluator
from mobo_linac.verification.verifier import ParetoVerifier


@pytest.fixture
def sample_candidate():
    return EvaluationResult(
        evaluation_id="eval_000001",
        run_id="test_run",
        x_physical=[0.2, 1.0, -1.0, -10.0, -5.0, 0.0],
        objectives_physical=[3.5e-6, 3.6e-6, 0.9e6],
        objectives_model=[-3.5e-6, -3.6e-6, -0.9e6],
        diagnostics={
            "sigma_x_m": 0.5e-3,
            "sigma_y_m": 0.5e-3,
            "sigma_xp_rad": 0.4e-3,
            "sigma_yp_rad": 0.4e-3,
            "sigma_z_m": 0.6e-3,
            "mean_kinetic_energy_eV": 200.0e6,
            "transmission_fraction": 1.0,
        },
        simulation_valid=True,
        physically_feasible=True,
    )


def test_compute_metric_deltas_identical(sample_candidate):
    """Verifies that identical nominal and rerun results yield 0% deltas."""
    deltas = compute_metric_deltas(sample_candidate, sample_candidate)
    assert deltas["diff_emit_x_pct"] == 0.0
    assert deltas["diff_emit_y_pct"] == 0.0
    assert deltas["diff_sigma_energy_pct"] == 0.0
    assert deltas["diff_transmission_pct"] == 0.0
    assert deltas["max_diff_pct"] == 0.0


def test_compute_metric_deltas_perturbed(sample_candidate):
    """Verifies correct calculation of percentage metric deltas."""
    perturbed = EvaluationResult(
        evaluation_id="eval_000002",
        run_id="test_run",
        x_physical=[0.2, 1.0, -1.0, -10.0, -5.0, 0.0],
        objectives_physical=[3.85e-6, 3.6e-6, 0.99e6],  # +10% emit_x, +10% sigma_e
        diagnostics={"transmission_fraction": 0.95},      # -5% transmission
        simulation_valid=True,
        physically_feasible=True,
    )
    deltas = compute_metric_deltas(sample_candidate, perturbed)
    assert pytest.approx(deltas["diff_emit_x_pct"], 1e-4) == 10.0
    assert pytest.approx(deltas["diff_emit_y_pct"], 1e-4) == 0.0
    assert pytest.approx(deltas["diff_sigma_energy_pct"], 1e-4) == 10.0
    assert pytest.approx(deltas["diff_transmission_pct"], 1e-4) == 5.0
    assert pytest.approx(deltas["max_diff_pct"], 1e-4) == 10.0


def test_robustness_evaluator_plan_and_execution(sample_candidate, tmp_path):
    """Verifies RobustnessEvaluator task plan generation and custom evaluator execution."""
    robust_eval = RobustnessEvaluator(base_output_dir=tmp_path / "robustness")
    tasks = robust_eval.generate_evaluation_plan([sample_candidate], num_perturbations=5, seed=42)
    assert len(tasks) == 5
    assert tasks[0].nominal_result == sample_candidate
    assert len(tasks[0].parameters) == 6

    def mock_eval(params, run_id, eval_id):
        return {
            "status": "success",
            "eval_id": eval_id,
            "run_id": run_id,
            "parameters": params,
            "objectives": {"norm_emit_x": 3.55e-6, "norm_emit_y": 3.65e-6, "sigma_energy": 0.92e6},
            "diagnostics": {
                "sigma_x_m": 0.5e-3,
                "sigma_y_m": 0.5e-3,
                "sigma_xp_rad": 0.4e-3,
                "sigma_yp_rad": 0.4e-3,
                "sigma_z_m": 0.6e-3,
                "transmission_fraction": 0.98,
                "mean_kinetic_energy_eV": 200.0e6,
            },
        }

    summaries = robust_eval.evaluate_candidates(
        candidates=[sample_candidate],
        num_perturbations=5,
        seed=42,
        custom_evaluator=mock_eval,
    )
    assert len(summaries) == 1
    assert summaries[0]["probability_of_feasibility"] == 1.0
    assert summaries[0]["robust_score"] > 0.0


def test_pareto_verifier_plan_and_execution(sample_candidate, tmp_path):
    """Verifies ParetoVerifier task plan generation and verification pipeline."""
    verifier = ParetoVerifier(base_output_dir=tmp_path / "verification")
    tasks = verifier.generate_evaluation_plan([sample_candidate], roles=["knee_point"])
    assert len(tasks) == 1
    assert tasks[0].role == "knee_point"

    def mock_eval(params, run_id, eval_id):
        return {
            "status": "success",
            "eval_id": eval_id,
            "run_id": run_id,
            "parameters": params,
            "objectives": {"norm_emit_x": 3.5001e-6, "norm_emit_y": 3.6001e-6, "sigma_energy": 0.9001e6},
            "diagnostics": {"transmission_fraction": 1.0, "mean_kinetic_energy": 200e6},
        }

    cands_dict = {"knee_point": sample_candidate}
    records, manifest_p, tex_p = verifier.verify_candidates(cands_dict, mock_evaluator=mock_eval)
    assert len(records) == 1
    assert records[0]["verification_status"] == "VERIFIED"
    assert manifest_p.exists()
    assert tex_p.exists()
