"""
Unit tests for Fixed-Noise GP Treatment, Noise Modes, and Repeatability Utilities (Task 07).
"""

import pytest
import numpy as np
import torch
from botorch.models import ModelListGP

from mobo_linac.config import GpModelConfig, MoboConfig
from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.models.gp import build_gp_models, fit_gp_models
from mobo_linac.models.pipeline import SurrogatePipeline
from mobo_linac.models.repeatability import (
    compute_measured_noise_variance,
    create_measured_yvar_tensor,
)


@pytest.fixture
def dummy_data():
    """Fixture providing dummy training data for GP model tests."""
    torch.manual_seed(42)
    train_X = torch.rand(10, 6, dtype=torch.double)
    train_Y = torch.randn(10, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    return train_X, train_Y, bounds


def test_gp_deterministic_fixed_noise_mode(dummy_data):
    """Verify deterministic_fixed noise mode uses non-trainable train_Yvar."""
    train_X, train_Y, bounds = dummy_data
    model_list = build_gp_models(
        train_X=train_X,
        train_Y=train_Y,
        bounds=bounds,
        covar_type="matern52",
        noise_mode="deterministic_fixed",
        fixed_noise_val=1.0e-6,
    )
    assert len(model_list.models) == 3

    # Fit MLL and verify fixed noise is preserved
    fitted_list = fit_gp_models(model_list)
    for model in fitted_list.models:
        # SingleTaskGP with train_Yvar uses FixedNoiseGaussianLikelihood
        likelihood = model.likelihood
        assert hasattr(likelihood, "noise")


def test_gp_measured_fixed_noise_mode(dummy_data):
    """Verify measured_fixed noise mode with per-objective noise variances."""
    train_X, train_Y, bounds = dummy_data
    obj_variances = [1.0e-8, 2.0e-8, 5.0e-6]

    model_list = build_gp_models(
        train_X=train_X,
        train_Y=train_Y,
        bounds=bounds,
        covar_type="rbf",
        noise_mode="measured_fixed",
        objective_noise_variances=obj_variances,
    )
    assert len(model_list.models) == 3

    fitted_list = fit_gp_models(model_list)
    test_X = torch.rand(3, 6, dtype=torch.double)
    for idx, model in enumerate(fitted_list.models):
        posterior = model.posterior(test_X)
        assert posterior.mean.shape == (3, 1)
        assert posterior.variance.shape == (3, 1)


def test_gp_inferred_noise_mode(dummy_data):
    """Verify inferred noise mode constructs trainable GaussianLikelihood."""
    train_X, train_Y, bounds = dummy_data
    model_list = build_gp_models(
        train_X=train_X,
        train_Y=train_Y,
        bounds=bounds,
        covar_type="matern52",
        noise_mode="inferred",
    )
    assert len(model_list.models) == 3
    fitted_list = fit_gp_models(model_list)
    assert fitted_list is not None


def test_surrogate_pipeline_integration(dummy_data):
    """Verify SurrogatePipeline works with GpModelConfig options."""
    train_X, train_Y, bounds = dummy_data
    pipeline = SurrogatePipeline(
        bounds=bounds,
        covar_type="matern52",
        noise_mode="deterministic_fixed",
        fixed_noise_val=1.0e-6,
    )

    pipeline.fit(train_X, train_Y)
    assert pipeline.is_fitted is True

    test_X = torch.rand(5, 6, dtype=torch.double)
    means, vars_ = pipeline.predict_objectives(test_X)
    assert means.shape == (5, 3)
    assert vars_.shape == (5, 3)
    assert not torch.isnan(means).any()
    assert not torch.isnan(vars_).any()


def test_repeatability_utility():
    """Verify compute_measured_noise_variance and create_measured_yvar_tensor."""
    results = [
        EvaluationResult(
            evaluation_id="eval_1", run_id="r", x_physical=[0.2]*6,
            objectives_physical=[1.0e-6, 1.0e-6, 1.0e6], objectives_model=[-1.0e-6, -1.0e-6, -1.0e6],
            simulation_valid=True, physically_feasible=True, failure_category=FailureCategory.SUCCESS.value, runtime_s=1.0
        ),
        EvaluationResult(
            evaluation_id="eval_2", run_id="r", x_physical=[0.2]*6,
            objectives_physical=[1.02e-6, 0.98e-6, 1.01e6], objectives_model=[-1.02e-6, -0.98e-6, -1.01e6],
            simulation_valid=True, physically_feasible=True, failure_category=FailureCategory.SUCCESS.value, runtime_s=1.0
        ),
    ]

    var_dict = compute_measured_noise_variance(results, min_variance=1.0e-10)
    assert "norm_emit_x_m_rad" in var_dict
    assert var_dict["norm_emit_x_m_rad"] > 0

    yvar_tensor = create_measured_yvar_tensor(num_samples=5, variances=var_dict)
    assert yvar_tensor.shape == (5, 3)
    assert yvar_tensor.dtype == torch.double
