#!/usr/bin/env python3
"""C5-08: the primary feasible fractions under the largest observed upward size scale.

The upward check of C4-02 (``analyze_revision_shift_scenarios.py``) scales the beam sizes and
divergences by the largest step-only increase. Some single-factor and regenerated-source
levels of the refinement check (``evidence/r2_convergence_values.csv``) increase individual
sizes more. This analysis applies, as one common transformation, the largest increase of a
size or divergence at any level, rounded up to two decimals, combined with the same
bunch-length and mean-energy shifts. It is a post-hoc sensitivity scenario on the archived
diagnostics, not re-tracking or an error bound.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

from analyze_revision_resolution_bounds import paired, run_table
from revision_ledgers import SEEDS, TRANSVERSE, load_ledgers

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
VALUES = EVIDENCE / "r2_convergence_values.csv"
CONSTRAINED = "constrained_qlognehvi"


def largest_increase(values: pd.DataFrame) -> dict:
    """The largest relative increase of a size or divergence over all refinement and source levels."""
    rows = values[values.quantity.isin(TRANSVERSE) & (values.level != "production")]
    top = rows.loc[rows.delta_rel.idxmax()]
    return {"role": top.role, "level": top.level, "quantity": top.quantity,
            "delta_rel": float(top.delta_rel),
            "scale": math.ceil(round((1.0 + float(top.delta_rel)) * 100, 6)) / 100}


def summarize(pairs: pd.DataFrame) -> dict:
    post = pairs[(pairs.metric == "post_init_feasible_fraction") & (pairs.first_method == CONSTRAINED)]
    nominal = post[(post.bunch_scale == 1.0) & (post.energy_shift_MeV == 0.0)]
    return {"post_init_difference_nominal": {f"{CONSTRAINED} - {r.second_method}": round(r.mean_difference, 4)
                                             for r in nominal.itertuples()},
            "post_init_difference_range": {f"{CONSTRAINED} - {b}": [round(g.mean_difference.min(), 4),
                                                                   round(g.mean_difference.max(), 4)]
                                           for b, g in post.groupby("second_method")},
            "post_init_smallest_ci_lower": {f"{CONSTRAINED} - {b}": round(g.ci_lower.min(), 4)
                                            for b, g in post.groupby("second_method")},
            "all_groups_positive_post_init": bool((pairs[pairs.metric == "post_init_feasible_fraction"]
                                                   .n_positive == len(SEEDS)).all())}


def analyze(ledgers: pd.DataFrame, values: pd.DataFrame):
    source = largest_increase(values)
    table = run_table(ledgers, (source["scale"],))
    pairs = paired(table)
    return table, pairs, {"largest_increase": source, **summarize(pairs)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE)
    args = parser.parse_args(argv)
    table, pairs, result = analyze(load_ledgers(), pd.read_csv(VALUES))
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "r5_upward_max_runs.csv", index=False)
    pairs.to_csv(out / "r5_upward_max_paired.csv", index=False)
    (out / "r5_upward_max_metadata.json").write_text(json.dumps({
        "analysis": "C5-08 largest observed upward size scale (post hoc)",
        "source": "docs/paper/revisions/evidence/r2_convergence_values.csv", "groups": list(SEEDS),
        "note": "Sensitivity scenario on archived diagnostics; not re-tracking, a refinement model "
                "for every evaluation, or an error bound.",
        **result}, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
