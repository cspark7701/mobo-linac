"""Surrogate validation, prediction failures and failed tuning must remain explicit."""

from types import SimpleNamespace

import pytest
import torch
from botorch.models import SingleTaskGP
from gpytorch.mlls import ExactMarginalLogLikelihood

from mobo_linac.models import gp, artifacts, tuning
from mobo_linac.models.pipeline import SurrogatePipeline
from mobo_linac.models.diagnostics import compute_predictive_diagnostics
from mobo_linac.models.repeatability import compute_measured_noise_variance, create_measured_yvar_tensor


@pytest.fixture
def data():
    x = torch.tensor([[0.1], [0.4], [0.8]], dtype=torch.double)
    return x, x.square(), torch.tensor([[0.0], [1.0]], dtype=torch.double)


@pytest.mark.parametrize(
    "settings",
    [
        {"covar_type": "bad"},
        {"noise_mode": "bad"},
        {"relative_noise_ratio": -1},
        {"noise_mode": "inferred", "objective_noise_variances": [1]},
        {"noise_mode": "inferred", "fixed_noise_variance": 1},
    ],
)
def test_invalid_surrogate_settings(settings):
    with pytest.raises(ValueError):
        gp.SurrogateSettings(**settings)


@pytest.mark.parametrize("fault", ["empty", "empty_list", "shape", "bounds", "list_shape"])
def test_invalid_training_data(data, fault):
    x, y, b = data
    if fault in ("empty", "empty_list"):
        x, y = x[:0], y[:0]
    if fault == "shape":
        y = y[:1]
    if fault == "bounds":
        b = b.flip(0)
    if fault == "list_shape":
        y = y.squeeze(-1)
    factory = gp.build_gp_models if fault in ("empty_list", "list_shape") else gp.build_output_gp
    with pytest.raises(ValueError):
        factory(x, y, b, device="cpu")


def test_scalar_outcomes_noise_and_external_model_validation(data):
    x, y, b = data
    model = gp.build_output_gp(x, y.squeeze(-1), b, train_Yvar=torch.full((3,), 1e-5), device="cpu")
    assert model.train_targets.shape == (3,)
    from botorch.models.transforms.input import Normalize

    external = SingleTaskGP(x, y, input_transform=Normalize(d=1, bounds=b))
    with pytest.raises(ValueError, match="record is unknown"):
        gp.channel_record(external)
    external.eval()
    external.posterior(x)
    gp._verify_prediction(external)
    external.posterior = lambda x: SimpleNamespace(mean=x * float("nan"), variance=x)
    with pytest.raises(RuntimeError, match="nonfinite predictions"):
        gp._verify_prediction(external)


def test_adam_failure_restores_prior(data, monkeypatch):
    x, y, b = data
    model = gp.build_output_gp(x, y, b, device="cpu")

    def fail(*a, **k):
        raise RuntimeError("lbfgs failed")

    monkeypatch.setattr(gp, "fit_gpytorch_mll", fail)
    monkeypatch.setattr(
        gp,
        "fit_gpytorch_mll_torch",
        lambda *a, **k: SimpleNamespace(status=SimpleNamespace(name="FAILURE"), message="rejected"),
    )
    outcome = gp._fit_single_mll_resilient(ExactMarginalLogLikelihood(model.likelihood, model))
    assert outcome.status == "restored_prior"
    assert "Adam optimization failed" in outcome.errors[-1]


def test_pipeline_preconditions_and_artifact_kinds(data, sample_config, tmp_path, monkeypatch):
    x, y, b = data
    pipeline = SurrogatePipeline(b, constraints_config=sample_config, device="cpu")
    assert pipeline.constraints_config is sample_config.constraints
    with pytest.raises(ValueError, match="constraint_layout"):
        SurrogatePipeline(b, constraint_layout="bad", device="cpu")
    with pytest.raises(ValueError, match="fewer than 2"):
        pipeline.fit(x[:1], y[:1])
    with pytest.raises(ValueError, match="training_ids"):
        pipeline.fit(x, y, training_ids=[1])
    with pytest.raises(ValueError, match="Constraint noise"):
        pipeline.fit(x, y, train_constraints_var=y)
    with pytest.raises(RuntimeError, match="unfitted"):
        pipeline.save_artifact(tmp_path / "unfitted.pt")
    with pytest.raises(RuntimeError, match="fitted"):
        pipeline.predict_objectives(x)
    with pytest.raises(RuntimeError, match="fitted"):
        pipeline.predict_probability_of_feasibility(x)
    monkeypatch.setattr("mobo_linac.models.pipeline.fit_gp_models", lambda model: model)
    pipeline.fit(x, y)
    with pytest.raises(ValueError, match="training_ids"):
        pipeline.save_artifact(tmp_path / "bad_ids.pt", training_ids=[1])
    pipeline.save_artifact(tmp_path / "pipeline.pt")
    with pytest.raises(ValueError, match="GP model"):
        artifacts.load_model_artifact(tmp_path / "pipeline.pt")
    model = gp.build_output_gp(x, y, b, device="cpu")
    with pytest.raises(ValueError, match="training_ids"):
        artifacts.save_model_artifact(model, tmp_path / "bad.pt", training_ids=[1])
    artifacts.save_model_artifact(model, tmp_path / "gp.pt")
    with pytest.raises(ValueError, match="pipeline artifact"):
        SurrogatePipeline.load_artifact(tmp_path / "gp.pt")
    pipeline.constraint_model = SimpleNamespace(
        posterior=lambda x: SimpleNamespace(mean=x, variance=torch.ones_like(x))
    )
    with pytest.raises(ValueError, match="canonical"):
        pipeline.predict_probability_of_feasibility(x)
    assert "objective_0" in compute_predictive_diagnostics(model, x, y)["objectives"]


def test_repeatability_floors_and_variance_shapes(sample_config):
    floors = compute_measured_noise_variance([], sample_config)
    assert all(v > 0 for v in floors.values())
    with pytest.raises(TypeError):
        create_measured_yvar_tensor(2, {})
    with pytest.raises(ValueError):
        create_measured_yvar_tensor(2, {}, sample_config)
    assert create_measured_yvar_tensor(2, [1, 2, 3]).tolist() == [[1, 2, 3], [1, 2, 3]]


def test_tuning_failures_do_not_produce_a_winner(data, monkeypatch):
    x, y, b = data

    def fail(*a, **k):
        raise RuntimeError("invalid posterior")

    monkeypatch.setattr(tuning, "build_gp_models", fail)
    with pytest.raises(RuntimeError, match="No surrogate"):
        tuning.tune_gp_hyperparameters(x, y, b, candidate_covars=["rbf"], candidate_noise_modes=["inferred"])
    monkeypatch.setattr(tuning, "build_acquisition_function", fail)
    with pytest.raises(RuntimeError, match="No acquisition"):
        tuning.tune_acquisition_hyperparameters(
            None, x, y, [-1], b, candidate_acq_types=["qLogEHVI"], candidate_restarts=[1], candidate_raw_samples=[2]
        )
    with pytest.raises(ValueError, match="recorded reporting"):
        tuning.tune_full_optimization_pipeline(x, y, b, None)
    assert tuning.compute_candidate_diversity(x[:1]) == 0


def test_nonfinite_tuning_score_is_not_a_winner(data, monkeypatch):
    x, y, b = data
    monkeypatch.setattr(tuning, "fit_gp_models", lambda model: model)
    monkeypatch.setattr(
        tuning,
        "compute_predictive_diagnostics",
        lambda *a: {
            "objectives": {"one": {"loo_coverage_2sigma": 1.0, "loo_log_predictive_density": float("nan")}},
            "mean_loo_log_predictive_density": float("nan"),
            "mean_in_sample_r2": 1.0,
        },
    )
    with pytest.raises(RuntimeError, match="Nonfinite LOO"):
        tuning.tune_gp_hyperparameters(x, y, b, candidate_covars=["rbf"], candidate_noise_modes=["inferred"])


def test_strategy_feasible_reference_and_cuda_cleanup(sample_config, monkeypatch):
    from mobo_linac.campaigns import strategies
    from mobo_linac.io.results import TrainingObservations

    x = torch.tensor([sample_config.get_nominal_parameters()] * 2, dtype=torch.double)
    y = torch.tensor([[-1e-6, -2e-6, -5e5], [-2e-6, -3e-6, -6e5]], dtype=torch.double)
    training = TrainingObservations((("r", "1"), ("r", "2")), x, y, torch.tensor([True, False]))
    sample_config.execution.acquisition_reference_basis = "feasible"
    multi = strategies.MultiObjectiveProposal(
        sample_config,
        torch.device("cpu"),
        False,
        "qLogEHVI",
        sample_config.get_parameter_bounds_tensor(),
        lambda *a, **k: None,
    )
    monkeypatch.setattr(strategies.MultiObjectiveProposal, "_surrogate", lambda *a: (None, None, None, None))
    seen = []
    monkeypatch.setattr(strategies, "build_acquisition_function", lambda **kw: seen.append(kw) or object())
    monkeypatch.setattr(strategies, "_optimize", lambda *a: ([[1]], {}))
    _, metadata = multi.propose(training, 1, 1, None)
    assert seen[0]["ref_point"].shape == (3,)
    assert torch.all(seen[0]["ref_point"] > y[1])
    assert metadata["acquisition_reference"]["basis"] == "feasible"
    # Exercise CUDA resource handling on CPU; this does not verify GPU numerical execution.
    cuda = torch.device("cuda:0")
    original_to = torch.Tensor.to
    original_tensor = torch.tensor

    def cpu_to(self, *args, **kwargs):
        if kwargs.get("device") == cuda:
            kwargs = dict(kwargs, device="cpu")
        return original_to(self, *args, **kwargs)

    def cpu_tensor(*args, **kwargs):
        if kwargs.get("device") == cuda:
            kwargs = dict(kwargs, device="cpu")
        return original_tensor(*args, **kwargs)

    monkeypatch.setattr(torch.Tensor, "to", cpu_to)
    monkeypatch.setattr(torch, "tensor", cpu_tensor)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    cleared = []
    monkeypatch.setattr(torch.cuda, "empty_cache", lambda: cleared.append(True))
    monkeypatch.setattr(strategies, "build_output_gp", lambda *a, **k: object())
    monkeypatch.setattr(strategies, "fit_gp_models", lambda *a: None)
    monkeypatch.setattr(strategies, "qLogNoisyExpectedImprovement", lambda **kw: object())
    scalar = strategies.ScalarizedProposal(
        sample_config, cuda, original_tensor([1 / 3] * 3), sample_config.get_parameter_bounds_tensor(), lambda *a: None
    )
    scalar.propose(training, 1, 1, None)
    assert cleared == [True]
