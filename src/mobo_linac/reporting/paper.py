"""Manuscript figures and LaTeX tables from recorded campaign phases (no simulation is rerun).

Outputs: ``hypervolume_comparison.png``, ``pareto_front_comparison.png``,
``verification_rerun_comparison.png``, ``feasible_fraction.png`` and the ``verification_table.tex``,
``results_table.tex`` and (with a Phase 1 suite) ``phase1_cases_table.tex`` tables.
"""

from pathlib import Path
from typing import Optional

from mobo_linac.campaigns.scalarized_suite import export_phase1_cases_latex_table
from mobo_linac.io.run_data import read_comparable_runs, read_run_data
from mobo_linac.metrics.latex import generate_verification_latex_table
from mobo_linac.metrics.publication import generate_campaign_summary_latex_table
from mobo_linac.utils.logger import get_logger

logger = get_logger(__name__)


REQUIRED_RESULT_FILES = [
    "hypervolume.csv",
    "pareto.csv",
    "train_X.csv",
    "train_Y.csv",
    "config.yaml",
]

REQUIRED_FIGURE_NAMES = [
    "hypervolume_comparison.png",
    "pareto_front_comparison.png",
    "verification_rerun_comparison.png",
    "feasible_fraction.png",
]

REQUIRED_TABLE_NAMES = [
    "verification_table.tex",
    "results_table.tex",
]


def check_manuscript_consistency(
    phase2_dir: Path,
    phase3_dir: Path,
    figures_dir: Path,
    tables_dir: Path,
    verification_csv: Path,
    phase1_dir: Optional[Path] = None,
) -> bool:
    """
    Checks that all required result files, figures, and tables exist.
    Returns True if all checks pass, False otherwise.
    """
    errors = []

    check_runs = [(phase2_dir, "Phase 2"), (phase3_dir, "Phase 3")]
    if phase1_dir is not None and phase1_dir.is_dir():
        check_runs.append((phase1_dir, "Phase 1"))

    for name in REQUIRED_RESULT_FILES:
        for run_dir, label in check_runs:
            p = run_dir / name
            if not p.exists():
                errors.append(f"Missing {label} result file: {p}")

    if not verification_csv.exists():
        errors.append(f"Missing verification CSV: {verification_csv}")

    for name in REQUIRED_FIGURE_NAMES:
        p = figures_dir / name
        if not p.exists():
            errors.append(f"Missing figure: {p}")

    for name in REQUIRED_TABLE_NAMES:
        p = tables_dir / name
        if not p.exists():
            errors.append(f"Missing table: {p}")

    if errors:
        logger.error("[MANUSCRIPT CONSISTENCY CHECK] FAILED:\n" + "\n".join(f"  ✗ {e}" for e in errors))
        return False
    logger.info("[MANUSCRIPT CONSISTENCY CHECK] PASSED — all required files present.")
    return True


def generate_paper_artifacts(phase2_dir: Path, phase3_dir: Path, verification_csv: Path, figures_dir: Path,
                             tables_dir: Path, phase1_dir: Optional[Path] = None) -> dict:
    """Write every manuscript figure and table, then run the consistency check (returns HV statistics)."""
    from mobo_linac.plotting.publication import (
        plot_feasible_fraction, plot_hypervolume_comparison, plot_pareto_front_comparison,
        plot_verification_comparison,
    )
    phases = ([phase1_dir] if phase1_dir is not None else []) + [phase2_dir, phase3_dir]
    read_comparable_runs(phases)
    config = read_run_data(phase3_dir).config
    stats = plot_hypervolume_comparison(phase2_dir, phase3_dir, figures_dir / "hypervolume_comparison.png",
                                        phase1_dir=phase1_dir)
    plot_pareto_front_comparison(phase2_dir, phase3_dir, figures_dir / "pareto_front_comparison.png",
                                 phase1_dir=phase1_dir)
    plot_feasible_fraction(phase2_dir, phase3_dir, figures_dir / "feasible_fraction.png", phase1_dir=phase1_dir)
    if verification_csv.exists():
        plot_verification_comparison(verification_csv, figures_dir / "verification_rerun_comparison.png")
        generate_verification_latex_table(verification_csv, output_path=tables_dir / "verification_table.tex",
                                          config=config)
    else:
        logger.warning(f"Verification CSV not found; verification figure and table skipped: {verification_csv}")
    names = (["Phase 1 (Scalarized)"] if phase1_dir is not None else []) + ["Phase 2 (Unconstrained)",
                                                                            "Phase 3 (Constrained)"]
    generate_campaign_summary_latex_table(phases, tables_dir / "results_table.tex", names)
    if phase1_dir is not None and (phase1_dir / "cases_summary.csv").exists():
        export_phase1_cases_latex_table(phase1_dir / "cases_summary.csv", tables_dir / "phase1_cases_table.tex",
                                        config=config)
    check_manuscript_consistency(phase2_dir, phase3_dir, figures_dir, tables_dir, verification_csv,
                                 phase1_dir=phase1_dir)
    return stats or {}
