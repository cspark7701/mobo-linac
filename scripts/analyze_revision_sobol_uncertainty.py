#!/usr/bin/env python3
"""C3-04: run-level uncertainty of the Sobol-arm and initial-design feasible fractions.

Points within one scrambled Sobol sequence are deliberately dependent, and the adaptive BO
observations of one campaign are not independent draws either. The independent units are the
ten matched groups (one scramble and one campaign each). This analysis therefore replaces the
pooled exact-binomial intervals of ``r2_space_filling_initial.csv`` and the manuscript's
Sobol-arm interval with run-level summaries: the ten per-run fractions, their mean, standard
deviation and range, and a percentile bootstrap over the ten runs. With ten replicates the
bootstrap interval is approximate and tends to be too narrow. The observed counts and the
paired group-bootstrap differences (``r2_sobol_arm_paired.csv``) are unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_revision_validation import N_INIT, SEEDS, feasible, load_ledgers

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
METHODS = ("sobol", "constrained_qlognehvi", "unconstrained_qlognehvi", "scalarized_bo")
BOOTSTRAP, RNG_SEED = 10000, 20261029


def per_run(ledgers: pd.DataFrame) -> pd.DataFrame:
    data = ledgers.assign(ok=feasible(ledgers) & ledgers.simulation_valid.astype(bool),
                          post=ledgers.index_in_run > N_INIT)
    rows = []
    for (arm, seed), group in data.groupby(["arm", "seed"]):
        if arm == METHODS[1]:  # the shared initial design, counted once per group
            initial = group[~group.post]
            rows.append({"population": "shared_initial_design", "seed": seed, "n": len(initial),
                         "feasible": int(initial.ok.sum()), "feasible_fraction": initial.ok.mean()})
        post = group[group.post]
        rows.append({"population": f"{arm}_post_initialization", "seed": seed, "n": len(post),
                     "feasible": int(post.ok.sum()), "feasible_fraction": post.ok.mean()})
    return pd.DataFrame(rows)


def summary(table: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    index = rng.integers(0, len(SEEDS), size=(BOOTSTRAP, len(SEEDS)))
    rows = []
    for population, group in table.groupby("population", sort=False):
        values = group.set_index("seed").loc[list(SEEDS), "feasible_fraction"].to_numpy(float)
        lo, hi = np.quantile(values[index].mean(axis=1), [0.025, 0.975])
        rows.append({"population": population, "runs": len(values), "n": int(group.n.sum()),
                     "feasible": int(group.feasible.sum()), "pooled_fraction": group.feasible.sum() / group.n.sum(),
                     "run_mean": values.mean(), "run_sd": values.std(ddof=1), "run_min": values.min(),
                     "run_max": values.max(), "bootstrap_lower": lo, "bootstrap_upper": hi})
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE)
    args = parser.parse_args(argv)
    ledgers = load_ledgers()
    table = per_run(ledgers[ledgers.arm.isin(METHODS)])
    result = summary(table)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "r3_sobol_uncertainty_runs.csv", index=False)
    result.to_csv(out / "r3_sobol_uncertainty_summary.csv", index=False)
    (out / "r3_sobol_uncertainty_metadata.json").write_text(json.dumps({
        "analysis": "C3-04 run-level uncertainty of feasible fractions (supersedes pooled binomial intervals)",
        "supersedes": ["ci_lower/ci_upper of r2_space_filling_initial.csv",
                       "the exact-binomial Sobol-arm interval of the round2 manuscript"],
        "sampling_unit": "matched group (one scramble and one campaign per group); ten groups",
        "bootstrap_resamples": BOOTSTRAP, "analysis_rng": RNG_SEED, "groups": list(SEEDS),
        "caveat": "Percentile bootstrap over ten runs; approximate and likely too narrow."}, indent=2) + "\n")
    print(result.round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
