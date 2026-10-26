#!/usr/bin/env python3
"""Draw measured feasible 3-objective fronts for every production seed/case.

No hypervolume reference, GP prediction, surface interpolation, or new simulation
is used. Static PNGs and a multipage vector PDF preserve the comparison for sharing.
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from mobo_linac.io.run_data import read_run_data
from mobo_linac.plotting.common import PlotSchema, nondominated_mask

ALGORITHMS = ("constrained_qlognehvi", "unconstrained_qlognehvi", "scalarized_bo")
LABELS = ("Constrained MOBO", "Unconstrained MOBO", "Scalarized BO")
STYLES = (("#0072B2", "o"), ("#D55E00", "^"), ("#009E73", "s"))


@dataclass
class Front:
    algorithm: str
    frame: pd.DataFrame


def pooled_front(frames, schema):
    """Nondominance of the union, computed jointly in all objective dimensions."""
    frame = pd.concat(frames, ignore_index=True)
    return frame.loc[nondominated_mask(frame, schema)].reset_index(drop=True)


def coordinates(frame, schema):
    return frame[[s.column for s in schema.objectives]].to_numpy(dtype=float) / np.asarray(
        [s.scale for s in schema.objectives])


def axis_label(spec):
    # Some recorded single-quoted YAML labels escape a backslash twice.
    return spec.label.replace("\\\\", "\\")


def limits(fronts, schema):
    values = np.concatenate([coordinates(f.frame, schema) for f in fronts if len(f.frame)])
    low, high = values.min(axis=0), values.max(axis=0)
    pad = np.maximum(high - low, np.maximum(np.abs(high), 1.) * .01) * .07
    return list(zip(low - pad, high + pad))


def paper_comparison(fronts, schema):
    """Readable portrait panels for a manuscript; all observed points stay visible."""
    fig, axes = plt.subplots(3, 1, figsize=(6.5, 8.5), layout="constrained")
    bounds = limits(fronts, schema)
    for ax, pair, letter in zip(axes, combinations(range(3), 2), "abc"):
        draw(ax, fronts, schema, pair=pair, bounds=bounds)
        ax.set_title(f"({letter})", loc="left", fontsize=11)
    handles = [Line2D([], [], linestyle="", color=color, marker=marker, label=label)
               for label, (color, marker) in zip(LABELS, STYLES)]
    axes[0].legend(handles=handles, fontsize=8, loc="best")
    return fig


def draw(ax, fronts, schema, is3d=False, pair=(0, 1), bounds=None, legend=False):
    for front in fronts:
        index = ALGORITHMS.index(front.algorithm)
        color, marker = STYLES[index]
        xyz = coordinates(front.frame, schema)
        kwargs = dict(color=color, marker=marker, s=30 if is3d else 38, alpha=.85,
                      edgecolors="white", linewidths=.35,
                      label=f"{LABELS[index]} (n={len(xyz)})")
        if is3d:
            ax.scatter(xyz[:, 0], xyz[:, 1], xyz[:, 2], depthshade=False, **kwargs)
        else:
            ax.scatter(xyz[:, pair[0]], xyz[:, pair[1]], **kwargs)
    if is3d:
        ax.set_xlabel(axis_label(schema.objectives[0]), labelpad=7)
        ax.set_ylabel(axis_label(schema.objectives[1]), labelpad=7)
        ax.set_zlabel(axis_label(schema.objectives[2]), labelpad=7)
        ax.view_init(elev=23, azim=35)
        ax.set_box_aspect((1, 1, .8))
        if bounds:
            ax.set_xlim(bounds[0]); ax.set_ylim(bounds[1]); ax.set_zlim(bounds[2])
    else:
        ax.set_xlabel(axis_label(schema.objectives[pair[0]]))
        ax.set_ylabel(axis_label(schema.objectives[pair[1]]))
        ax.grid(alpha=.25, linestyle=":")
        if bounds:
            ax.set_xlim(bounds[pair[0]]); ax.set_ylim(bounds[pair[1]])
    if legend:
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, fontsize=8, loc="best")


def comparison(fronts, schema, title, subtitle, two_d=False):
    fig = plt.figure(figsize=(16, 5) if two_d else (12, 9), layout="constrained")
    grid = fig.add_gridspec(1, 3) if two_d else fig.add_gridspec(2, 2)
    bound = limits(fronts, schema)
    if not two_d:
        ax = fig.add_subplot(grid[0, 0], projection="3d")
        draw(ax, fronts, schema, is3d=True, bounds=bound)
        ax.set_title("Three-objective view", fontsize=11)
    positions = [(0, 0), (0, 1), (0, 2)] if two_d else [(0, 1), (1, 0), (1, 1)]
    for position, pair in zip(positions, combinations(range(3), 2)):
        ax = fig.add_subplot(grid[position])
        draw(ax, fronts, schema, pair=pair, bounds=bound, legend=position == (0, 1))
        ax.set_title("Projection of the same 3D nondominated points", fontsize=10)
    fig.suptitle(title + "\n" + subtitle, fontsize=13)
    return fig


def pairwise_small_multiples(groups, schema, path, title, notes, columns):
    rows = int(np.ceil(len(groups) / columns))
    bounds = limits([f for _, fronts in groups for f in fronts], schema)
    for pair in combinations(range(3), 2):
        fig, axes = plt.subplots(rows, columns, figsize=(4.4 * columns, 3.7 * rows + 1), squeeze=False)
        for ax, (label, fronts) in zip(axes.flat, groups):
            draw(ax, fronts, schema, pair=pair, bounds=bounds)
            ax.set_title(label, fontsize=10)
        for ax in list(axes.flat)[len(groups):]:
            ax.set_visible(False)
        handles = [Line2D([], [], linestyle="", color=color, marker=marker, label=label)
                   for label, (color, marker) in zip(LABELS, STYLES)]
        fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False)
        fig.suptitle(title + "\n" + notes, fontsize=13)
        fig.tight_layout(rect=(0, .055, 1, .92))
        target = path.parent / f"{path.name}_pair_{pair[0]+1}{pair[1]+1}"
        fig.savefig(target.with_suffix(".png"), dpi=180)
        fig.savefig(target.with_suffix(".pdf"))
        plt.close(fig)


def small_multiples(groups, schema, path, title, notes, columns):
    rows = int(np.ceil(len(groups) / columns))
    fig = plt.figure(figsize=(4.5 * columns, 4.0 * rows + .7))
    bounds = limits([f for _, fronts in groups for f in fronts], schema)
    for i, (label, fronts) in enumerate(groups):
        ax = fig.add_subplot(rows, columns, i + 1, projection="3d")
        draw(ax, fronts, schema, is3d=True, bounds=bounds)
        counts = "/".join(str(len(f.frame)) for f in fronts)
        ax.set_title(f"{label}\nFront sizes C/U/S: {counts}", fontsize=10)
        ax.tick_params(labelsize=7)
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            axis.label.set_size(8)
    handles = [Line2D([], [], linestyle="", color=color, marker=marker, label=label)
               for label, (color, marker) in zip(LABELS, STYLES)]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=10)
    fig.suptitle(title + "\n" + notes, fontsize=13, y=.985)
    fig.subplots_adjust(left=.025, right=.97, top=.87 if rows == 1 else .89,
                        bottom=.10, wspace=.16, hspace=.25)
    fig.savefig(path.with_suffix(".png"), dpi=200, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def generate(root, output, two_d=False, paper_dir=None):
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Select a fresh comparison directory; existing outputs are preserved")
    manifest = pd.read_csv(root / "04_primary/benchmark/campaign_manifest.csv")
    seeds = sorted(manifest.seed.unique())
    if set(manifest.algorithm) != set(ALGORITHMS) or len(manifest) != len(seeds) * 3:
        raise ValueError("Require complete three-method paired benchmark manifest")
    output.mkdir(parents=True, exist_ok=True)
    schema = None
    all_rows, summaries = [], []

    def load(directory, algorithm, seed, scope, case):
        nonlocal schema
        run = read_run_data(directory)
        candidate_schema = PlotSchema.from_config(run.config)
        if len(candidate_schema.objectives) != 3:
            raise ValueError("This comparison requires three configured objectives")
        key = lambda s: [(x.column, x.scale, x.sign) for x in s.objectives]
        if schema is None:
            schema = candidate_schema
        elif key(schema) != key(candidate_schema):
            raise ValueError("Objective definitions/units differ between campaigns")
        frame = run.pareto(feasible=True).copy()
        if frame.empty:
            raise ValueError(f"No feasible Pareto observations in {directory}")
        frame["comparison_scope"] = scope
        frame["algorithm"] = algorithm
        frame["seed"] = int(seed)
        frame["case"] = case
        frame["source_run_directory"] = str(directory)
        all_rows.append(frame)
        summaries.append(dict(scope=scope, algorithm=algorithm, seed=int(seed), case=case,
                              evaluations=len(run.results), feasible=len(run.valid_results(feasible=True)),
                              pareto_size=len(frame)))
        return Front(algorithm, frame)

    primary, per_algorithm = [], defaultdict(list)
    for run_index, seed in enumerate(seeds, 1):
        fronts = []
        for algorithm in ALGORITHMS:
            directory = root / "04_primary/benchmark/per_seed" / f"{algorithm}_seed_{seed}"
            front = load(directory, algorithm, seed, "primary", "balanced" if algorithm == "scalarized_bo" else algorithm)
            fronts.append(front); per_algorithm[algorithm].append(front.frame)
        primary.append((f"Paired run {run_index}", fronts))
    pooled = [Front(a, pooled_front(per_algorithm[a], schema)) for a in ALGORITHMS]
    cases = pd.read_csv(root / "05_operating_points/campaign/phase1_scalarized/cases_summary.csv")
    records = sorted((root / "05_operating_points").glob("step_record_*.json"))
    base_seed = int(json.loads(records[-1].read_text())["parameters"]["seed"])
    survey_mobo = [load(root / "05_operating_points/campaign" / path, algorithm, base_seed, "survey", path)
                   for path, algorithm in [("phase3_constrained", ALGORITHMS[0]), ("phase2_unconstrained", ALGORITHMS[1])]]
    survey, scalar_fronts = [], []
    for row in cases.itertuples():
        front = load(root / "05_operating_points/campaign/phase1_scalarized" / row.case_id,
                     ALGORITHMS[2], row.seed, "survey", row.case_id)
        scalar_fronts.append(front.frame)
        survey.append((f"{row.case_id.replace('_', ' ')}", [*survey_mobo, front]))
    pooled_survey = [*survey_mobo, Front(ALGORITHMS[2], pooled_front(scalar_fronts, schema))]
    with PdfPages(output / "all_pareto_comparisons.pdf") as book:
        def page(fronts, title, subtitle, filename):
            fig = comparison(fronts, schema, title, subtitle, two_d=two_d)
            fig.savefig(output / f"{filename}.png", dpi=180)
            book.savefig(fig)
            plt.close(fig)

        page(pooled, "Primary comparison: pooled empirical feasible fronts",
             f"{len(seeds)} seeds × 160 evaluations per method; nondominance recomputed after pooling; smaller is better",
             "primary_pooled_fronts")
        for label, fronts in primary:
            page(fronts, "Primary comparison — " + label,
                 "160 evaluations per method; feasible 3-objective nondominance; no hypervolume reference filter",
                 "primary_" + label.lower().replace(" ", "_"))
        for label, fronts in survey:
            page(fronts, "Survey comparison — " + label,
                 "176 evaluations per campaign; independently initialized weight cases (descriptive, unpaired)",
                 "survey_" + label.split(" (")[0].replace(" ", "_"))
        page(pooled_survey, "Survey: descriptive aggregate of feasible fronts",
             "Scalarized: 5 × 176 = 880 evaluations; each MOBO: 176. Unequal budgets — no algorithm ranking.",
             "survey_pooled_fronts")
    if two_d:
        pairwise_small_multiples(primary, schema, output / "primary_all_seeds_2d",
                                "Primary comparison: all paired seeds", "160 evaluations per method/seed; shared axes; all objectives minimized", 5)
        pairwise_small_multiples(survey, schema, output / "survey_all_cases_2d",
                                "Survey comparison: all scalarized weight cases", "176 evaluations per campaign; independently initialized weight cases; shared axes", 3)
    else:
        small_multiples(primary, schema, output / "primary_all_seeds_3d",
                        "Primary comparison: all paired seeds", "160 evaluations per method/seed; shared axes; all objectives minimized", 5)
        small_multiples(survey, schema, output / "survey_all_cases_3d",
                        "Survey comparison: all five scalarized weight cases", "176 evaluations per campaign; independently initialized weight cases; shared axes", 3)
    if paper_dir is not None:
        paper_dir.mkdir(parents=True, exist_ok=True)
        for name, fronts in [("primary_pareto_points", pooled), ("survey_pareto_points", pooled_survey)]:
            fig = paper_comparison(fronts, schema)
            fig.savefig(paper_dir / f"{name}.pdf")
            fig.savefig(paper_dir / f"{name}.png", dpi=200)
            plt.close(fig)
    pd.concat(all_rows, ignore_index=True).to_csv(output / "all_per_run_pareto_points.csv", index=False)
    pd.DataFrame(summaries).to_csv(output / "campaign_front_summary.csv", index=False)
    for name, fronts in [("primary", pooled), ("survey", pooled_survey)]:
        pd.concat([f.frame for f in fronts], ignore_index=True).to_csv(output / f"{name}_pooled_pareto_points.csv", index=False)
    notes = {"two_dimensional_only": two_d, "projected_envelope_guides": False, "reference_filter_used": False, "objectives": [{"column": s.column, "display_label": axis_label(s),
             "physical_to_display_divisor": s.scale, "direction_sign": s.sign} for s in schema.objectives],
             "primary_pooled_front_sizes": {f.algorithm: len(f.frame) for f in pooled},
             "survey_pooled_front_sizes": {f.algorithm: len(f.frame) for f in pooled_survey},
             "run_count": len(summaries), "pdf_pages": 2 + len(primary) + len(survey),
             "interpretation": "Measured feasible Pareto approximations; no certified global front or interpolated surface. Pooled fronts do not describe a single campaign."}
    (output / "plot_metadata.json").write_text(json.dumps(notes, indent=2) + "\n")
    print(json.dumps(notes, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-root", type=Path, default=Path("results/paper_production"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--two-d", action="store_true", help="Only 2D objective pairs; omit every 3D axis")
    parser.add_argument("--paper-dir", type=Path, help="Also export portrait manuscript panels to this figure directory")
    args = parser.parse_args()
    generate(args.production_root, args.output_dir, two_d=args.two_d, paper_dir=args.paper_dir)
