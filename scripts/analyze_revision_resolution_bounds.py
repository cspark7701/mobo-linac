#!/usr/bin/env python3
"""C3-02: feasible fractions of the primary comparison under the measured refinement shifts.

The archived diagnostics of the 4,800 primary evaluations and the 1,600 Sobol-arm evaluations
are reclassified under the production profile after bounding shifts taken from the C2-12
refinement check (``evidence/r2_convergence_summary.csv``): a common scale factor on the beam
sizes and divergences (down to the largest observed reduction), a bunch-length change of
+-1 % and a mean-energy shift of +-0.05 MeV. Transmission is unchanged. The shifts bound
the changes seen at ten settings; they are not a per-point refinement model or an error bound.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from revision_ledgers import N_INIT, SEEDS, feasible, load_ledgers

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
SUMMARY = EVIDENCE / "r2_convergence_summary.csv"
METHODS = ("constrained_qlognehvi", "unconstrained_qlognehvi", "scalarized_bo", "sobol")
PAIRS = (("constrained_qlognehvi", "unconstrained_qlognehvi"), ("constrained_qlognehvi", "scalarized_bo"),
         ("constrained_qlognehvi", "sobol"), ("unconstrained_qlognehvi", "sobol"), ("scalarized_bo", "sobol"))
BOOTSTRAP, RNG_SEED = 10000, 20261029
BUNCH_SCALES = (0.99, 1.0, 1.01)
ENERGY_SHIFTS_EV = (-0.05e6, 0.0, 0.05e6)


def size_scales(summary: pd.DataFrame) -> tuple:
    """1.0, the midpoint and the largest observed fine-level reduction of sizes and divergences."""
    rows = summary[summary.quantity.isin(["sigma_x_m", "sigma_y_m", "sigma_xp_rad", "sigma_yp_rad"])]
    smallest = round(1.0 + float(rows.delta_rel_fine.min()), 2)
    return (smallest, round((1.0 + smallest) / 2, 2), 1.0)


def run_table(ledgers: pd.DataFrame, scales: tuple) -> pd.DataFrame:
    data = ledgers[ledgers.arm.isin(METHODS)].copy()
    valid = data.simulation_valid.astype(bool)
    post = data.index_in_run > N_INIT
    rows = []
    for size, bunch, energy in itertools.product(scales, BUNCH_SCALES, ENERGY_SHIFTS_EV):
        ok = feasible(data, size, bunch, energy) & valid  # invalid evaluations stay infeasible
        frame = data.assign(ok=ok, post=post)
        for (arm, seed), group in frame.groupby(["arm", "seed"]):
            rows.append({"size_scale": size, "bunch_scale": bunch, "energy_shift_MeV": energy / 1e6,
                         "method": arm, "seed": seed, "feasible_fraction": group.ok.mean(),
                         "post_init_feasible_fraction": group.ok[group.post].mean()})
    return pd.DataFrame(rows)


def paired(table: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    index = rng.integers(0, len(SEEDS), size=(BOOTSTRAP, len(SEEDS)))
    rows = []
    keys = ["size_scale", "bunch_scale", "energy_shift_MeV"]
    for shift, group in table.groupby(keys):
        for metric in ("feasible_fraction", "post_init_feasible_fraction"):
            wide = group.pivot(index="seed", columns="method", values=metric).loc[list(SEEDS)]
            for first, second in PAIRS:
                if second == "sobol" and metric == "feasible_fraction":
                    continue  # the Sobol arm shares the initial design; compare after initialization
                d = (wide[first] - wide[second]).to_numpy(float)
                lo, hi = np.quantile(d[index].mean(axis=1), [0.025, 0.975])
                rows.append({**dict(zip(keys, shift)), "metric": metric, "first_method": first,
                             "second_method": second, "mean_difference": float(d.mean()),
                             "ci_lower": float(lo), "ci_upper": float(hi),
                             "n_positive": int((d > 0).sum()), "n_negative": int((d < 0).sum())})
    return pd.DataFrame(rows)


def summarize(table: pd.DataFrame, pairs: pd.DataFrame) -> dict:
    medians = table.groupby(["size_scale", "bunch_scale", "energy_shift_MeV", "method"]).feasible_fraction.median()
    by_method = medians.groupby("method").agg(["min", "max"]).round(4)
    nominal = medians.xs((1.0, 1.0, 0.0), level=[0, 1, 2]).round(4)
    gaps = pairs[pairs.metric == "post_init_feasible_fraction"].groupby(["first_method", "second_method"])
    return {"median_feasible_fraction_nominal": nominal.to_dict(),
            "median_feasible_fraction_range": {m: by_method.loc[m].tolist() for m in by_method.index},
            "post_init_paired_difference_range": {f"{a} - {b}": [round(g.mean_difference.min(), 4),
                                                                 round(g.mean_difference.max(), 4)]
                                                  for (a, b), g in gaps},
            "post_init_smallest_ci_lower": {f"{a} - {b}": round(g.ci_lower.min(), 4) for (a, b), g in gaps},
            "all_groups_positive_post_init": bool((pairs[pairs.metric == "post_init_feasible_fraction"]
                                                   .n_positive == len(SEEDS)).all())}


def analyze(ledgers: pd.DataFrame, summary: pd.DataFrame):
    scales = size_scales(summary)
    table = run_table(ledgers, scales)
    pairs = paired(table)
    return table, pairs, scales, summarize(table, pairs)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE)
    args = parser.parse_args(argv)
    table, pairs, scales, result = analyze(load_ledgers(), pd.read_csv(SUMMARY))
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "r3_resolution_bounds_runs.csv", index=False)
    pairs.to_csv(out / "r3_resolution_bounds_paired.csv", index=False)
    (out / "r3_resolution_bounds_metadata.json").write_text(json.dumps({
        "analysis": "C3-02 feasible fractions under the C2-12 refinement bounds (post hoc)",
        "source": "docs/paper/revisions/evidence/r2_convergence_summary.csv",
        "size_scales": list(scales), "bunch_scales": list(BUNCH_SCALES),
        "energy_shifts_MeV": [e / 1e6 for e in ENERGY_SHIFTS_EV], "transmission": "unchanged",
        "bootstrap_resamples": BOOTSTRAP, "analysis_rng": RNG_SEED, "groups": list(SEEDS),
        "note": "Bounds from ten settings, not a per-point refinement model or an error bound.",
        **result}, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
