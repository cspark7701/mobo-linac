"""
Unit tests for Fixed-Noise GP Treatment, Noise Modes, and Repeatability Utilities.
"""

import pytest
import numpy as np
import torch

from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.models.gp import SurrogateSettings, build_gp_models, channel_record, fit_gp_models
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
        train_X, train_Y, bounds,
        SurrogateSettings(covar_type="matern52", noise_mode="deterministic_fixed", fixed_noise_variance=1.0e-6),
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
        train_X, train_Y, bounds,
        SurrogateSettings(covar_type="rbf", noise_mode="measured_fixed", objective_noise_variances=obj_variances),
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
        train_X, train_Y, bounds,
        SurrogateSettings(covar_type="matern52", noise_mode="inferred"),
    )
    assert len(model_list.models) == 3
    fitted_list = fit_gp_models(model_list)
    assert fitted_list is not None


def test_surrogate_pipeline_integration(dummy_data):
    """Verify SurrogatePipeline works with GpModelConfig options."""
    train_X, train_Y, bounds = dummy_data
    pipeline = SurrogatePipeline(
        bounds, SurrogateSettings(covar_type="matern52", noise_mode="deterministic_fixed", fixed_noise_variance=1.0e-6))

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

    from mobo_linac.config import load_config
    config = load_config("configs/mobo_200MeV.yaml")
    var_dict = compute_measured_noise_variance(results, config, min_relative_std=1.0e-6)
    assert "norm_emit_x_m_rad" in var_dict
    assert var_dict["norm_emit_x_m_rad"] > 0

    yvar_tensor = create_measured_yvar_tensor(num_samples=5, variances=var_dict, config=config)
    assert yvar_tensor.shape == (5, 3)
    assert yvar_tensor.dtype == torch.double


def test_relative_noise_variance_scaling():
    """
    Verify that relative noise scaling assigns observation variance proportional to
    each objective's empirical scale.
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
        train_X, train_Y, bounds,
        SurrogateSettings(covar_type="matern52", noise_mode="deterministic_fixed", relative_noise_ratio=1.0e-6),
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
    assert "LOO Log Predictive Density" in tuning_summary.comparison_table.columns
    assert tuning_summary.best_candidate.status == "SUCCESS"
    assert np.isfinite(tuning_summary.best_candidate.mean_loo_log_predictive_density)


def test_build_output_gp(dummy_data):
    """Verify build_output_gp constructs and fits one output's SingleTaskGP."""
    from mobo_linac.models.gp import build_output_gp
    from botorch.models import SingleTaskGP

    train_X, train_Y, bounds = dummy_data
    scalar_Y = train_Y[:, 0:1]

    gp = build_output_gp(train_X, scalar_Y, bounds,
                         SurrogateSettings(covar_type="matern52", noise_mode="deterministic_fixed",
                                           relative_noise_ratio=1.0e-6))

    assert isinstance(gp, SingleTaskGP)
    fitted_gp = fit_gp_models(gp)
    assert fitted_gp is not None

    model_device = next(fitted_gp.parameters()).device
    test_X = torch.rand(4, 6, dtype=torch.double, device=model_device)
    with torch.no_grad():
        post = fitted_gp.posterior(test_X)
        assert post.mean.shape == (4, 1)
        assert post.variance.shape == (4, 1)



def test_heteroscedastic_noise_precedence_and_scaling(dummy_data):
    X, Y, bounds = dummy_data
    noise = torch.arange(1, 31, dtype=torch.double).reshape(10, 3) * 0.01
    models = build_gp_models(X, Y, bounds, SurrogateSettings(noise_mode="measured_fixed",
                             objective_noise_variances=[0.9] * 3, fixed_noise_variance=0.8),
                             train_Yvar=noise, device="cpu")
    for index, model in enumerate(models.models):
        expected = noise[:, index] / Y[:, index].var()
        torch.testing.assert_close(model.likelihood.noise, expected)
        torch.testing.assert_close(channel_record(model).train_Yvar, noise[:, index:index+1])
    fit_gp_models(models)
    for index, model in enumerate(models.models):
        torch.testing.assert_close(model.likelihood.noise, noise[:, index] / Y[:, index].var())


@pytest.mark.parametrize("invalid", ["missing", "shape", "nan", "negative", "zero", "inferred", "partial"])
def test_noise_contract_rejects_invalid_inputs(dummy_data, invalid):
    X, Y, bounds = dummy_data
    noise = torch.full_like(Y, 0.01)
    kwargs = {"noise_mode": "measured_fixed", "train_Yvar": noise}
    if invalid == "missing":
        kwargs.pop("train_Yvar")
    elif invalid == "shape":
        kwargs["train_Yvar"] = noise[:-1]
    elif invalid in ("nan", "negative", "zero"):
        noise[0, 0] = {"nan": float("nan"), "negative": -1, "zero": 0}[invalid]
    elif invalid == "inferred":
        kwargs["noise_mode"] = "inferred"
    else:
        kwargs = {"objective_noise_variances": [0.1]}
    with pytest.raises(ValueError):
        train_Yvar = kwargs.pop("train_Yvar", None)
        build_gp_models(X, Y, bounds, SurrogateSettings(**kwargs), train_Yvar=train_Yvar)


@pytest.mark.parametrize("adam_succeeds", [False, True])
def test_fit_failures_restore_snapshot_before_fallback(dummy_data, monkeypatch, adam_succeeds):
    from copy import deepcopy
    import mobo_linac.models.gp as gp_module
    X, Y, bounds = dummy_data
    model = gp_module.build_output_gp(X, Y[:, :1], bounds, device="cpu")
    snapshot = deepcopy(model.state_dict())
    fixed_noise = model.likelihood.noise.detach().clone()
    def fail_lbfgs(mll):
        with torch.no_grad():
            next(mll.model.parameters()).fill_(float("nan"))
        mll.model.likelihood.noise_covar.noise.fill_(0.5)
        raise RuntimeError("injected lbfgs mutation")
    def adam(mll, **kwargs):
        torch.testing.assert_close(mll.model.likelihood.noise, fixed_noise)
        for key, value in snapshot.items():
            torch.testing.assert_close(mll.model.state_dict()[key], value)
        if not adam_succeeds:
            with torch.no_grad():
                next(mll.model.parameters()).fill_(100)
            mll.model.likelihood.noise_covar.noise.fill_(0.7)
            raise RuntimeError("injected adam mutation")
    monkeypatch.setattr(gp_module, "fit_gpytorch_mll", fail_lbfgs)
    monkeypatch.setattr(gp_module, "fit_gpytorch_mll_torch", adam)
    fitted = fit_gp_models(model)
    assert gp_module.fit_outcomes(fitted)[0].status == ("adam" if adam_succeeds else "restored_prior")
    assert len(gp_module.fit_outcomes(fitted)[0].errors) == (1 if adam_succeeds else 2)
    for key, value in snapshot.items():
        torch.testing.assert_close(model.state_dict()[key], value)
    torch.testing.assert_close(model.likelihood.noise, fixed_noise)
    assert torch.isfinite(model.posterior(X).mean).all()


def test_unusable_prior_is_not_advertised_as_fitted(dummy_data, monkeypatch):
    import mobo_linac.models.gp as gp_module
    X, Y, bounds = dummy_data
    model = gp_module.build_output_gp(X, Y[:, :1], bounds, device="cpu")
    with torch.no_grad():
        next(model.parameters()).fill_(float("nan"))
    monkeypatch.setattr(gp_module, "fit_gpytorch_mll", lambda mll: None)
    monkeypatch.setattr(gp_module, "fit_gpytorch_mll_torch", lambda mll, **kwargs: None)
    with pytest.raises(RuntimeError, match="nonfinite parameters"):
        fit_gp_models(model)
    assert gp_module.fit_outcomes(model) == ()
    assert not hasattr(model, "fit_outcomes")  # fitted state is never attached to BoTorch modules


def test_exact_loo_matches_explicit_leave_one_out_conditioning():
    """Closed-form LOO equals conditioning the same fitted GP on the other observations."""
    from mobo_linac.models.diagnostics import loo_predictions
    torch.manual_seed(0)
    train_X = torch.rand(9, 2, dtype=torch.double)
    train_Y = torch.sin(4 * train_X[:, :1]) + train_X[:, 1:] ** 2
    bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)
    gp = fit_gp_models(build_gp_models(train_X, train_Y, bounds, device="cpu")).models[0]
    loo = loo_predictions(gp)
    inputs, targets = gp.train_inputs[0], gp.train_targets
    with torch.no_grad():
        K = gp.covar_module(inputs).to_dense() + torch.diag_embed(gp.likelihood.noise.reshape(-1).expand(9))
        mean = gp.mean_module(inputs)
    for i in range(9):
        keep = [j for j in range(9) if j != i]
        k = K[i, keep]
        solve = torch.linalg.solve(K[keep][:, keep], torch.stack([targets[keep] - mean[keep], k], dim=-1))
        assert loo["mean_std"][i] == pytest.approx(float(mean[i] + k @ solve[:, 0]), rel=1e-5, abs=1e-8)  # stabilizing jitter
        assert loo["var_std"][i] == pytest.approx(float(K[i, i] - k @ solve[:, 1]), rel=1e-5, abs=1e-10)


def test_tuning_records_failures_without_sentinel_scores(monkeypatch):
    from mobo_linac.models import tuning
    train_X = torch.rand(8, 2, dtype=torch.double)
    train_Y = torch.rand(8, 2, dtype=torch.double)
    bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)
    original = tuning.build_gp_models

    def flaky(train_X, train_Y, bounds, settings, **kwargs):
        if settings.covar_type == "rbf":
            raise RuntimeError("injected rbf failure")
        return original(train_X, train_Y, bounds, settings, **kwargs)

    monkeypatch.setattr(tuning, "build_gp_models", flaky)
    summary = tuning.tune_gp_hyperparameters(train_X, train_Y, bounds, candidate_noise_ratios=[1e-6],
                                             candidate_noise_modes=["deterministic_fixed"])
    failed = [c for c in summary.candidates if c.status == "FAILED"]
    assert len(failed) == 1 and "injected rbf failure" in failed[0].error
    assert np.isnan(failed[0].mean_loo_log_predictive_density)
    assert summary.best_candidate.covar_type == "matern52"
