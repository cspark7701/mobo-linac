"""
Gaussian Process Surrogate Models for Linac Optimization.

Builds independent SingleTaskGP models with explicit ARD Matérn-5/2 or RBF kernels,
configurable observation noise treatment (fixed near-zero for deterministic simulation
or inferred), Normalize input transforms, and Standardize outcome transforms grouped in a ModelListGP.
"""

from dataclasses import dataclass
from copy import deepcopy
import math
from typing import List, Optional, Union
import torch
from botorch.fit import fit_gpytorch_mll, fit_gpytorch_mll_torch
from botorch.models import ModelListGP, SingleTaskGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
from gpytorch.likelihoods import FixedNoiseGaussianLikelihood
from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel
from gpytorch.mlls import ExactMarginalLogLikelihood
import linear_operator

from mobo_linac.utils.logger import get_logger

logger = get_logger(__name__)


def build_scalarized_gp_model(
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    bounds: torch.Tensor,
    covar_type: str = "matern52",
    noise_mode: str = "deterministic_fixed",
    fixed_noise_val: Optional[float] = None,
    relative_noise_ratio: float = 1.0e-6,
    min_noise_variance: float = 1.0e-24,
    device: Optional[Union[str, torch.device]] = None,
    train_Yvar: Optional[torch.Tensor] = None,
) -> SingleTaskGP:
    """
    Builds an individual SingleTaskGP surrogate for scalarized single-objective BO
    with explicit ARD covariance kernel, input Normalization, and outcome Standardization.

    Args:
        train_X: (N, D) PyTorch double tensor of design variables.
        train_Y: (N, 1) or (N,) PyTorch double tensor of scalarized objective values.
        bounds: (2, D) PyTorch double tensor of parameter bounds.
        covar_type: Covariance kernel type ('matern52' or 'rbf').
        noise_mode: Noise treatment ('deterministic_fixed', 'fixed', 'measured_fixed', or 'inferred').
        fixed_noise_val: Optional fixed observation noise variance override.
        relative_noise_ratio: Ratio of empirical objective variance for deterministic noise scaling.
        min_noise_variance: Absolute minimum variance floor for numerical stability.
        train_Yvar: Observation variances in squared output units, matching train_Y.
            Overrides scalar noise settings; Standardize scales them with outcomes.
            Inferred mode rejects explicit noise rather than ignoring it.
        device: Target PyTorch device (GPU or CPU). Automatically selected if None.

    Returns:
        Constructed SingleTaskGP instance.
    """
    if train_X.shape[0] == 0:
        raise ValueError("Cannot build GP model with empty training set.")

    from mobo_linac.utils import get_device
    target_device = get_device(device if isinstance(device, str) else (str(device) if device is not None else None))

    train_X_dbl = train_X.to(dtype=torch.double, device=target_device)
    train_Y_dbl = train_Y.to(dtype=torch.double, device=target_device)
    bounds_dbl = bounds.to(dtype=torch.double, device=target_device)

    if train_Y_dbl.ndim == 1:
        train_Y_dbl = train_Y_dbl.unsqueeze(-1)

    if (train_X_dbl.ndim != 2 or train_Y_dbl.shape != (train_X_dbl.shape[0], 1)
            or not torch.isfinite(train_X_dbl).all() or not torch.isfinite(train_Y_dbl).all()):
        raise ValueError("Training inputs and scalar outcomes must be aligned finite matrices.")
    if (bounds_dbl.shape != (2, train_X_dbl.shape[1]) or not torch.isfinite(bounds_dbl).all()
            or not (bounds_dbl[1] > bounds_dbl[0]).all()):
        raise ValueError("Bounds must be finite, increasing, and match the design dimension.")
    if train_Yvar is not None:
        train_Yvar = train_Yvar.to(dtype=torch.double, device=target_device)
        if train_Yvar.ndim == 1:
            train_Yvar = train_Yvar.unsqueeze(-1)
        _validate_noise(train_Yvar, train_Y_dbl.shape)
    for value in (fixed_noise_val, relative_noise_ratio, min_noise_variance):
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError("Noise settings must be finite and strictly positive.")

    input_dim = bounds_dbl.shape[1]
    input_transform = Normalize(d=input_dim, bounds=bounds_dbl)

    # Explicit ARD Kernel Construction
    if covar_type == "rbf":
        base_kernel = RBFKernel(ard_num_dims=input_dim)
    elif covar_type == "matern52":
        base_kernel = MaternKernel(nu=2.5, ard_num_dims=input_dim)
    else:
        raise ValueError(f"Unsupported covar_type: '{covar_type}'. Choose 'matern52' or 'rbf'.")

    covar_module = ScaleKernel(base_kernel)

    mode = "deterministic_fixed" if noise_mode == "fixed" else noise_mode

    if mode in ("deterministic_fixed", "measured_fixed"):
        if train_Yvar is not None:
            yvar = train_Yvar
        elif fixed_noise_val is not None:
            yvar = torch.full_like(train_Y_dbl, fill_value=float(fixed_noise_val), device=target_device)
        else:
            if mode == "measured_fixed":
                raise ValueError("measured_fixed requires train_Yvar or explicit fixed noise.")
            if train_Y_dbl.shape[0] > 1:
                sample_var = float(torch.var(train_Y_dbl, unbiased=True).item())
            else:
                sample_var = 0.0
            computed_var = max(relative_noise_ratio * sample_var, min_noise_variance)
            yvar = torch.full_like(train_Y_dbl, fill_value=float(computed_var), device=target_device)

        gp = SingleTaskGP(
            train_X=train_X_dbl,
            train_Y=train_Y_dbl,
            train_Yvar=yvar,
            covar_module=covar_module,
            input_transform=input_transform,
            outcome_transform=Standardize(m=1),
        ).to(device=target_device, dtype=torch.double)
    elif mode == "inferred":
        if train_Yvar is not None or fixed_noise_val is not None:
            raise ValueError("inferred noise cannot accept explicit observation noise.")
        yvar = None
        gp = SingleTaskGP(
            train_X=train_X_dbl,
            train_Y=train_Y_dbl,
            covar_module=covar_module,
            input_transform=input_transform,
            outcome_transform=Standardize(m=1),
        ).to(device=target_device, dtype=torch.double)
    else:
        raise ValueError(
            f"Unsupported noise_mode: '{noise_mode}'. Choose 'deterministic_fixed', 'measured_fixed', or 'inferred'."
        )

    gp.artifact_metadata = {
        "train_X": train_X_dbl.detach().cpu().clone(),
        "train_Y": train_Y_dbl.detach().cpu().clone(),
        "bounds": bounds_dbl.detach().cpu().clone(),
        "covar_type": covar_type, "noise_mode": mode,
        "train_Yvar": yvar.detach().cpu().clone() if yvar is not None else None,
    }
    return gp


def build_gp_models(
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    bounds: torch.Tensor,
    covar_type: str = "matern52",
    noise_mode: str = "deterministic_fixed",
    fixed_noise_val: Optional[float] = None,
    objective_noise_variances: Optional[List[float]] = None,
    train_Yvar: Optional[torch.Tensor] = None,
    relative_noise_ratio: float = 1.0e-6,
    min_noise_variance: float = 1.0e-24,
    device: Optional[Union[str, torch.device]] = None,
) -> ModelListGP:
    """
    Builds a ModelListGP containing an independent SingleTaskGP for each objective
    with explicit ARD covariance kernel and noise model.

    Args:
        train_X: (N, D) PyTorch double tensor of design variables.
        train_Y: (N, M) PyTorch double tensor of model-space objectives.
        bounds: (2, D) PyTorch double tensor of parameter bounds.
        covar_type: Covariance kernel type ('matern52' or 'rbf').
        noise_mode: Noise treatment ('deterministic_fixed', 'fixed', 'measured_fixed', or 'inferred').
        fixed_noise_val: Optional fixed observation noise variance override when noise_mode == 'deterministic_fixed'.
        objective_noise_variances: Optional list of noise variances per objective.
        train_Yvar: Optional (N, M) variances in squared output units. Precedence:
            tensor, per-output variances, scalar fixed noise, deterministic relative noise.
        relative_noise_ratio: Ratio of empirical objective variance for deterministic noise scaling (default 1e-6).
        min_noise_variance: Absolute minimum variance floor for numerical stability (default 1e-24).
        device: Target PyTorch device (GPU or CPU). Automatically selected if None.

    Returns:
        Constructed ModelListGP instance.
    """
    if train_X.shape[0] == 0:
        raise ValueError("Cannot build GP model with empty training set.")

    from mobo_linac.utils import get_device
    target_device = get_device(device if isinstance(device, str) else (str(device) if device is not None else None))

    train_X_dbl = train_X.to(dtype=torch.double, device=target_device)
    train_Y_dbl = train_Y.to(dtype=torch.double, device=target_device)
    bounds_dbl = bounds.to(dtype=torch.double, device=target_device)

    if train_Y_dbl.ndim != 2 or train_Y_dbl.shape[1] < 1:
        raise ValueError("train_Y must be a nonempty (N, M) matrix.")
    if train_Yvar is not None:
        _validate_noise(train_Yvar, train_Y_dbl.shape)
    if objective_noise_variances is not None:
        if len(objective_noise_variances) != train_Y_dbl.shape[1]:
            raise ValueError("objective_noise_variances must define every output.")
        _validate_noise(torch.tensor(objective_noise_variances, dtype=torch.double), (train_Y_dbl.shape[1],))
        if noise_mode == "inferred":
            raise ValueError("inferred noise cannot accept explicit observation noise.")
    num_objectives = train_Y_dbl.shape[-1]
    models = []

    for idx in range(num_objectives):
        y_col = train_Y_dbl[:, idx : idx + 1]
        obj_fixed_val = (
            objective_noise_variances[idx]
            if (objective_noise_variances is not None and len(objective_noise_variances) > idx)
            else fixed_noise_val
        )

        gp = build_scalarized_gp_model(
            train_X=train_X_dbl,
            train_Y=y_col,
            bounds=bounds_dbl,
            covar_type=covar_type,
            noise_mode=noise_mode,
            fixed_noise_val=obj_fixed_val,
            train_Yvar=train_Yvar[:, idx:idx + 1] if train_Yvar is not None else None,
            relative_noise_ratio=relative_noise_ratio,
            min_noise_variance=min_noise_variance,
            device=target_device,
        )
        models.append(gp)

    model_list = ModelListGP(*models).to(device=target_device, dtype=torch.double)
    return model_list


def _validate_noise(noise: torch.Tensor, shape) -> None:
    if noise.shape != shape or not torch.isfinite(noise).all() or not (noise > 0).all():
        raise ValueError("Observation noise must match output dimensions and be finite and strictly positive.")


@dataclass(frozen=True)
class FitOutcome:
    """Per-channel optimization outcome; restored_prior is usable but not optimized."""

    status: str
    errors: tuple[str, ...] = ()
    optimizer_status: Optional[str] = None


def _verify_prediction(model: SingleTaskGP) -> None:
    model.eval()
    if not all(torch.isfinite(parameter).all() for parameter in model.parameters()):
        raise RuntimeError("GP state contains nonfinite parameters.")
    if hasattr(model, "artifact_metadata"):
        inputs = model.artifact_metadata["train_X"].to(next(model.parameters()))
    else:
        inputs = model.train_inputs[0]
        if getattr(model, "_has_transformed_inputs", False):
            inputs = model.input_transform.untransform(inputs)
    with torch.no_grad():
        posterior = model.posterior(inputs)
        if not torch.isfinite(posterior.mean).all() or not torch.isfinite(posterior.variance).all():
            raise RuntimeError("GP state produces nonfinite predictions.")


def _fit_single_mll_resilient(mll: ExactMarginalLogLikelihood) -> FitOutcome:
    snapshot = deepcopy(mll.state_dict())
    fixed_noise = (mll.model.likelihood.noise.detach().clone()
                   if isinstance(mll.model.likelihood, FixedNoiseGaussianLikelihood) else None)

    def restore():
        mll.load_state_dict(snapshot)
        if fixed_noise is not None:
            mll.model.likelihood.noise_covar.noise = fixed_noise.clone()

    errors = []
    for name, optimizer, jitter in (
        ("lbfgs", lambda: fit_gpytorch_mll(mll), 1e-4),
        ("adam", lambda: fit_gpytorch_mll_torch(mll, step_limit=200), 1e-3),
    ):
        restore()
        mll.train()
        try:
            with linear_operator.settings.cholesky_jitter(jitter):
                result = optimizer()
                if name == "adam" and getattr(getattr(result, "status", None), "name", None) == "FAILURE":
                    raise RuntimeError(f"Adam optimization failed: {result.message}")
                _verify_prediction(mll.model)
            optimizer_status = getattr(getattr(result, "status", None), "name", None)
            return FitOutcome(name, tuple(errors), optimizer_status)
        except Exception as error:
            errors.append(f"{name}: {type(error).__name__}: {error}")
            logger.warning(f"GP fitting failed: {errors[-1]}")
    restore()
    mll.eval()
    _verify_prediction(mll.model)
    return FitOutcome("restored_prior", tuple(errors))


def fit_gp_models(model_list: Union[ModelListGP, SingleTaskGP]) -> Union[ModelListGP, SingleTaskGP]:
    """Fit models in place and expose structured per-channel ``fit_outcomes``.

    Both optimizers start from the same snapshot. If both fail, restore and verify
    that snapshot before exposing a usable prior fallback. An unusable prior raises.
    """
    models = [model_list] if isinstance(model_list, SingleTaskGP) else model_list.models
    outcomes = []
    for target in [model_list, *models]:
        if hasattr(target, "fit_outcomes"):
            del target.fit_outcomes
    for model in models:
        outcome = _fit_single_mll_resilient(ExactMarginalLogLikelihood(model.likelihood, model))
        model.fit_outcomes = (outcome,)
        outcomes.append(outcome)
    model_list.fit_outcomes = tuple(outcomes)
    model_list.eval()
    return model_list
