"""
Unit tests for GP Kernels, Noise Models, Acquisition Functions, and Predictive Diagnostics (Task 04).
"""

import pytest
import torch
import gpytorch
from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel
from gpytorch.likelihoods import GaussianLikelihood

from mobo_linac.config import ConstraintsConfig
from mobo_linac.models.gp import build_gp_models, fit_gp_models
from mobo_linac.models.diagnostics import compute_predictive_diagnostics
from mobo_linac.acquisition.mobo import ProposalResult, build_acquisition_function, generate_next_candidates
from mobo_linac.models.gp import SurrogateSettings


def _unpack(result: ProposalResult):
    return result.candidates, result.acq_values


def test_gp_kernel_and_ard_dimensions():
    """Verify explicit Matérn-5/2 and RBF kernel construction with ARD dimensions."""
    train_X = torch.rand(10, 6, dtype=torch.double)
    train_Y = torch.rand(10, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)

    # 1. Test Matérn-5/2 kernel construction
    gp_matern = build_gp_models(train_X, train_Y, bounds, SurrogateSettings(covar_type="matern52"))
    assert len(gp_matern.models) == 3
    for sub_model in gp_matern.models:
        assert isinstance(sub_model.covar_module, ScaleKernel)
        base = sub_model.covar_module.base_kernel
        assert isinstance(base, MaternKernel)
        assert base.nu == 2.5
        assert base.ard_num_dims == 6

    # 2. Test RBF kernel construction
    gp_rbf = build_gp_models(train_X, train_Y, bounds, SurrogateSettings(covar_type="rbf"))
    for sub_model in gp_rbf.models:
        assert isinstance(sub_model.covar_module, ScaleKernel)
        base = sub_model.covar_module.base_kernel
        assert isinstance(base, RBFKernel)
        assert base.ard_num_dims == 6


def test_gp_noise_model_and_likelihood():
    """Verify fixed near-zero noise variance and inferred noise models."""
    train_X = torch.rand(10, 6, dtype=torch.double)
    train_Y = torch.rand(10, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)

    # 1. Fixed noise model
    gp_fixed = build_gp_models(train_X, train_Y, bounds, SurrogateSettings(noise_mode="deterministic_fixed", fixed_noise_variance=1e-6))
    for sub_model in gp_fixed.models:
        assert hasattr(sub_model.likelihood, "noise") or hasattr(sub_model.likelihood, "noise_covar")

    # 2. Inferred noise model
    gp_inferred = build_gp_models(train_X, train_Y, bounds, SurrogateSettings(noise_mode="inferred"))
    for sub_model in gp_inferred.models:
        assert isinstance(sub_model.likelihood, GaussianLikelihood)



def test_gp_posterior_output_shape():
    """Verify GP posterior mean and variance output shapes."""
    train_X = torch.rand(12, 6, dtype=torch.double)
    train_Y = torch.rand(12, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)

    gp_model = build_gp_models(train_X, train_Y, bounds)
    model_device = next(gp_model.parameters()).device
    test_X = torch.rand(5, 6, dtype=torch.double, device=model_device)

    gp_model.eval()
    with torch.no_grad():
        posterior = gp_model.posterior(test_X)
        assert posterior.mean.shape == (5, 3)
        assert posterior.variance.shape == (5, 3)


def test_acquisition_function_construction():
    """Verify construction of qLogNEHVI, qLogEHVI, qEHVI, and qNEHVI acquisition functions."""
    train_X = torch.rand(15, 6, dtype=torch.double)
    train_Y = torch.rand(15, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    ref_point = torch.tensor([-1.0, -1.0, -1.0], dtype=torch.double)

    gp_model = build_gp_models(train_X, train_Y, bounds)

    for acq_type in ["qLogNEHVI", "qLogEHVI", "qEHVI", "qNEHVI"]:
        acq_func = build_acquisition_function(
            model=gp_model,
            train_X=train_X,
            train_Y=train_Y,
            ref_point=ref_point,
            acq_type=acq_type,
        )
        assert acq_func is not None


def test_predictive_diagnostics_calculation():
    """Verify computation of predictive diagnostics (RMSE, R^2, standardized residuals)."""
    train_X = torch.rand(20, 6, dtype=torch.double)
    train_Y = torch.rand(20, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)

    gp_model = build_gp_models(train_X, train_Y, bounds)

    diag_dict = compute_predictive_diagnostics(
        model=gp_model,
        train_X=train_X,
        train_Y=train_Y,
        objective_names=["norm_emit_x", "norm_emit_y", "sigma_energy"],
    )

    assert diag_dict["num_samples"] == 20
    assert diag_dict["num_objectives"] == 3
    assert "mean_in_sample_r2" in diag_dict
    assert "mean_loo_log_predictive_density" in diag_dict

    for obj_name in ["norm_emit_x", "norm_emit_y", "sigma_energy"]:
        obj_diag = diag_dict["objectives"][obj_name]
        assert {"in_sample_rmse", "in_sample_r2", "loo_rmse", "loo_log_predictive_density",
                "loo_coverage_1sigma", "loo_coverage_2sigma", "mean_standardized_residual"} <= set(obj_diag)
        assert "loo_rmse_estimate" not in obj_diag


def test_constrained_acquisition_construction():
    """Verify construction of constrained acquisition functions with SliceObjective and 8 tensor constraints."""
    from botorch.models import ModelListGP
    from mobo_linac.acquisition.mobo import SliceObjective
    from mobo_linac.constraints import get_botorch_constraint_functions

    train_X = torch.rand(15, 6, dtype=torch.double)
    train_Y = torch.rand(15, 10, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    ref_point = torch.tensor([-1.0, -1.0, -1.0], dtype=torch.double)

    joint_model = build_gp_models(train_X, train_Y, bounds)
    c_funcs = get_botorch_constraint_functions(ConstraintsConfig(), num_objectives=3)
    slice_obj = SliceObjective(num_objectives=3)

    acq_func = build_acquisition_function(
        model=joint_model,
        train_X=train_X,
        train_Y=train_Y[:, :3],
        ref_point=ref_point,
        acq_type="qLogNEHVI",
        constraints=c_funcs,
        objective=slice_obj,
    )
    assert acq_func is not None
    assert len(c_funcs) == 8


def test_configurable_acquisition_optimization_budget():
    """Verify rapid execution of generate_next_candidates with custom restart budget."""
    from mobo_linac.config import ExecutionConfig

    # 1. Verify ExecutionConfig defaults
    exec_cfg = ExecutionConfig()
    assert exec_cfg.acqf_num_restarts == 10
    assert exec_cfg.acqf_raw_samples == 1024
    assert exec_cfg.acqf_maxiter == 200
    assert exec_cfg.acqf_batch_limit == 5

    # 2. Test fast acquisition candidate generation with reduced restart budget
    train_X = torch.rand(10, 6, dtype=torch.double)
    train_Y = torch.rand(10, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    ref_point = torch.tensor([-1.0, -1.0, -1.0], dtype=torch.double)

    gp_model = build_gp_models(train_X, train_Y, bounds)
    acq_func = build_acquisition_function(
        model=gp_model,
        train_X=train_X,
        train_Y=train_Y,
        ref_point=ref_point,
        acq_type="qLogNEHVI",
    )

    batch_size = 3
    candidates, acq_values = _unpack(generate_next_candidates(
        acq_func=acq_func,
        bounds=bounds,
        batch_size=batch_size,
        num_restarts=2,
        raw_samples=32,
        maxiter=10,
        batch_limit=2,
    ))

    assert candidates.shape == (batch_size, 6)
    assert candidates.dtype == torch.double
    bounds_dev = bounds.to(device=candidates.device, dtype=torch.double)
    assert (candidates >= bounds_dev[0] - 1e-6).all()
    assert (candidates <= bounds_dev[1] + 1e-6).all()


def test_resilient_acquisition_sobol_fallback():
    """Verify graceful fallback to Sobol quasi-random candidate generation on invalid acquisition function."""
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    batch_size = 4

    # Create dummy broken acquisition function that raises RuntimeError on call
    class BrokenAcqFunc:
        def __call__(self, X):
            raise RuntimeError("Simulated numerical optimization failure")

    broken_acq = BrokenAcqFunc()

    # generate_next_candidates should catch the error and fallback to Sobol sampling
    candidates, acq_values = _unpack(generate_next_candidates(
        acq_func=broken_acq,
        bounds=bounds,
        batch_size=batch_size,
        num_restarts=2,
        raw_samples=16,
        retry_on_failure=True,
    ))

    assert candidates.shape == (batch_size, 6)
    assert candidates.dtype == torch.double
    bounds_dev = bounds.to(device=candidates.device, dtype=torch.double)
    assert (candidates >= bounds_dev[0] - 1e-6).all()
    assert (candidates <= bounds_dev[1] + 1e-6).all()
    assert acq_values.shape == (batch_size,)


def test_compare_acquisition_functions():
    """Verify benchmarking and comparison of multiple acquisition function types."""
    from mobo_linac.models.tuning import compare_acquisition_functions

    train_X = torch.rand(12, 6, dtype=torch.double)
    train_Y = torch.rand(12, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    ref_point = torch.tensor([-1.0, -1.0, -1.0], dtype=torch.double)

    model = build_gp_models(train_X, train_Y, bounds)
    summary_df = compare_acquisition_functions(
        model=model,
        train_X=train_X,
        train_Y=train_Y,
        ref_point=ref_point,
        bounds=bounds,
        acq_types=["qLogNEHVI", "qLogEHVI"],
        batch_size=2,
        num_restarts=2,
        raw_samples=16,
        maxiter=5,
    )

    assert not summary_df.empty
    assert len(summary_df) == 2
    assert "Acquisition Type" in summary_df.columns
    assert "Total Time (s)" in summary_df.columns
    assert (summary_df["Status"] == "SUCCESS").all()


def test_tune_acquisition_hyperparameters():
    """Verify acquisition hyperparameter grid search and ExecutionConfig selection."""
    from mobo_linac.models.tuning import tune_acquisition_hyperparameters

    train_X = torch.rand(10, 6, dtype=torch.double)
    train_Y = torch.rand(10, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)
    ref_point = torch.tensor([-1.0, -1.0, -1.0], dtype=torch.double)

    model = build_gp_models(train_X, train_Y, bounds)
    acq_summary = tune_acquisition_hyperparameters(
        model=model,
        train_X=train_X,
        train_Y=train_Y,
        ref_point=ref_point,
        bounds=bounds,
        candidate_acq_types=["qLogNEHVI"],
        candidate_restarts=[2],
        candidate_raw_samples=[16],
        batch_size=2,
        maxiter=5,
    )

    assert acq_summary.best_acq_type == "qLogNEHVI"
    assert acq_summary.best_execution_config.acqf_num_restarts == 2
    assert not acq_summary.comparison_table.empty


def test_tune_full_optimization_pipeline():
    """Verify unified joint surrogate and acquisition hyperparameter optimization."""
    from mobo_linac.models.tuning import tune_full_optimization_pipeline

    train_X = torch.rand(10, 6, dtype=torch.double)
    train_Y = torch.rand(10, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)

    pipeline_summary = tune_full_optimization_pipeline(
        train_X=train_X,
        train_Y=train_Y,
        bounds=bounds,
        ref_point=torch.tensor([-1.0, -1.0, -1.0], dtype=torch.double),
        batch_size=2,
        candidate_covars=["matern52"],
        candidate_noise_ratios=[1.0e-6],
        candidate_acq_types=["qLogNEHVI", "qEHVI"],
        candidate_restarts=[2],
        candidate_raw_samples=[16],
        maxiter=5,
    )

    assert pipeline_summary.best_gp_config is not None
    assert pipeline_summary.best_acq_type in ["qLogNEHVI", "qLogEHVI", "qEHVI"]
    assert not pipeline_summary.gp_comparison_table.empty
    assert not pipeline_summary.acq_comparison_table.empty





def test_single_gp_artifact_preserves_fallback_predictions(tmp_path, monkeypatch):
    from mobo_linac.models.gp import build_output_gp, fit_outcomes
    from mobo_linac.models.artifacts import save_model_artifact, load_model_artifact
    X = torch.tensor([[0.1], [0.4], [0.8]], dtype=torch.double)
    model = build_output_gp(X, X.sin(), torch.tensor([[0.0], [1.0]]), device="cpu")
    def fail(*args, **kwargs):
        raise RuntimeError("injected optimizer failure")
    monkeypatch.setattr("mobo_linac.models.gp.fit_gpytorch_mll", fail)
    monkeypatch.setattr("mobo_linac.models.gp.fit_gpytorch_mll_torch", fail)
    fit_gp_models(model)
    before = model.posterior(X)
    path = tmp_path / "model.pt"
    save_model_artifact(model, path, training_ids=[("r", str(i)) for i in range(3)])
    restored = load_model_artifact(path)
    after = restored.model.posterior(X)
    torch.testing.assert_close(before.mean, after.mean)
    torch.testing.assert_close(before.variance, after.variance)
    assert fit_outcomes(restored.model) == fit_outcomes(model)
    assert fit_outcomes(restored.model)[0].status == "restored_prior"
    assert restored.training_ids == [("r", str(i)) for i in range(3)]
    assert not hasattr(restored.model, "training_ids")


@pytest.mark.parametrize("mode", ["scalarized_bo", "constrained_mobo", "unconstrained_mobo"])
def test_campaign_checkpoint_links_reloadable_model(tmp_path, monkeypatch, mode):
    import hashlib
    from pathlib import Path
    from mobo_linac.config import load_config
    from mobo_linac.execution import MockEvaluator
    from mobo_linac.io.checkpoint import load_run_checkpoint
    from mobo_linac.models.pipeline import SurrogatePipeline
    from mobo_linac.models.artifacts import load_model_artifact
    import mobo_linac.campaigns.runner as campaign
    import mobo_linac.campaigns.strategies as strategies_module

    from mobo_linac.acquisition.mobo import ProposalResult
    monkeypatch.setattr(strategies_module, "generate_next_candidates", lambda **kwargs: ProposalResult(
        kwargs["bounds"].mean(dim=0).repeat(kwargs["batch_size"], 1), torch.zeros(1), None))
    runner = campaign.MoboCampaignRunner(
        config=load_config("configs/mobo_200MeV.yaml"), output_dir=tmp_path,
        num_initial_samples=3, num_batches=1, batch_size=1, seed=7, device="cpu",
        optimization_mode=mode, constrained=mode == "constrained_mobo",
        evaluator=MockEvaluator(tmp_path), export_plots=False, export_env_info=False,
    )
    results, _, _ = runner.run()
    state = load_run_checkpoint(tmp_path)
    reference = state.model_artifact
    path = Path(reference["path"])
    assert path.parent == tmp_path / "gp_checkpoint"
    assert reference["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert reference["proposal_iteration"] == 1
    restored = load_model_artifact(path) if mode == "scalarized_bo" else SurrogatePipeline.load_artifact(path)
    metadata = restored.metadata if mode == "scalarized_bo" else restored.campaign_metadata
    assert restored.training_ids == [(result.run_id, result.evaluation_id) for result in results[:3]]
    assert metadata["optimization_mode"] == mode
    assert metadata["proposal_iteration"] == 1
    query = torch.tensor([results[-1].x_physical], dtype=torch.double)
    mean = restored.model.posterior(query).mean if mode == "scalarized_bo" else restored.predict_objectives(query)[0]
    assert torch.isfinite(mean).all()


@pytest.mark.parametrize("success_tier", [0, 1, 2, None])
def test_forced_proposal_tiers_validate_metadata_and_preserve_module(monkeypatch, success_tier):
    import mobo_linac.acquisition.mobo as acquisition
    class Module(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.parameter = torch.nn.Parameter(torch.tensor([2.], dtype=torch.double))
            self.register_buffer("cached", torch.tensor([3.], dtype=torch.double))
    module = Module()
    calls = []
    def optimize(**kwargs):
        index = len(calls)
        calls.append(kwargs)
        if index == 2:
            assert kwargs["acq_function"] is not module
            with torch.no_grad():
                kwargs["acq_function"].parameter.add_(100)
                kwargs["acq_function"].cached.add_(100)
        else:
            assert kwargs["acq_function"] is module
        if index != success_tier:
            raise RuntimeError(f"forced failure {index}")
        return kwargs["bounds"].mean(dim=0).repeat(kwargs["q"], 1), torch.tensor([0.2])
    monkeypatch.setattr(acquisition, "optimize_acqf", optimize)
    bounds = torch.tensor([[-2., 0.], [2., 1.]], dtype=torch.double)
    stream = torch.quasirandom.SobolEngine(2, scramble=True, seed=17)
    stream.draw(3)
    result = acquisition.generate_next_candidates(module, bounds, batch_size=2, num_restarts=8, raw_samples=128,
                                                  options={"maxiter": 50}, sobol_engine=stream, device="cpu")
    candidates, values = result.candidates, result.acq_values
    assert not hasattr(result, "__iter__")  # no tuple emulation
    assert candidates.shape == (2, 2)
    assert torch.isfinite(candidates).all() and torch.isfinite(values).all()
    assert ((candidates >= bounds[0]) & (candidates <= bounds[1])).all()
    expected = ["primary", "retry", "cpu", "sobol"][success_tier if success_tier is not None else 3]
    assert result.metadata["method"] == expected
    assert len(result.metadata["attempts"]) == (success_tier + 1 if success_tier is not None else 3)
    assert result.metadata["attempts"][0]["options"]["maxiter"] == 50
    assert result.metadata["attempts"][0]["num_restarts"] == 8
    if success_tier != 0:
        assert result.metadata["attempts"][1]["num_restarts"] == 4
        assert result.metadata["attempts"][1]["raw_samples"] == 32
        assert "forced failure" in result.metadata["fallback_reason"]
    assert result.metadata["sobol"]["end"] == (5 if success_tier is None else 3)
    torch.testing.assert_close(module.parameter, torch.tensor([2.], dtype=torch.double))
    torch.testing.assert_close(module.cached, torch.tensor([3.], dtype=torch.double))
    assert module.parameter.device.type == module.cached.device.type == "cpu"


@pytest.mark.parametrize("invalid", ["shape", "nan", "bounds", "value"])
def test_invalid_optimizer_success_is_retried(monkeypatch, invalid):
    import mobo_linac.acquisition.mobo as acquisition
    bounds = torch.tensor([[0.], [1.]], dtype=torch.double)
    calls = []
    def optimize(**kwargs):
        calls.append(kwargs)
        candidates, values = torch.full((2, 1), .5, dtype=torch.double), torch.tensor([.2])
        if len(calls) == 1:
            if invalid == "shape":
                candidates = candidates[:1]
            elif invalid == "nan":
                candidates[0, 0] = float("nan")
            elif invalid == "bounds":
                candidates[0, 0] = 2
            else:
                values[0] = float("nan")
        return candidates, values
    monkeypatch.setattr(acquisition, "optimize_acqf", optimize)
    result = acquisition.generate_next_candidates(torch.nn.Linear(1, 1).double(), bounds, batch_size=2)
    assert result.metadata["method"] == "retry"
    assert result.metadata["attempts"][0]["status"] == "failed"
    assert result.metadata["attempts"][1]["status"] == "success"


def test_standalone_fallback_is_seeded_and_can_disable_retry(monkeypatch):
    import mobo_linac.acquisition.mobo as acquisition
    def fail(**kwargs):
        raise RuntimeError("forced failure")
    monkeypatch.setattr(acquisition, "optimize_acqf", fail)
    bounds = torch.tensor([[0.], [1.]], dtype=torch.double)
    module = torch.nn.Linear(1, 1).double()
    first = acquisition.generate_next_candidates(module, bounds, fallback_seed=123)
    torch.rand(100)
    second = acquisition.generate_next_candidates(module, bounds, fallback_seed=123)
    torch.testing.assert_close(first.candidates, second.candidates)
    assert first.metadata == second.metadata
    assert first.metadata["sobol"] == {"seed": 123, "start": 0, "end": 8}
    with pytest.raises(RuntimeError, match="forced failure"):
        acquisition.generate_next_candidates(module, bounds, retry_on_failure=False)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
@pytest.mark.parametrize("cpu_succeeds", [False, True])
def test_cuda_fallback_preserves_real_gp_placement(monkeypatch, cpu_succeeds):
    import mobo_linac.acquisition.mobo as acquisition
    X = torch.tensor([[.1], [.4], [.8]], dtype=torch.double)
    model = build_gp_models(X, X.sin(), torch.tensor([[0.], [1.]]), device="cuda:0")
    module = torch.nn.Module()
    module.model = model
    module.register_buffer("cached", torch.ones(1, device="cuda:0", dtype=torch.double))
    calls = []
    def optimize(**kwargs):
        calls.append(kwargs)
        if len(calls) < 3 or not cpu_succeeds:
            raise RuntimeError("forced failure")
        assert kwargs["acq_function"] is not module
        assert next(kwargs["acq_function"].parameters()).device.type == "cpu"
        return kwargs["bounds"].mean(dim=0).repeat(kwargs["q"], 1), torch.zeros(1)
    monkeypatch.setattr(acquisition, "optimize_acqf", optimize)
    stream = torch.quasirandom.SobolEngine(1, scramble=True, seed=9)
    result = acquisition.generate_next_candidates(module, torch.tensor([[0.], [1.]]), device="cuda:0", sobol_engine=stream)
    assert result.metadata["method"] == ("cpu" if cpu_succeeds else "sobol")
    assert result.candidates.device == torch.device("cuda:0")
    assert all(parameter.device == torch.device("cuda:0") for parameter in module.parameters())
    assert all(buffer.device == torch.device("cuda:0") for buffer in module.buffers())
    assert model.models[0].train_inputs[0].device == torch.device("cuda:0")
    assert model.models[0].likelihood.noise.device == torch.device("cuda:0")


def test_real_acquisition_cpu_copy_keeps_original_state(monkeypatch):
    import mobo_linac.acquisition.mobo as acquisition
    X = torch.tensor([[.1], [.4], [.8]], dtype=torch.double)
    Y = torch.cat((X.sin(), X.cos()), dim=1)
    bounds = torch.tensor([[0.], [1.]], dtype=torch.double)
    model = build_gp_models(X, Y, bounds, device="cpu")
    module = build_acquisition_function(model, X, Y, torch.tensor([-2., -2.]), acq_type="qLogEHVI")
    original = {name: tensor.clone() for name, tensor in module.state_dict().items()}
    calls = []
    def optimize(**kwargs):
        calls.append(kwargs)
        if len(calls) < 3:
            raise RuntimeError("forced failure")
        assert kwargs["acq_function"] is not module
        return kwargs["bounds"].mean(0).repeat(kwargs["q"], 1), torch.zeros(1)
    monkeypatch.setattr(acquisition, "optimize_acqf", optimize)
    result = acquisition.generate_next_candidates(module, bounds)
    # BoTorch caches may be non-leaf tensors that cannot be deep-copied.
    assert result.metadata["method"] in ("cpu", "sobol")
    if result.metadata["method"] == "sobol":
        assert result.metadata["attempts"][-1]["status"] == "failed"
        assert "deepcopy" in result.metadata["attempts"][-1]["error"].lower() or "deepcop" in result.metadata["attempts"][-1]["error"].lower()
    for name, tensor in module.state_dict().items():
        torch.testing.assert_close(tensor, original[name])


def test_uncopyable_cpu_fallback_preserves_supplied_module(monkeypatch):
    import mobo_linac.acquisition.mobo as acquisition
    module = torch.nn.Linear(1, 1).double()
    module.cached = module.weight * 2  # Non-leaf tensors deliberately reject deepcopy.
    before = module.weight.detach().clone()
    calls = []
    def fail(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("forced failure")
    monkeypatch.setattr(acquisition, "optimize_acqf", fail)
    result = acquisition.generate_next_candidates(module, torch.tensor([[0.], [1.]]))
    assert len(calls) == 2
    assert result.metadata["method"] == "sobol"
    assert result.metadata["attempts"][-1]["tier"] == "cpu"
    assert result.metadata["attempts"][-1]["status"] == "failed"
    assert "deepcop" in result.metadata["fallback_reason"].lower()
    torch.testing.assert_close(module.weight, before)
    assert module.weight.device.type == module.cached.device.type == "cpu"
