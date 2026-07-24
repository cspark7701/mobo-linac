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
    noise_mode: str = "fixed",
    fixed_noise_val: float = 1e-6,
) -> ModelListGP:
    """
    Builds a ModelListGP containing an independent SingleTaskGP for each objective
    with explicit ARD covariance kernel and noise model.

    Args:
        train_X: (N, D) PyTorch double tensor of design variables.
        train_Y: (N, M) PyTorch double tensor of model-space objectives.
        bounds: (2, D) PyTorch double tensor of parameter bounds.
        covar_type: Covariance kernel type ('matern52' or 'rbf').
        noise_mode: Noise treatment ('fixed' near-zero for deterministic or 'inferred').
        fixed_noise_val: Fixed observation noise variance when noise_mode == 'fixed'.

    Returns:
        Constructed ModelListGP instance.
    """
    if train_X.shape[0] == 0:
        raise ValueError("Cannot build GP model with empty training set.")

    train_X_dbl = train_X.to(dtype=torch.double)
    train_Y_dbl = train_Y.to(dtype=torch.double)
    bounds_dbl = bounds.to(dtype=torch.double)

    input_dim = bounds_dbl.shape[1]
    num_objectives = train_Y_dbl.shape[-1]
    input_transform = Normalize(d=input_dim, bounds=bounds_dbl)

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

        # Noise Likelihood Construction
        if noise_mode == "fixed":
            likelihood = GaussianLikelihood(noise_constraint=GreaterThan(1e-8))
            likelihood.noise = torch.tensor([fixed_noise_val], dtype=torch.double)
        elif noise_mode == "inferred":
            likelihood = GaussianLikelihood()
        else:
            raise ValueError(f"Unsupported noise_mode: '{noise_mode}'. Choose 'fixed' or 'inferred'.")

        gp = SingleTaskGP(
            train_X=train_X_dbl,
            train_Y=y_col,
            likelihood=likelihood,
            covar_module=covar_module,
            input_transform=input_transform,
            outcome_transform=Standardize(m=1),
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

