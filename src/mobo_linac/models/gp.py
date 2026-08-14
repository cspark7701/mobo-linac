"""
Gaussian Process Surrogate Models for Linac Optimization.

Builds independent SingleTaskGP models with explicit ARD Matérn-5/2 or RBF kernels,
configurable observation noise treatment (fixed near-zero for deterministic simulation
or inferred), Normalize input transforms, and Standardize outcome transforms grouped in a ModelListGP.
"""

from typing import Dict, List, Optional, Tuple, Union
import torch
from botorch.fit import fit_gpytorch_mll
from botorch.models import ModelListGP, SingleTaskGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
import gpytorch
from gpytorch.constraints import GreaterThan
from gpytorch.kernels import MaternKernel, RBFKernel, ScaleKernel
from gpytorch.likelihoods import GaussianLikelihood
from gpytorch.mlls import SumMarginalLogLikelihood


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
        train_Yvar: Optional (N, M) tensor of observation noise variances.
        relative_noise_ratio: Ratio of empirical objective variance for deterministic noise scaling (default 1e-6).
        min_noise_variance: Absolute minimum variance floor for numerical stability (default 1e-14).
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

    input_dim = bounds_dbl.shape[1]
    num_objectives = train_Y_dbl.shape[-1]
    input_transform = Normalize(d=input_dim, bounds=bounds_dbl)

    # Normalize noise_mode alias
    mode = "deterministic_fixed" if noise_mode == "fixed" else noise_mode

    models = []
    for idx in range(num_objectives):
        y_col = train_Y_dbl[:, idx : idx + 1]

        # Explicit ARD Kernel Construction
        if covar_type == "rbf":
            base_kernel = RBFKernel(ard_num_dims=input_dim)
        elif covar_type == "matern52":
            base_kernel = MaternKernel(nu=2.5, ard_num_dims=input_dim)
        else:
            raise ValueError(f"Unsupported covar_type: '{covar_type}'. Choose 'matern52' or 'rbf'.")

        covar_module = ScaleKernel(base_kernel)

        # Noise Treatment Construction
        if mode in ("deterministic_fixed", "measured_fixed"):
            if train_Yvar is not None and train_Yvar.shape[0] == train_Y_dbl.shape[0]:
                yvar_col = train_Yvar[:, idx : idx + 1].to(dtype=torch.double, device=target_device)
            elif objective_noise_variances is not None and len(objective_noise_variances) > idx and objective_noise_variances[idx] is not None:
                yvar_col = torch.full_like(y_col, fill_value=float(objective_noise_variances[idx]), device=target_device)
            elif fixed_noise_val is not None:
                yvar_col = torch.full_like(y_col, fill_value=float(fixed_noise_val), device=target_device)
            else:
                # Relative noise scaling based on empirical sample variance
                if y_col.shape[0] > 1:
                    sample_var = float(torch.var(y_col, unbiased=True).item())
                else:
                    sample_var = 0.0
                computed_var = max(relative_noise_ratio * sample_var, min_noise_variance)
                yvar_col = torch.full_like(y_col, fill_value=float(computed_var), device=target_device)

            gp = SingleTaskGP(
                train_X=train_X_dbl,
                train_Y=y_col,
                train_Yvar=yvar_col,
                covar_module=covar_module,
                input_transform=input_transform,
                outcome_transform=Standardize(m=1),
            )
        elif mode == "inferred":
            gp = SingleTaskGP(
                train_X=train_X_dbl,
                train_Y=y_col,
                covar_module=covar_module,
                input_transform=input_transform,
                outcome_transform=Standardize(m=1),
            )
        else:
            raise ValueError(
                f"Unsupported noise_mode: '{noise_mode}'. Choose 'deterministic_fixed', 'measured_fixed', or 'inferred'."
            )

        models.append(gp)

    model_list = ModelListGP(*models)
    return model_list



def fit_gp_models(model_list: ModelListGP) -> ModelListGP:
    """
    Fits Marginal Log-Likelihood hyperparameters for all models in ModelListGP.

    Args:
        model_list: ModelListGP instance to fit.

    Returns:
        Fitted ModelListGP instance.
    """
    mll = SumMarginalLogLikelihood(model_list.likelihood, model_list)
    fit_gpytorch_mll(mll)
    return model_list

