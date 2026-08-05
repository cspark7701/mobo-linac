"""
Plotting and Visualization Routines for mobo_linac.

Reads physical objective values and diagnostic metrics to produce
publication-ready figures covering:
  - Hypervolume progress & comparison
  - Pareto front 2D projections & 3D scatter
  - Objective evolution & best-so-far progression
  - Constraint diagnostics & violin plots
  - Feasibility rate over iterations
  - Design variable correlation heatmap
  - Parallel coordinates plot
  - GP surrogate mean & uncertainty
  - Scalarized objective trace (Phase 1)
  - Phase comparison overlays
  - Pareto candidate verification
"""

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import (
    DESIGN_VAR_COLUMNS,
    results_to_dataframe,
)

# ── shared unit helpers ───────────────────────────────────────────────────────
_EMIT_SCALE = 1e6   # m·rad  → mm·mrad
_ENERGY_SCALE = 1e-6  # eV   → MeV
_DESIGN_VAR_LABELS = [
    r"$B_\mathrm{sol}$ [T]",
    r"$G_{q1}$ [T/m]",
    r"$G_{q2}$ [T/m]",
    r"$\phi_\mathrm{gun}$ [°]",
    r"$\phi_\mathrm{acc1/2}$ [°]",
    r"$\phi_\mathrm{acc3/4}$ [°]",
]
_OBJ_LABELS = [
    r"$\varepsilon_{n,x}$ [mm·mrad]",
    r"$\varepsilon_{n,y}$ [mm·mrad]",
    r"$\sigma_E$ [MeV]",
]


def _save(fig: plt.Figure, output_path: Optional[Union[str, Path]]) -> None:
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=300, bbox_inches="tight")


# ═════════════════════════════════════════════════════════════════════════════
# 1. Hypervolume progress
# ═════════════════════════════════════════════════════════════════════════════
def plot_hypervolume_progress(
    history: Union[pd.DataFrame, List[dict]],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Hypervolume progress (feasible + all-point) over cumulative evaluations or iterations."""
    df = pd.DataFrame(history) if isinstance(history, list) else history

    if "cumulative_astra_evaluations" in df.columns:
        x = df["cumulative_astra_evaluations"]
        xlabel = "Cumulative ASTRA Evaluations"
    elif "cumulative_evaluations" in df.columns:
        x = df["cumulative_evaluations"]
        xlabel = "Cumulative ASTRA Evaluations"
    elif "num_valid_points" in df.columns:
        x = df["num_valid_points"]
        xlabel = "Cumulative Evaluations"
    elif "iteration" in df.columns:
        x = df["iteration"]
        xlabel = "Iteration"
    else:
        x = range(1, len(df) + 1)
        xlabel = "Step"

    fig, ax = plt.subplots(figsize=(9, 5))
    if "feasible_hypervolume" in df.columns:
        ax.plot(x, df["feasible_hypervolume"], "o-", color="steelblue",
                linewidth=2, markersize=5, label="Feasible Hypervolume")
    elif "fixed_ref_feasible_hv" in df.columns:
        ax.plot(x, df["fixed_ref_feasible_hv"], "o-", color="steelblue",
                linewidth=2, markersize=5, label="Feasible Hypervolume")

    if "all_point_hypervolume" in df.columns:
        ax.plot(x, df["all_point_hypervolume"], "s--", color="slategray",
                linewidth=1.5, alpha=0.7, label="All-Point Hypervolume")
    elif "fixed_ref_all_valid_hv" in df.columns:
        ax.plot(x, df["fixed_ref_all_valid_hv"], "s--", color="slategray",
                linewidth=1.5, alpha=0.7, label="All-Point Hypervolume")

    ax.set_xlabel(xlabel, fontsize=13)
    ax.set_ylabel("Hypervolume", fontsize=13)
    ax.set_title("Hypervolume Progress", fontsize=15)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=11)
    fig.tight_layout()
    _save(fig, output_path)
    return fig



# ═════════════════════════════════════════════════════════════════════════════
# 2. Pareto front — 2D projections
# ═════════════════════════════════════════════════════════════════════════════
def plot_pareto_front(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """2D projections of objective space highlighting feasible Pareto front."""
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]]
    feas = valid[valid["physically_feasible"]]

    ex_a = valid["norm_emit_x_m_rad"] * _EMIT_SCALE
    ey_a = valid["norm_emit_y_m_rad"] * _EMIT_SCALE
    se_a = valid["sigma_energy_eV"] * _ENERGY_SCALE
    ex_f = feas["norm_emit_x_m_rad"] * _EMIT_SCALE
    ey_f = feas["norm_emit_y_m_rad"] * _EMIT_SCALE
    se_f = feas["sigma_energy_eV"] * _ENERGY_SCALE

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    pairs = [
        (ex_a, ey_a, ex_f, ey_f, _OBJ_LABELS[0], _OBJ_LABELS[1],
         r"$\varepsilon_{n,x}$ vs $\varepsilon_{n,y}$"),
        (se_a, ex_a, se_f, ex_f, _OBJ_LABELS[2], _OBJ_LABELS[0],
         r"$\sigma_E$ vs $\varepsilon_{n,x}$"),
        (se_a, ey_a, se_f, ey_f, _OBJ_LABELS[2], _OBJ_LABELS[1],
         r"$\sigma_E$ vs $\varepsilon_{n,y}$"),
    ]
    for ax, (xa, ya, xf, yf, xl, yl, title) in zip(axes, pairs):
        ax.scatter(xa, ya, c="lightgray", s=25, alpha=0.5, label="All valid")
        ax.scatter(xf, yf, c="steelblue", s=45, alpha=0.85, label="Feasible")
        ax.set_xlabel(xl, fontsize=12)
        ax.set_ylabel(yl, fontsize=12)
        ax.set_title(title, fontsize=13)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=10)

    fig.suptitle("Objective Space — 2D Projections", fontsize=15, y=1.01)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 3. Pareto front — 3D scatter
# ═════════════════════════════════════════════════════════════════════════════
def plot_pareto_front_3d(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
    elev: float = 25.0,
    azim: float = 45.0,
) -> plt.Figure:
    """3D scatter of the feasible Pareto front across all three objectives."""
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]]
    feas = valid[valid["physically_feasible"]]
    infeas = valid[~valid["physically_feasible"]]

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    if len(infeas):
        ax.scatter(
            infeas["norm_emit_x_m_rad"] * _EMIT_SCALE,
            infeas["norm_emit_y_m_rad"] * _EMIT_SCALE,
            infeas["sigma_energy_eV"] * _ENERGY_SCALE,
            c="lightgray", s=15, alpha=0.3, label="Infeasible",
        )
    if len(feas):
        sc = ax.scatter(
            feas["norm_emit_x_m_rad"] * _EMIT_SCALE,
            feas["norm_emit_y_m_rad"] * _EMIT_SCALE,
            feas["sigma_energy_eV"] * _ENERGY_SCALE,
            c=feas["sigma_energy_eV"] * _ENERGY_SCALE,
            cmap="plasma", s=55, alpha=0.9, label="Feasible Pareto",
        )
        fig.colorbar(sc, ax=ax, pad=0.1, shrink=0.6,
                     label=r"$\sigma_E$ [MeV]")

    ax.set_xlabel(_OBJ_LABELS[0], fontsize=11, labelpad=8)
    ax.set_ylabel(_OBJ_LABELS[1], fontsize=11, labelpad=8)
    ax.set_zlabel(_OBJ_LABELS[2], fontsize=11, labelpad=8)
    ax.set_title("3D Pareto Front — Objective Space", fontsize=14)
    ax.view_init(elev=elev, azim=azim)
    ax.legend(fontsize=10)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 4. Objective evolution
# ═════════════════════════════════════════════════════════════════════════════
def plot_objective_evolution(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Three-panel time-series of each physical objective across evaluations."""
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].reset_index(drop=True)
    idx = range(1, len(valid) + 1)

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    colors = ["steelblue", "darkorange", "seagreen"]
    cols = ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
    scales = [_EMIT_SCALE, _EMIT_SCALE, _ENERGY_SCALE]

    for ax, col, scale, label, color in zip(axes, cols, scales, _OBJ_LABELS, colors):
        vals = valid[col] * scale
        ax.plot(idx, vals, color=color, linewidth=1.5, alpha=0.8)
        ax.scatter(idx, vals, c=color, s=18, zorder=3)
        # rolling minimum line
        ax.plot(idx, vals.cummin(), color=color, linestyle="--",
                linewidth=1.2, alpha=0.5, label="Best so far")
        ax.set_ylabel(label, fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=9, loc="upper right")

    axes[-1].set_xlabel("Evaluation Index", fontsize=12)
    fig.suptitle("Physical Objectives — Evaluation History", fontsize=14)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 5. Best-so-far progression (per objective + feasibility gate)
# ═════════════════════════════════════════════════════════════════════════════
def plot_best_so_far(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Running best (feasible) value for each objective vs evaluation index.
    Only improves when a new feasible evaluation beats the previous best.
    """
    df = results_to_dataframe(results)
    feas = df[df["simulation_valid"] & df["physically_feasible"]].reset_index(drop=True)

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    colors = ["steelblue", "darkorange", "seagreen"]
    cols = ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
    scales = [_EMIT_SCALE, _EMIT_SCALE, _ENERGY_SCALE]

    for ax, col, scale, label, color in zip(axes, cols, scales, _OBJ_LABELS, colors):
        vals = feas[col] * scale
        best = vals.cummin()
        idx = range(1, len(feas) + 1)
        ax.step(idx, best, where="post", color=color, linewidth=2.5, label="Best (feasible)")
        ax.scatter(idx, vals, c="lightgray", s=18, zorder=2, label="Feasible evals")
        ax.set_ylabel(label, fontsize=11)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=9, loc="upper right")

    axes[-1].set_xlabel("Feasible Evaluation Index", fontsize=12)
    fig.suptitle("Best-so-Far Progression (Feasible Evaluations)", fontsize=14)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 6. Feasibility rate over iterations
# ═════════════════════════════════════════════════════════════════════════════
def plot_feasibility_rate(
    results: List[EvaluationResult],
    window: int = 10,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Cumulative and rolling feasibility rate (fraction of valid, feasible
    evaluations) as BO progresses.
    """
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].reset_index(drop=True)
    feasible_flag = valid["physically_feasible"].astype(float)
    idx = range(1, len(valid) + 1)

    cumulative_rate = feasible_flag.expanding().mean() * 100
    rolling_rate = feasible_flag.rolling(window=window, min_periods=1).mean() * 100

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(idx, cumulative_rate, color="steelblue", linewidth=2,
            label="Cumulative feasibility rate")
    ax.plot(idx, rolling_rate, color="darkorange", linewidth=1.8,
            linestyle="--", label=f"Rolling {window}-eval window")
    ax.fill_between(idx, cumulative_rate, alpha=0.12, color="steelblue")
    ax.set_ylim(0, 105)
    ax.set_xlabel("Valid Evaluation Index", fontsize=12)
    ax.set_ylabel("Feasibility Rate [%]", fontsize=12)
    ax.set_title("Beam Feasibility Rate Over BO Campaign", fontsize=14)
    ax.axhline(50, color="gray", linestyle=":", alpha=0.5, label="50% reference")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=10)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 7. Design variable correlation heatmap
# ═════════════════════════════════════════════════════════════════════════════
def plot_design_variable_heatmap(
    results: List[EvaluationResult],
    feasible_only: bool = True,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Pearson correlation heatmap between all 6 design variables.
    Optionally restricted to feasible evaluations only.
    """
    df = results_to_dataframe(results)
    subset = df[df["simulation_valid"]]
    if feasible_only:
        subset = subset[subset["physically_feasible"]]

    corr = subset[DESIGN_VAR_COLUMNS].dropna().corr()
    short_labels = [r"$B_{sol}$", r"$G_{q1}$", r"$G_{q2}$",
                    r"$\phi_{gun}$", r"$\phi_{12}$", r"$\phi_{34}$"]

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
    fig.colorbar(im, ax=ax, label="Pearson r", shrink=0.85)

    ax.set_xticks(range(6))
    ax.set_yticks(range(6))
    ax.set_xticklabels(short_labels, fontsize=11, rotation=30, ha="right")
    ax.set_yticklabels(short_labels, fontsize=11)

    for i in range(6):
        for j in range(6):
            val = corr.values[i, j]
            txt_color = "white" if abs(val) > 0.6 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=9, color=txt_color)

    label = "Feasible" if feasible_only else "All Valid"
    ax.set_title(f"Design Variable Correlation ({label} Evaluations)", fontsize=13)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 8. Parallel coordinates — design variables coloured by objective
# ═════════════════════════════════════════════════════════════════════════════
def plot_parallel_coordinates(
    results: List[EvaluationResult],
    color_by: str = "norm_emit_x_m_rad",
    feasible_only: bool = True,
    n_lines: int = 200,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Parallel coordinates plot of the 6 design variables, coloured by one
    physical objective (default: ε_nx).

    Args:
        results:       list of EvaluationResult objects.
        color_by:      DataFrame column to use for colouring lines.
        feasible_only: restrict to physically feasible evaluations.
        n_lines:       maximum number of lines to draw (random sample).
    """
    df = results_to_dataframe(results)
    subset = df[df["simulation_valid"]]
    if feasible_only:
        subset = subset[subset["physically_feasible"]]
    subset = subset.dropna(subset=DESIGN_VAR_COLUMNS + [color_by])
    if len(subset) > n_lines:
        subset = subset.sample(n_lines, random_state=0)

    # normalise each axis to [0, 1] for plotting
    norm_df = subset[DESIGN_VAR_COLUMNS].copy()
    for col in DESIGN_VAR_COLUMNS:
        lo, hi = norm_df[col].min(), norm_df[col].max()
        norm_df[col] = (norm_df[col] - lo) / (hi - lo + 1e-30)

    c_vals = subset[color_by].values
    cmap = cm.plasma
    c_norm = mcolors.Normalize(c_vals.min(), c_vals.max())
    sm = cm.ScalarMappable(cmap=cmap, norm=c_norm)

    fig, ax = plt.subplots(figsize=(12, 6))
    n_vars = len(DESIGN_VAR_COLUMNS)
    xs = np.arange(n_vars)

    for _, row in norm_df.iterrows():
        orig_idx = row.name
        rgba = cmap(c_norm(c_vals[list(subset.index).index(orig_idx)]))
        ax.plot(xs, row.values, color=rgba, alpha=0.4, linewidth=0.9)

    ax.set_xticks(xs)
    ax.set_xticklabels(_DESIGN_VAR_LABELS, fontsize=11)
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel("Normalised Value", fontsize=11)
    label = "Feasible" if feasible_only else "All Valid"
    cb_label = (r"$\varepsilon_{n,x}$ [m·rad]" if color_by == "norm_emit_x_m_rad"
                else color_by)
    ax.set_title(f"Parallel Coordinates — Design Variables ({label})", fontsize=13)
    fig.colorbar(sm, ax=ax, label=cb_label, shrink=0.85, pad=0.01)
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 9. Constraint diagnostics (time-series)
# ═════════════════════════════════════════════════════════════════════════════
def plot_constraint_diagnostics(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    2×2 grid of constraint-diagnostic time-series with limit reference lines:
    beam sizes, divergences, bunch length, and mean kinetic energy.
    """
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].reset_index(drop=True)
    idx = range(1, len(valid) + 1)

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))

    # 1. Transverse beam sizes
    axes[0, 0].plot(idx, valid["sigma_x_m"] * 1e3, label=r"$\sigma_x$", color="steelblue")
    axes[0, 0].plot(idx, valid["sigma_y_m"] * 1e3, label=r"$\sigma_y$", color="darkorange")
    axes[0, 0].axhline(1.0, color="crimson", linestyle="--", linewidth=1.4, label="Limit 1.0 mm")
    axes[0, 0].set_ylabel(r"$\sigma_{x,y}$ [mm]", fontsize=11)
    axes[0, 0].set_title("Transverse Beam Size", fontsize=12)
    axes[0, 0].grid(True, linestyle=":", alpha=0.6)
    axes[0, 0].legend(fontsize=9)

    # 2. Transverse divergence
    axes[0, 1].plot(idx, valid["sigma_xp_rad"] * 1e3, label=r"$\sigma_{x'}$", color="seagreen")
    axes[0, 1].plot(idx, valid["sigma_yp_rad"] * 1e3, label=r"$\sigma_{y'}$", color="purple")
    axes[0, 1].axhline(1.0, color="crimson", linestyle="--", linewidth=1.4, label="Limit 1.0 mrad")
    axes[0, 1].set_ylabel(r"$\sigma_{x',y'}$ [mrad]", fontsize=11)
    axes[0, 1].set_title("Transverse Divergence", fontsize=12)
    axes[0, 1].grid(True, linestyle=":", alpha=0.6)
    axes[0, 1].legend(fontsize=9)

    # 3. Bunch length
    axes[1, 0].plot(idx, valid["sigma_z_m"] * 1e3, label=r"$\sigma_z$", color="firebrick")
    axes[1, 0].axhline(1.0, color="crimson", linestyle="--", linewidth=1.4, label="Limit 1.0 mm")
    axes[1, 0].set_ylabel(r"$\sigma_z$ [mm]", fontsize=11)
    axes[1, 0].set_xlabel("Evaluation Index", fontsize=11)
    axes[1, 0].set_title("Bunch Length", fontsize=12)
    axes[1, 0].grid(True, linestyle=":", alpha=0.6)
    axes[1, 0].legend(fontsize=9)

    # 4. Mean kinetic energy
    axes[1, 1].plot(idx, valid["mean_kinetic_energy_eV"] * _ENERGY_SCALE,
                    label=r"$E_{kin}$", color="saddlebrown")
    axes[1, 1].axhline(195.0, color="crimson", linestyle="--", linewidth=1.4, label="Min 195 MeV")
    axes[1, 1].axhline(205.0, color="crimson", linestyle="--", linewidth=1.4, label="Max 205 MeV")
    axes[1, 1].fill_between(idx, 195.0, 205.0, alpha=0.06, color="seagreen")
    axes[1, 1].set_ylabel("Kinetic Energy [MeV]", fontsize=11)
    axes[1, 1].set_xlabel("Evaluation Index", fontsize=11)
    axes[1, 1].set_title("Mean Kinetic Energy", fontsize=12)
    axes[1, 1].grid(True, linestyle=":", alpha=0.6)
    axes[1, 1].legend(fontsize=9)

    fig.suptitle("Beam Quality Constraint Diagnostics", fontsize=14)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 10. Constraint violin plots (distribution across evaluations)
# ═════════════════════════════════════════════════════════════════════════════
def plot_constraint_violins(
    results: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Violin plots of each constraint diagnostic split by feasibility status,
    making the margin and tail behaviour immediately visible.
    """
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].copy()

    diag_cols = {
        r"$\sigma_x$ [mm]": ("sigma_x_m", 1e3, 1.0),
        r"$\sigma_y$ [mm]": ("sigma_y_m", 1e3, 1.0),
        r"$\sigma_{x'}$ [mrad]": ("sigma_xp_rad", 1e3, 1.0),
        r"$\sigma_{y'}$ [mrad]": ("sigma_yp_rad", 1e3, 1.0),
        r"$\sigma_z$ [mm]": ("sigma_z_m", 1e3, 1.0),
    }

    fig, axes = plt.subplots(1, len(diag_cols), figsize=(15, 5), sharey=False)

    feas = valid[valid["physically_feasible"]]
    infeas = valid[~valid["physically_feasible"]]

    for ax, (ylabel, (col, scale, limit)) in zip(axes, diag_cols.items()):
        data_f = (feas[col].dropna() * scale).values
        data_i = (infeas[col].dropna() * scale).values
        parts = ax.violinplot(
            [d for d in [data_f, data_i] if len(d)],
            positions=[1, 2][:sum([len(data_f) > 0, len(data_i) > 0])],
            showmedians=True, showextrema=True,
        )
        for pc in parts["bodies"]:
            pc.set_alpha(0.6)
        ax.axhline(limit, color="crimson", linestyle="--", linewidth=1.3)
        labels = [lbl for lbl, d in zip(["Feasible", "Infeasible"], [data_f, data_i]) if len(d)]
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, fontsize=9, rotation=15)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(True, axis="y", linestyle=":", alpha=0.6)

    fig.suptitle("Constraint Diagnostic Distributions (Feasible vs Infeasible)", fontsize=13)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 11. Scalarized objective trace (Phase 1)
# ═════════════════════════════════════════════════════════════════════════════
def plot_scalarized_objective_trace(
    results: List[EvaluationResult],
    weights: Sequence[float] = (1.0, 1.0, 1.0),
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    Phase 1 specific: plots the scalarised merit function value
    f(x) = w1*ε_nx + w2*ε_ny + w3*σ_E (normalised by first value) and the
    individual objective contributions, over evaluation history.

    Args:
        results: list of EvaluationResult objects.
        weights: three-element weight vector [w_ex, w_ey, w_sE].
    """
    df = results_to_dataframe(results)
    valid = df[df["simulation_valid"]].reset_index(drop=True)
    w = np.array(weights, dtype=float)

    ex = valid["norm_emit_x_m_rad"].values * _EMIT_SCALE
    ey = valid["norm_emit_y_m_rad"].values * _EMIT_SCALE
    se = valid["sigma_energy_eV"].values * _ENERGY_SCALE

    # Normalise each objective by its first observed value
    def _safe_norm(arr: np.ndarray) -> np.ndarray:
        ref = arr[arr > 0][0] if np.any(arr > 0) else 1.0
        return arr / ref

    ex_n, ey_n, se_n = _safe_norm(ex), _safe_norm(ey), _safe_norm(se)
    scalar = w[0] * ex_n + w[1] * ey_n + w[2] * se_n
    idx = range(1, len(valid) + 1)

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    # Top: scalarized merit + running minimum
    ax_top.plot(idx, scalar, color="steelblue", linewidth=1.5, alpha=0.8, label="f(x)")
    ax_top.plot(idx, pd.Series(scalar).cummin(), color="crimson", linestyle="--",
                linewidth=2, label="Best so far")
    ax_top.set_ylabel(f"f(x) = {w[0]:.1f}·ε̃_x + {w[1]:.1f}·ε̃_y + {w[2]:.1f}·σ̃_E", fontsize=11)
    ax_top.set_title(f"Scalarized Objective Trace  (weights {w.tolist()})", fontsize=13)
    ax_top.grid(True, linestyle=":", alpha=0.6)
    ax_top.legend(fontsize=10)

    # Bottom: stacked area of individual (normalised) contributions
    ax_bot.stackplot(
        idx, w[0] * ex_n, w[1] * ey_n, w[2] * se_n,
        labels=[r"$w_1\tilde\varepsilon_{n,x}$",
                r"$w_2\tilde\varepsilon_{n,y}$",
                r"$w_3\tilde\sigma_E$"],
        colors=["steelblue", "darkorange", "seagreen"],
        alpha=0.65,
    )
    ax_bot.set_xlabel("Evaluation Index", fontsize=12)
    ax_bot.set_ylabel("Normalised contribution", fontsize=11)
    ax_bot.set_title("Objective Contribution Breakdown", fontsize=12)
    ax_bot.grid(True, linestyle=":", alpha=0.6)
    ax_bot.legend(loc="upper right", fontsize=9)

    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 12. GP surrogate mean & uncertainty (1D slice)
# ═════════════════════════════════════════════════════════════════════════════
def plot_gp_surrogate_slice(
    model,
    bounds: "torch.Tensor",  # noqa: F821
    fixed_x: "torch.Tensor",  # noqa: F821
    dim: int = 0,
    obj_idx: int = 0,
    n_points: int = 100,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """
    1D slice through the GP surrogate posterior along one design variable,
    keeping all other dimensions fixed at `fixed_x`.

    Args:
        model:    Fitted GP model (single-output or ModelListGP[obj_idx]).
        bounds:   (2 × d) tensor of parameter bounds.
        fixed_x:  (d,) tensor — the reference point for all other dims.
        dim:      which design variable to sweep (0–5).
        obj_idx:  which GP output to query if model is a ModelListGP.
        n_points: resolution of the 1D sweep.
    """
    import torch

    lo, hi = bounds[0, dim].item(), bounds[1, dim].item()
    sweep = torch.linspace(lo, hi, n_points, dtype=torch.double)

    X_test = fixed_x.unsqueeze(0).repeat(n_points, 1).clone()
    X_test[:, dim] = sweep

    # Handle ModelListGP vs single GP
    try:
        m = model.models[obj_idx]
    except AttributeError:
        m = model

    with torch.no_grad():
        post = m.posterior(X_test)
        mean = post.mean.squeeze().cpu().numpy()
        std = post.variance.clamp_min(0).sqrt().squeeze().cpu().numpy()

    sweep_np = sweep.cpu().numpy()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(sweep_np, mean, color="steelblue", linewidth=2, label="GP mean")
    ax.fill_between(sweep_np, mean - 2 * std, mean + 2 * std,
                    alpha=0.25, color="steelblue", label="±2σ")
    ax.set_xlabel(_DESIGN_VAR_LABELS[dim], fontsize=12)
    ax.set_ylabel(_OBJ_LABELS[obj_idx] if obj_idx < 3 else f"Output {obj_idx}", fontsize=12)
    ax.set_title(f"GP Posterior Slice — dim {dim} ({_DESIGN_VAR_LABELS[dim]})", fontsize=13)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=10)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 13. Phase comparison: hypervolume overlay
# ═════════════════════════════════════════════════════════════════════════════
def plot_hypervolume_comparison(
    hist_p2: pd.DataFrame,
    hist_p3: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Overlaid hypervolume progress for Phase 2 (unconstrained) vs Phase 3 (constrained)."""
    fig, ax = plt.subplots(figsize=(9, 5))

    iters_p2 = hist_p2.get("iteration", range(len(hist_p2)))
    iters_p3 = hist_p3.get("iteration", range(len(hist_p3)))

    ax.plot(iters_p2, hist_p2["feasible_hypervolume"], "o-",
            color="steelblue", linewidth=2, label="Phase 2 (Unconstrained HV)")
    ax.plot(iters_p3, hist_p3["feasible_hypervolume"], "s-",
            color="seagreen", linewidth=2, label="Phase 3 (Constrained HV)")

    for (iters, hist, color) in [(iters_p2, hist_p2, "steelblue"),
                                  (iters_p3, hist_p3, "seagreen")]:
        if "all_point_hypervolume" in hist.columns:
            ax.plot(iters, hist["all_point_hypervolume"], linestyle="--",
                    color=color, alpha=0.4)

    ax.set_xlabel("Iteration", fontsize=13)
    ax.set_ylabel("Hypervolume", fontsize=13)
    ax.set_title("Feasible Hypervolume: Phase 2 vs Phase 3", fontsize=14)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=11)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 14. Phase comparison: Pareto front overlay
# ═════════════════════════════════════════════════════════════════════════════
def plot_pareto_front_comparison(
    results_p2: List[EvaluationResult],
    results_p3: List[EvaluationResult],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Overlaid 2D projections comparing Phase 2 and Phase 3 feasible Pareto fronts."""
    df2 = results_to_dataframe(results_p2)
    df3 = results_to_dataframe(results_p3)
    feas2 = df2[df2["simulation_valid"] & df2["physically_feasible"]]
    feas3 = df3[df3["simulation_valid"] & df3["physically_feasible"]]

    ex2, ey2, se2 = (feas2["norm_emit_x_m_rad"] * _EMIT_SCALE,
                     feas2["norm_emit_y_m_rad"] * _EMIT_SCALE,
                     feas2["sigma_energy_eV"] * _ENERGY_SCALE)
    ex3, ey3, se3 = (feas3["norm_emit_x_m_rad"] * _EMIT_SCALE,
                     feas3["norm_emit_y_m_rad"] * _EMIT_SCALE,
                     feas3["sigma_energy_eV"] * _ENERGY_SCALE)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    pairs = [
        (ex2, ey2, ex3, ey3, _OBJ_LABELS[0], _OBJ_LABELS[1], r"$\varepsilon_{n,x}$ vs $\varepsilon_{n,y}$"),
        (se2, ex2, se3, ex3, _OBJ_LABELS[2], _OBJ_LABELS[0], r"$\sigma_E$ vs $\varepsilon_{n,x}$"),
        (se2, ey2, se3, ey3, _OBJ_LABELS[2], _OBJ_LABELS[1], r"$\sigma_E$ vs $\varepsilon_{n,y}$"),
    ]
    for ax, (x2, y2, x3, y3, xl, yl, title) in zip(axes, pairs):
        ax.scatter(x2, y2, c="steelblue", s=40, alpha=0.7, marker="o", label="Phase 2")
        ax.scatter(x3, y3, c="seagreen", s=50, alpha=0.8, marker="^", label="Phase 3")
        ax.set_xlabel(xl, fontsize=12)
        ax.set_ylabel(yl, fontsize=12)
        ax.set_title(title, fontsize=13)
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend(fontsize=10)

    fig.suptitle("Pareto Front Comparison: Phase 2 vs Phase 3", fontsize=15, y=1.01)
    fig.tight_layout()
    _save(fig, output_path)
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# 15. Pareto verification comparison (bar chart)
# ═════════════════════════════════════════════════════════════════════════════
def plot_pareto_verification_comparison(
    verification_records: List[dict],
    output_path: Optional[Union[str, Path]] = None,
) -> plt.Figure:
    """Stored vs rerun ε_nx for each verified Pareto candidate."""
    fig, ax = plt.subplots(figsize=(10, 5))
    roles = [rec["role"] for rec in verification_records]
    stored = [rec["stored_emit_x_m_rad"] * _EMIT_SCALE for rec in verification_records]
    rerun = [rec["rerun_emit_x_m_rad"] * _EMIT_SCALE for rec in verification_records]

    x = np.arange(len(roles))
    w = 0.35
    ax.bar(x - w / 2, stored, w, label="Stored", color="steelblue", alpha=0.85)
    ax.bar(x + w / 2, rerun, w, label="Rerun", color="seagreen", alpha=0.85)

    ax.set_ylabel(_OBJ_LABELS[0], fontsize=12)
    ax.set_title("Pareto Candidate Verification (Stored vs Independent Rerun)", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(roles, rotation=15, ha="right", fontsize=10)
    ax.legend(fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.6, axis="y")
    fig.tight_layout()
    _save(fig, output_path)
    return fig
