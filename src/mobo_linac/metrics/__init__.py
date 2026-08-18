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
from mobo_linac.metrics.latex import (
    generate_verification_latex_table,
    generate_results_summary_latex_table,
    generate_robustness_summary_latex_table,
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
    "generate_verification_latex_table",
    "generate_results_summary_latex_table",
    "generate_robustness_summary_latex_table",
]
