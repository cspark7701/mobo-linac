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
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

FIXED_REF_PHYSICAL = [6.651628e-05, 1.0746763e-04, 3_369_572.0]   # m·rad, m·rad, eV
EMIT_SCALE = 1e6      # m·rad → μm·mrad
ENERGY_SCALE = 1e-6   # eV    → MeV


def _save(fig: plt.Figure, path: Path, dpi: int = 300) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    print(f"  ✓ Saved {path}")
    plt.close(fig)


def _load_hypervolume_csv(run_dir: Path) -> pd.DataFrame:
    csv_path = run_dir / "hypervolume.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"hypervolume.csv not found in {run_dir}")
    df = pd.read_csv(csv_path)
    return df


def _load_pareto_csv(run_dir: Path) -> pd.DataFrame:
    csv_path = run_dir / "pareto.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"pareto.csv not found in {run_dir}")
    df = pd.read_csv(csv_path, comment="#")
    expected_cols = ["solenoid_field_T", "quad_1_gradient_T_m", "quad_2_gradient_T_m",
                     "gun_phase_deg", "acc1_acc2_phase_deg", "acc3_acc4_phase_deg",
                     "norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
    if list(df.columns) != expected_cols:
        if len(df.columns) == 9 and isinstance(df.columns[0], str) and not df.columns[0].replace('.', '', 1).replace('-', '', 1).isdigit():
            df.columns = expected_cols
        else:
            df = pd.read_csv(csv_path, comment="#", names=expected_cols)
    df = df.dropna(how="all")
    return df


def _load_train_csv(run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (train_X, train_Y) DataFrames."""
    tx = pd.read_csv(run_dir / "train_X.csv")
    ty = pd.read_csv(run_dir / "train_Y.csv")
    return tx, ty


# ---------------------------------------------------------------------------
# Figure 1: Hypervolume progress comparison
# ---------------------------------------------------------------------------

def plot_hypervolume_comparison(
    phase2_dir: Path,
    phase3_dir: Path,
    output_path: Path,
    phase1_dir: Path | None = None,
) -> dict:
    """
    Plots feasible hypervolume vs. cumulative ASTRA evaluations for Phase 1
    (Scalarized), Phase 2 (Unconstrained), and Phase 3 (Constrained) MOBO campaigns.

    Data source: hypervolume.csv from each campaign run directory.
    """
    df2 = _load_hypervolume_csv(phase2_dir)
    df3 = _load_hypervolume_csv(phase3_dir)
    df1 = _load_hypervolume_csv(phase1_dir) if phase1_dir and (phase1_dir / "hypervolume.csv").exists() else None

    # Use num_valid_points as cumulative evaluations (iteration 0 = Sobol init)
    x_col = "num_valid_points" if "num_valid_points" in df2.columns else "iteration"
    hv_col = "feasible_hypervolume"

    fig, ax = plt.subplots(figsize=(8, 5))

    if df1 is not None:
        x_col1 = "num_valid_points" if "num_valid_points" in df1.columns else "iteration"
        ax.plot(df1[x_col1], df1[hv_col], "^:", color="#7570b3", linewidth=2.0,
                markersize=5, label="Phase 1 — Scalarized BO")
        final_hv1 = float(df1[hv_col].iloc[-1])
        ax.annotate(f"{final_hv1:.4f}", xy=(df1[x_col1].iloc[-1], final_hv1),
                    xytext=(3, -12), textcoords="offset points", fontsize=9, color="#7570b3")

    ax.plot(df2[x_col], df2[hv_col], "o-", color="#1f6fb5", linewidth=2.2,
            markersize=6, label="Phase 2 — Unconstrained MOBO")
    ax.plot(df3[x_col], df3[hv_col], "s--", color="#d95f02", linewidth=2.2,
            markersize=6, label="Phase 3 — Constrained MOBO")

    # Annotate final HV values derived from data (not hard-coded)
    final_hv2 = float(df2[hv_col].iloc[-1])
    final_hv3 = float(df3[hv_col].iloc[-1])
    ax.annotate(f"{final_hv2:.4f}", xy=(df2[x_col].iloc[-1], final_hv2),
                xytext=(3, 6), textcoords="offset points", fontsize=9, color="#1f6fb5")
    ax.annotate(f"{final_hv3:.4f}", xy=(df3[x_col].iloc[-1], final_hv3),
                xytext=(3, -14), textcoords="offset points", fontsize=9, color="#d95f02")

    ax.set_xlabel("Cumulative ASTRA Evaluations", fontsize=13)
    ax.set_ylabel("Feasible Hypervolume (Fixed Reference)", fontsize=13)
    title_text = (
        "Feasible Hypervolume Progress: Phases 1, 2, and 3"
        if df1 is not None
        else "Feasible Hypervolume Progress: Unconstrained vs. Constrained MOBO"
    )
    ax.set_title(title_text, fontsize=13, pad=10)
    ax.legend(fontsize=11, loc="lower right")
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    _save(fig, output_path)

    # Return summary stats for potential use in tables
    stats = {
        "phase2_final_hv": final_hv2,
        "phase3_final_hv": final_hv3,
        "phase2_n_evals": int(df2[x_col].iloc[-1]),
        "phase3_n_evals": int(df3[x_col].iloc[-1]),
        "phase2_n_feasible_final": int(df2["num_feasible_points"].iloc[-1]) if "num_feasible_points" in df2.columns else None,
        "phase3_n_feasible_final": int(df3["num_feasible_points"].iloc[-1]) if "num_feasible_points" in df3.columns else None,
    }
    if df1 is not None:
        stats["phase1_final_hv"] = final_hv1
        stats["phase1_n_evals"] = int(df1[x_col1].iloc[-1])
        stats["phase1_n_feasible_final"] = int(df1["num_feasible_points"].iloc[-1]) if "num_feasible_points" in df1.columns else None
    return stats


# ---------------------------------------------------------------------------
# Figure 2: Pareto front 2D projections comparison
# ---------------------------------------------------------------------------

def plot_pareto_front_comparison(
    phase2_dir: Path,
    phase3_dir: Path,
    output_path: Path,
    phase1_dir: Path | None = None,
) -> None:
    """
    2D projections of the physical objective space comparing Phase 1, Phase 2,
    and Phase 3 Pareto fronts.

    Data source: pareto.csv from each campaign run directory.
    """
    df2 = _load_pareto_csv(phase2_dir)
    df3 = _load_pareto_csv(phase3_dir)
    df1 = _load_pareto_csv(phase1_dir) if phase1_dir and (phase1_dir / "pareto.csv").exists() else None

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    pairs = [
        ("norm_emit_x_m_rad", "norm_emit_y_m_rad",
         r"$\varepsilon_{n,x}$ [$\mu$m·mrad]", r"$\varepsilon_{n,y}$ [$\mu$m·mrad]",
         EMIT_SCALE, EMIT_SCALE),
        ("norm_emit_x_m_rad", "sigma_energy_eV",
         r"$\varepsilon_{n,x}$ [$\mu$m·mrad]", r"$\sigma_E$ [MeV]",
         EMIT_SCALE, ENERGY_SCALE),
        ("norm_emit_y_m_rad", "sigma_energy_eV",
         r"$\varepsilon_{n,y}$ [$\mu$m·mrad]", r"$\sigma_E$ [MeV]",
         EMIT_SCALE, ENERGY_SCALE),
    ]

    for ax, (cx, cy, lx, ly, sx, sy) in zip(axes, pairs):
        if df1 is not None and cx in df1.columns and cy in df1.columns:
            ax.scatter(df1[cx] * sx, df1[cy] * sy,
                       c="#7570b3", marker="^", s=50, label="Phase 1", alpha=0.75, zorder=2)
        ax.scatter(df2[cx] * sx, df2[cy] * sy,
                       c="#1f6fb5", marker="o", s=60, label="Phase 2", alpha=0.85, zorder=3)
        ax.scatter(df3[cx] * sx, df3[cy] * sy,
                       c="#d95f02", marker="s", s=60, label="Phase 3", alpha=0.85, zorder=3)
        ax.set_xlabel(lx, fontsize=11)
        ax.set_ylabel(ly, fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(fontsize=9)

    title_text = (
        "Pareto Front Comparison — Phases 1, 2, and 3"
        if df1 is not None
        else "Pareto Front Comparison — Phase 2 vs Phase 3"
    )
    axes[1].set_title(title_text, fontsize=12)
    fig.tight_layout()
    _save(fig, output_path)


# ---------------------------------------------------------------------------
# Figure 3: Independent verification rerun bar chart
# ---------------------------------------------------------------------------

def plot_verification_comparison(
    verification_csv: Path,
    output_path: Path,
) -> pd.DataFrame:
    """
    Grouped bar chart: stored vs independent rerun emittance values for each
    representative Pareto candidate.

    Data source: verification_summary.csv (never hard-coded).
    """
    df = pd.read_csv(verification_csv)

    roles = df["role"].tolist()
    x = np.arange(len(roles))
    width = 0.35

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

    # Panel 1: horizontal emittance
    axes[0].bar(x - width / 2, df["stored_emit_x_m_rad"] * EMIT_SCALE, width,
                label="Stored", color="#1f6fb5", alpha=0.85)
    axes[0].bar(x + width / 2, df["rerun_emit_x_m_rad"] * EMIT_SCALE, width,
                label="Rerun", color="#2ca02c", alpha=0.85)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(roles, rotation=15, ha="right", fontsize=9)
    axes[0].set_ylabel(r"$\varepsilon_{n,x}$ [$\mu$m·mrad]", fontsize=11)
    axes[0].set_title(r"Horizontal Emittance $\varepsilon_{n,x}$", fontsize=11)
    axes[0].legend(fontsize=10)
    axes[0].grid(True, axis="y", linestyle="--", alpha=0.5)

    # Panel 2: energy spread
    axes[1].bar(x - width / 2, df["stored_sigma_energy_eV"] * ENERGY_SCALE, width,
                label="Stored", color="#1f6fb5", alpha=0.85)
    axes[1].bar(x + width / 2, df["rerun_sigma_energy_eV"] * ENERGY_SCALE, width,
                label="Rerun", color="#2ca02c", alpha=0.85)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(roles, rotation=15, ha="right", fontsize=9)
    axes[1].set_ylabel(r"$\sigma_E$ [MeV]", fontsize=11)
    axes[1].set_title(r"RMS Energy Spread $\sigma_E$", fontsize=11)
    axes[1].legend(fontsize=10)
    axes[1].grid(True, axis="y", linestyle="--", alpha=0.5)

    fig.suptitle(
        "Independent Pareto Candidate Rerun Verification\n"
        "(Stored vs. Fresh Isolated-Directory Rerun)",
        fontsize=12, y=1.01
    )
    fig.tight_layout()
    _save(fig, output_path)
    return df


# ---------------------------------------------------------------------------
# Figure 4: Feasible fraction progress
# ---------------------------------------------------------------------------

def plot_feasible_fraction(
    phase2_dir: Path,
    phase3_dir: Path,
    output_path: Path,
    phase1_dir: Path | None = None,
) -> None:
    """
    Feasible beam fraction (num_feasible_points / num_valid_points) vs.
    cumulative ASTRA evaluations for Phase 1, Phase 2, and Phase 3.
    """
    df2 = _load_hypervolume_csv(phase2_dir)
    df3 = _load_hypervolume_csv(phase3_dir)
    df1 = _load_hypervolume_csv(phase1_dir) if phase1_dir and (phase1_dir / "hypervolume.csv").exists() else None

    x_col = "num_valid_points" if "num_valid_points" in df2.columns else "iteration"

    def frac(df: pd.DataFrame) -> pd.Series:
        if "num_feasible_points" in df.columns and "num_valid_points" in df.columns:
            valid = df["num_valid_points"].replace(0, np.nan)
            return df["num_feasible_points"] / valid
        return pd.Series([np.nan] * len(df))

    fig, ax = plt.subplots(figsize=(7, 4.5))
    if df1 is not None:
        x_col1 = "num_valid_points" if "num_valid_points" in df1.columns else "iteration"
        ax.plot(df1[x_col1], frac(df1) * 100, "^:", color="#7570b3", linewidth=2,
                markersize=5, label="Phase 1 — Scalarized BO")
    ax.plot(df2[x_col], frac(df2) * 100, "o-", color="#1f6fb5", linewidth=2,
            markersize=6, label="Phase 2 — Unconstrained MOBO")
    ax.plot(df3[x_col], frac(df3) * 100, "s--", color="#d95f02", linewidth=2,
            markersize=6, label="Phase 3 — Constrained MOBO")
    ax.set_xlabel("Cumulative ASTRA Evaluations", fontsize=12)
    ax.set_ylabel("Feasible Beam Fraction [%]", fontsize=12)
    title_text = (
        "Feasible Beam Fraction vs. Evaluations (Phases 1–3)"
        if df1 is not None
        else "Feasible Beam Fraction vs. Evaluations"
    )
    ax.set_title(title_text, fontsize=12)
    ax.set_ylim(-5, 105)
    ax.legend(fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    _save(fig, output_path)


# ---------------------------------------------------------------------------
# Table 1: Verification results LaTeX table (data-driven)
# ---------------------------------------------------------------------------

def export_verification_latex_table(
    verification_csv: Path,
    output_path: Path,
) -> None:
    """
    Generates the verification LaTeX table from verification_summary.csv.
    All values come from data — nothing is hard-coded.
    """
    df = pd.read_csv(verification_csv)

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Independent rerun verification of representative Pareto candidates."
        r" All values derived from \texttt{verification\_summary.csv}.}",
        r"\label{tab:pareto_verification}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        r"\textbf{Candidate Role} & "
        r"\textbf{Stored $\varepsilon_{n,x}$ [$\mu$m]} & "
        r"\textbf{Rerun $\varepsilon_{n,x}$ [$\mu$m]} & "
        r"\textbf{Stored $\sigma_E$ [MeV]} & "
        r"\textbf{Rerun $\sigma_E$ [MeV]} & "
        r"\textbf{Max Diff [\%]} & "
        r"\textbf{Status} \\",
        r"\midrule",
    ]

    for _, row in df.iterrows():
        role = str(row["role"]).replace("_", r"\_")
        s_ex = float(row["stored_emit_x_m_rad"]) * EMIT_SCALE
        r_ex = float(row["rerun_emit_x_m_rad"]) * EMIT_SCALE
        s_se = float(row["stored_sigma_energy_eV"]) * ENERGY_SCALE
        r_se = float(row["rerun_sigma_energy_eV"]) * ENERGY_SCALE
        max_diff = float(row["max_diff_pct"])
        status = str(row["verification_status"])
        status_tex = r"\textbf{VERIFIED}" if status == "VERIFIED" else status
        lines.append(
            f"\\texttt{{{role}}} & {s_ex:.4f} & {r_ex:.4f} & "
            f"{s_se:.4f} & {r_se:.4f} & {max_diff:.6f} & {status_tex} \\\\"
        )

    lines += [
        r"\bottomrule",
        r"\end{tabular}}",
        r"\end{table}",
    ]

    content = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"  ✓ Saved {output_path}")


# ---------------------------------------------------------------------------
# Table 2: Campaign summary results table (data-driven)
# ---------------------------------------------------------------------------

def export_results_summary_latex_table(
    phase2_dir: Path,
    phase3_dir: Path,
    output_path: Path,
    phase1_dir: Path | None = None,
) -> None:
    """
    Generates a campaign summary LaTeX table comparing Phase 1, Phase 2, and Phase 3
    MOBO outcomes. Values come from hypervolume.csv and pareto.csv.
    """
    df2_hv = _load_hypervolume_csv(phase2_dir)
    df3_hv = _load_hypervolume_csv(phase3_dir)
    df2_p = _load_pareto_csv(phase2_dir)
    df3_p = _load_pareto_csv(phase3_dir)

    df1_hv = _load_hypervolume_csv(phase1_dir) if phase1_dir and (phase1_dir / "hypervolume.csv").exists() else None
    df1_p = _load_pareto_csv(phase1_dir) if phase1_dir and (phase1_dir / "pareto.csv").exists() else None

    def summary(hv_df: pd.DataFrame, pareto_df: pd.DataFrame) -> dict:
        final = hv_df.iloc[-1]
        n_eval = int(final.get("num_valid_points", len(hv_df)))
        n_feas = int(final.get("num_feasible_points", 0))
        feas_frac = n_feas / n_eval * 100.0 if n_eval > 0 else 0.0
        final_hv = float(final.get("feasible_hypervolume", 0.0))
        all_hv = float(final.get("all_point_hypervolume", final_hv))
        pareto_size = int(final.get("pareto_size", len(pareto_df)))
        min_ex = float(pareto_df["norm_emit_x_m_rad"].min()) * EMIT_SCALE if len(pareto_df) and "norm_emit_x_m_rad" in pareto_df.columns else float("nan")
        min_ey = float(pareto_df["norm_emit_y_m_rad"].min()) * EMIT_SCALE if len(pareto_df) and "norm_emit_y_m_rad" in pareto_df.columns else float("nan")
        min_se = float(pareto_df["sigma_energy_eV"].min()) * ENERGY_SCALE if len(pareto_df) and "sigma_energy_eV" in pareto_df.columns else float("nan")
        return dict(
            n_eval=n_eval, n_feas=n_feas, feas_frac=feas_frac,
            final_hv=final_hv, all_hv=all_hv, pareto_size=pareto_size,
            min_ex=min_ex, min_ey=min_ey, min_se=min_se
        )

    s2 = summary(df2_hv, df2_p)
    s3 = summary(df3_hv, df3_p)

    if df1_hv is not None and df1_p is not None:
        s1 = summary(df1_hv, df1_p)
        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            r"\caption{Campaign summary comparison across optimization phases. Fixed reporting reference point $\mathbf{r}_\mathrm{rep} = [6.65\times10^{-5},\,1.07\times10^{-4},\,3.37\times10^{6}]$ (physical, [m$\cdot$rad, m$\cdot$rad, eV]).}",
            r"\label{tab:campaign_summary}",
            r"\resizebox{\textwidth}{!}{%",
            r"\begin{tabular}{lccc}",
            r"\toprule",
            r"\textbf{Metric} & \textbf{Phase 1 (Scalarized)} & \textbf{Phase 2 (Unconstrained)} & \textbf{Phase 3 (Constrained)} \\",
            r"\midrule",
            f"Total ASTRA Evaluations & {s1['n_eval']} & {s2['n_eval']} & {s3['n_eval']} \\\\",
            f"Simulation Validity & {s1['n_eval']} (100\\%) & {s2['n_eval']} (100\\%) & {s3['n_eval']} (100\\%) \\\\",
            f"Feasible Evaluations & {s1['n_feas']} ({s1['feas_frac']:.1f}\\%) & {s2['n_feas']} ({s2['feas_frac']:.1f}\\%) & {s3['n_feas']} ({s3['feas_frac']:.1f}\\%) \\\\",
            f"Unconstrained Hypervolume & {s1['all_hv']:.6f} & {s2['all_hv']:.6f} & {s3['all_hv']:.6f} \\\\",
            f"Feasible Hypervolume & {s1['final_hv']:.6f} & {s2['final_hv']:.6f} & {s3['final_hv']:.6f} \\\\",
            f"Final Pareto Size & {s1['pareto_size']} & {s2['pareto_size']} & {s3['pareto_size']} \\\\",
            f"Min $\\varepsilon_{{n,x}}$ [$\\mu$m$\\cdot$rad] & {s1['min_ex']:.4f} & {s2['min_ex']:.4f} & {s3['min_ex']:.4f} \\\\",
            f"Min $\\varepsilon_{{n,y}}$ [$\\mu$m$\\cdot$rad] & {s1['min_ey']:.4f} & {s2['min_ey']:.4f} & {s3['min_ey']:.4f} \\\\",
            f"Min $\\sigma_E$ [MeV] & {s1['min_se']:.4f} & {s2['min_se']:.4f} & {s3['min_se']:.4f} \\\\",
            r"\bottomrule",
            r"\end{tabular}}",
            r"\end{table}",
        ]
    else:
        lines = [
            r"\begin{table}[htbp]",
            r"\centering",
            r"\caption{Campaign summary comparison: Phase~2 (Unconstrained MOBO) vs."
            r" Phase~3 (Constrained MOBO). Fixed reporting reference point"
            r" $\mathbf{r}_\mathrm{rep} = [6.65\times10^{-5},\,1.07\times10^{-4},\,3.37\times10^{6}]$"
            r" (physical, [m$\cdot$rad, m$\cdot$rad, eV]).}",
            r"\label{tab:campaign_summary}",
            r"\begin{tabular}{lcc}",
            r"\toprule",
            r"\textbf{Metric} & \textbf{Phase 2 (Unconstrained)} & \textbf{Phase 3 (Constrained)} \\",
            r"\midrule",
            f"Total ASTRA Evaluations & {s2['n_eval']} & {s3['n_eval']} \\\\",
            f"Feasible Evaluations & {s2['n_feas']} ({s2['feas_frac']:.1f}\\%) & {s3['n_feas']} ({s3['feas_frac']:.1f}\\%) \\\\",
            f"Final Feasible Hypervolume & {s2['final_hv']:.6f} & {s3['final_hv']:.6f} \\\\",
            f"Final Pareto Size & {s2['pareto_size']} & {s3['pareto_size']} \\\\",
            f"Min $\\varepsilon_{{n,x}}$ [$\\mu$m] & {s2['min_ex']:.4f} & {s3['min_ex']:.4f} \\\\",
            f"Min $\\sigma_E$ [MeV] & {s2['min_se']:.4f} & {s3['min_se']:.4f} \\\\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]

    content = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"  ✓ Saved {output_path}")


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

    # Auto-detect Phase 1 directory if not explicitly provided
    if p1 is None:
        if (p2.parent / "phase1_scalarized").is_dir():
            p1 = p2.parent / "phase1_scalarized"
        elif Path("results/full_production/phase1_scalarized").is_dir():
            p1 = Path("results/full_production/phase1_scalarized")

    if p1 is not None and not p1.is_dir():
        print(f"Warning: --phase1-dir specified but does not exist: {p1}", file=sys.stderr)
        p1 = None

    # Validate source directories exist
    for p, label in [(p2, "--phase2-dir"), (p3, "--phase3-dir")]:
        if not p.is_dir():
            print(f"Error: {label} directory does not exist: {p}", file=sys.stderr)
            return 1

    if args.check_only:
        ok = check_manuscript_consistency(p2, p3, fig_dir, tab_dir, ver_csv, phase1_dir=p1)
        return 0 if ok else 1

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
        export_verification_latex_table(ver_csv, tab_dir / "verification_table.tex")
    else:
        print(f"[Table 1] Skipped — verification CSV not found: {ver_csv}")

    # --- Table 2: Campaign summary LaTeX table ---
    print("[Table 2] Campaign summary LaTeX table...")
    export_results_summary_latex_table(p2, p3, tab_dir / "results_table.tex", phase1_dir=p1)

    # --- Table 3: Phase 1 Option 2 cases LaTeX table ---
    if p1 is not None:
        p1_cases_csv = p1 / "cases_summary.csv"
        if not p1_cases_csv.exists() and (p1 / "evaluations.csv").exists():
            from mobo_linac.campaigns.scalarized_suite import aggregate_scalarized_cases
            aggregate_scalarized_cases(p1)
            p1_cases_csv = p1 / "cases_summary.csv"

        if p1_cases_csv.exists():
            print("[Table 3] Phase 1 Option 2 cases LaTeX table...")
            from mobo_linac.campaigns.scalarized_suite import export_phase1_cases_latex_table
            export_phase1_cases_latex_table(p1_cases_csv, tab_dir / "phase1_cases_table.tex")
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
