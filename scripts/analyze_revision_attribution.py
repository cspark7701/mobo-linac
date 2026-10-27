#!/usr/bin/env python3
"""C2-02: attribute the feasible-sampling gap to violated constraint channels.

Descriptive analysis of the immutable primary evaluations. Each post-initialization
evaluation is classified under the production profile into one exclusive category of
violated channel groups. Because feasible fraction = 1 - sum of infeasible category shares,
the paired feasible-fraction gap between two methods divides exactly among the categories.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("constrained_qlognehvi", "unconstrained_qlognehvi", "scalarized_bo")
LABELS = ("Constrained MOBO", "Unconstrained MOBO", "Scalarized BO")
COLORS = ("#0072B2", "#D55E00", "#009E73")
MARKERS = ("o", "^", "s")
SEEDS = tuple(range(42, 52))
N_INITIAL, BATCH, BUDGET = 16, 8, 160
# Upper quarter of the inherited ACC3/ACC4 interval [279.04807728, 341.05876112] deg.
ACC34_LOW, ACC34_HIGH = 279.04807728, 341.05876112
ACC34_UPPER_QUARTER = ACC34_LOW + 0.75 * (ACC34_HIGH - ACC34_LOW)
CATEGORIES = ("energy_only", "transverse_only", "bunch_length_only", "energy_transverse",
              "energy_bunch_length", "transverse_bunch_length", "energy_transverse_bunch_length",
              "transmission")
CATEGORY_LABELS = {"energy_only": "Energy only", "transverse_only": "Transverse only",
                   "bunch_length_only": "Bunch length only", "energy_transverse": "Energy + transverse",
                   "energy_bunch_length": "Energy + bunch length",
                   "transverse_bunch_length": "Transverse + bunch length",
                   "energy_transverse_bunch_length": "All three groups", "transmission": "Transmission"}
BOOTSTRAP, RNG_SEED = 10000, 20261027


def violations(df: pd.DataFrame, limits: dict) -> pd.DataFrame:
    """Production-profile channel-group violations of valid evaluations."""
    energy = ((df.mean_kinetic_energy_eV < limits["min_mean_kinetic_energy_eV"])
              | (df.mean_kinetic_energy_eV > limits["max_mean_kinetic_energy_eV"]))
    transverse = ((df.sigma_x_m > limits["max_sigma_x_m"]) | (df.sigma_y_m > limits["max_sigma_y_m"])
                  | (df.sigma_xp_rad > limits["max_sigma_xp_rad"]) | (df.sigma_yp_rad > limits["max_sigma_yp_rad"]))
    bunch = df.sigma_z_m > limits["max_sigma_z_m"]
    transmission = df.transmission_fraction < limits["min_transmission"]
    return pd.DataFrame({"energy": energy, "transverse": transverse, "bunch_length": bunch,
                         "transmission": transmission})


def categorize(v: pd.DataFrame) -> pd.Series:
    """One exclusive category per infeasible evaluation; feasible rows are 'feasible'."""
    out = pd.Series("feasible", index=v.index, dtype=object)
    out[v.transmission] = "transmission"
    rest = ~v.transmission
    e, t, b = v.energy & rest, v.transverse & rest, v.bunch_length & rest
    out[e & ~t & ~b] = "energy_only"
    out[~e & t & ~b & rest] = "transverse_only"
    out[~e & ~t & b & rest] = "bunch_length_only"
    out[e & t & ~b] = "energy_transverse"
    out[e & ~t & b] = "energy_bunch_length"
    out[~e & t & b & rest] = "transverse_bunch_length"
    out[e & t & b] = "energy_transverse_bunch_length"
    return out


def load_runs(root: Path):
    runs, manifest = {}, []
    for method in METHODS:
        for seed in SEEDS:
            run = root / f"{method}_seed_{seed}"
            path = run / "evaluations.csv"
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            marker = json.loads((run / "run_complete.json").read_text())
            if digest != marker["artifacts"]["evaluations.csv"]:
                raise ValueError(f"Checksum mismatch for {path}")
            df = pd.read_csv(path)
            if len(df) != BUDGET or not df.simulation_valid.all():
                raise ValueError(f"Unexpected ledger {path}")
            df["index"] = df.evaluation_id.str.extract(r"(\d+)$")[0].astype(int)
            df = df.sort_values("index").reset_index(drop=True)
            if not (df["index"].to_numpy() == np.arange(1, BUDGET + 1)).all():
                raise ValueError(f"Evaluation identities are not 1..{BUDGET} in {path}")
            df["batch"] = np.where(df["index"] <= N_INITIAL, 0, (df["index"] - N_INITIAL - 1) // BATCH + 1)
            limits = json.loads((run / "config.json").read_text())["constraints"]
            v = violations(df, limits)
            df["category"] = categorize(v)
            if not (df.category.eq("feasible") == df.physically_feasible.astype(bool)).all():
                raise ValueError(f"Recomputed feasibility disagrees with recorded labels in {path}")
            df = pd.concat([df, v.add_prefix("violates_")], axis=1)
            runs[(method, seed)] = df
            manifest.append({"run": run.name, "sha256": digest})
    return runs, manifest


def per_run(runs) -> pd.DataFrame:
    rows = []
    for (method, seed), df in runs.items():
        post = df[df.batch > 0]
        energy_ok = post[~post.violates_energy]
        row = {"method": method, "seed": seed, "n_post": len(post),
               "feasible_fraction": float((post.category == "feasible").mean()),
               "energy_violation_fraction": float(post.violates_energy.mean()),
               "transverse_violation_fraction": float(post.violates_transverse.mean()),
               "bunch_length_violation_fraction": float(post.violates_bunch_length.mean()),
               "acc34_upper_quarter_fraction": float((post.acc3_acc4_phase_deg > ACC34_UPPER_QUARTER).mean()),
               "acc34_upper_quarter_energy_violation_fraction":
                   float(post[post.acc3_acc4_phase_deg > ACC34_UPPER_QUARTER].violates_energy.mean())
                   if (post.acc3_acc4_phase_deg > ACC34_UPPER_QUARTER).any() else float("nan"),
               "n_energy_ok": len(energy_ok),
               "conditional_feasible_fraction_given_energy":
                   float((energy_ok.category == "feasible").mean()) if len(energy_ok) else float("nan")}
        for category in CATEGORIES:
            row[f"share_{category}"] = float((post.category == category).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def per_batch(runs) -> pd.DataFrame:
    rows = []
    for (method, seed), df in runs.items():
        for batch, group in df.groupby("batch"):
            rows.append({"method": method, "seed": seed, "batch": int(batch),
                         "acc34_upper_quarter_fraction": float((group.acc3_acc4_phase_deg > ACC34_UPPER_QUARTER).mean()),
                         "energy_violation_fraction": float(group.violates_energy.mean()),
                         "transverse_violation_fraction": float(group.violates_transverse.mean()),
                         "feasible_fraction": float((group.category == "feasible").mean())})
    return pd.DataFrame(rows)


def paired(run_table: pd.DataFrame, metrics) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    index = rng.integers(0, len(SEEDS), size=(BOOTSTRAP, len(SEEDS)))
    rows = []
    for metric in metrics:
        wide = run_table.pivot(index="seed", columns="method", values=metric).loc[list(SEEDS)]
        for baseline in METHODS[1:]:
            d = (wide[METHODS[0]] - wide[baseline]).to_numpy(float)
            if not np.isfinite(d).all():
                raise ValueError(f"Nonfinite paired difference for {metric}")
            lo, hi = np.quantile(d[index].mean(axis=1), [0.025, 0.975])
            rows.append({"metric": metric, "first_method": METHODS[0], "second_method": baseline,
                         "mean_difference": float(d.mean()), "ci_lower": float(lo), "ci_upper": float(hi),
                         "n_positive": int((d > 0).sum()), "n_negative": int((d < 0).sum()),
                         "n_zero": int((d == 0).sum())})
    return pd.DataFrame(rows)


def gap_decomposition(run_table: pd.DataFrame) -> pd.DataFrame:
    """Mean paired gap in feasible fraction and each category's exact contribution to it."""
    rows = []
    for baseline in METHODS[1:]:
        a = run_table[run_table.method == METHODS[0]].set_index("seed").loc[list(SEEDS)]
        b = run_table[run_table.method == baseline].set_index("seed").loc[list(SEEDS)]
        gap = float((a.feasible_fraction - b.feasible_fraction).mean())
        total = 0.0
        for category in CATEGORIES:
            contribution = float((b[f"share_{category}"] - a[f"share_{category}"]).mean())
            total += contribution
            rows.append({"baseline": baseline, "category": category, "contribution": contribution,
                         "fraction_of_gap": contribution / gap if gap else float("nan"), "gap": gap})
        if not np.isclose(total, gap, atol=1e-12):
            raise AssertionError("Category contributions do not sum to the feasible-fraction gap")
    return pd.DataFrame(rows)


def figure(batch_table: pd.DataFrame, run_table: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.9), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    for method, label, color, marker in zip(METHODS, LABELS, COLORS, MARKERS):
        table = batch_table[batch_table.method == method].pivot(index="batch", columns="seed",
                                                                 values="acc34_upper_quarter_fraction")
        # Cumulative occupancy after each batch; batch 0 holds 16 points, later batches 8.
        weights = np.where(table.index.to_numpy() == 0, N_INITIAL, BATCH)[:, None]
        cumulative = (table.to_numpy() * weights).cumsum(axis=0) / weights.cumsum(axis=0)
        x = N_INITIAL + BATCH * table.index.to_numpy()
        ax.fill_between(x, np.quantile(cumulative, 0.25, axis=1), np.quantile(cumulative, 0.75, axis=1),
                        color=color, alpha=0.15)
        ax.plot(x, np.median(cumulative, axis=1), color=color, marker=marker, ms=4, lw=1.4, label=label)
    ax.set(xlabel="Evaluations per campaign", ylabel="Cumulative fraction in upper ACC3/4 quarter",
           xlim=(N_INITIAL, BUDGET), ylim=(0, 0.4))
    ax.grid(alpha=0.35, ls=":")
    ax.legend(fontsize=8)
    ax.text(0.02, 0.97, "(a)", transform=ax.transAxes, va="top", fontsize=10)
    ax = axes[1]
    styles = {"energy_only": ("0.88", "///"), "energy_transverse": ("0.68", "///"),
              "energy_bunch_length": ("0.5", "///"), "energy_transverse_bunch_length": ("0.3", "///"),
              "transverse_only": ("0.8", ""), "bunch_length_only": ("0.6", ""),
              "transverse_bunch_length": ("0.4", ""), "transmission": ("0.15", "")}
    order = ("energy_only", "energy_transverse", "energy_bunch_length", "energy_transverse_bunch_length",
             "transverse_only", "transverse_bunch_length", "bunch_length_only", "transmission")
    bottom = np.zeros(len(METHODS))
    handles = []
    for category in order:
        heights = np.array([run_table[run_table.method == m][f"share_{category}"].mean() for m in METHODS])
        if not heights.any():
            continue
        shade, hatch = styles[category]
        handles.append(ax.bar(range(len(METHODS)), heights, bottom=bottom, color=shade, hatch=hatch,
                              edgecolor="white", linewidth=0.6, label=CATEGORY_LABELS[category]))
        bottom += heights
    feasible = np.array([run_table[run_table.method == m].feasible_fraction.mean() for m in METHODS])
    ax.bar(range(len(METHODS)), feasible, bottom=bottom, color=COLORS, edgecolor="white")
    handles.append(Patch(facecolor="white", edgecolor="0.3", label="Feasible (method colour)"))
    ax.set_xticks(range(len(METHODS)), [label.replace(" ", "\n", 1) for label in LABELS], fontsize=8)
    ax.set(ylabel="Share of post-initialization evaluations", ylim=(0, 1))
    ax.legend(handles=handles, fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0),
              title="Hatched: energy band violated", title_fontsize=7)
    ax.text(0.02, 0.97, "(b)", transform=ax.transAxes, va="top", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


def analyze(root: Path, out: Path, figure_path: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    runs, manifest = load_runs(root)
    run_table, batch_table = per_run(runs), per_batch(runs)
    metrics = ("feasible_fraction", "energy_violation_fraction", "transverse_violation_fraction",
               "bunch_length_violation_fraction", "acc34_upper_quarter_fraction",
               "conditional_feasible_fraction_given_energy")
    effects, decomposition = paired(run_table, metrics), gap_decomposition(run_table)
    run_table.to_csv(out / "r2_attribution_runs.csv", index=False)
    batch_table.to_csv(out / "r2_attribution_batches.csv", index=False)
    effects.to_csv(out / "r2_attribution_paired.csv", index=False)
    decomposition.to_csv(out / "r2_attribution_gap.csv", index=False)
    figure(batch_table, run_table, figure_path)
    summary = {
        "analysis": "C2-02 descriptive attribution; production profile; post-initialization evaluations 17-160",
        "acc34_upper_quarter_deg": [ACC34_UPPER_QUARTER, ACC34_HIGH],
        "bootstrap_resamples": BOOTSTRAP, "analysis_rng": RNG_SEED, "groups": list(SEEDS),
        "medians": run_table.groupby("method")[list(metrics)].median().to_dict(),
        "inputs": manifest,
    }
    (out / "r2_attribution_metadata.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "results/paper_production/04_primary/benchmark/per_seed")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/paper/revisions/evidence")
    parser.add_argument("--figure", type=Path, default=ROOT / "docs/paper/figures/revision_attribution.pdf")
    args = parser.parse_args(argv)
    analyze(args.root, args.output, args.figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
