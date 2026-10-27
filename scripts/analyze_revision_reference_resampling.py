#!/usr/bin/env python3
"""C2-06: paired quality effects with the empirical reference rebuilt inside each resample.

The round1 C03/C04 indicators use one empirical reference front (and HV reference point)
estimated from all tested runs, then treat it as fixed in the paired bootstrap. Here the
matched groups are resampled with replacement and, inside every resample, the reference
front and the HV reference (pooled nadir + 25 % of span) are rebuilt from the resampled
groups only. The resulting percentile intervals for mean paired differences therefore
include reference-construction uncertainty. The estimand is the mean paired difference of
terminal indicators over matched groups; no p-value is derived from this procedure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_revision_fronts import (  # noqa: E402
    METHODS, additive_epsilon, hypervolume, igd_plus, load_runs, nondominated,
)

ENDPOINTS = ("epsilon", "igd_plus", "hv_25")
RESAMPLES, RNG_SEED = 2000, 20261027


def indicators(fronts: dict, groups: list) -> dict:
    """Terminal epsilon, IGD+ and HV(25 %) per (method, position) for one group sample."""
    reference = nondominated(np.vstack([fronts[(m, g)] for g in groups for m in METHODS if len(fronts[(m, g)])]))
    nadir, span = reference.max(0), np.ptp(reference, axis=0)
    hv_reference = nadir + 0.25 * span
    out = {}
    for position, group in enumerate(groups):
        for method in METHODS:
            front = fronts[(method, group)]
            out[(method, position)] = (additive_epsilon(front, reference), igd_plus(front, reference),
                                       hypervolume(front, hv_reference))
    return out


def mean_differences(values: dict, n: int) -> dict:
    result = {}
    for first, second in combinations(METHODS, 2):
        for k, endpoint in enumerate(ENDPOINTS):
            d = np.array([values[(first, i)][k] - values[(second, i)][k] for i in range(n)], float)
            result[(endpoint, first, second)] = float(d.mean()) if np.isfinite(d).all() else float("nan")
    return result


def analyze(root: Path, out: Path, resamples: int = RESAMPLES) -> pd.DataFrame:
    runs, groups, manifest = load_runs(root)
    fronts = {(method, group): nondominated(vals[feasible]) for (method, group), (_, vals, feasible) in runs.items()}
    observed = mean_differences(indicators(fronts, groups), len(groups))
    rng = np.random.default_rng(RNG_SEED)
    draws = {key: [] for key in observed}
    nonfinite = 0
    for _ in range(resamples):
        sample = [groups[i] for i in rng.integers(0, len(groups), size=len(groups))]
        values = mean_differences(indicators(fronts, sample), len(sample))
        for key, value in values.items():
            if np.isfinite(value):
                draws[key].append(value)
            else:
                nonfinite += 1
    fixed = pd.read_csv(out / "c04_paired_effects.csv")
    rows = []
    for (endpoint, first, second), value in observed.items():
        sample = np.array(draws[(endpoint, first, second)])
        lo, hi = np.quantile(sample, [0.025, 0.975])
        reference = fixed[(fixed.endpoint == endpoint) & (fixed.first_method == first) & (fixed.second_method == second)]
        rows.append({"endpoint": endpoint, "first_method": first, "second_method": second,
                     "mean_difference": value, "rebuilt_ci_lower": float(lo), "rebuilt_ci_upper": float(hi),
                     "fixed_ci_lower": float(reference.ci_lower.iloc[0]), "fixed_ci_upper": float(reference.ci_upper.iloc[0]),
                     "fixed_mean_difference": float(reference.mean_difference.iloc[0]),
                     "resamples_used": int(sample.size),
                     "interval_excludes_zero": bool(lo > 0 or hi < 0)})
    table = pd.DataFrame(rows)
    table.to_csv(out / "r2_rebuilt_reference_effects.csv", index=False)
    (out / "r2_rebuilt_reference_metadata.json").write_text(json.dumps({
        "analysis": "C2-06 exploratory sensitivity; reference front and HV(25%) reference rebuilt in each group resample",
        "estimand": "mean paired difference (first minus second) of terminal indicators over matched groups",
        "resamples": resamples, "analysis_rng": RNG_SEED, "nonfinite_draws_dropped": nonfinite,
        "groups": groups, "no_p_values": True,
        "inputs": manifest,
        "c04_paired_effects_sha256": hashlib.sha256((out / "c04_paired_effects.csv").read_bytes()).hexdigest(),
    }, indent=2) + "\n")
    return table


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "results/paper_production/04_primary/benchmark/per_seed")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/paper/revisions/evidence")
    parser.add_argument("--resamples", type=int, default=RESAMPLES)
    args = parser.parse_args(argv)
    print(analyze(args.root, args.output, args.resamples).round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
