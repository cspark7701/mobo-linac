"""
Standardized Reporting Metrics and Fixed Reference Point Module for mobo_linac (Task 05).

Provides objective normalization using fixed engineering scales, fixed reporting
reference points in normalized dimensionless space, cross-run compatibility verification,
and full campaign metrics computation.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
import torch
from mobo_linac.metrics.front import dominating_front, hypervolume, normalize

from mobo_linac.config import MoboConfig, load_config
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


def reporting_metadata(config, reference_model, reference_policy="initial_design"):
    """Record the scientific convention without selecting a new reference or scale."""
    from dataclasses import asdict
    from mobo_linac.result_schema import ResultSchema
    schema = ResultSchema.from_config(config)
    reference = np.asarray(reference_model, dtype=float)
    if reference.shape != (len(schema.signs),) or not np.isfinite(reference).all():
        raise ValueError("Reporting reference must match finite configured objectives.")
    return {
        "schema_version": 1,
        "objective_names": list(schema.physical_columns),
        "objective_units": [obj.unit for obj in config.objectives],
        "objective_signs": list(schema.signs),
        "objective_scales": list(schema.scales),
        "reporting_ref_point": reference.tolist(),
        "reporting_ref_point_normalized": (reference / np.asarray(schema.scales)).tolist(),
        "reference_space": "model",
        "reference_policy": reference_policy,
        "constraint_profile": asdict(config.constraints),
        "design_columns": list(schema.design_columns),
        "hypervolume_columns": {"hypervolume.csv": "physical_model", "metrics_history.csv": "normalized_model"},
        "pareto_alias": "pareto_all.csv",
    }


def validate_campaign_compatibility(meta_a, meta_b, atol=0.0, raise_on_incompatible=True):
    """Require complete matching scientific metadata before comparing measurements.

    Reference origin may differ when the actual recorded convention is identical.
    Default comparison is exact, including scales much smaller than 1e-6.
    """
    required = ("schema_version", "objective_names", "objective_units", "objective_signs",
                "objective_scales", "reporting_ref_point", "reporting_ref_point_normalized",
                "reference_space", "constraint_profile", "design_columns", "hypervolume_columns")
    def reject(message):
        if raise_on_incompatible:
            raise ValueError(message)
        return False
    for meta in (meta_a, meta_b):
        if not isinstance(meta, dict) or any(key not in meta for key in required):
            return reject("Incomplete reporting metadata; an explicit convention is required.")
        count = len(meta["objective_names"])
        if meta["schema_version"] != 1 or count == 0:
            return reject("Unsupported reporting schema.")
        for key in ("objective_scales", "reporting_ref_point", "reporting_ref_point_normalized", "objective_signs", "objective_units"):
            if len(meta[key]) != count:
                return reject("Reporting metadata objective dimensions disagree.")
        scales = np.asarray(meta["objective_scales"], dtype=float)
        ref = np.asarray(meta["reporting_ref_point"], dtype=float)
        norm = np.asarray(meta["reporting_ref_point_normalized"], dtype=float)
        if (not np.isfinite(scales).all() or (scales <= 0).any() or not np.isfinite(ref).all()
                or not np.array_equal(norm, ref / scales)):
            return reject("Invalid reporting reference or objective scales.")
    for key in required:
        if meta_a[key] != meta_b[key]:
            return reject(f"Incompatible reporting metadata: {key} differs.")
    return True


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
