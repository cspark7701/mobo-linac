"""
Gaussian Process Surrogate Models for Linac Optimization.

Builds independent SingleTaskGP models with Normalize input transforms
and Standardize outcome transforms grouped in a ModelListGP.
"""

from typing import Optional, Tuple
import torch
from botorch.fit import fit_gpytorch_mll
from botorch.models import ModelListGP, SingleTaskGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
from gpytorch.mlls import SumMarginalLogLikelihood


def build_gp_models(
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    bounds: torch.Tensor,
) -> ModelListGP:
    """
    Builds a ModelListGP containing an independent SingleTaskGP for each objective.

    Args:
        train_X: (N, D) PyTorch double tensor of design variables.
        train_Y: (N, M) PyTorch double tensor of model-space objectives.
        bounds: (2, D) PyTorch double tensor of parameter bounds.

    Returns:
        Constructed ModelListGP instance.
    """
    if train_X.shape[0] == 0:
        raise ValueError("Cannot build GP model with empty training set.")

    train_X_dbl = train_X.to(dtype=torch.double)
    train_Y_dbl = train_Y.to(dtype=torch.double)
    bounds_dbl = bounds.to(dtype=torch.double)

    models = []
    num_objectives = train_Y_dbl.shape[-1]
    input_transform = Normalize(d=bounds_dbl.shape[1], bounds=bounds_dbl)

    for idx in range(num_objectives):
        y_col = train_Y_dbl[:, idx : idx + 1]
        gp = SingleTaskGP(
            train_X=train_X_dbl,
            train_Y=y_col,
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
