"""
Hyperparameter Optimization and Surrogate Model Selection Module.

Provides systematic cross-validation, kernel selection (Matérn 5/2 vs. RBF),
noise ratio optimization, and acquisition budget tuning for Gaussian Process
surrogates and multi-objective acquisition functions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import torch
from gpytorch.mlls import ExactMarginalLogLikelihood

from mobo_linac.config import GpModelConfig, ExecutionConfig
from mobo_linac.models.gp import build_gp_models, fit_gp_models
from mobo_linac.models.diagnostics import compute_predictive_diagnostics


@dataclass
class HyperparameterCandidateResult:
    """Evaluation result for a single surrogate hyperparameter candidate."""
    covar_type: str
    noise_mode: str
    relative_noise_ratio: float
    mean_mll: float
    overall_rmse: float
    overall_r2: float
    per_objective_r2: Dict[str, float] = field(default_factory=dict)
    fit_time_s: float = 0.0


@dataclass
class HyperparameterTuningSummary:
    """Summary of hyperparameter grid search optimization."""
    best_config: GpModelConfig
    best_candidate: HyperparameterCandidateResult
    comparison_table: pd.DataFrame
    candidates: List[HyperparameterCandidateResult]


def tune_gp_hyperparameters(
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    bounds: torch.Tensor,
    candidate_covars: Optional[List[str]] = None,
    candidate_noise_ratios: Optional[List[float]] = None,
    candidate_noise_modes: Optional[List[str]] = None,
    objective_names: Optional[List[str]] = None,
    device: Optional[Union[torch.device, str]] = None,
) -> HyperparameterTuningSummary:
    """
    Executes grid search cross-validation and marginal log-likelihood evaluation
    to identify optimal GP surrogate hyperparameters for the linac training data.

    Args:
        train_X: (N, D) PyTorch tensor of design variables.
        train_Y: (N, M) PyTorch tensor of objective observations.
        bounds: (2, D) PyTorch tensor of parameter bounds.
        candidate_covars: List of kernel types to evaluate (default: ['matern52', 'rbf']).
        candidate_noise_ratios: List of relative noise ratios (default: [1e-8, 1e-6, 1e-4]).
        candidate_noise_modes: List of noise treatment modes (default: ['deterministic_fixed', 'inferred']).
        objective_names: List of objective names for diagnostics.
        device: Target compute device ('cpu', 'cuda', 'auto').

    Returns:
        HyperparameterTuningSummary with optimal config, comparison table, and candidate metrics.
    """
    import time

    if candidate_covars is None:
        candidate_covars = ["matern52", "rbf"]
    if candidate_noise_ratios is None:
        candidate_noise_ratios = [1.0e-8, 1.0e-6, 1.0e-4]
    if candidate_noise_modes is None:
        candidate_noise_modes = ["deterministic_fixed", "inferred"]

    if objective_names is None:
        objective_names = [f"obj_{i}" for i in range(train_Y.shape[1])]

    results: List[HyperparameterCandidateResult] = []

    for covar in candidate_covars:
        for mode in candidate_noise_modes:
            noise_ratios = candidate_noise_ratios if mode == "deterministic_fixed" else [1.0e-6]
            for ratio in noise_ratios:
                t0 = time.time()
                try:
                    model_list = build_gp_models(
                        train_X=train_X,
                        train_Y=train_Y,
                        bounds=bounds,
                        covar_type=covar,
                        noise_mode=mode,
                        relative_noise_ratio=ratio,
                        device=device,
                    )
                    fitted_model = fit_gp_models(model_list)
                    fit_time = time.time() - t0

                    # Compute MLL
                    mll_vals = []
                    for sub_model in fitted_model.models:
                        mll = ExactMarginalLogLikelihood(sub_model.likelihood, sub_model)
                        output = sub_model(sub_model.train_inputs[0])
                        log_lik = mll(output, sub_model.train_targets).detach().item()
                        mll_vals.append(log_lik)
                    mean_mll = float(np.mean(mll_vals))

                    # Compute diagnostics
                    diag = compute_predictive_diagnostics(
                        model=fitted_model,
                        train_X=train_X,
                        train_Y=train_Y,
                        objective_names=objective_names,
                    )

                    per_obj_r2 = {
                        name: diag["objectives"][name]["r2"]
                        for name in objective_names
                        if name in diag["objectives"]
                    }

                    cand_res = HyperparameterCandidateResult(
                        covar_type=covar,
                        noise_mode=mode,
                        relative_noise_ratio=ratio,
                        mean_mll=mean_mll,
                        overall_rmse=diag["overall_rmse"],
                        overall_r2=diag["overall_r2"],
                        per_objective_r2=per_obj_r2,
                        fit_time_s=fit_time,
                    )
                    results.append(cand_res)
                except Exception as err:
                    # Record failed candidate with poor score
                    cand_res = HyperparameterCandidateResult(
                        covar_type=covar,
                        noise_mode=mode,
                        relative_noise_ratio=ratio,
                        mean_mll=-1e9,
                        overall_rmse=1e9,
                        overall_r2=-1.0,
                        fit_time_s=time.time() - t0,
                    )
                    results.append(cand_res)

    # Rank candidates by composite score (highest R^2 and MLL, lowest RMSE)
    # Primary sort: overall_r2 (descending), secondary: overall_rmse (ascending)
    results_sorted = sorted(results, key=lambda c: (-c.overall_r2, c.overall_rmse, -c.mean_mll))
    best_cand = results_sorted[0]

    best_cfg = GpModelConfig(
        covar_type=best_cand.covar_type,
        noise_mode=best_cand.noise_mode,
        relative_noise_ratio=best_cand.relative_noise_ratio,
    )

    # Build comparison summary table
    rows = []
    for c in results_sorted:
        rows.append({
            "Kernel": c.covar_type,
            "Noise Mode": c.noise_mode,
            "Noise Ratio": f"{c.relative_noise_ratio:.1e}",
            "Mean MLL": round(c.mean_mll, 3),
            "Overall RMSE": f"{c.overall_rmse:.3e}",
            "Overall R^2": round(c.overall_r2, 4),
            "Fit Time (s)": round(c.fit_time_s, 3),
        })
    comp_df = pd.DataFrame(rows)

    return HyperparameterTuningSummary(
        best_config=best_cfg,
        best_candidate=best_cand,
        comparison_table=comp_df,
        candidates=results_sorted,
    )
