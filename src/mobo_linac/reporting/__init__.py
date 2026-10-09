"""
Cross-campaign reporting: phase comparison with audited verification, and manuscript artifacts.
"""

from mobo_linac.reporting.comparison import run_phase_comparison, verify_pareto_candidates
from mobo_linac.reporting.paper import check_manuscript_consistency, generate_paper_artifacts

__all__ = ["run_phase_comparison", "verify_pareto_candidates", "generate_paper_artifacts",
           "check_manuscript_consistency"]
