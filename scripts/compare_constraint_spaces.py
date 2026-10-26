#!/usr/bin/env python3
"""Plot recorded constraint diagnostics for every production run and survey case.

Shading satisfies the displayed limits only; filled markers satisfy all channels.
Invalid evaluations remain counted but are never assigned artificial coordinates.
"""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
import numpy as np
import pandas as pd

from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS
from mobo_linac.io.results import results_to_dataframe
from mobo_linac.io.run_data import read_run_data
from mobo_linac.plotting.common import PlotSchema

ALGORITHMS = ("constrained_qlognehvi", "unconstrained_qlognehvi", "scalarized_bo")
LABELS = ("Constrained MOBO", "Unconstrained MOBO", "Scalarized BO")
STYLES = (("#0072B2", "o"), ("#D55E00", "^"), ("#009E73", "s"))
PAIRS = (("sigma_x_m", "sigma_y_m", "Beam sizes"),
         ("sigma_xp_rad", "sigma_yp_rad", "Beam divergences"),
         ("mean_kinetic_energy_eV", "sigma_z_m", "Energy and bunch length"),
         ("mean_kinetic_energy_eV", "transmission_fraction", "Energy and transmission"))
PHYSICAL = {channel.name: channel for channel in DIAGNOSTIC_CHANNELS}


@dataclass
class Campaign:
    algorithm: str
    frame: pd.DataFrame


def measured_constraints(frame, schema):
    """Validate measured flags against inclusive configured limits; never impute."""
    valid = frame.loc[frame.simulation_valid == True].copy()
    masks = {}
    for spec in schema.constraints:
        values = valid[spec.column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"Missing/nonfinite valid diagnostic: {spec.column}")
        mask = np.ones(len(valid), dtype=bool)
        if spec.lower is not None:
            mask &= values >= spec.lower
        if spec.upper is not None:
            mask &= values <= spec.upper
        masks[spec.column] = mask
    joint = np.logical_and.reduce(list(masks.values()))
    if not np.array_equal(joint, valid.physically_feasible.to_numpy()):
        raise ValueError("Recorded feasibility conflicts with configured diagnostic limits")
    return valid, masks


def display_domain(spec, data_bounds):
    """Clip the displayed acceptance rectangle to limits and physical domain."""
    channel = PHYSICAL[spec.column]
    low, high = data_bounds
    for value in (spec.lower, channel.physical_minimum):
        if value is not None:
            low = max(low, value / spec.scale)
    for value in (spec.upper, channel.physical_maximum):
        if value is not None:
            high = min(high, value / spec.scale)
    return low, high


def plot_bounds(campaigns, schema):
    bounds = {}
    frame = pd.concat([c.frame for c in campaigns], ignore_index=True)
    for spec in schema.constraints:
        values = frame[spec.column].to_numpy(dtype=float) / spec.scale
        anchors = [x / spec.scale for x in (spec.lower, spec.upper) if x is not None]
        # Physical transmission endpoints keep a constant-100% series legible.
        if PHYSICAL[spec.column].physical_maximum is not None:
            anchors.append(PHYSICAL[spec.column].physical_maximum / spec.scale)
        finite = np.r_[values[np.isfinite(values)], anchors]
        if not len(finite):
            raise ValueError(f"No measured diagnostics or limits for {spec.column}")
        low, high = finite.min(), finite.max()
        pad = .06 * max(high-low, abs(high)*.01, .01)
        bounds[spec.column] = (max(0., low-pad), high+pad)
    return bounds


def constraint_figure(campaigns, schema, title=None, bounds=None):
    """Show all measured points, displayed acceptance boxes and joint feasibility."""
    specs = {s.column: s for s in schema.constraints}
    bounds = bounds or plot_bounds(campaigns, schema)
    fig, axes = plt.subplots(2, 2, figsize=(7.5, 6.4))
    for ax, (xname, yname, label), letter in zip(axes.flat, PAIRS, "abcd"):
        x, y = specs[xname], specs[yname]
        ax.set(xlim=bounds[xname], ylim=bounds[yname],
               xlabel=f"{x.column}", ylabel=f"{y.column}")
        ax.set_facecolor("#f7eded")
        left, right = display_domain(x, bounds[xname])
        bottom, top = display_domain(y, bounds[yname])
        if right >= left and top >= bottom:
            ax.add_patch(Rectangle((left, bottom), right-left, top-bottom,
                                   facecolor="#d8efdc", edgecolor="#438b55", linewidth=.8, zorder=0))
        for campaign in campaigns:
            color, marker = STYLES[ALGORITHMS.index(campaign.algorithm)]
            frame = campaign.frame
            feasible = frame.physically_feasible.to_numpy(dtype=bool)
            for mask, filled in [(~feasible, False), (feasible, True)]:
                ax.scatter(frame.loc[mask, xname]/x.scale, frame.loc[mask, yname]/y.scale,
                           marker=marker, s=13 if filled else 10, linewidths=.45,
                           facecolors=color if filled else "none", edgecolors=color,
                           alpha=.62 if filled else .22, zorder=3 if filled else 2)
        ax.set_xlabel(f"{PHYSICAL[xname].label} [{PHYSICAL[xname].display_unit}]", fontsize=9)
        ax.set_ylabel(f"{PHYSICAL[yname].label} [{PHYSICAL[yname].display_unit}]", fontsize=9)
        ax.set_title(f"({letter}) {label}", fontsize=10)
        ax.set_axisbelow(True)
        ax.grid(alpha=.4, linestyle=":", linewidth=.6)
        ax.tick_params(labelsize=8)
    handles = [Line2D([], [], color=c, marker=m, linestyle="", label=label)
               for label, (c, m) in zip(LABELS, STYLES)]
    handles += [Line2D([], [], color="0.25", marker="o", linestyle="", label="All constraints pass"),
                Line2D([], [], color="0.25", marker="o", markerfacecolor="none", linestyle="", label="At least one fails"),
                Patch(facecolor="#d8efdc", edgecolor="#438b55", label="Shown limits satisfied")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, .95 if title else 1.0),
               ncol=3, frameon=False, fontsize=8)
    if title:
        fig.suptitle(title, fontsize=12, y=.995)
    fig.subplots_adjust(top=.80 if title else .85, bottom=.09, left=.10, right=.98, hspace=.38, wspace=.28)
    return fig


def generate(root, output, paper_dir=None):
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Select a fresh output directory; existing evidence is preserved")
    manifest = pd.read_csv(root / "04_primary/benchmark/campaign_manifest.csv")
    if set(manifest.algorithm) != set(ALGORITHMS) or manifest.duplicated(["algorithm", "seed"]).any():
        raise ValueError("Require a unique, complete three-algorithm primary manifest")
    seeds = sorted(manifest.seed.unique())
    if len(manifest) != 3*len(seeds):
        raise ValueError("Require every paired primary campaign")
    inventory = []
    for i, seed in enumerate(seeds, 1):
        for algorithm in ALGORITHMS:
            inventory.append(("primary", f"Paired run {i}", f"primary_run_{i}_{algorithm}", algorithm,
                              root/"04_primary/benchmark/per_seed"/f"{algorithm}_seed_{seed}"))
    survey = root/"05_operating_points/campaign"
    for row in pd.read_csv(survey/"phase1_scalarized/cases_summary.csv").itertuples():
        inventory.append(("survey", row.case_id.replace("_", " "), f"survey_{row.case_id}",
                          ALGORITHMS[2], survey/"phase1_scalarized"/row.case_id))
    for path, algorithm in [("phase3_constrained", ALGORITHMS[0]), ("phase2_unconstrained", ALGORITHMS[1])]:
        inventory.append(("survey", LABELS[ALGORITHMS.index(algorithm)], f"survey_{algorithm}", algorithm, survey/path))
    schema, data, summary, frames, sources = None, [], [], [], []
    for scope, label, filename, algorithm, directory in inventory:
        run = read_run_data(directory)
        candidate = PlotSchema.from_config(run.config)
        key = lambda s: [(x.column, x.scale, x.lower, x.upper) for x in s.constraints]
        if schema is None:
            schema = candidate
        elif key(schema) != key(candidate):
            raise ValueError("Constraint definitions/units differ between campaigns")
        frame = results_to_dataframe(run.results, run.config)
        valid, masks = measured_constraints(frame, schema)
        if valid.empty:
            raise ValueError(f"No measured constraint coordinates: {directory}")
        valid["scope"], valid["algorithm"], valid["case_label"] = scope, algorithm, label
        valid["source_run_directory"] = str(directory)
        frames.append(valid[["run_id", "evaluation_id", "scope", "algorithm", "case_label", "source_run_directory",
                             "simulation_valid", "physically_feasible", *[s.column for s in schema.constraints]]])
        campaign = Campaign(algorithm, valid)
        data.append((scope, label, filename, campaign))
        summary.append(dict(scope=scope, case_label=label, algorithm=algorithm, total=len(frame),
                            valid=len(valid), invalid=len(frame)-len(valid), feasible=int(valid.physically_feasible.sum()),
                            **{name+"_passes": int(mask.sum()) for name, mask in masks.items()}))
        sources.append(str(directory))
    output.mkdir(parents=True, exist_ok=True)
    with PdfPages(output/"all_campaign_constraint_spaces.pdf") as book:
        for scope, label, filename, campaign in data:
            fig = constraint_figure([campaign], schema, f"{scope.capitalize()}: {label} — {LABELS[ALGORITHMS.index(campaign.algorithm)]}")
            fig.savefig(output/f"{filename}.png", dpi=170)
            book.savefig(fig)
            plt.close(fig)
    with PdfPages(output/"all_constraint_comparisons.pdf") as book:
        def page(campaigns, title, filename, paper=False):
            fig = constraint_figure(campaigns, schema, title)
            fig.savefig(output/f"{filename}.png", dpi=180)
            book.savefig(fig)
            plt.close(fig)
            if paper and paper_dir is not None:
                paper_dir.mkdir(parents=True, exist_ok=True)
                fig = constraint_figure(campaigns, schema)
                for ext in ("png", "pdf"):
                    fig.savefig(paper_dir/f"{filename}.{ext}", dpi=220)
                plt.close(fig)
        for scope in ("primary", "survey"):
            selected = [(label, c) for s, label, _, c in data if s == scope]
            pooled = [Campaign(a, pd.concat([c.frame for _, c in selected if c.algorithm == a], ignore_index=True)) for a in ALGORITHMS]
            page(pooled, f"{scope.capitalize()}: all evaluated settings" + (" (unequal survey budgets)" if scope=="survey" else ""),
                 f"{scope}_constraint_spaces", paper=True)
        for i in range(1, len(seeds)+1):
            page([c for scope, label, _, c in data if scope=="primary" and label==f"Paired run {i}"],
                 f"Primary: paired run {i}", f"primary_comparison_run_{i}")
        mobo = [c for scope, _, _, c in data if scope=="survey" and c.algorithm!=ALGORITHMS[2]]
        for scope, label, filename, c in data:
            if scope=="survey" and c.algorithm==ALGORITHMS[2]:
                page([*mobo,c], f"Survey: {label} (independent initializations)", filename+"_comparison")
    pd.concat(frames, ignore_index=True).to_csv(output/"constraint_observations.csv", index=False)
    pd.DataFrame(summary).to_csv(output/"campaign_constraint_summary.csv", index=False)
    metadata = {"campaign_count": len(data), "campaign_pdf_pages": len(data),
                "comparison_pdf_pages": 2+len(seeds)+sum(s=="survey" and c.algorithm==ALGORITHMS[2] for s,_,_,c in data),
                "constraints": [dict(column=s.column, display_scale=s.scale, lower=s.lower, upper=s.upper) for s in schema.constraints],
                "source_run_directories": sources,
                "interpretation": "Shading satisfies shown limits only. Filled markers satisfy all constraints; open markers fail at least one. All numerically valid observations are shown; invalid attempts remain counted without invented coordinates. Survey pooling has unequal budgets."}
    (output/"plot_metadata.json").write_text(json.dumps(metadata, indent=2)+"\n")
    (output/"README.md").write_text("# Constraint-space comparisons\n\n"+metadata["interpretation"]+"\n\nEach campaign has its own PNG and PDF page. The comparison PDF contains pooled primary/survey views, every paired primary run and every scalarization case. Actual seed values remain in source records rather than plot labels.\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-root", type=Path, default=Path("results/paper_production"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--paper-dir", type=Path)
    args = parser.parse_args()
    generate(args.production_root, args.output_dir, args.paper_dir)
