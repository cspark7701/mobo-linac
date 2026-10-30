#!/usr/bin/env python3
"""C4-02: two further post-hoc diagnostic-shift scenarios for the primary feasible fractions.

The 27 common-shift scenarios of C3-02 (``analyze_revision_resolution_bounds.py``) scale the
beam sizes and divergences only downward. This analysis adds

* an upward scenario: sizes and divergences scaled by the largest increase of the step-only
  refinement level of Table I (``evidence/r2_convergence_values.csv``), combined with the same
  bunch-length and mean-energy shifts;
* a differential case per matched group: the lowest constraint-aware post-initialization
  feasible fraction over the 27 common-shift scenarios minus the highest fraction of each
  other method over the same scenarios.

Both are sensitivity scenarios on the archived diagnostics, not re-tracking or an error bound.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from analyze_revision_resolution_bounds import METHODS, SUMMARY, paired, run_table, size_scales
from revision_ledgers import SEEDS, TRANSVERSE, load_ledgers

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
VALUES = EVIDENCE / "r2_convergence_values.csv"
STEP_LEVEL = "step_quarter"
CONSTRAINED = "constrained_qlognehvi"


def upward_scale(values: pd.DataFrame) -> float:
    """1 plus the largest relative increase of a size or divergence at the step-only level."""
    rows = values[values.quantity.isin(TRANSVERSE) & (values.level == STEP_LEVEL)]
    return round(1.0 + float(rows.delta_rel.max()), 3)


def differential(table: pd.DataFrame) -> pd.DataFrame:
    """Per group: lowest constraint-aware fraction over all scenarios minus each other's highest."""
    wide = table.groupby(["seed", "method"]).post_init_feasible_fraction.agg(["min", "max"]).unstack()
    rows = []
    for other in METHODS[1:]:
        for seed in SEEDS:
            low, high = wide.loc[seed, ("min", CONSTRAINED)], wide.loc[seed, ("max", other)]
            rows.append({"first_method": CONSTRAINED, "second_method": other, "seed": seed,
                         "first_min_post_init": low, "second_max_post_init": high,
                         "difference": low - high})
    return pd.DataFrame(rows)


def summarize(up_pairs: pd.DataFrame, diff: pd.DataFrame, scale: float) -> dict:
    post = up_pairs[(up_pairs.metric == "post_init_feasible_fraction") & (up_pairs.first_method == CONSTRAINED)]
    nominal = post[(post.bunch_scale == 1.0) & (post.energy_shift_MeV == 0.0)]
    return {"upward_scale": scale,
            "upward_post_init_difference_nominal": {f"{CONSTRAINED} - {r.second_method}": round(r.mean_difference, 4)
                                                     for r in nominal.itertuples()},
            "upward_post_init_difference_range": {f"{CONSTRAINED} - {b}": [round(g.mean_difference.min(), 4),
                                                                          round(g.mean_difference.max(), 4)]
                                                  for b, g in post.groupby("second_method")},
            "upward_all_groups_positive": bool((post.n_positive == len(SEEDS)).all()),
            "differential": {f"{CONSTRAINED} - {b}": {"mean": round(g.difference.mean(), 4),
                                                       "smallest": round(g.difference.min(), 4),
                                                       "n_positive": int((g.difference > 0).sum())}
                             for b, g in diff.groupby("second_method")}}


def analyze(ledgers: pd.DataFrame, summary: pd.DataFrame, values: pd.DataFrame):
    scale = upward_scale(values)
    up_table = run_table(ledgers, (scale,))
    up_pairs = paired(up_table)
    diff = differential(run_table(ledgers, size_scales(summary)))
    return up_table, up_pairs, diff, summarize(up_pairs, diff, scale)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE)
    args = parser.parse_args(argv)
    up_table, up_pairs, diff, result = analyze(load_ledgers(), pd.read_csv(SUMMARY), pd.read_csv(VALUES))
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    up_table.to_csv(out / "r4_shift_scenarios_upward_runs.csv", index=False)
    up_pairs.to_csv(out / "r4_shift_scenarios_upward_paired.csv", index=False)
    diff.to_csv(out / "r4_shift_scenarios_differential.csv", index=False)
    (out / "r4_shift_scenarios_metadata.json").write_text(json.dumps({
        "analysis": "C4-02 upward and differential diagnostic-shift scenarios (post hoc)",
        "sources": ["docs/paper/revisions/evidence/r2_convergence_values.csv",
                    "docs/paper/revisions/evidence/r2_convergence_summary.csv"],
        "upward_level": STEP_LEVEL, "groups": list(SEEDS),
        "note": "Sensitivity scenarios on archived diagnostics; not re-tracking, a refinement model "
                "for every evaluation, or an error bound.",
        **result}, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
