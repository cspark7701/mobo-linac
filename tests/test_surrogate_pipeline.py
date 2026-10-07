"""
Unit tests for SurrogatePipeline (Task 31 refactoring).
"""

import pytest
import torch
from mobo_linac.models.pipeline import SurrogatePipeline


@pytest.mark.parametrize("layout", ["diagnostics", "residual"])
def test_seven_channel_probability_respects_declared_layout(layout):
    from types import SimpleNamespace

    mean = torch.tensor([[0.9e-3, 1.1e-3, 0.4e-3, 0.3e-3, 1.2e-3, 194e6, 0.90]], dtype=torch.double)
    sigma = torch.tensor([[0.2e-3] * 5 + [3e6, 0.03]], dtype=torch.double)
    class FixedPosterior:
        def posterior(self, X):
            return SimpleNamespace(mean=mean, variance=sigma.square())
    pipeline = SurrogatePipeline(torch.tensor([[0.0], [1.0]]), constraint_layout=layout, device="cpu")
    pipeline.is_fitted = True
    pipeline.constraint_model = FixedPosterior()
    result = pipeline.predict_probability_of_feasibility(torch.tensor([[0.5]]))
    normal = torch.distributions.Normal(0.0, 1.0)
    if layout == "diagnostics":
        expected = normal.cdf((1e-3 - mean[0, :5]) / sigma[0, :5]).prod()
        expected *= normal.cdf((205e6 - mean[0, 5]) / sigma[0, 5]) - normal.cdf((195e6 - mean[0, 5]) / sigma[0, 5])
        expected *= normal.cdf((mean[0, 6] - 0.90) / sigma[0, 6])
    else:
        expected = normal.cdf(-mean / sigma).prod()
    assert result.item() == pytest.approx(expected.item(), abs=1e-14)


@pytest.mark.parametrize("invalid", ["row_count", "channels", "nan", "objective_nan", "design_inf", "negative_rms", "transmission_range"])
def test_pipeline_rejects_unobserved_or_misaligned_training_before_fit(monkeypatch, invalid):
    def forbid_model_build(**kwargs):
        pytest.fail("Invalid observations reached model construction")
    monkeypatch.setattr("mobo_linac.models.pipeline.build_gp_models", forbid_model_build)
    X = torch.tensor([[0.1], [0.2]], dtype=torch.double)
    Y = torch.tensor([[-1.0], [-2.0]], dtype=torch.double)
    C = torch.tensor([[0.5e-3] * 5 + [200e6, 1.0]] * 2, dtype=torch.double)
    if invalid == "row_count":
        C = C[:1]
    elif invalid == "channels":
        C = C[:, :-1]
    elif invalid == "nan":
        C[0, 0] = float("nan")
    elif invalid == "objective_nan":
        Y[0, 0] = float("nan")
    elif invalid == "design_inf":
        X[0, 0] = float("inf")
    elif invalid == "negative_rms":
        C[0, 0] = -1e-3
    else:
        C[0, 6] = 1.5
    pipeline = SurrogatePipeline(torch.tensor([[0.0], [1.0]]), device="cpu")
    with pytest.raises(ValueError, match="observations|Unphysical observed"):
        pipeline.fit(X, Y, C)
    assert pipeline.is_fitted is False


def test_selected_identity_rows_reach_both_gp_models(monkeypatch):
    from mobo_linac.evaluation import EvaluationResult
    from mobo_linac.io.results import get_training_observations

    records = [EvaluationResult(evaluation_id=str(index), run_id="r", x_physical=[index / 10],
                                objectives_model=[-float(index)], simulation_valid=True,
                                diagnostics=dict(zip(
                                    ["sigma_x_m", "sigma_y_m", "sigma_xp_rad", "sigma_yp_rad", "sigma_z_m", "mean_kinetic_energy_eV", "transmission_fraction"],
                                    [0.5e-3] * 5 + [200e6, 1.0]))) for index in (1, 2, 3)]
    del records[1].diagnostics["sigma_yp_rad"]
    from mobo_linac.config import load_config
    config = load_config("configs/mobo_200MeV.yaml")
    config.design_variables = config.design_variables[:1]
    config.objectives = config.objectives[:1]
    observed = get_training_observations(records, require_diagnostics=True, config=config)
    calls = []
    def record_build(**kwargs):
        calls.append(kwargs)
        return object()
    monkeypatch.setattr("mobo_linac.models.pipeline.build_gp_models", record_build)
    monkeypatch.setattr("mobo_linac.models.pipeline.fit_gp_models", lambda model: model)
    pipeline = SurrogatePipeline(torch.tensor([[0.0], [1.0]]), device="cpu")
    pipeline.fit(observed.train_X, observed.train_Y, observed.constraints)
    assert observed.evaluation_ids == (("r", "1"), ("r", "3"))
    assert len(calls) == 2
    assert calls[0]["train_X"].tolist() == calls[1]["train_X"].tolist() == [[0.1], [0.3]]
    assert calls[0]["train_Y"].tolist() == [[-1.0], [-3.0]]
    assert calls[1]["train_Y"].shape == (2, 7)


def test_surrogate_pipeline_fit_and_prediction():
    """Test fitting objective surrogates and making predictions."""
    bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)
    train_X = torch.tensor([[0.2, 0.3], [0.5, 0.6], [0.8, 0.9]], dtype=torch.double)
    train_Y = torch.tensor([[-0.1, -0.2], [-0.4, -0.5], [-0.7, -0.8]], dtype=torch.double)

    pipeline = SurrogatePipeline(bounds=bounds)
    assert pipeline.is_fitted is False

    pipeline.fit(train_X, train_Y)
    assert pipeline.is_fitted is True
    assert pipeline.objective_model is not None
    assert pipeline.constraint_model is None

    test_X = torch.tensor([[0.3, 0.4]], dtype=torch.double)
    mean, var = pipeline.predict_objectives(test_X)
    assert mean.shape == (1, 2)
    assert var.shape == (1, 2)

    # Predict feasibility without constraint models returns 1.0
    prob_feas = pipeline.predict_probability_of_feasibility(test_X)
    assert prob_feas.shape == (1,)
    assert prob_feas.item() == pytest.approx(1.0)


def test_surrogate_pipeline_constraint_surrogates():
    """Test fitting constraint surrogates and predicting probability of feasibility."""
    bounds = torch.tensor([[0.0, 0.0], [1.0, 1.0]], dtype=torch.double)
    train_X = torch.tensor([[0.2, 0.3], [0.5, 0.6], [0.8, 0.9]], dtype=torch.double)
    train_Y = torch.tensor([[-0.1], [-0.4], [-0.7]], dtype=torch.double)
    # Generic constraints: values <= 0 mean feasible, > 0 mean infeasible
    train_constraints = torch.tensor([[-0.5], [0.1], [-0.2]], dtype=torch.double)

    pipeline = SurrogatePipeline(bounds=bounds, constraint_layout="residual")
    pipeline.fit(train_X, train_Y, train_constraints=train_constraints)

    assert pipeline.constraint_model is not None

    test_X = torch.tensor([[0.2, 0.3]], dtype=torch.double)
    prob_feas = pipeline.predict_probability_of_feasibility(test_X)
    assert prob_feas.shape == (1,)
    assert 0.0 <= prob_feas.item() <= 1.0


def test_surrogate_pipeline_analytical_physical_feasibility():
    """Verify exact analytical Normal CDF feasibility calculation on 7-channel physical linac diagnostics."""
    from mobo_linac.config import ConstraintsConfig

    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    train_X = torch.tensor([
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        [0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        [0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    ], dtype=torch.double)
    train_Y = torch.tensor([[-1.0e-6, -1.0e-6, -1.0e6]] * 4, dtype=torch.double)

    # 7 Physical channels: [sigma_x, sigma_y, sigma_xp, sigma_yp, sigma_z, energy, transmission]
    # Well within nominal feasible bounds
    train_c = torch.tensor([
        [0.4e-3, 0.4e-3, 0.4e-3, 0.4e-3, 0.4e-3, 200.0e6, 1.0],
        [0.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 0.5e-3, 200.1e6, 0.99],
        [0.6e-3, 0.6e-3, 0.6e-3, 0.6e-3, 0.6e-3, 199.9e6, 0.98],
        [0.45e-3, 0.45e-3, 0.45e-3, 0.45e-3, 0.45e-3, 200.0e6, 0.995],
    ], dtype=torch.double)

    c_cfg = ConstraintsConfig(
        max_sigma_x_m=1.0e-3,
        max_sigma_y_m=1.0e-3,
        max_sigma_xp_rad=1.0e-3,
        max_sigma_yp_rad=1.0e-3,
        max_sigma_z_m=1.0e-3,
        min_mean_kinetic_energy_eV=195.0e6,
        max_mean_kinetic_energy_eV=205.0e6,
        min_transmission=0.90,
    )

    pipeline = SurrogatePipeline(bounds=bounds, constraints_config=c_cfg)
    pipeline.fit(train_X, train_Y, train_constraints=train_c)

    test_X = torch.tensor([[0.25, 0.35, 0.45, 0.55, 0.65, 0.75]], dtype=torch.double)
    p_feas = pipeline.predict_probability_of_feasibility(test_X)

    assert p_feas.shape == (1,)
    # Since candidates are well within feasible interior, P_feas should be high (> 0.8)
    assert p_feas.item() > 0.8
    assert p_feas.item() <= 1.0


@pytest.mark.parametrize("noise_mode", ["measured_fixed", "inferred"])
def test_pipeline_artifact_roundtrip_without_fitting(tmp_path, monkeypatch, noise_mode):
    X = torch.tensor([[0.1], [0.4], [0.8]], dtype=torch.double)
    Y = torch.cat((X.sin(), X.cos()), dim=1)
    C = X - 0.5
    noise = torch.tensor([[0.01, 0.02], [0.03, 0.04], [0.05, 0.06]], dtype=torch.double)
    pipeline = SurrogatePipeline(torch.tensor([[0.0], [1.0]]), noise_mode=noise_mode,
                                 constraint_layout="residual", device="cpu")
    kwargs = {"train_Yvar": noise, "train_constraints_var": noise[:, :1]} if noise_mode == "measured_fixed" else {}
    ids = [("run", str(i)) for i in range(3)]
    pipeline.fit(X, Y, C, training_ids=ids, **kwargs)
    query = torch.tensor([[0.25], [0.65]], dtype=torch.double)
    before = pipeline.predict_objectives(query)
    feasibility = pipeline.predict_probability_of_feasibility(query)
    path = tmp_path / "surrogate.pt"
    pipeline.save_artifact(path, metadata={"proposal_iteration": 2})
    def forbid(*args, **kwargs):
        pytest.fail("Reload must not optimize or simulate")
    monkeypatch.setattr("mobo_linac.models.pipeline.fit_gp_models", forbid)
    restored = SurrogatePipeline.load_artifact(path)
    for expected, actual in zip(before, restored.predict_objectives(query)):
        torch.testing.assert_close(actual, expected, rtol=1e-12, atol=1e-12)
    torch.testing.assert_close(restored.predict_probability_of_feasibility(query), feasibility)
    assert restored.training_ids == ids
    assert restored.fit_outcomes == pipeline.fit_outcomes
    assert restored.campaign_metadata == {"proposal_iteration": 2}
    for old, new in zip(pipeline.objective_model.models, restored.objective_model.models):
        torch.testing.assert_close(old.likelihood.noise, new.likelihood.noise)


def test_measured_constraint_noise_must_be_explicit():
    X = torch.tensor([[0.1], [0.4]], dtype=torch.double)
    pipeline = SurrogatePipeline(torch.tensor([[0.0], [1.0]]), noise_mode="measured_fixed",
                                 constraint_layout="residual", device="cpu")
    with pytest.raises(ValueError, match="measured_fixed requires"):
        pipeline.fit(X, X.sin(), X - 0.5, train_Yvar=torch.full_like(X, 0.01))
    assert not pipeline.is_fitted


def test_pipeline_exposes_usable_prior_fallback(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("optimizer unavailable")
    monkeypatch.setattr("mobo_linac.models.gp.fit_gpytorch_mll", fail)
    monkeypatch.setattr("mobo_linac.models.gp.fit_gpytorch_mll_torch", fail)
    X = torch.tensor([[0.1], [0.4], [0.8]], dtype=torch.double)
    pipeline = SurrogatePipeline(torch.tensor([[0.0], [1.0]]), device="cpu").fit(X, X.sin())
    assert pipeline.is_fitted
    assert not pipeline.is_optimized
    assert pipeline.fit_outcomes["objectives"][0].status == "restored_prior"
    assert torch.isfinite(pipeline.predict_objectives(X)[0]).all()
    path = tmp_path / "prior.pt"
    pipeline.save_artifact(path)
    restored = SurrogatePipeline.load_artifact(path)
    assert restored.is_fitted and not restored.is_optimized
    assert restored.fit_outcomes == pipeline.fit_outcomes


def test_artifact_rejects_unknown_version(tmp_path):
    path = tmp_path / "unknown.pt"
    torch.save({"version": 999, "kind": "pipeline"}, path)
    with pytest.raises(ValueError, match="Unsupported surrogate artifact version"):
        SurrogatePipeline.load_artifact(path)
