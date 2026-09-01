"""
Unit tests for GP Kernels, Noise Models, Acquisition Functions, and Predictive Diagnostics (Task 04).
"""

import pytest
import torch
import gpytorch
from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel
from gpytorch.likelihoods import GaussianLikelihood

from mobo_linac.models.gp import build_gp_models, fit_gp_models
from mobo_linac.models.diagnostics import compute_predictive_diagnostics
from mobo_linac.acquisition.mobo import build_acquisition_function, generate_next_candidates


def test_gp_kernel_and_ard_dimensions():
    """Verify explicit Matérn-5/2 and RBF kernel construction with ARD dimensions."""
    train_X = torch.rand(10, 6, dtype=torch.double)
    train_Y = torch.rand(10, 3, dtype=torch.double)
    bounds = torch.tensor([[0.0] * 6, [1.0] * 6], dtype=torch.double)

    # 1. Test Matérn-5/2 kernel construction
    gp_matern = build_gp_models(train_X, train_Y, bounds, covar_type="matern52")
    assert len(gp_matern.models) == 3
    for sub_model in gp_matern.models:
        assert isinstance(sub_model.covar_module, ScaleKernel)
        base = sub_model.covar_module.base_kernel
        assert isinstance(base, MaternKernel)
        assert base.nu == 2.5
        assert base.ard_num_dims == 6

    # 2. Test RBF kernel construction
    gp_rbf = build_gp_models(train_X, train_Y, bounds, covar_type="rbf")
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
    gp_fixed = build_gp_models(train_X, train_Y, bounds, noise_mode="fixed", fixed_noise_val=1e-6)
    for sub_model in gp_fixed.models:
        assert hasattr(sub_model.likelihood, "noise") or hasattr(sub_model.likelihood, "noise_covar")

    # 2. Inferred noise model
    gp_inferred = build_gp_models(train_X, train_Y, bounds, noise_mode="inferred")
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
    assert "overall_rmse" in diag_dict
    assert "overall_r2" in diag_dict

    for obj_name in ["norm_emit_x", "norm_emit_y", "sigma_energy"]:
        assert obj_name in diag_dict["objectives"]
        obj_diag = diag_dict["objectives"][obj_name]
        assert "rmse" in obj_diag
        assert "r2" in obj_diag
        assert "mean_standardized_residual" in obj_diag


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
    c_funcs = get_botorch_constraint_functions()
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
    assert exec_cfg.acqf_num_restarts == 20
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
    candidates, acq_values = generate_next_candidates(
        acq_func=acq_func,
        bounds=bounds,
        batch_size=batch_size,
        num_restarts=2,
        raw_samples=32,
        maxiter=10,
        batch_limit=2,
    )

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
    candidates, acq_values = generate_next_candidates(
        acq_func=broken_acq,
        bounds=bounds,
        batch_size=batch_size,
        num_restarts=2,
        raw_samples=16,
        retry_on_failure=True,
    )

    assert candidates.shape == (batch_size, 6)
    assert candidates.dtype == torch.double
    bounds_dev = bounds.to(device=candidates.device, dtype=torch.double)
    assert (candidates >= bounds_dev[0] - 1e-6).all()
    assert (candidates <= bounds_dev[1] + 1e-6).all()
    assert acq_values.shape == (batch_size,)



