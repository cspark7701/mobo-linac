"""Comparison of recorded campaign phases with an audited verification of the last phase."""

from pathlib import Path
from typing import List, Optional, Sequence

from mobo_linac.io.run_data import read_run_data
from mobo_linac.metrics.publication import generate_comparison_report, read_comparison_runs
from mobo_linac.plotting.publication import plot_pareto_front_comparison, plot_verification_comparison
from mobo_linac.utils.logger import get_logger
from mobo_linac.verification.verifier import run_verification_pipeline

logger = get_logger(__name__)

PHASE_NAMES = ("Phase 1 (Scalarized BO)", "Phase 2 (Unconstrained MOBO)", "Phase 3 (Constrained MOBO)")
REPORT_TITLE = "Multi-Phase Linac Bayesian Optimization Comparative Analysis & Verification Report"


def load_phase_results(phase_dir, config):
    return read_run_data(phase_dir, config=config).results


def verify_pareto_candidates(results, config, output_dir, evaluator=None, num_workers=None) -> List[dict]:
    """Audited reruns of the representative feasible-Pareto roles (``output_dir/verification``)."""
    records, _, _ = run_verification_pipeline(results, config=config, output_dir=Path(output_dir) / "verification",
                                              evaluator=evaluator, num_workers=num_workers)
    return [dict(record, status=record["verification_status"]) for record in records]


def run_phase_comparison(phase_dirs: Sequence[Path], output_dir, config, names: Optional[Sequence[str]] = None,
                         num_workers=None, evaluator=None) -> Path:
    """Compare recorded phases, verify the last one (falling back to the previous if it has no
    results) and write ``comparison_report.md`` with the figures it references."""
    phase_dirs = [Path(path) for path in phase_dirs]
    names = list(names or PHASE_NAMES[-len(phase_dirs):])
    runs = read_comparison_runs(phase_dirs)
    output_dir = Path(output_dir)
    figures = output_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    if len(phase_dirs) >= 2:
        plot_pareto_front_comparison(phase_dirs[-2], phase_dirs[-1], figures / "pareto_front_comparison.png",
                                     phase1_dir=phase_dirs[-3] if len(phase_dirs) >= 3 else None)
    target = next((run for run in reversed(runs) if run.results), runs[-1])
    records = verify_pareto_candidates(target.results, config, output_dir, evaluator=evaluator, num_workers=num_workers)
    plot_verification_comparison(output_dir / "verification" / "verification_summary.csv",
                                 figures / "verification_rerun_comparison.png")
    report = generate_comparison_report(runs, names, records, output_dir / "comparison_report.md", title=REPORT_TITLE)
    logger.info(f"Comparison report written to {report}")
    return report
