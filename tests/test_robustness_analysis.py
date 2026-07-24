"""
Unit tests for Machine and Beam Robustness Analysis (Task 07).
"""

import pytest
import numpy as np

from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.robustness.evaluator import (
    compute_robustness_summary,
    generate_perturbed_parameters,
    select_representative_pareto_candidates,
)


@pytest.fixture
def sample_pareto_results():
    results = []
    for i in range(1, 6):
        res = EvaluationResult(
            evaluation_id=f"eval_{i}",
            run_id="test_run",
            x_physical=[0.19 + 0.01 * i, 1.2, -2.8, 35.0, -39.0, 310.0],
            objectives_physical=[1.0e-6 * i, 2.0e-6 / i, 0.2e6 * i],
            objectives_model=[-1.0e-6 * i, -2.0e-6 / i, -0.2e6 * i],
            diagnostics={
                "sigma_x_m": 0.5e-3,
                "sigma_y_m": 0.5e-3,
                "sigma_xp_rad": 0.5e-3,
                "sigma_yp_rad": 0.5e-3,
                "sigma_z_m": 0.5e-3,
                "mean_kinetic_energy_eV": 200.0e6,
                "transmission_fraction": 1.0,
            },
            simulation_valid=True,
            physically_feasible=True,
            failure_category=FailureCategory.SUCCESS.value,
        )
        results.append(res)
    return results


def test_select_representative_pareto_candidates(sample_pareto_results):
    """Verify representative Pareto candidate selection."""
    candidates = select_representative_pareto_candidates(sample_pareto_results)

    assert "min_emit_x" in candidates
    assert "min_emit_y" in candidates
    assert "min_sigma_energy" in candidates
    assert "knee_point" in candidates
    assert "balanced" in candidates

    # min_emit_x should be eval_1 (1.0e-6)
    assert candidates["min_emit_x"].evaluation_id == "eval_1"
    # min_sigma_energy should be eval_1 (0.2e6)
    assert candidates["min_sigma_energy"].evaluation_id == "eval_1"
    # min_emit_y should be eval_5 (2.0e-6 / 5 = 0.4e-6)
    assert candidates["min_emit_y"].evaluation_id == "eval_5"


def test_generate_perturbed_parameters():
    """Verify perturbed design vector generation."""
    nominal_x = [0.194, 1.28, -2.88, 35.6, -39.5, 310.0]
    num_samples = 20

    perturbed = generate_perturbed_parameters(nominal_x, num_perturbations=num_samples, seed=42)
    assert len(perturbed) == num_samples
    assert len(perturbed[0]) == 6

    # Verify reproducibility with same seed
    perturbed_b = generate_perturbed_parameters(nominal_x, num_perturbations=num_samples, seed=42)
    assert perturbed == perturbed_b


def test_compute_robustness_summary(sample_pareto_results):
    """Verify calculation of robustness statistics and fragile classification."""
    nominal = sample_pareto_results[0]
    perturbed_list = []

    # 8 feasible, 2 infeasible
    for i in range(10):
        is_feas = i < 8
        res = EvaluationResult(
            evaluation_id=f"pert_{i}",
            run_id="test_run",
            x_physical=nominal.x_physical,
            objectives_physical=[1.05e-6, 1.05e-6, 0.21e6] if is_feas else [2.5e-6, 2.5e-6, 0.5e6],
            simulation_valid=True,
            physically_feasible=is_feas,
            failure_category=FailureCategory.SUCCESS.value if is_feas else FailureCategory.INFEASIBLE_BEAM.value,
        )
        perturbed_list.append(res)

    summary = compute_robustness_summary("knee_point", nominal, perturbed_list)

    assert summary["candidate_label"] == "knee_point"
    assert summary["probability_of_feasibility"] == pytest.approx(0.80)
    assert summary["mean_emit_x"] > 0
    assert summary["is_fragile"] is False
