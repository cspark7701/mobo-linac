"""
Standardized Reporting Metrics and Fixed Reference Point Module for mobo_linac (Task 05).

Provides objective normalization using fixed engineering scales, fixed reporting
reference points in normalized dimensionless space, cross-run compatibility verification,
and full campaign metrics computation.
"""

from typing import List, Optional, Sequence, Union
import numpy as np
import pandas as pd
import torch
from mobo_linac.metrics.front import dominating_front, hypervolume, normalize

from mobo_linac.conventions import reporting_metadata, validate_campaign_compatibility  # noqa: F401
from mobo_linac.evaluation import EvaluationResult


def normalize_objectives_physical(
    physical_objs: Union[Sequence[float], np.ndarray, torch.Tensor],
    scales: Sequence[float],
) -> torch.Tensor:
    """Normalize objective values by configured reporting scales (``ResultSchema.scales``)."""
    return normalize(physical_objs, scales)


# Normalization is sign independent; model-space values use the same operation.
normalize_objectives_model = normalize_objectives_physical


def compute_normalized_hypervolume(
    train_Y_model: torch.Tensor,
    ref_point_model_norm: Union[Sequence[float], torch.Tensor],
    scales: Sequence[float],
) -> float:
    """Dimensionless hypervolume of scaled model-space objectives w.r.t. a normalized reference."""
    if train_Y_model is None or train_Y_model.shape[0] == 0:
        return 0.0
    return hypervolume(normalize(train_Y_model, scales), ref_point_model_norm)


def compute_campaign_metrics_history(
    results: List[EvaluationResult],
    scales: Sequence[float],
    reporting_ref_point_norm: Sequence[float],
    elapsed_wall_times: Optional[Sequence[Optional[float]]] = None,
) -> pd.DataFrame:
    """
    Computes complete iteration/evaluation metrics history for a campaign:
    - cumulative_astra_evaluations
    - fixed_ref_all_valid_hv
    - fixed_ref_feasible_hv
    - feasible_fraction
    - first_feasible_eval_index
    - pareto_set_size
    - invalid_run_count
    - total_wallclock_s (measured elapsed observations, unknown when absent)
    - total_simulation_runtime_s

    Args:
        results: List of EvaluationResult records.
        scales: Normalization scales.
        reporting_ref_point_norm: Fixed reporting reference point in normalized model space.
        elapsed_wall_times: Measured cumulative active-session time per logical record.
            Missing observations stay unknown; worker runtimes never supply wall time.

    Returns:
        Pandas DataFrame containing metrics history across cumulative evaluations.
    """
    if elapsed_wall_times is not None and len(elapsed_wall_times) != len(results):
        raise ValueError("Wall-time observations must align with evaluation history.")
    rows = []
    invalid_count = 0
    feasible_count = 0
    first_feasible_idx: Optional[int] = None
    cum_wallclock = 0.0
    cum_sim_runtime = 0.0
    reference = None
    # Incremental fronts: hypervolume is recomputed only when a new point enters a front.
    fronts = {"valid": None, "feasible": None}
    values = {"valid": 0.0, "feasible": 0.0}

    def update(kind, point):
        nonlocal reference
        point = normalize(torch.as_tensor([point], dtype=torch.double), scales)
        if reference is None:
            reference = torch.as_tensor(reporting_ref_point_norm, dtype=torch.double)
        if not bool((point > reference).all()):
            return
        front = fronts[kind]
        if front is not None and bool(((front >= point).all(dim=-1)).any()):
            return  # dominated (or equal): front and hypervolume unchanged
        candidates = point if front is None else torch.cat([front, point])
        fronts[kind] = dominating_front(candidates, reference)
        values[kind] = hypervolume(fronts[kind], reference)

    for idx, res in enumerate(results, start=1):
        observed = elapsed_wall_times[idx - 1] if elapsed_wall_times is not None else None
        if observed is not None:
            if not np.isfinite(observed) or observed < 0:
                raise ValueError("Elapsed wall time must be finite and nonnegative.")
            cum_wallclock = max(cum_wallclock, float(observed))
        cum_sim_runtime += float(res.runtime_s)

        if not res.simulation_valid:
            invalid_count += 1
        else:
            if res.objectives_model is not None:
                update("valid", res.objectives_model)
            if res.physically_feasible:
                feasible_count += 1
                if first_feasible_idx is None:
                    first_feasible_idx = idx
                if res.objectives_model is not None:
                    update("feasible", res.objectives_model)

        rows.append({
            "cumulative_astra_evaluations": idx,
            "fixed_ref_all_valid_hv": values["valid"],
            "fixed_ref_feasible_hv": values["feasible"],
            "feasible_fraction": float(feasible_count) / float(idx),
            "first_feasible_eval_index": first_feasible_idx if first_feasible_idx is not None else np.nan,
            "pareto_set_size": 0 if fronts["feasible"] is None else int(fronts["feasible"].shape[0]),
            "invalid_run_count": invalid_count,
            "total_wallclock_s": cum_wallclock if elapsed_wall_times is not None and observed is not None else np.nan,
            "total_simulation_runtime_s": cum_sim_runtime,
        })

    return pd.DataFrame(rows, columns=["cumulative_astra_evaluations", "fixed_ref_all_valid_hv", "fixed_ref_feasible_hv", "feasible_fraction", "first_feasible_eval_index", "pareto_set_size", "invalid_run_count", "total_wallclock_s", "total_simulation_runtime_s"])
