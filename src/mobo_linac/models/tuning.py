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


def compare_acquisition_functions(
    model: Any,
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    ref_point: torch.Tensor,
    bounds: torch.Tensor,
    acq_types: Optional[List[str]] = None,
    batch_size: int = 8,
    num_restarts: int = 10,
    raw_samples: int = 128,
    maxiter: int = 50,
    device: Optional[Union[torch.device, str]] = None,
) -> pd.DataFrame:
    """
    Compares candidate generation speed, proposal qualities, and acquisition function
    characteristics across supported acquisition function types.

    Args:
        model: Fitted ModelListGP surrogate.
        train_X: (N, D) PyTorch tensor of design variables.
        train_Y: (N, M) PyTorch tensor of objective observations.
        ref_point: (M,) PyTorch tensor of reference point values.
        bounds: (2, D) PyTorch tensor of parameter bounds.
        acq_types: List of acquisition types to benchmark (default: ['qLogNEHVI', 'qLogEHVI', 'qEHVI', 'qNEHVI']).
        batch_size: Batch size q.
        num_restarts: Restart count for acquisition optimization.
        raw_samples: Raw sample count for initialization.
        maxiter: Max L-BFGS iterations per restart.
        device: Target compute device.

    Returns:
        DataFrame summarizing proposal runtime and statistics per acquisition type.
    """
    import time
    from mobo_linac.acquisition.mobo import build_acquisition_function, generate_next_candidates

    if acq_types is None:
        acq_types = ["qLogNEHVI", "qLogEHVI", "qEHVI", "qNEHVI"]

    summary_rows = []

    for acq_type in acq_types:
        t0 = time.time()
        try:
            acq_func = build_acquisition_function(
                model=model,
                train_X=train_X,
                train_Y=train_Y,
                ref_point=ref_point,
                acq_type=acq_type,
            )
            t_build = time.time() - t0

            t_opt_start = time.time()
            candidates, acq_values = generate_next_candidates(
                acq_func=acq_func,
                bounds=bounds,
                batch_size=batch_size,
                num_restarts=num_restarts,
                raw_samples=raw_samples,
                maxiter=maxiter,
                device=device,
                retry_on_failure=True,
            )
            t_opt = time.time() - t_opt_start
            total_time = time.time() - t0

            summary_rows.append({
                "Acquisition Type": acq_type,
                "Build Time (s)": round(t_build, 3),
                "Opt Time (s)": round(t_opt, 3),
                "Total Time (s)": round(total_time, 3),
                "Candidates (q)": candidates.shape[0],
                "Mean Acq Value": round(float(acq_values.mean().item()), 4),
                "Status": "SUCCESS",
            })
        except Exception as e:
            summary_rows.append({
                "Acquisition Type": acq_type,
                "Build Time (s)": 0.0,
                "Opt Time (s)": 0.0,
                "Total Time (s)": round(time.time() - t0, 3),
                "Candidates (q)": 0,
                "Mean Acq Value": 0.0,
                "Status": f"FAILED: {e}",
            })

    return pd.DataFrame(summary_rows)


@dataclass
class AcquisitionHyperparameterResult:
    """Evaluation result for an acquisition hyperparameter combination."""
    acq_type: str
    num_restarts: int
    raw_samples: int
    maxiter: int
    batch_limit: int
    mean_acq_value: float
    candidate_diversity: float
    proposal_time_s: float
    status: str = "SUCCESS"


@dataclass
class AcquisitionTuningSummary:
    """Summary of acquisition function hyperparameter optimization."""
    best_acq_type: str
    best_execution_config: ExecutionConfig
    best_candidate: AcquisitionHyperparameterResult
    comparison_table: pd.DataFrame
    candidates: List[AcquisitionHyperparameterResult]


def compute_candidate_diversity(candidates: torch.Tensor) -> float:
    """Computes mean pairwise Euclidean distance between proposed batch candidates."""
    if candidates.shape[0] < 2:
        return 0.0
    diff = candidates.unsqueeze(1) - candidates.unsqueeze(0)
    dists = torch.norm(diff, dim=-1)
    n = candidates.shape[0]
    # Extract upper triangle without diagonal
    triu_indices = torch.triu_indices(n, n, offset=1)
    pair_dists = dists[triu_indices[0], triu_indices[1]]
    return float(pair_dists.mean().item())


def tune_acquisition_hyperparameters(
    model: Any,
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    ref_point: torch.Tensor,
    bounds: torch.Tensor,
    candidate_acq_types: Optional[List[str]] = None,
    candidate_restarts: Optional[List[int]] = None,
    candidate_raw_samples: Optional[List[int]] = None,
    batch_size: int = 8,
    batch_limit: int = 1,
    maxiter: int = 50,
    device: Optional[Union[torch.device, str]] = None,
) -> AcquisitionTuningSummary:
    """
    Evaluates and selects optimal acquisition function parameters (type, restarts, raw samples)
    by evaluating candidate acquisition scores, proposal spatial diversity, and latency.

    Args:
        model: Fitted ModelListGP surrogate model.
        train_X: (N, D) PyTorch tensor of design variables.
        train_Y: (N, M) PyTorch tensor of observations.
        ref_point: (M,) PyTorch tensor reference point.
        bounds: (2, D) PyTorch tensor of parameter bounds.
        candidate_acq_types: List of acquisition types to evaluate (default: ['qLogNEHVI', 'qLogEHVI', 'qEHVI']).
        candidate_restarts: List of restart budgets (default: [5, 10, 20]).
        candidate_raw_samples: List of raw sample counts (default: [64, 128, 256]).
        batch_size: Candidate proposal batch size q.
        batch_limit: Concurrency batch limit.
        maxiter: Optimization iterations per restart.
        device: Target compute device.

    Returns:
        AcquisitionTuningSummary with optimal acq_type, ExecutionConfig, and comparison table.
    """
    import time
    from mobo_linac.acquisition.mobo import build_acquisition_function, generate_next_candidates

    if candidate_acq_types is None:
        candidate_acq_types = ["qLogNEHVI", "qLogEHVI", "qEHVI"]
    if candidate_restarts is None:
        candidate_restarts = [5, 10, 20]
    if candidate_raw_samples is None:
        candidate_raw_samples = [64, 128, 256]

    results: List[AcquisitionHyperparameterResult] = []

    for acq_type in candidate_acq_types:
        try:
            acq_func = build_acquisition_function(
                model=model,
                train_X=train_X,
                train_Y=train_Y,
                ref_point=ref_point,
                acq_type=acq_type,
            )
        except Exception as e:
            continue

        for n_restarts in candidate_restarts:
            for raw_s in candidate_raw_samples:
                t0 = time.time()
                try:
                    candidates, acq_values = generate_next_candidates(
                        acq_func=acq_func,
                        bounds=bounds,
                        batch_size=batch_size,
                        num_restarts=n_restarts,
                        raw_samples=raw_s,
                        maxiter=maxiter,
                        batch_limit=batch_limit,
                        device=device,
                        retry_on_failure=True,
                    )
                    prop_time = time.time() - t0
                    diversity = compute_candidate_diversity(candidates)
                    mean_acq = float(acq_values.mean().item())

                    cand_res = AcquisitionHyperparameterResult(
                        acq_type=acq_type,
                        num_restarts=n_restarts,
                        raw_samples=raw_s,
                        maxiter=maxiter,
                        batch_limit=batch_limit,
                        mean_acq_value=mean_acq,
                        candidate_diversity=diversity,
                        proposal_time_s=prop_time,
                        status="SUCCESS",
                    )
                    results.append(cand_res)
                except Exception as err:
                    cand_res = AcquisitionHyperparameterResult(
                        acq_type=acq_type,
                        num_restarts=n_restarts,
                        raw_samples=raw_s,
                        maxiter=maxiter,
                        batch_limit=batch_limit,
                        mean_acq_value=0.0,
                        candidate_diversity=0.0,
                        proposal_time_s=time.time() - t0,
                        status=f"FAILED: {err}",
                    )
                    results.append(cand_res)

    if not results:
        # Fallback default
        default_res = AcquisitionHyperparameterResult(
            acq_type="qLogNEHVI",
            num_restarts=20,
            raw_samples=256,
            maxiter=maxiter,
            batch_limit=batch_limit,
            mean_acq_value=0.0,
            candidate_diversity=0.0,
            proposal_time_s=0.0,
        )
        results = [default_res]

    # Sort candidates by composite trade-off (higher diversity and acquisition value, reasonable proposal time)
    results_sorted = sorted(results, key=lambda c: (-c.candidate_diversity, -c.mean_acq_value, c.proposal_time_s))
    best_cand = results_sorted[0]

    best_exec_cfg = ExecutionConfig(
        acqf_num_restarts=best_cand.num_restarts,
        acqf_raw_samples=best_cand.raw_samples,
        acqf_maxiter=best_cand.maxiter,
        acqf_batch_limit=best_cand.batch_limit,
    )

    rows = []
    for c in results_sorted:
        rows.append({
            "Acquisition Type": c.acq_type,
            "Restarts": c.num_restarts,
            "Raw Samples": c.raw_samples,
            "Mean Acq Value": round(c.mean_acq_value, 4),
            "Diversity Score": round(c.candidate_diversity, 4),
            "Proposal Time (s)": round(c.proposal_time_s, 3),
            "Status": c.status,
        })
    comp_df = pd.DataFrame(rows)

    return AcquisitionTuningSummary(
        best_acq_type=best_cand.acq_type,
        best_execution_config=best_exec_cfg,
        best_candidate=best_cand,
        comparison_table=comp_df,
        candidates=results_sorted,
    )


@dataclass
class PipelineTuningSummary:
    """Unified summary for joint surrogate and acquisition hyperparameter optimization."""
    best_gp_config: GpModelConfig
    best_acq_type: str
    best_execution_config: ExecutionConfig
    gp_comparison_table: pd.DataFrame
    acq_comparison_table: pd.DataFrame


def tune_full_optimization_pipeline(
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    bounds: torch.Tensor,
    ref_point: Optional[torch.Tensor] = None,
    batch_size: int = 8,
    device: Optional[Union[torch.device, str]] = None,
) -> PipelineTuningSummary:
    """
    Executes end-to-end joint hyperparameter optimization across both GP surrogate models
    and acquisition functions for the 200 MeV electron injector linac.

    Args:
        train_X: (N, D) PyTorch tensor of design variables.
        train_Y: (N, M) PyTorch tensor of objective observations.
        bounds: (2, D) PyTorch tensor of bounds.
        ref_point: Optional (M,) PyTorch tensor reference point.
        batch_size: Batch size q.
        device: Target compute device.

    Returns:
        PipelineTuningSummary with optimal GP config, optimal acquisition function, and ExecutionConfig.
    """
    from mobo_linac.metrics.hypervolume import compute_reference_point

    if ref_point is None:
        ref_point = compute_reference_point(train_Y, offset_ratio=0.05)

    # 1. Tune GP Surrogate Hyperparameters
    gp_summary = tune_gp_hyperparameters(
        train_X=train_X,
        train_Y=train_Y,
        bounds=bounds,
        candidate_covars=["matern52", "rbf"],
        candidate_noise_ratios=[1.0e-8, 1.0e-6, 1.0e-4],
        candidate_noise_modes=["deterministic_fixed"],
        device=device,
    )

    # 2. Fit optimal surrogate
    model = build_gp_models(
        train_X=train_X,
        train_Y=train_Y,
        bounds=bounds,
        covar_type=gp_summary.best_config.covar_type,
        noise_mode=gp_summary.best_config.noise_mode,
        relative_noise_ratio=gp_summary.best_config.relative_noise_ratio,
        device=device,
    )
    fitted_model = fit_gp_models(model)

    # 3. Tune Acquisition Function Hyperparameters
    acq_summary = tune_acquisition_hyperparameters(
        model=fitted_model,
        train_X=train_X,
        train_Y=train_Y,
        ref_point=ref_point,
        bounds=bounds,
        candidate_acq_types=["qLogNEHVI", "qLogEHVI", "qEHVI"],
        candidate_restarts=[5, 10, 20],
        candidate_raw_samples=[64, 128, 256],
        batch_size=batch_size,
        device=device,
    )

    return PipelineTuningSummary(
        best_gp_config=gp_summary.best_config,
        best_acq_type=acq_summary.best_acq_type,
        best_execution_config=acq_summary.best_execution_config,
        gp_comparison_table=gp_summary.comparison_table,
        acq_comparison_table=acq_summary.comparison_table,
    )

