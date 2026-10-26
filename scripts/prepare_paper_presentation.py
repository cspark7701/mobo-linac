#!/usr/bin/env python3
"""Prepare injector schematic and audit tables from existing production evidence.

Run after reproduce_paper.sh; this changes presentation only and launches no simulation.
The schematic is an ordered component diagram, not a drawing of magnet or RF lengths.
"""

import argparse
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from mobo_linac.config import load_config
from mobo_linac.metrics.latex import generate_verification_latex_table


def layout(template, output):
    text = template.read_text()

    def value(name):
        match = re.search(r"(?im)^\s*" + re.escape(name) + r"\s*=\s*([-+\d.eEdD]+)", text)
        if match is None:
            raise ValueError(f"Missing beamline location: {name}")
        return float(match[1].replace("D", "e").replace("d", "e"))

    elements = [(value("C_pos(1)"), "RF gun", r"$\phi_{\rm gun}$", "#DAA520", .45),
                (value("S_pos(1)"), "Solenoid", r"$B_{\rm sol}$", "#009E73", .28)]
    elements += [(value(f"C_pos({i+1})"), f"ACC{i}", "", "#56B4E9", .85) for i in range(1, 5)]
    elements += [(value(f"Q_pos({i})"), f"Q{i}", rf"$G_{{q{i}}}$", "#CC79A7", .20) for i in range(1, 3)]
    elements.sort()
    exit_z = value("ZSTOP")
    if elements[-1][0] >= exit_z:
        raise ValueError("An element starts beyond the exit plane")
    fig, ax = plt.subplots(figsize=(7.0, 2.45), layout="constrained")
    ax.annotate("", xy=(9.8, 0), xytext=(-.5, 0), arrowprops=dict(arrowstyle="->", color="0.35", lw=1.2))
    positions = {}
    for index, (_, label, variable, color, width) in enumerate(elements):
        x = index * 1.12
        positions[label] = x
        ax.add_patch(Rectangle((x-width/2, -.15), width, .30, facecolor=color, edgecolor="0.2", zorder=3))
        ax.text(x, .30 if index % 2 == 0 else .58, label, ha="center", fontsize=9)
        if variable:
            ax.text(x, -.43, variable, ha="center", fontsize=10)
    for first, last, label in [("ACC1", "ACC2", r"$\phi_{\rm acc1/2}$"),
                                ("ACC3", "ACC4", r"$\phi_{\rm acc3/4}$")]:
        left, right = positions[first], positions[last]
        ax.annotate("", xy=(left, -.63), xytext=(right, -.63),
                    arrowprops=dict(arrowstyle="|-|", color="0.4", lw=.8))
        ax.text((left+right)/2, -.83, label, ha="center", fontsize=10)
    ax.axvline(9.1, ymin=.18, ymax=.75, color="0.3", linestyle=":", linewidth=1)
    ax.text(9.1, .58, "Exit", ha="center", fontsize=9)
    ax.text(9.1, -.48, f"{exit_z:g} m", ha="center", fontsize=9)
    ax.text(4.1, 1.02, "200 MeV S-band electron injector linac", ha="center", fontsize=11)
    ax.text(4.1, -1.12, "Beam direction →     •     Component symbols not to scale", ha="center", fontsize=8, color="0.35")
    ax.set(xlim=(-.6, 9.9), ylim=(-1.25, 1.22))
    ax.axis("off")
    output.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png"):
        fig.savefig(output / f"injector_linac_layout.{suffix}", dpi=220)
    plt.close(fig)


def prepare(root, paper, template):
    layout(template, paper / "figures")
    survey = root / "05_operating_points/campaign"
    primary_config = load_config(root / "04_primary/benchmark/per_seed/constrained_qlognehvi_seed_42/config.json")
    survey_config = load_config(survey / "phase3_constrained/config.json")
    generate_verification_latex_table(root / "06_candidate_audit/verification/verification_summary.csv",
        paper / "audit_verification_table.tex", config=primary_config,
        caption="Independent nominal reruns of the representatives of the primary constraint-aware MOBO audit run.",
        label="tab:audit_verification")
    generate_verification_latex_table(survey / "analysis/verification/verification_summary.csv",
        paper / "verification_table.tex", config=survey_config,
        caption="Independent nominal reruns of the representatives of the constraint-aware MOBO survey.")
    # Reformat the caption of the regenerated survey table; all numeric cells are retained.
    table = paper / "results_table.tex"
    text = table.read_text()
    text = re.sub(r"\\caption\{[^\n]*\}", lambda _: r"\caption{Operating-point survey. Extrema use feasible observations; feasibility rates use all evaluations. The scalarized suite has five times the budget of either MOBO campaign. The fixed reporting reference is defined in the text.}", text, count=1)
    table.write_text(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-root", type=Path, default=Path("results/paper_production"))
    parser.add_argument("--paper-dir", type=Path, default=Path("docs/paper"))
    parser.add_argument("--template", type=Path, default=Path("astra.in"))
    args = parser.parse_args()
    prepare(args.production_root, args.paper_dir, args.template)
