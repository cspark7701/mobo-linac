"""
Pareto Front Extraction, Filtering, and Representative Candidate Selection Module (Task 08).

Ensures all representative candidates for robustness analysis, independent verification,
and reporting are selected strictly from the non-dominated physically feasible Pareto set.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import torch
from botorch.utils.multi_objective.pareto import is_non_dominated

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.metrics.reporting import normalize_objectives_physical


def extract_pareto_sets(
    results: List[EvaluationResult],
) -> Dict[str, List[EvaluationResult]]:
    """
    Extracts all-valid Pareto set, feasible Pareto set, and dominated feasible set.

    Args:
        results: List of EvaluationResult objects.

    Returns:
        Dict containing:
        - 'all_valid_pareto': Non-dominated results among all valid simulations.
        - 'feasible_pareto': Non-dominated results among physically feasible simulations only.
        - 'feasible_dominated': Physically feasible simulations dominated by at least one other feasible result.
    """
    valid_results = []
    for res in results:
        if res.simulation_valid and res.objectives_physical is not None and res.x_physical and len(res.x_physical) == 6:
            if res.objectives_model is None:
                res.objectives_model = [-x for x in res.objectives_physical]
            valid_results.append(res)

    if not valid_results:
        return {
            "all_valid_pareto": [],
            "feasible_pareto": [],
            "feasible_dominated": [],
        }

    # Model objectives are negated physical objectives (-physical)
    # is_non_dominated expects maximization space
    model_objs_all = torch.tensor([r.objectives_model for r in valid_results], dtype=torch.double)
    all_pareto_mask = is_non_dominated(model_objs_all)
    all_valid_pareto = [res for res, mask in zip(valid_results, all_pareto_mask) if mask.item()]


    feasible_results = [res for res in valid_results if res.physically_feasible]

    if feasible_results:
        model_objs_feas = torch.tensor([r.objectives_model for r in feasible_results], dtype=torch.double)
        feas_pareto_mask = is_non_dominated(model_objs_feas)
        feasible_pareto = [res for res, mask in zip(feasible_results, feas_pareto_mask) if mask.item()]
        feasible_dominated = [res for res, mask in zip(feasible_results, feas_pareto_mask) if not mask.item()]
    else:
        feasible_pareto = all_valid_pareto
        feasible_dominated = []

    return {
        "all_valid_pareto": all_valid_pareto,
        "feasible_pareto": feasible_pareto,
        "feasible_dominated": feasible_dominated,
    }


def compute_crowding_distances(
    objs: Union[np.ndarray, Sequence[Sequence[float]]],
) -> np.ndarray:
    """
    Computes NSGA-II crowding distances for a matrix of objective vectors.

    Handles raw or normalized objective matrices, N <= 2 edge cases,
    identical objective points, and zero-range dimensions gracefully.

    Args:
        objs: (N, M) array-like of objective values (raw or normalized).

    Returns:
        1D array of crowding distance values (float64), length N.
    """
    objs_arr = np.asarray(objs, dtype=np.float64)
    if objs_arr.ndim == 1:
        objs_arr = objs_arr[:, np.newaxis]

    if objs_arr.size == 0:
        return np.zeros(0, dtype=np.float64)

    n, m = objs_arr.shape
    if n <= 2:
        return np.full(n, np.inf, dtype=np.float64)

    if m == 0:
        return np.zeros(n, dtype=np.float64)

    distances = np.zeros(n, dtype=np.float64)
    for col in range(m):
        sorted_indices = np.argsort(objs_arr[:, col])
        distances[sorted_indices[0]] = np.inf
        distances[sorted_indices[-1]] = np.inf

        obj_range = objs_arr[sorted_indices[-1], col] - objs_arr[sorted_indices[0], col]
        if abs(obj_range) <= 1e-12:
            continue

        for i in range(1, n - 1):
            idx = sorted_indices[i]
            if not np.isinf(distances[idx]):
                prev_idx = sorted_indices[i - 1]
                next_idx = sorted_indices[i + 1]
                distances[idx] += (objs_arr[next_idx, col] - objs_arr[prev_idx, col]) / obj_range

    return distances


def select_representative_pareto_candidates(
    results: List[EvaluationResult],
    scales: Optional[Sequence[float]] = None,
) -> Dict[str, EvaluationResult]:
    """
    Selects representative Pareto candidates strictly from the feasible Pareto set:
    - min_emit_x: Objective extreme for horizontal emittance
    - min_emit_y: Objective extreme for vertical emittance
    - min_sigma_energy: Objective extreme for energy spread
    - knee_point: Solution closest to origin in normalized objective space
    - balanced: Solution closest to centroid of feasible Pareto set
    - crowding_distance_max: Solution with maximum finite crowding distance

    Args:
        results: List of EvaluationResult objects.
        scales: Normalization scale factors. Defaults to [1e-6, 1e-6, 1e6].

    Returns:
        Dict mapping candidate label -> EvaluationResult.
    """
    pareto_sets = extract_pareto_sets(results)
    feasible_pareto = pareto_sets["feasible_pareto"]

    if not feasible_pareto:
        raise ValueError("No valid candidates available in feasible Pareto set.")

    # 1. Objective extremes
    min_ex = min(feasible_pareto, key=lambda r: r.objectives_physical[0])
    min_ey = min(feasible_pareto, key=lambda r: r.objectives_physical[1])
    min_se = min(feasible_pareto, key=lambda r: r.objectives_physical[2])

    # 2. Normalized physical objectives
    if scales is None:
        scales = [1.0e-6, 1.0e-6, 1.0e6]
    scale_arr = np.array(scales, dtype=np.float64)
    norm_objs = np.array([np.array(r.objectives_physical) / scale_arr for r in feasible_pareto])

    # 3. Knee point (closest to ideal minimum [0, 0, 0] in normalized space)
    dist_origin = np.linalg.norm(norm_objs, axis=1)
    knee_idx = int(np.argmin(dist_origin))
    knee_res = feasible_pareto[knee_idx]

    # 4. Balanced solution (closest to centroid of feasible Pareto set)
    centroid = np.mean(norm_objs, axis=0)
    dist_centroid = np.linalg.norm(norm_objs - centroid, axis=1)
    balanced_idx = int(np.argmin(dist_centroid))
    balanced_res = feasible_pareto[balanced_idx]

    # 5. Crowding distance max
    crowd_dists = compute_crowding_distances(norm_objs)
    finite_mask = ~np.isinf(crowd_dists)
    if finite_mask.any():
        max_cd_idx = int(np.argmax(np.where(finite_mask, crowd_dists, -1.0)))
    else:
        max_cd_idx = knee_idx
    crowd_res = feasible_pareto[max_cd_idx]

    candidates = {
        "min_emit_x": min_ex,
        "min_emit_y": min_ey,
        "min_sigma_energy": min_se,
        "knee_point": knee_res,
        "balanced": balanced_res,
        "crowding_distance_max": crowd_res,
    }

    return candidates


def detect_and_report_candidate_duplicates(
    candidates: Dict[str, EvaluationResult]
) -> Dict[str, Any]:
    """
    Audits selected representative candidates to identify duplicate selections across roles.

    Args:
        candidates: Dict mapping role label -> EvaluationResult.

    Returns:
        Dict with 'unique_candidates', 'duplicates_map', and 'summary_message'.
    """
    id_to_roles: Dict[str, List[str]] = {}
    for role, res in candidates.items():
        eval_id = getattr(res, "evaluation_id", str(id(res)))
        id_to_roles.setdefault(eval_id, []).append(role)

    duplicates_map = {eval_id: roles for eval_id, roles in id_to_roles.items() if len(roles) > 1}

    unique_candidates = {}
    for eval_id, roles in id_to_roles.items():
        # Find candidate instance
        first_role = roles[0]
        unique_candidates[first_role] = candidates[first_role]

    dup_details = []
    for eval_id, roles in duplicates_map.items():
        dup_details.append(f"Evaluation '{eval_id}' satisfies multiple roles: {roles}")

    summary_msg = "; ".join(dup_details) if dup_details else "All representative candidate roles map to unique solutions."

    return {
        "unique_candidates": unique_candidates,
        "duplicates_map": duplicates_map,
        "summary_message": summary_msg,
    }
