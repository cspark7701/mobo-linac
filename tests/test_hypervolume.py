"""
Unit tests for Fixed Reporting Reference Point and Hypervolume Audit (Task 06).
"""

import numpy as np
import pytest
import torch

from mobo_linac.metrics.hypervolume import (
    HypervolumeTracker,
    compute_hypervolume,
    compute_reference_point,
    validate_reference_point_compatibility,
)


def test_analytical_hypervolume_3d_box():
    """Verify hypervolume calculation against exact analytical 3D box calculation."""
    ref_point = torch.tensor([-10.0, -10.0, -10.0], dtype=torch.double)

    # Point 1: [-1, -2, -3] -> lengths from ref: [9, 8, 7] -> box 1 volume = 504
    # Point 2: [-2, -1, -3] -> lengths from ref: [8, 9, 7] -> box 2 volume = 504
    # Intersection box: [-2, -2, -3] -> lengths from ref: [8, 8, 7] -> volume = 448
    # Total volume = 504 + 504 - 448 = 560
    Y = torch.tensor(
        [
            [-1.0, -2.0, -3.0],
            [-2.0, -1.0, -3.0],
        ],
        dtype=torch.double,
    )

    volume = compute_hypervolume(Y, ref_point)
    assert volume == pytest.approx(560.0)


def test_hypervolume_nonnegative_and_empty():
    """Verify hypervolume is always >= 0.0 and 0.0 for empty/worse-than-ref points."""
    ref_point = torch.tensor([-1.0, -1.0, -1.0], dtype=torch.double)

    # Empty candidate tensor
    empty_Y = torch.empty((0, 3), dtype=torch.double)
    assert compute_hypervolume(empty_Y, ref_point) == 0.0

    # Points worse than ref_point
    worse_Y = torch.tensor([[-2.0, -2.0, -2.0]], dtype=torch.double)
    assert compute_hypervolume(worse_Y, ref_point) == 0.0


def test_fixed_reporting_ref_point_immutability():
    """Verify reporting reference point remains fixed throughout tracking iterations."""
    ref_point = torch.tensor([-1.0e-4, -1.0e-4, -1.0e7], dtype=torch.double)
    tracker = HypervolumeTracker(reporting_ref_point=ref_point)

    # Initial samples
    train_Y_iter1 = torch.tensor([[-1.0e-6, -1.0e-6, -1.0e5]], dtype=torch.double)
    train_feas_iter1 = torch.tensor([True], dtype=torch.bool)

    rec1 = tracker.track_iteration(1, train_Y_iter1, train_feas_iter1)

    # Iteration 2 with additional samples
    train_Y_iter2 = torch.tensor(
        [
            [-1.0e-6, -1.0e-6, -1.0e5],
            [-0.5e-6, -0.5e-6, -0.5e5],
        ],
        dtype=torch.double,
    )
    train_feas_iter2 = torch.tensor([True, True], dtype=torch.bool)

    rec2 = tracker.track_iteration(2, train_Y_iter2, train_feas_iter2)

    # Reporting reference point must NOT change between iterations
    assert rec1["reporting_ref_point_model"] == rec2["reporting_ref_point_model"]
    assert tracker.reporting_ref_point.tolist() == ref_point.tolist()

    # Hypervolume must increase or stay non-decreasing
    assert rec2["feasible_hypervolume"] >= rec1["feasible_hypervolume"]


def test_reference_point_compatibility_validation():
    """Verify validation rejects incompatible reporting reference points."""
    ref_a = [-1.0e-4, -1.0e-4, -1.0e7]
    ref_b = [-1.0e-4, -1.0e-4, -1.0e7]
    ref_incompatible = [-2.0e-4, -1.0e-4, -1.0e7]

    assert validate_reference_point_compatibility(ref_a, ref_b) is True
    assert validate_reference_point_compatibility(ref_a, ref_incompatible, raise_on_incompatible=False) is False

    with pytest.raises(ValueError, match="Incompatible reporting reference points"):
        validate_reference_point_compatibility(ref_a, ref_incompatible, raise_on_incompatible=True)


def test_compute_reference_point_generation():
    """Test generating a reference point with safety offset from initial samples."""
    train_Y = torch.tensor(
        [
            [-1.0e-6, -2.0e-6, -3.0e5],
            [-2.0e-6, -1.0e-6, -4.0e5],
        ],
        dtype=torch.double,
    )

    ref_point = compute_reference_point(train_Y, offset_ratio=0.10)

    # All initial samples must strictly dominate the generated reference point in model space
    assert (train_Y > ref_point).all()
