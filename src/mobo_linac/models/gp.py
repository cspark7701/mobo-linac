"""
Gaussian Process Surrogate Models for Linac Optimization.

Builds independent SingleTaskGP models with explicit ARD Matérn-5/2 or RBF kernels,
configurable observation noise treatment (fixed near-zero for deterministic simulation
or inferred), Normalize input transforms, and Standardize outcome transforms grouped in a ModelListGP.
"""

from dataclasses import dataclass, replace
from copy import deepcopy
import math
from typing import Any, Dict, List, Optional, Tuple, Union
import weakref
import warnings
import torch
from botorch.exceptions.warnings import InputDataWarning
from botorch import settings as botorch_settings
from botorch.fit import fit_gpytorch_mll, fit_gpytorch_mll_torch
from botorch.models import ModelListGP, SingleTaskGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
from botorch.models.utils.assorted import check_min_max_scaling
from gpytorch.likelihoods import FixedNoiseGaussianLikelihood
from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel
from gpytorch.mlls import ExactMarginalLogLikelihood
import linear_operator

from mobo_linac.utils.logger import get_logger
from mobo_linac.utils import get_device

logger = get_logger(__name__)


NOISE_MODES = ("deterministic_fixed", "measured_fixed", "inferred")
COVARIANCE_KERNELS = ("matern52", "rbf")
# Preserve Standardize's default mean-only policy for small/constant outcomes.
OUTCOME_MIN_STDV = 1.0e-8


@dataclass(frozen=True)
class SurrogateSettings:
    """GP surrogate settings shared by every output model (built from ``GpModelConfig``).

    Adding a setting means adding it here, to ``GpModelConfig`` and to :func:`build_output_gp`.
    """

    covar_type: str = "matern52"
    noise_mode: str = "deterministic_fixed"
    fixed_noise_variance: Optional[float] = None
    relative_noise_ratio: float = 1.0e-6
    min_noise_variance: float = 1.0e-24
    objective_noise_variances: Optional[Tuple[float, ...]] = None

    def __post_init__(self):
        if self.covar_type not in COVARIANCE_KERNELS:
            raise ValueError(f"Unsupported covar_type: '{self.covar_type}'. Choose 'matern52' or 'rbf'.")
        if self.noise_mode not in NOISE_MODES:
            raise ValueError(f"Unsupported noise_mode: '{self.noise_mode}'. Choose one of {list(NOISE_MODES)} "
                             "(the former alias 'fixed' is 'deterministic_fixed').")
        for value in (self.fixed_noise_variance, self.relative_noise_ratio, self.min_noise_variance):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError("Noise settings must be finite and strictly positive.")
        if self.objective_noise_variances is not None:
            object.__setattr__(self, "objective_noise_variances", tuple(float(v) for v in self.objective_noise_variances))
            _validate_noise(torch.tensor(self.objective_noise_variances, dtype=torch.double),
                            (len(self.objective_noise_variances),))
            if self.noise_mode == "inferred":
                raise ValueError("inferred noise cannot accept explicit observation noise.")
        if self.noise_mode == "inferred" and self.fixed_noise_variance is not None:
            raise ValueError("inferred noise cannot accept explicit observation noise.")

    @classmethod
    def from_config(cls, model_config) -> "SurrogateSettings":
        return cls(covar_type=model_config.covar_type, noise_mode=model_config.noise_mode,
                   fixed_noise_variance=model_config.fixed_noise_variance,
                   relative_noise_ratio=model_config.relative_noise_ratio,
                   min_noise_variance=model_config.min_noise_variance,
                   objective_noise_variances=model_config.objective_noise_variances)

    def for_output(self, index: Optional[int]) -> "SurrogateSettings":
        """Settings of one output: its per-objective noise variance (when given) becomes the fixed noise."""
        if index is None or self.objective_noise_variances is None:
            return replace(self, objective_noise_variances=None)
        return replace(self, fixed_noise_variance=self.objective_noise_variances[index], objective_noise_variances=None)


@dataclass
class ChannelRecord:
    """Training data, settings and fit outcome of one fitted output GP (kept beside the module)."""

    train_X: torch.Tensor
    train_Y: torch.Tensor
    bounds: torch.Tensor
    covar_type: str
    noise_mode: str
    train_Yvar: Optional[torch.Tensor]
    fit_outcome: Optional["FitOutcome"] = None

    def artifact_metadata(self) -> Dict[str, Any]:
        return {"train_X": self.train_X, "train_Y": self.train_Y, "bounds": self.bounds,
                "covar_type": self.covar_type, "noise_mode": self.noise_mode, "train_Yvar": self.train_Yvar}


# Fitted state lives in this side table keyed by the GP module; nothing is attached to
# BoTorch/GPyTorch objects.
_RECORDS: "weakref.WeakKeyDictionary[SingleTaskGP, ChannelRecord]" = weakref.WeakKeyDictionary()


def channel_record(model: SingleTaskGP) -> ChannelRecord:
    try:
        return _RECORDS[model]
    except KeyError:
        raise ValueError("Model was not built by build_output_gp; its training record is unknown.") from None


def output_models(model: Union[ModelListGP, SingleTaskGP]) -> List[SingleTaskGP]:
    return [model] if isinstance(model, SingleTaskGP) else list(model.models)


def fit_outcomes(model: Union[ModelListGP, SingleTaskGP, None]) -> Tuple["FitOutcome", ...]:
    """Per-output fit outcomes of a fitted surrogate (empty when not fitted)."""
    if model is None:
        return ()
    outcomes = [_RECORDS[m].fit_outcome for m in output_models(model) if m in _RECORDS]
    return tuple(outcome for outcome in outcomes if outcome is not None)


def build_output_gp(
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    bounds: torch.Tensor,
    settings: SurrogateSettings = SurrogateSettings(),
    *,
    train_Yvar: Optional[torch.Tensor] = None,
    device: Optional[Union[str, torch.device]] = None,
) -> SingleTaskGP:
    """One output's SingleTaskGP: ARD kernel, Normalize inputs, Standardize outcome, configured noise.

    ``train_Yvar`` (squared output units) overrides scalar noise settings; inferred noise rejects it.
    Deterministic fixed noise is ``max(relative_noise_ratio * Var(Y), min_noise_variance)``.
    """
    if train_X.shape[0] == 0:
        raise ValueError("Cannot build GP model with empty training set.")
    target_device = get_device(device)
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

    input_dim = bounds_dbl.shape[1]
    base_kernel = (RBFKernel(ard_num_dims=input_dim) if settings.covar_type == "rbf"
                   else MaternKernel(nu=2.5, ard_num_dims=input_dim))
    if settings.noise_mode == "inferred":
        if train_Yvar is not None:
            raise ValueError("inferred noise cannot accept explicit observation noise.")
        yvar = None
    elif train_Yvar is not None:
        yvar = train_Yvar
    elif settings.fixed_noise_variance is not None:
        yvar = torch.full_like(train_Y_dbl, fill_value=float(settings.fixed_noise_variance), device=target_device)
    elif settings.noise_mode == "measured_fixed":
        raise ValueError("measured_fixed requires train_Yvar or explicit fixed noise.")
    else:
        sample_var = float(torch.var(train_Y_dbl, unbiased=True).item()) if train_Y_dbl.shape[0] > 1 else 0.0
        computed_var = max(settings.relative_noise_ratio * sample_var, settings.min_noise_variance)
        yvar = torch.full_like(train_Y_dbl, fill_value=float(computed_var), device=target_device)

    input_transform = Normalize(d=input_dim, bounds=bounds_dbl)
    # BoTorch skips scaling checks for custom covariance modules. Our kernels
    # still use normalized inputs, so check those explicitly without clipping.
    if botorch_settings.validate_input_scaling.on():
        with torch.no_grad():
            check_min_max_scaling(input_transform(train_X_dbl))

    mean_only = train_Y_dbl.shape[0] > 1 and bool(train_Y_dbl.std() < OUTCOME_MIN_STDV)
    with warnings.catch_warnings():
        if mean_only:
            # Unit variance is intentionally unavailable under Standardize's
            # small-output policy. Suppress only that constructor notice;
            # input scaling and all numerical warnings remain visible.
            warnings.filterwarnings(
                "ignore", message=r"^Data \(outcome observations\) is not standardized \(std =",
                category=InputDataWarning,
            )
            logger.debug("GP outcome uses mean-only scaling: observed std is below %g.", OUTCOME_MIN_STDV)
        gp = SingleTaskGP(
            train_X=train_X_dbl, train_Y=train_Y_dbl, train_Yvar=yvar,
            covar_module=ScaleKernel(base_kernel),
            input_transform=input_transform,
            outcome_transform=Standardize(m=1, min_stdv=OUTCOME_MIN_STDV),
        ).to(device=target_device, dtype=torch.double)
    _RECORDS[gp] = ChannelRecord(
        train_X=train_X_dbl.detach().cpu().clone(), train_Y=train_Y_dbl.detach().cpu().clone(),
        bounds=bounds_dbl.detach().cpu().clone(), covar_type=settings.covar_type, noise_mode=settings.noise_mode,
        train_Yvar=yvar.detach().cpu().clone() if yvar is not None else None)
    return gp


def build_gp_models(
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    bounds: torch.Tensor,
    settings: SurrogateSettings = SurrogateSettings(),
    *,
    train_Yvar: Optional[torch.Tensor] = None,
    per_output_noise: bool = True,
    device: Optional[Union[str, torch.device]] = None,
) -> ModelListGP:
    """Independent :func:`build_output_gp` models for every column of ``train_Y``.

    Noise precedence: ``train_Yvar`` tensor, per-output ``objective_noise_variances`` (when
    ``per_output_noise``), scalar fixed noise, deterministic relative noise.
    """
    if train_X.shape[0] == 0:
        raise ValueError("Cannot build GP model with empty training set.")
    target_device = get_device(device)
    train_Y_dbl = train_Y.to(dtype=torch.double, device=target_device)
    if train_Y_dbl.ndim != 2 or train_Y_dbl.shape[1] < 1:
        raise ValueError("train_Y must be a nonempty (N, M) matrix.")
    if train_Yvar is not None:
        _validate_noise(train_Yvar, train_Y_dbl.shape)
    count = train_Y_dbl.shape[1]
    if per_output_noise and settings.objective_noise_variances is not None and len(settings.objective_noise_variances) != count:
        raise ValueError("objective_noise_variances must define every output.")
    models = [build_output_gp(train_X, train_Y_dbl[:, index:index + 1], bounds,
                              settings.for_output(index if per_output_noise else None),
                              train_Yvar=train_Yvar[:, index:index + 1] if train_Yvar is not None else None,
                              device=target_device)
              for index in range(count)]
    return ModelListGP(*models).to(device=target_device, dtype=torch.double)


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
    if model in _RECORDS:
        inputs = _RECORDS[model].train_X.to(next(model.parameters()))
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
    """Fit models in place; per-output outcomes are available from :func:`fit_outcomes`.

    Both optimizers start from the same snapshot. If both fail, restore and verify
    that snapshot before exposing a usable prior fallback. An unusable prior raises.
    """
    for model in output_models(model_list):
        record = channel_record(model)
        record.fit_outcome = None
        record.fit_outcome = _fit_single_mll_resilient(ExactMarginalLogLikelihood(model.likelihood, model))
    model_list.eval()
    return model_list
