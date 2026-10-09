#!/usr/bin/env python3
"""
generate_paper_figures.py — Manuscript Figure & Table Generator (Task 10)
===========================================================================
Produces all paper figures and LaTeX tables from processed CSV/JSON result
files WITHOUT rerunning any ASTRA simulation.

Usage
-----
    python scripts/generate_paper_figures.py \\
        --phase2-dir results/phase2_unconstrained_<timestamp> \\
        --phase3-dir results/phase3_constrained_<timestamp> \\
        --verification-csv results/verification/verification_summary.csv \\
        --output-dir docs/paper/figures \\
        --tables-dir docs/paper

Output files
------------
    docs/paper/figures/hypervolume_comparison.png
    docs/paper/figures/pareto_front_comparison.png
    docs/paper/figures/verification_rerun_comparison.png
    docs/paper/figures/feasible_fraction.png
    docs/paper/verification_table.tex
    docs/paper/results_table.tex
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

from mobo_linac.plotting.publication import (
    plot_hypervolume_comparison, plot_pareto_front_comparison,
    plot_verification_comparison, plot_feasible_fraction,
)
from mobo_linac.metrics.latex import generate_verification_latex_table
from mobo_linac.metrics.publication import generate_campaign_summary_latex_table
from mobo_linac.io.run_data import read_comparable_runs


def export_verification_latex_table(verification_csv, output_path, config=None):
    return generate_verification_latex_table(verification_csv, output_path=output_path, config=config)


def export_results_summary_latex_table(phase2_dir, phase3_dir, output_path, phase1_dir=None):
    directories = ([phase1_dir] if phase1_dir is not None else []) + [phase2_dir, phase3_dir]
    names = (["Phase 1 (Scalarized)"] if phase1_dir is not None else []) + ["Phase 2 (Unconstrained)", "Phase 3 (Constrained)"]
    return generate_campaign_summary_latex_table(directories, output_path, names)


# ---------------------------------------------------------------------------
# Manuscript consistency check (pre-flight)
# ---------------------------------------------------------------------------

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
    phase1_dir: Path | None = None,
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
        print("\n[MANUSCRIPT CONSISTENCY CHECK] FAILED:")
        for e in errors:
            print(f"  ✗ {e}")
        return False

    print("\n[MANUSCRIPT CONSISTENCY CHECK] PASSED — all required files present.")
    return True


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate all manuscript figures and LaTeX tables from campaign results."
    )
    parser.add_argument(
        "--phase1-dir", type=Path, default=None,
        help="Path to Phase 1 (scalarized) BO campaign run directory."
    )
    parser.add_argument(
        "--phase2-dir", type=Path, required=True,
        help="Path to Phase 2 (unconstrained) MOBO campaign run directory."
    )
    parser.add_argument(
        "--phase3-dir", type=Path, required=True,
        help="Path to Phase 3 (constrained) MOBO campaign run directory."
    )
    parser.add_argument(
        "--verification-csv", type=Path,
        default=Path("results/verification/verification_summary.csv"),
        help="Path to verification_summary.csv (default: results/verification/verification_summary.csv)."
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("docs/paper/figures"),
        help="Output directory for PNG figures (default: docs/paper/figures)."
    )
    parser.add_argument(
        "--tables-dir", type=Path, default=Path("docs/paper"),
        help="Output directory for LaTeX table files (default: docs/paper)."
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Only run the manuscript consistency check, do not generate figures."
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    fig_dir: Path = args.output_dir
    tab_dir: Path = args.tables_dir
    ver_csv: Path = args.verification_csv
    p1: Path | None = args.phase1_dir
    p2: Path = args.phase2_dir
    p3: Path = args.phase3_dir

    if p1 is not None and not p1.is_dir():
        print(f"Warning: --phase1-dir specified but does not exist: {p1}", file=sys.stderr)
        return 1

    # Validate source directories exist
    for p, label in [(p2, "--phase2-dir"), (p3, "--phase3-dir")]:
        if not p.is_dir():
            print(f"Error: {label} directory does not exist: {p}", file=sys.stderr)
            return 1

    if args.check_only:
        ok = check_manuscript_consistency(p2, p3, fig_dir, tab_dir, ver_csv, phase1_dir=p1)
        return 0 if ok else 1

    read_comparable_runs(([p1] if p1 is not None else []) + [p2, p3])

    print("=== Generating Paper Figures and Tables ===\n")
    if p1 is not None:
        print(f"  Including Phase 1 data from: {p1}")

    # --- Figure 1: Hypervolume comparison ---
    print("[Figure 1] Hypervolume comparison...")
    stats = plot_hypervolume_comparison(
        p2, p3,
        fig_dir / "hypervolume_comparison.png",
        phase1_dir=p1,
    )

    # --- Figure 2: Pareto front comparison ---
    print("[Figure 2] Pareto front 2D projections...")
    plot_pareto_front_comparison(
        p2, p3,
        fig_dir / "pareto_front_comparison.png",
        phase1_dir=p1,
    )

    # --- Figure 3: Verification bar chart ---
    if ver_csv.exists():
        print("[Figure 3] Verification rerun comparison...")
        plot_verification_comparison(
            ver_csv,
            fig_dir / "verification_rerun_comparison.png",
        )
    else:
        print(f"[Figure 3] Skipped — verification CSV not found: {ver_csv}")

    # --- Figure 4: Feasible fraction ---
    print("[Figure 4] Feasible fraction progress...")
    plot_feasible_fraction(
        p2, p3,
        fig_dir / "feasible_fraction.png",
        phase1_dir=p1,
    )

    # --- Table 1: Verification LaTeX table ---
    if ver_csv.exists():
        print("[Table 1] Verification results LaTeX table...")
        from mobo_linac.io.run_data import read_run_data
        export_verification_latex_table(ver_csv, tab_dir / "verification_table.tex", config=read_run_data(p3).config)
    else:
        print(f"[Table 1] Skipped — verification CSV not found: {ver_csv}")

    # --- Table 2: Campaign summary LaTeX table ---
    print("[Table 2] Campaign summary LaTeX table...")
    export_results_summary_latex_table(p2, p3, tab_dir / "results_table.tex", phase1_dir=p1)

    # --- Table 3: Phase 1 Option 2 cases LaTeX table ---
    if p1 is not None:
        p1_cases_csv = p1 / "cases_summary.csv"
        if p1_cases_csv.exists():
            print("[Table 3] Phase 1 Option 2 cases LaTeX table...")
            from mobo_linac.campaigns.scalarized_suite import export_phase1_cases_latex_table
            from mobo_linac.io.run_data import read_run_data
            export_phase1_cases_latex_table(p1_cases_csv, tab_dir / "phase1_cases_table.tex", config=read_run_data(p3).config)
            print(f"  ✓ Saved {tab_dir / 'phase1_cases_table.tex'}")

    # --- Consistency check ---
    check_manuscript_consistency(p2, p3, fig_dir, tab_dir, ver_csv, phase1_dir=p1)

    print("\n=== Paper Figure & Table Generation Complete ===")
    if stats:
        if "phase1_final_hv" in stats:
            print(f"    Phase 1 final feasible HV: {stats['phase1_final_hv']:.6f}")
        print(f"    Phase 2 final feasible HV: {stats['phase2_final_hv']:.6f}")
        print(f"    Phase 3 final feasible HV: {stats['phase3_final_hv']:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
