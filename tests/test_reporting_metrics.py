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

    df = compute_campaign_metrics_history(results, elapsed_wall_times=[1.0, 2.0, 3.0])
    assert len(df) == 3
    assert list(df["cumulative_astra_evaluations"]) == [1, 2, 3]
    assert df["invalid_run_count"].iloc[-1] == 1
    assert df["first_feasible_eval_index"].iloc[0] == 1
    assert df["first_feasible_eval_index"].iloc[-1] == 1
    assert df["feasible_fraction"].iloc[-1] == pytest.approx(2.0 / 3.0)
    assert df["total_wallclock_s"].iloc[-1] == pytest.approx(3.0)
    assert df["total_simulation_runtime_s"].iloc[-1] == pytest.approx(34.5)


def test_campaign_compatibility_verification():
    """Verify cross-run metrics compatibility checking."""
    from copy import deepcopy
    from mobo_linac.config import load_config
    from mobo_linac.metrics.reporting import reporting_metadata
    meta_a = reporting_metadata(load_config("configs/mobo_200MeV.yaml"), [-1e-5, -1e-5, -1e7])
    meta_b = deepcopy(meta_a)
    meta_incompat = deepcopy(meta_a)
    meta_incompat["reporting_ref_point"] = [-5e-6, -5e-6, -5e6]
    meta_incompat["reporting_ref_point_normalized"] = [-5.0, -5.0, -5.0]

    assert validate_campaign_compatibility(meta_a, meta_b) is True
    assert validate_campaign_compatibility(meta_a, meta_incompat, raise_on_incompatible=False) is False

    with pytest.raises(ValueError):
        validate_campaign_compatibility(meta_a, meta_incompat, raise_on_incompatible=True)


@pytest.mark.parametrize("field,value", [
    ("objective_units", ["mm", "m", "eV"]),
    ("objective_signs", [1, -1, -1]),
    ("objective_names", ["energy", "x", "y"]),
    ("constraint_profile", {"min_transmission": 0.1}),
    ("schema_version", 2),
])
def test_reporting_comparison_rejects_different_scientific_conventions(field, value):
    from copy import deepcopy
    from mobo_linac.config import load_config
    from mobo_linac.metrics.reporting import reporting_metadata
    meta = reporting_metadata(load_config("configs/mobo_200MeV.yaml"), [-1e-5, -1e-5, -1e6])
    other = deepcopy(meta)
    other[field] = value
    assert not validate_campaign_compatibility(meta, other, raise_on_incompatible=False)
    with pytest.raises(ValueError):
        validate_campaign_compatibility(meta, other)


def test_reporting_comparison_has_no_implicit_defaults_or_micro_scale_tolerance():
    from copy import deepcopy
    from mobo_linac.config import load_config
    from mobo_linac.metrics.reporting import reporting_metadata
    assert not validate_campaign_compatibility({}, {}, raise_on_incompatible=False)
    config = load_config("configs/mobo_200MeV.yaml")
    meta = reporting_metadata(config, [-1e-5, -1e-5, -1e6])
    config.objectives[0].reporting_scale = 1.01e-6
    other = reporting_metadata(config, [-1e-5, -1e-5, -1e6])
    assert not validate_campaign_compatibility(meta, other, raise_on_incompatible=False)


def test_worker_runtime_does_not_supply_unknown_wall_time():
    record = EvaluationResult(evaluation_id="e", run_id="r", x_physical=[0.0] * 6, runtime_s=8.0)
    frame = compute_campaign_metrics_history([record])
    assert pd.isna(frame.total_wallclock_s.iloc[0])
    assert frame.total_simulation_runtime_s.iloc[0] == 8.0
    assert compute_campaign_metrics_history([]).shape == (0, 9)


@pytest.mark.parametrize("device", ["cpu", "cuda:0"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_normalization_and_hypervolume_use_input_placement(device, dtype):
    if device.startswith("cuda") and not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    values = torch.tensor([[1e-6, 2e-6, 3e5]], device=device, dtype=dtype)
    for normalize in (normalize_objectives_physical, normalize_objectives_model):
        normalized = normalize(values)
        assert normalized.device == values.device
        assert normalized.dtype == values.dtype
        torch.testing.assert_close(normalized, values.new_tensor([[1.0, 2.0, 0.3]]))
    model = torch.zeros((1, 3), device=device, dtype=dtype)
    # CPU reference tensors must follow GPU observations, too.
    reference = torch.tensor([-2., -2., -2.], dtype=torch.double)
    assert compute_normalized_hypervolume(model, reference, scales=[1., 1., 1.]) == pytest.approx(8.)


def test_integer_objectives_retain_floating_normalization():
    values = torch.tensor([[1, 2, 3]], dtype=torch.int64)
    result = normalize_objectives_physical(values)
    assert result.dtype == torch.double
    torch.testing.assert_close(result, torch.tensor([[1e6, 2e6, 3e-6]], dtype=torch.double))
