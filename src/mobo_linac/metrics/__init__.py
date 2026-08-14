"""
Metrics and Hypervolume Module for mobo_linac.
"""

from mobo_linac.metrics.hypervolume import (
    HypervolumeTracker,
    compute_hypervolume,
    compute_reference_point,
    validate_reference_point_compatibility,
)
from mobo_linac.metrics.pareto import (
    compute_crowding_distances,
    detect_and_report_candidate_duplicates,
    extract_pareto_sets,
    select_representative_pareto_candidates,
)

__all__ = [
    "compute_hypervolume",
    "compute_reference_point",
    "validate_reference_point_compatibility",
    "HypervolumeTracker",
    "compute_crowding_distances",
    "extract_pareto_sets",
    "select_representative_pareto_candidates",
    "detect_and_report_candidate_duplicates",
]
