"""
Predictive Diagnostics for Gaussian Process Surrogate Models.

In-sample fit statistics are reported separately from exact leave-one-out (LOO)
predictions. LOO uses the closed form for a GP with fixed hyperparameters: with
``K`` the training covariance including observation noise and ``r = y - m``,

    mu_{-i}  = y_i - [K^{-1} r]_i / [K^{-1}]_{ii},     var_{-i} = 1 / [K^{-1}]_{ii},

computed in the model's internal (input-normalized, outcome-standardized) space and
mapped back to output units.
"""

import math
from typing import Any, Dict, List, Optional

import numpy as np
import torch


def _single_models(model) -> List[Any]:
    return list(model.models) if hasattr(model, "models") else [model]


def loo_predictions(model) -> Dict[str, torch.Tensor]:
    """Exact LOO predictive mean/variance of every training observation of a single-output GP.

    Returns standardized-space quantities (``mean_std``, ``var_std``, ``target_std``) and the
    same quantities in output units (``mean``, ``var``, ``target``).
    """
    model.eval()
    inputs = model.train_inputs[0]
    targets = model.train_targets
    with torch.no_grad():
        covariance = model.covar_module(inputs).to_dense()
        noise = model.likelihood.noise.reshape(-1).expand(targets.shape[-1])
        covariance = covariance + torch.diag_embed(noise)
        residual = targets - model.mean_module(inputs)
        jitter = 1e-10 * covariance.diagonal().mean()
        factor = torch.linalg.cholesky(covariance + jitter * torch.eye(covariance.shape[-1], dtype=covariance.dtype,
                                                                       device=covariance.device))
        inverse = torch.cholesky_inverse(factor)
        diagonal = inverse.diagonal()
        mean_std = targets - (inverse @ residual) / diagonal
        var_std = 1.0 / diagonal
    scale = torch.ones((), dtype=targets.dtype, device=targets.device)
    offset = torch.zeros((), dtype=targets.dtype, device=targets.device)
    transform = getattr(model, "outcome_transform", None)
    if transform is not None and hasattr(transform, "stdvs"):
        scale, offset = transform.stdvs.reshape(()), transform.means.reshape(())
    return {"mean_std": mean_std, "var_std": var_std, "target_std": targets,
            "mean": mean_std * scale + offset, "var": var_std * scale ** 2, "target": targets * scale + offset}


def _gaussian_log_density(target, mean, var) -> torch.Tensor:
    return -0.5 * (torch.log(2 * math.pi * var) + (target - mean) ** 2 / var)


def compute_predictive_diagnostics(
    model: Any,
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    objective_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    In-sample fit and exact LOO diagnostics for each output of a fitted GP (or model list).

    Per output: in-sample RMSE/MAE/R^2 and standardized residual moments, and LOO RMSE,
    LOO mean log predictive density in standardized units (comparable across outputs),
    and the LOO coverage of the +-1 and +-2 sigma intervals.
    """
    try:
        model_device = next(model.parameters()).device
    except (StopIteration, AttributeError):
        model_device = train_X.device

    train_X_dbl = train_X.to(device=model_device, dtype=torch.double)
    train_Y_dbl = train_Y.to(device=model_device, dtype=torch.double)
    num_samples, num_objectives = train_Y_dbl.shape
    if objective_names is None:
        objective_names = [f"objective_{i}" for i in range(num_objectives)]

    model.eval()
    with torch.no_grad():
        posterior = model.posterior(train_X_dbl)
        pred_means = posterior.mean
        pred_stds = posterior.variance.clamp_min(1e-12).sqrt()

    diagnostics: Dict[str, Dict[str, float]] = {}
    for index, sub_model in enumerate(_single_models(model)[:num_objectives]):
        name = objective_names[index]
        y_true, y_pred = train_Y_dbl[:, index], pred_means[:, index]
        residual = y_true - y_pred
        std_res = residual / pred_stds[:, index]
        y_var = float(torch.var(y_true, unbiased=False))
        rmse = float(torch.sqrt(torch.mean(residual ** 2)))
        loo = loo_predictions(sub_model)
        loo_error = loo["target"] - loo["mean"]
        z = (loo["target_std"] - loo["mean_std"]) / loo["var_std"].sqrt()
        diagnostics[name] = {
            "in_sample_rmse": rmse,
            "in_sample_mae": float(torch.mean(residual.abs())),
            "in_sample_r2": float(1.0 - rmse ** 2 / y_var) if y_var > 1e-12 else 1.0,
            "mean_standardized_residual": float(std_res.mean()),
            "std_standardized_residual": float(std_res.std()),
            "loo_rmse": float(torch.sqrt(torch.mean(loo_error ** 2))),
            "loo_log_predictive_density": float(
                _gaussian_log_density(loo["target_std"], loo["mean_std"], loo["var_std"]).mean()),
            "loo_coverage_1sigma": float((z.abs() <= 1.0).double().mean()),
            "loo_coverage_2sigma": float((z.abs() <= 2.0).double().mean()),
        }

    return {
        "num_samples": num_samples,
        "num_objectives": num_objectives,
        "mean_in_sample_r2": float(np.mean([d["in_sample_r2"] for d in diagnostics.values()])),
        "mean_loo_log_predictive_density": float(np.mean([d["loo_log_predictive_density"] for d in diagnostics.values()])),
        "objectives": diagnostics,
    }
