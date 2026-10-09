"""
Pareto front extraction and representative candidate selection.

Representative candidates for robustness analysis, independent verification and
reporting are selected strictly from the measured feasible Pareto set by
:mod:`mobo_linac.metrics.selection`.
"""

from typing import Any, Dict, List

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.metrics.selection import (
    compute_crowding_distances,
    pareto_subset,
    select_representatives,
    valid_measured,
)
from mobo_linac.result_schema import ResultSchema

__all__ = [
    "compute_crowding_distances",
    "detect_and_report_candidate_duplicates",
    "extract_pareto_sets",
    "select_representative_pareto_candidates",
]


def extract_pareto_sets(results: List[EvaluationResult], config) -> Dict[str, List[EvaluationResult]]:
    """
    Extract the all-valid Pareto set, the feasible Pareto set and dominated feasible points.

    Inputs are not modified. When no feasible point exists, the feasible sets are empty.
    """
    schema = ResultSchema.from_config(config)
    all_valid_pareto = pareto_subset(results, schema, feasible=False)
    feasible_pareto = pareto_subset(results, schema, feasible=True)
    feasible, _ = valid_measured(results, schema, feasible=True)
    front = {id(result) for result in feasible_pareto}
    return {
        "all_valid_pareto": all_valid_pareto,
        "feasible_pareto": feasible_pareto,
        "feasible_dominated": [result for result in feasible if id(result) not in front],
    }


def select_representative_pareto_candidates(results: List[EvaluationResult], config) -> Dict[str, EvaluationResult]:
    """Role -> candidate mapping from the shared feasible-Pareto selection service."""
    return dict(select_representatives(results, config).roles)


def detect_and_report_candidate_duplicates(candidates: Dict[str, EvaluationResult]) -> Dict[str, Any]:
    """
    Audit selected representative candidates for evaluations that fill several roles.

    Evaluations are identified by ``(run_id, evaluation_id)``.
    """
    id_to_roles: Dict[tuple, List[str]] = {}
    for role, result in candidates.items():
        id_to_roles.setdefault((result.run_id, result.evaluation_id), []).append(role)

    duplicates_map = {identity: roles for identity, roles in id_to_roles.items() if len(roles) > 1}
    unique_candidates = {roles[0]: candidates[roles[0]] for roles in id_to_roles.values()}
    details = [f"Evaluation '{evaluation_id}' (run '{run_id}') satisfies multiple roles: {roles}"
               for (run_id, evaluation_id), roles in duplicates_map.items()]
    return {
        "unique_candidates": unique_candidates,
        "duplicates_map": duplicates_map,
        "summary_message": "; ".join(details) if details else "All representative candidate roles map to unique solutions.",
    }
