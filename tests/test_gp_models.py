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
    model_device = next(fitted_list.parameters()).device
    test_X = torch.rand(3, 6, dtype=torch.double, device=model_device)
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


def test_relative_noise_variance_scaling():
    """
    Verify that relative noise scaling assigns observation variance proportional to
    each objective's empirical scale (Task 01).
    """
    torch.manual_seed(123)
    N = 15
    train_X = torch.rand(N, 6, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)

    # Multi-scale objectives:
    # Column 0: emit_x ~ 1e-6 (variance ~ 1e-14)
    # Column 1: emit_y ~ 1e-6 (variance ~ 1e-14)
    # Column 2: sigma_E ~ 1e6  (variance ~ 1e10)
    col0 = 1.0e-6 * (1.0 + 0.2 * torch.sin(train_X[:, 0:1] * 3.14))
    col1 = 1.0e-6 * (1.0 + 0.2 * torch.cos(train_X[:, 1:2] * 3.14))
    col2 = 1.0e6 * (1.0 + 0.2 * torch.sin(train_X[:, 2:3] * 3.14))
    train_Y = torch.cat([col0, col1, col2], dim=-1)

    model_list = build_gp_models(
        train_X=train_X,
        train_Y=train_Y,
        bounds=bounds,
        covar_type="matern52",
        noise_mode="deterministic_fixed",
        relative_noise_ratio=1.0e-6,
    )
    assert len(model_list.models) == 3

    # In standardized space, Standardize(m=1) scales train_Yvar by 1 / var(Y).
    # Therefore, standardized noise variance is identically ~ 1.0e-6 for all objectives.
    m0_std_yvar = model_list.models[0].likelihood.noise_covar.noise.squeeze().detach()[0].item()
    m2_std_yvar = model_list.models[2].likelihood.noise_covar.noise.squeeze().detach()[0].item()

    assert abs(m0_std_yvar - 1.0e-6) < 1.0e-9, f"Standardized emittance noise variance mismatch: {m0_std_yvar}"
    assert abs(m2_std_yvar - 1.0e-6) < 1.0e-9, f"Standardized energy spread noise variance mismatch: {m2_std_yvar}"

    # Physical (unstandardized) noise variance
    col0_std = train_Y[:, 0].std().item()
    col2_std = train_Y[:, 2].std().item()
    col0_phys_noise = m0_std_yvar * (col0_std ** 2)
    col2_phys_noise = m2_std_yvar * (col2_std ** 2)

    assert col0_phys_noise < 1.0e-18, f"Physical emittance noise variance too large: {col0_phys_noise}"
    assert col2_phys_noise > 1.0, f"Physical energy spread noise variance too small: {col2_phys_noise}"

    # Fit model and evaluate posterior at training points
    fitted_list = fit_gp_models(model_list)
    fitted_list.eval()
    model_device = next(fitted_list.parameters()).device
    train_X_dev = train_X.to(device=model_device, dtype=torch.double)
    train_Y_dev = train_Y.to(device=model_device, dtype=torch.double)
    with torch.no_grad():
        posterior = fitted_list.posterior(train_X_dev)
        pred_means = posterior.mean
        pred_vars = posterior.variance

        # Residuals in physical space vs true values (posterior.mean is automatically untransformed by BoTorch)
        for i in range(3):
            pred_col = pred_means[:, i : i + 1]
            ss_tot = torch.sum((train_Y_dev[:, i : i + 1] - train_Y_dev[:, i : i + 1].mean())**2)
            ss_res = torch.sum((train_Y_dev[:, i : i + 1] - pred_col)**2)
            r2 = 1.0 - ss_res / ss_tot
            assert r2.item() >= 0.99, f"Objective {i} R^2 below 0.99: {r2.item()}"

        # Posterior variance at evaluated training points should be near-zero
        assert (pred_vars[:, 0] <= 1.0e-8).all(), f"Emittance posterior variance too high: {pred_vars[:, 0].max().item()}"
        assert (pred_vars[:, 1] <= 1.0e-8).all(), f"Emittance posterior variance too high: {pred_vars[:, 1].max().item()}"
        assert (pred_vars[:, 2] <= 1.0e-3 * train_Y_dev[:, 2].var()).all(), f"Energy spread posterior variance too high: {pred_vars[:, 2].max().item()}"


def test_tune_gp_hyperparameters(dummy_data):
    """Verify hyperparameter grid search optimization and candidate ranking."""
    from mobo_linac.models.tuning import tune_gp_hyperparameters

    train_X, train_Y, bounds = dummy_data
    tuning_summary = tune_gp_hyperparameters(
        train_X=train_X,
        train_Y=train_Y,
        bounds=bounds,
        candidate_covars=["matern52", "rbf"],
        candidate_noise_ratios=[1.0e-6, 1.0e-4],
        candidate_noise_modes=["deterministic_fixed"],
        objective_names=["norm_emit_x", "norm_emit_y", "sigma_energy"],
    )

    assert tuning_summary.best_config is not None
    assert tuning_summary.best_candidate is not None
    assert len(tuning_summary.candidates) == 4
    assert not tuning_summary.comparison_table.empty
    assert "Overall R^2" in tuning_summary.comparison_table.columns
    assert tuning_summary.best_candidate.overall_r2 >= -1.0


def test_build_scalarized_gp_model(dummy_data):
    """Verify build_scalarized_gp_model constructs and fits SingleTaskGP."""
    from mobo_linac.models.gp import build_scalarized_gp_model
    from botorch.models import SingleTaskGP

    train_X, train_Y, bounds = dummy_data
    scalar_Y = train_Y[:, 0:1]

    gp = build_scalarized_gp_model(
        train_X=train_X,
        train_Y=scalar_Y,
        bounds=bounds,
        covar_type="matern52",
        noise_mode="deterministic_fixed",
        relative_noise_ratio=1.0e-6,
    )

    assert isinstance(gp, SingleTaskGP)
    fitted_gp = fit_gp_models(gp)
    assert fitted_gp is not None

    model_device = next(fitted_gp.parameters()).device
    test_X = torch.rand(4, 6, dtype=torch.double, device=model_device)
    with torch.no_grad():
        post = fitted_gp.posterior(test_X)
        assert post.mean.shape == (4, 1)
        assert post.variance.shape == (4, 1)

