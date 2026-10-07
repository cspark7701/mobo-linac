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
from botorch.utils.multi_objective.hypervolume import Hypervolume
from botorch.utils.multi_objective.pareto import is_non_dominated

from mobo_linac.config import MoboConfig, load_config
from mobo_linac.evaluation import EvaluationResult

# Default Fixed Engineering Normalization Scales
DEFAULT_ENGINEERING_SCALES = {
    "norm_emit_x_m_rad": 1.0e-6,   # 1 um.rad
    "norm_emit_y_m_rad": 1.0e-6,   # 1 um.rad
    "sigma_energy_eV": 1.0e6,       # 1 MeV
}
DEFAULT_REPORTING_SCALES = [1.0e-6, 1.0e-6, 1.0e6]

# Default Fixed Reporting Reference Point in Normalized Model Space
# (Physical space: [10.0, 10.0, 10.0] normalized; Model space: [-10.0, -10.0, -10.0])
DEFAULT_REPORTING_REF_POINT_MODEL_NORM = [-10.0, -10.0, -10.0]


def normalize_objectives_physical(
    physical_objs: Union[Sequence[float], np.ndarray, torch.Tensor],
    scales: Optional[Sequence[float]] = None,
) -> torch.Tensor:
    """
    Normalizes physical objective values by fixed engineering scales.

    Args:
        physical_objs: Physical objective values (minimization).
        scales: Scale factors per objective. Defaults to [1e-6, 1e-6, 1e6].

    Returns:
        PyTorch double tensor of normalized physical objective values.
    """
    if scales is None:
        scales = [1.0e-6, 1.0e-6, 1.0e6]

    scale_tensor = torch.tensor(scales, dtype=torch.double)
    if not isinstance(physical_objs, torch.Tensor):
        obj_tensor = torch.tensor(physical_objs, dtype=torch.double)
    else:
        obj_tensor = physical_objs.to(dtype=torch.double)

    return obj_tensor / scale_tensor


def normalize_objectives_model(
    model_objs: Union[Sequence[float], np.ndarray, torch.Tensor],
    scales: Optional[Sequence[float]] = None,
) -> torch.Tensor:
    """
    Normalizes model-space objective values (-1 * physical) by fixed engineering scales.

    Args:
        model_objs: Model-space objective values (maximization).
        scales: Scale factors per objective. Defaults to [1e-6, 1e-6, 1e6].

    Returns:
        PyTorch double tensor of normalized model-space objective values.
    """
    if scales is None:
        scales = [1.0e-6, 1.0e-6, 1.0e6]

    scale_tensor = torch.tensor(scales, dtype=torch.double)
    if not isinstance(model_objs, torch.Tensor):
        obj_tensor = torch.tensor(model_objs, dtype=torch.double)
    else:
        obj_tensor = model_objs.to(dtype=torch.double)

    return obj_tensor / scale_tensor


def compute_normalized_hypervolume(
    train_Y_model: torch.Tensor,
    ref_point_model_norm: Union[Sequence[float], torch.Tensor] = DEFAULT_REPORTING_REF_POINT_MODEL_NORM,
    scales: Optional[Sequence[float]] = None,
) -> float:
    """
    Computes dimensionless hypervolume in normalized objective space w.r.t a fixed reporting reference point.

    Args:
        train_Y_model: (N, D) PyTorch double tensor of model-space objectives (unnormalized).
        ref_point_model_norm: Reference point in normalized model space.
        scales: Scale factors per objective.

    Returns:
        Non-negative float hypervolume value.
    """
    if train_Y_model is None or train_Y_model.shape[0] == 0:
        return 0.0

    train_Y_norm = normalize_objectives_model(train_Y_model, scales)
    ref_tensor = (
        ref_point_model_norm.to(dtype=torch.double)
        if isinstance(ref_point_model_norm, torch.Tensor)
        else torch.tensor(ref_point_model_norm, dtype=torch.double)
    )

    # Filter candidates dominating reference point (Y_norm > ref_norm)
    strictly_better = (train_Y_norm > ref_tensor).all(dim=-1)
    Y_valid = train_Y_norm[strictly_better]

    if Y_valid.shape[0] == 0:
        return 0.0

    pareto_mask = is_non_dominated(Y_valid)
    pareto_Y = Y_valid[pareto_mask]

    hv_calc = Hypervolume(ref_point=ref_tensor)
    return max(0.0, float(hv_calc.compute(pareto_Y)))


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
    scales: Optional[Sequence[float]] = None,
    reporting_ref_point_norm: Sequence[float] = DEFAULT_REPORTING_REF_POINT_MODEL_NORM,
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
    cumulative_evals = 0
    invalid_count = 0
    feasible_count = 0
    first_feasible_idx: Optional[int] = None
    cum_wallclock = 0.0
    cum_sim_runtime = 0.0

    valid_Y_model_list = []
    feasible_Y_model_list = []

    for idx, res in enumerate(results, start=1):
        cumulative_evals += 1
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
                valid_Y_model_list.append(res.objectives_model)

            if res.physically_feasible:
                feasible_count += 1
                if first_feasible_idx is None:
                    first_feasible_idx = cumulative_evals
                if res.objectives_model is not None:
                    feasible_Y_model_list.append(res.objectives_model)

        # Compute hypervolumes at this step
        if valid_Y_model_list:
            Y_valid_tensor = torch.tensor(valid_Y_model_list, dtype=torch.double)
            all_hv = compute_normalized_hypervolume(Y_valid_tensor, reporting_ref_point_norm, scales)
        else:
            all_hv = 0.0

        pareto_size = 0
        if feasible_Y_model_list:
            Y_feas_tensor = torch.tensor(feasible_Y_model_list, dtype=torch.double)
            feas_hv = compute_normalized_hypervolume(Y_feas_tensor, reporting_ref_point_norm, scales)
            # Count Pareto set size
            Y_feas_norm = normalize_objectives_model(Y_feas_tensor, scales)
            ref_tensor = torch.tensor(reporting_ref_point_norm, dtype=torch.double)
            strictly_better = (Y_feas_norm > ref_tensor).all(dim=-1)
            Y_sub = Y_feas_norm[strictly_better]
            if Y_sub.shape[0] > 0:
                pareto_size = int(is_non_dominated(Y_sub).sum().item())
        else:
            feas_hv = 0.0

        feas_frac = float(feasible_count) / float(cumulative_evals)

        row = {
            "cumulative_astra_evaluations": cumulative_evals,
            "fixed_ref_all_valid_hv": all_hv,
            "fixed_ref_feasible_hv": feas_hv,
            "feasible_fraction": feas_frac,
            "first_feasible_eval_index": first_feasible_idx if first_feasible_idx is not None else np.nan,
            "pareto_set_size": pareto_size,
            "invalid_run_count": invalid_count,
            "total_wallclock_s": cum_wallclock if elapsed_wall_times is not None and observed is not None else np.nan,
            "total_simulation_runtime_s": cum_sim_runtime,
        }
        rows.append(row)

    return pd.DataFrame(rows, columns=["cumulative_astra_evaluations", "fixed_ref_all_valid_hv", "fixed_ref_feasible_hv", "feasible_fraction", "first_feasible_eval_index", "pareto_set_size", "invalid_run_count", "total_wallclock_s", "total_simulation_runtime_s"])
