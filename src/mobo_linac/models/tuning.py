"""
Surrogate and acquisition settings selection.

GP settings are ranked by exact leave-one-out (LOO) mean log predictive density in
standardized units, an out-of-sample criterion comparable across outputs; in-sample
fit statistics are reported but never used for ranking. Acquisition settings are
ranked by the expected hypervolume improvement (EHVI) of their proposed batch,
evaluated with one common non-log Monte Carlo estimator, fixed sampler and the
campaign's reporting reference, so different acquisition types are comparable.
Candidate diversity and timing are reported as diagnostics only. Failures are
recorded with their error and excluded from ranking.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd
import torch
from gpytorch.mlls import ExactMarginalLogLikelihood

from mobo_linac.campaign_options import MULTIOBJECTIVE_ACQUISITIONS
from mobo_linac.config import GpModelConfig, ExecutionConfig
from mobo_linac.models.diagnostics import compute_predictive_diagnostics
from mobo_linac.models.gp import build_gp_models, fit_gp_models


@dataclass
class HyperparameterCandidateResult:
    """Evaluation of one surrogate hyperparameter candidate."""
    covar_type: str
    noise_mode: str
    relative_noise_ratio: float
    status: str = "SUCCESS"
    error: Optional[str] = None
    mean_loo_log_predictive_density: float = float("nan")
    mean_loo_coverage_2sigma: float = float("nan")
    mean_mll: float = float("nan")
    mean_in_sample_r2: float = float("nan")
    per_objective_loo_lpd: Dict[str, float] = field(default_factory=dict)
    fit_time_s: float = 0.0


@dataclass
class HyperparameterTuningSummary:
    """Ranked surrogate hyperparameter candidates."""
    best_config: GpModelConfig
    best_candidate: HyperparameterCandidateResult
    comparison_table: pd.DataFrame
    candidates: List[HyperparameterCandidateResult]


def _error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


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
    Grid search over kernels and noise treatments ranked by exact LOO log predictive density.

    Raises RuntimeError if no candidate could be fitted; failed candidates keep their error.
    """
    candidate_covars = candidate_covars or ["matern52", "rbf"]
    candidate_noise_ratios = candidate_noise_ratios or [1.0e-8, 1.0e-6, 1.0e-4]
    candidate_noise_modes = candidate_noise_modes or ["deterministic_fixed", "inferred"]
    objective_names = objective_names or [f"obj_{i}" for i in range(train_Y.shape[1])]

    results: List[HyperparameterCandidateResult] = []
    for covar in candidate_covars:
        for mode in candidate_noise_modes:
            for ratio in (candidate_noise_ratios if mode == "deterministic_fixed" else [1.0e-6]):
                started = time.perf_counter()
                candidate = HyperparameterCandidateResult(covar, mode, ratio)
                try:
                    model = fit_gp_models(build_gp_models(train_X=train_X, train_Y=train_Y, bounds=bounds,
                                                          covar_type=covar, noise_mode=mode,
                                                          relative_noise_ratio=ratio, device=device))
                    mll_values = []
                    for sub_model in model.models:
                        mll = ExactMarginalLogLikelihood(sub_model.likelihood, sub_model)
                        sub_model.train()
                        output = sub_model(sub_model.train_inputs[0])
                        mll_values.append(float(mll(output, sub_model.train_targets).detach()))
                        sub_model.eval()
                    diagnostics = compute_predictive_diagnostics(model, train_X, train_Y, objective_names)
                    per_objective = diagnostics["objectives"]
                    candidate.mean_loo_log_predictive_density = diagnostics["mean_loo_log_predictive_density"]
                    candidate.mean_loo_coverage_2sigma = float(np.mean([d["loo_coverage_2sigma"] for d in per_objective.values()]))
                    candidate.mean_mll = float(np.mean(mll_values))
                    candidate.mean_in_sample_r2 = diagnostics["mean_in_sample_r2"]
                    candidate.per_objective_loo_lpd = {name: d["loo_log_predictive_density"] for name, d in per_objective.items()}
                    if not np.isfinite(candidate.mean_loo_log_predictive_density):
                        raise FloatingPointError("Nonfinite LOO log predictive density")
                except Exception as error:  # recorded, never scored
                    candidate.status, candidate.error = "FAILED", _error(error)
                candidate.fit_time_s = time.perf_counter() - started
                results.append(candidate)

    succeeded = [c for c in results if c.status == "SUCCESS"]
    if not succeeded:
        raise RuntimeError("No surrogate candidate could be fitted: " + "; ".join(c.error for c in results))
    ranked = sorted(succeeded, key=lambda c: (-c.mean_loo_log_predictive_density, c.fit_time_s))
    ordered = ranked + [c for c in results if c.status != "SUCCESS"]
    best = ranked[0]
    table = pd.DataFrame([{
        "Kernel": c.covar_type, "Noise Mode": c.noise_mode, "Noise Ratio": f"{c.relative_noise_ratio:.1e}",
        "LOO Log Predictive Density": round(c.mean_loo_log_predictive_density, 4),
        "LOO 2-sigma Coverage": round(c.mean_loo_coverage_2sigma, 3),
        "Mean MLL": round(c.mean_mll, 3), "In-Sample R^2": round(c.mean_in_sample_r2, 4),
        "Fit Time (s)": round(c.fit_time_s, 3), "Status": c.status, "Error": c.error or "",
    } for c in ordered])
    return HyperparameterTuningSummary(
        best_config=GpModelConfig(covar_type=best.covar_type, noise_mode=best.noise_mode,
                                  relative_noise_ratio=best.relative_noise_ratio),
        best_candidate=best, comparison_table=table, candidates=ordered)


def common_batch_ehvi(model: Any, candidates: torch.Tensor, train_Y: torch.Tensor,
                      ref_point: torch.Tensor, num_samples: int = 256, seed: int = 0) -> float:
    """EHVI of a proposed batch under one shared non-log estimator and fixed QMC sampler."""
    from botorch.acquisition.multi_objective.monte_carlo import qExpectedHypervolumeImprovement
    from botorch.sampling.normal import SobolQMCNormalSampler
    from botorch.utils.multi_objective.box_decompositions.non_dominated import FastNondominatedPartitioning
    device = next(model.parameters()).device
    reference = ref_point.to(device=device, dtype=torch.double)
    partitioning = FastNondominatedPartitioning(ref_point=reference, Y=train_Y.to(device=device, dtype=torch.double))
    acquisition = qExpectedHypervolumeImprovement(
        model=model, ref_point=reference, partitioning=partitioning,
        sampler=SobolQMCNormalSampler(sample_shape=torch.Size([num_samples]), seed=seed))
    with torch.no_grad():
        return float(acquisition(candidates.to(device=device, dtype=torch.double).unsqueeze(0)).item())


def compute_candidate_diversity(candidates: torch.Tensor) -> float:
    """Mean pairwise Euclidean distance between proposed batch candidates (diagnostic only)."""
    if candidates.shape[0] < 2:
        return 0.0
    distances = torch.cdist(candidates, candidates)
    upper = torch.triu_indices(candidates.shape[0], candidates.shape[0], offset=1)
    return float(distances[upper[0], upper[1]].mean())


@dataclass
class AcquisitionHyperparameterResult:
    """Evaluation of one acquisition type and optimizer budget."""
    acq_type: str
    num_restarts: int
    raw_samples: int
    maxiter: int
    batch_limit: int
    common_ehvi: float = float("nan")
    candidate_diversity: float = float("nan")
    proposal_time_s: float = 0.0
    proposal_method: Optional[str] = None
    status: str = "SUCCESS"
    error: Optional[str] = None


@dataclass
class AcquisitionTuningSummary:
    """Ranked acquisition settings."""
    best_acq_type: str
    best_execution_config: ExecutionConfig
    best_candidate: AcquisitionHyperparameterResult
    comparison_table: pd.DataFrame
    candidates: List[AcquisitionHyperparameterResult]


def _evaluate_acquisition(model, train_X, train_Y, ref_point, bounds, acq_type, restarts, raw_samples,
                          batch_size, maxiter, batch_limit, device) -> AcquisitionHyperparameterResult:
    from mobo_linac.acquisition.mobo import build_acquisition_function, generate_next_candidates
    result = AcquisitionHyperparameterResult(acq_type, restarts, raw_samples, maxiter, batch_limit)
    started = time.perf_counter()
    try:
        acquisition = build_acquisition_function(model=model, train_X=train_X, train_Y=train_Y,
                                                 ref_point=ref_point, acq_type=acq_type)
        proposal = generate_next_candidates(acq_func=acquisition, bounds=bounds, batch_size=batch_size,
                                            num_restarts=restarts, raw_samples=raw_samples, maxiter=maxiter,
                                            batch_limit=batch_limit, device=device, retry_on_failure=False)
        result.proposal_method = proposal.metadata.get("method")
        result.common_ehvi = common_batch_ehvi(model, proposal.candidates, train_Y, ref_point)
        result.candidate_diversity = compute_candidate_diversity(proposal.candidates)
    except Exception as error:  # recorded, never scored
        result.status, result.error = "FAILED", _error(error)
    result.proposal_time_s = time.perf_counter() - started
    return result


def _ranked(results):
    succeeded = sorted((r for r in results if r.status == "SUCCESS"), key=lambda r: (-r.common_ehvi, r.proposal_time_s))
    return succeeded + [r for r in results if r.status != "SUCCESS"]


def _acquisition_table(results) -> pd.DataFrame:
    return pd.DataFrame([{
        "Acquisition Type": r.acq_type, "Restarts": r.num_restarts, "Raw Samples": r.raw_samples,
        "Common EHVI": r.common_ehvi, "Diversity (diagnostic)": r.candidate_diversity,
        "Total Time (s)": round(r.proposal_time_s, 3), "Status": r.status, "Error": r.error or "",
    } for r in results])


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
    """Compare acquisition types at one optimizer budget by the common EHVI of their batches."""
    results = [_evaluate_acquisition(model, train_X, train_Y, ref_point, bounds, acq_type, num_restarts,
                                     raw_samples, batch_size, maxiter, 1, device)
               for acq_type in (acq_types or MULTIOBJECTIVE_ACQUISITIONS)]
    return _acquisition_table(_ranked(results))


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
    """Select acquisition type and optimizer budget by the common EHVI of the proposed batch."""
    results = [
        _evaluate_acquisition(model, train_X, train_Y, ref_point, bounds, acq_type, restarts, raw,
                              batch_size, maxiter, batch_limit, device)
        for acq_type in (candidate_acq_types or ["qLogNEHVI", "qLogEHVI", "qEHVI"])
        for restarts in (candidate_restarts or [5, 10, 20])
        for raw in (candidate_raw_samples or [64, 128, 256])
    ]
    ranked = _ranked(results)
    best = ranked[0]
    if best.status != "SUCCESS":
        raise RuntimeError("No acquisition setting produced a proposal: " + "; ".join(r.error for r in results))
    return AcquisitionTuningSummary(
        best_acq_type=best.acq_type,
        best_execution_config=ExecutionConfig(acqf_num_restarts=best.num_restarts, acqf_raw_samples=best.raw_samples,
                                              acqf_maxiter=best.maxiter, acqf_batch_limit=best.batch_limit),
        best_candidate=best, comparison_table=_acquisition_table(ranked), candidates=ranked)


@dataclass
class PipelineTuningSummary:
    """Unified summary for joint surrogate and acquisition settings selection."""
    best_gp_config: GpModelConfig
    best_acq_type: str
    best_execution_config: ExecutionConfig
    gp_comparison_table: pd.DataFrame
    acq_comparison_table: pd.DataFrame


def tune_full_optimization_pipeline(
    train_X: torch.Tensor,
    train_Y: torch.Tensor,
    bounds: torch.Tensor,
    ref_point: torch.Tensor,
    batch_size: int = 8,
    device: Optional[Union[torch.device, str]] = None,
    candidate_covars: Sequence[str] = ("matern52", "rbf"),
    candidate_noise_ratios: Sequence[float] = (1.0e-8, 1.0e-6, 1.0e-4),
    candidate_acq_types: Sequence[str] = ("qLogNEHVI", "qLogEHVI", "qEHVI"),
    candidate_restarts: Sequence[int] = (5, 10, 20),
    candidate_raw_samples: Sequence[int] = (64, 128, 256),
    maxiter: int = 50,
) -> PipelineTuningSummary:
    """
    Select GP settings by LOO predictive density, refit them, then select acquisition settings.

    ``ref_point`` is the campaign's recorded model-space reporting reference
    (``reporting_metadata.json``); no data-derived reference is substituted.
    """
    if ref_point is None:
        raise ValueError("Tuning requires the campaign's recorded reporting reference point.")
    gp_summary = tune_gp_hyperparameters(train_X=train_X, train_Y=train_Y, bounds=bounds,
                                         candidate_covars=list(candidate_covars),
                                         candidate_noise_ratios=list(candidate_noise_ratios),
                                         candidate_noise_modes=["deterministic_fixed"], device=device)
    model = fit_gp_models(build_gp_models(train_X=train_X, train_Y=train_Y, bounds=bounds,
                                          covar_type=gp_summary.best_config.covar_type,
                                          noise_mode=gp_summary.best_config.noise_mode,
                                          relative_noise_ratio=gp_summary.best_config.relative_noise_ratio,
                                          device=device))
    acq_summary = tune_acquisition_hyperparameters(
        model=model, train_X=train_X, train_Y=train_Y, ref_point=torch.as_tensor(ref_point, dtype=torch.double),
        bounds=bounds, candidate_acq_types=list(candidate_acq_types), candidate_restarts=list(candidate_restarts),
        candidate_raw_samples=list(candidate_raw_samples), batch_size=batch_size, maxiter=maxiter, device=device)
    return PipelineTuningSummary(
        best_gp_config=gp_summary.best_config,
        best_acq_type=acq_summary.best_acq_type,
        best_execution_config=acq_summary.best_execution_config,
        gp_comparison_table=gp_summary.comparison_table,
        acq_comparison_table=acq_summary.comparison_table,
    )
