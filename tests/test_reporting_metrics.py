"""
Unit tests for Standardized Reporting Metrics, Objective Normalization, and Known-Answer Hypervolume (Task 05).
"""

import pytest
import numpy as np
import pandas as pd
import torch

from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.metrics.reporting import (
    DEFAULT_REPORTING_REF_POINT_MODEL_NORM,
    compute_campaign_metrics_history,
    compute_normalized_hypervolume,
    normalize_objectives_model,
    normalize_objectives_physical,
    validate_campaign_compatibility,
)


def test_known_answer_hypervolume_single_point_3d():
    """Verify analytical known-answer hypervolume calculation for a single 3D point."""
    # Point at (0, 0, 0) in normalized model space
    # Reference point at (-2, -2, -2) in normalized model space
    # Expected volume = (0 - (-2)) * (0 - (-2)) * (0 - (-2)) = 2 * 2 * 2 = 8.0
    train_Y_model_norm = torch.tensor([[0.0, 0.0, 0.0]], dtype=torch.double)
    ref_point_norm = torch.tensor([-2.0, -2.0, -2.0], dtype=torch.double)

    # In compute_normalized_hypervolume, train_Y_model is passed unnormalized if scales are 1.0
    hv = compute_normalized_hypervolume(
        train_Y_model=train_Y_model_norm,
        ref_point_model_norm=ref_point_norm,
        scales=[1.0, 1.0, 1.0],
    )
    assert hv == pytest.approx(8.0)


def test_known_answer_hypervolume_two_points_2d():
    """Verify analytical known-answer hypervolume for two 2D Pareto non-dominated points."""
    # Point 1: (-1.0, -2.0), Point 2: (-2.0, -1.0)
    # Ref point: (-3.0, -3.0)
    # Hypervolume area = area(P1 box) + area(P2 box) - area(overlap)
    # P1 box: [-1 - (-3)] * [-2 - (-3)] = 2 * 1 = 2.0
    # P2 box: [-2 - (-3)] * [-1 - (-3)] = 1 * 2 = 2.0
    # Overlap box: [-2 - (-3)] * [-2 - (-3)] = 1 * 1 = 1.0
    # Total HV = 2.0 + 2.0 - 1.0 = 3.0
    train_Y_2d = torch.tensor([[-1.0, -2.0], [-2.0, -1.0]], dtype=torch.double)
    ref_2d = torch.tensor([-3.0, -3.0], dtype=torch.double)

    hv = compute_normalized_hypervolume(
        train_Y_model=train_Y_2d,
        ref_point_model_norm=ref_2d,
        scales=[1.0, 1.0],
    )
    assert hv == pytest.approx(3.0)


def test_objective_normalization_scales():
    """Verify objective normalization with fixed engineering scale factors."""
    phys_objs = [1.2e-6, 1.5e-6, 4.0e5]  # [1.2 um.rad, 1.5 um.rad, 0.4 MeV]
    scales = [1.0e-6, 1.0e-6, 1.0e6]

    norm_phys = normalize_objectives_physical(phys_objs, scales)
    assert norm_phys.tolist() == pytest.approx([1.2, 1.5, 0.4])

    model_objs = [-1.2e-6, -1.5e-6, -4.0e5]
    norm_model = normalize_objectives_model(model_objs, scales)
    assert norm_model.tolist() == pytest.approx([-1.2, -1.5, -0.4])


def test_campaign_metrics_history_computation():
    """Verify computation of cumulative campaign metrics dataframe."""
    results = [
        EvaluationResult(
            evaluation_id="eval_1", run_id="r", x_physical=[0.2]*6,
            objectives_physical=[1.0e-6, 1.0e-6, 0.5e6], objectives_model=[-1.0e-6, -1.0e-6, -0.5e6],
            simulation_valid=True, physically_feasible=True, failure_category=FailureCategory.SUCCESS.value, runtime_s=2.0
        ),
        EvaluationResult(
            evaluation_id="eval_2", run_id="r", x_physical=[0.2]*6,
            objectives_physical=None, objectives_model=None,
            simulation_valid=False, physically_feasible=False, failure_category=FailureCategory.ASTRA_TIMEOUT.value, runtime_s=30.0
        ),
        EvaluationResult(
            evaluation_id="eval_3", run_id="r", x_physical=[0.2]*6,
            objectives_physical=[0.8e-6, 0.8e-6, 0.4e6], objectives_model=[-0.8e-6, -0.8e-6, -0.4e6],
            simulation_valid=True, physically_feasible=True, failure_category=FailureCategory.SUCCESS.value, runtime_s=2.5
        ),
    ]

    df = compute_campaign_metrics_history(results)
    assert len(df) == 3
    assert list(df["cumulative_astra_evaluations"]) == [1, 2, 3]
    assert df["invalid_run_count"].iloc[-1] == 1
    assert df["first_feasible_eval_index"].iloc[0] == 1
    assert df["first_feasible_eval_index"].iloc[-1] == 1
    assert df["feasible_fraction"].iloc[-1] == pytest.approx(2.0 / 3.0)
    assert df["total_wallclock_s"].iloc[-1] == pytest.approx(34.5)


def test_campaign_compatibility_verification():
    """Verify cross-run metrics compatibility checking."""
    meta_a = {
        "objective_scales": [1e-6, 1e-6, 1e6],
        "reporting_ref_point": [-10.0, -10.0, -10.0],
    }
    meta_b = {
        "objective_scales": [1e-6, 1e-6, 1e6],
        "reporting_ref_point": [-10.0, -10.0, -10.0],
    }
    meta_incompat = {
        "objective_scales": [1e-6, 1e-6, 1e6],
        "reporting_ref_point": [-5.0, -5.0, -5.0],
    }

    assert validate_campaign_compatibility(meta_a, meta_b) is True
    assert validate_campaign_compatibility(meta_a, meta_incompat, raise_on_incompatible=False) is False

    with pytest.raises(ValueError):
        validate_campaign_compatibility(meta_a, meta_incompat, raise_on_incompatible=True)
