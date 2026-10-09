"""Publication figures using the explicit run contract; figures are closed after export."""
from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mobo_linac.io.run_data import read_run_data, read_comparable_runs
from mobo_linac.metrics.latex import verification_records, measured
from mobo_linac.plotting.common import PlotSchema

EMIT_SCALE = 1e6
ENERGY_SCALE = 1e-6

def _save(fig: plt.Figure, path: Path, dpi: int = 300) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    finally:
        plt.close(fig)


def _load_hypervolume_csv(run_dir):
    return read_run_data(run_dir).hypervolume


def _load_pareto_csv(run_dir):
    # Manuscript Pareto comparisons consistently use the feasible front.
    return read_run_data(run_dir).pareto(feasible=True)


# ---------------------------------------------------------------------------
# Figure 1: Hypervolume progress comparison
# ---------------------------------------------------------------------------

def plot_hypervolume_comparison(
    phase2_dir: Path,
    phase3_dir: Path,
    output_path: Path,
    phase1_dir: Optional[Path] = None,
) -> dict:
    """
    Plots feasible hypervolume vs. cumulative ASTRA evaluations for Phase 1
    (Scalarized), Phase 2 (Unconstrained), and Phase 3 (Constrained) MOBO campaigns.

    Data source: hypervolume.csv from each campaign run directory.
    """
    read_comparable_runs([phase2_dir, phase3_dir] + ([phase1_dir] if phase1_dir is not None else []))
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

    ax.set_xlabel("Cumulative Valid Observations", fontsize=13)
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
    phase1_dir: Optional[Path] = None,
) -> None:
    """
    2D projections of the physical objective space comparing Phase 1, Phase 2,
    and Phase 3 Pareto fronts.

    Data source: pareto.csv from each campaign run directory.
    """
    from itertools import combinations
    directories = ([phase1_dir] if phase1_dir is not None else []) + [phase2_dir, phase3_dir]
    runs = read_comparable_runs(directories)
    objectives = runs[0].config.objectives
    plot_schema = PlotSchema.from_config(runs[0].config)
    def label(objective):
        spec = plot_schema.objective(objective.explicit_name)
        return spec.label, 1.0 / spec.scale
    pairs = list(combinations(objectives, 2)) or [(None, objectives[0])]
    names = (["Phase 1"] if phase1_dir is not None else []) + ["Phase 2", "Phase 3"]
    colors = (["#7570b3"] if phase1_dir is not None else []) + ["#1f6fb5", "#d95f02"]
    fig, axes = plt.subplots(1, len(pairs), figsize=(5 * len(pairs), 4.5), squeeze=False)
    try:
        for ax, (first, second) in zip(axes[0], pairs):
            ylabel, yscale = label(second)
            xlabel, xscale = label(first) if first else ("Candidate", 1)
            for run, name, color in zip(runs, names, colors):
                frame = run.pareto(feasible=True)
                x = frame[first.explicit_name] * xscale if first else np.arange(len(frame))
                ax.scatter(x, frame[second.explicit_name] * yscale, label=name, color=color, alpha=.85)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(True, linestyle=":", alpha=.5)
            ax.legend()
        axes[0][len(pairs) // 2].set_title("Feasible Pareto Front Comparison")
        fig.tight_layout()
        _save(fig, output_path)
    finally:
        plt.close(fig)


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
    records = verification_records(verification_csv)
    df = pd.DataFrame(records)
    columns = records[0].get("objective_order", list(records[0].get("stored_objectives", {}))) if records else []
    units = records[0].get("objective_units", {}) if records else {}
    legacy = ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
    dynamic = bool(columns and (columns != legacy or (units and units != dict(zip(legacy, ["m*rad", "m*rad", "eV"])))))
    panels = [(name, f"{name} [{units.get(name, 'unknown')}]") for name in columns] if dynamic else [
        ("emit_x_m_rad", r"$\varepsilon_{n,x}$ [$\mu$m·rad]"), ("sigma_energy_eV", r"$\sigma_E$ [MeV]")]
    fig, axes = plt.subplots(1, len(panels), figsize=(6.5 * len(panels), 4.5), squeeze=False)
    try:
        x = np.arange(len(records))
        roles = [str(record.get("role", "candidate")).replace("$", r"\$") for record in records]
        for ax, (name, ylabel) in zip(axes[0], panels):
            for offset, group, prefix, color in ((-.175, "stored_objectives", "stored", "#1f6fb5"),
                                                  (.175, "rerun_objectives", "rerun", "#2ca02c")):
                values = [measured(record.get(group, {}).get(name)) if dynamic else measured(record.get(f"{prefix}_{name}")) * (1e6 if name == "emit_x_m_rad" else 1e-6) for record in records]
                ax.bar(x + offset, values, .35, label=prefix.title(), color=color, alpha=.85)
            ax.set_xticks(x)
            ax.set_xticklabels(roles, rotation=15, ha="right", fontsize=9)
            ax.set_ylabel(ylabel)
            ax.legend()
            ax.grid(True, axis="y", linestyle="--", alpha=.5)
        fig.suptitle("Independent Pareto Candidate Rerun Verification")
        fig.tight_layout()
        _save(fig, output_path)
    finally:
        plt.close(fig)
    return df


# ---------------------------------------------------------------------------
# Figure 4: Feasible fraction progress
# ---------------------------------------------------------------------------

def plot_feasible_fraction(
    phase2_dir: Path,
    phase3_dir: Path,
    output_path: Path,
    phase1_dir: Optional[Path] = None,
) -> None:
    """
    Feasible beam fraction (num_feasible_points / num_valid_points) vs.
    cumulative ASTRA evaluations for Phase 1, Phase 2, and Phase 3.
    """
    read_comparable_runs([phase2_dir, phase3_dir] + ([phase1_dir] if phase1_dir is not None else []))
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
    ax.set_xlabel("Cumulative Valid Observations", fontsize=12)
    ax.set_ylabel("Feasible Fraction of Valid Observations [%]", fontsize=12)
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
