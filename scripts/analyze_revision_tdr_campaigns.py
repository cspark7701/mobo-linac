#!/usr/bin/env python3
"""C2-01 optional runs: constraint-aware MOBO campaigns under the KLS TDR optimization constraints.

Three matched campaigns (seeds 42-44, 160 evaluations, the primary protocol) use
``configs/revision_tdr_200MeV.yaml``. Each observation is classified with the same
acceptance-profile masks used for the primary reclassification, and compared descriptively
with the TDR-reclassified primary campaigns of the same seeds. Those campaigns share the
initial designs but were steered by the production constraints, or by none. With three
groups no test is made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_revision_acceptance import METHODS, profile_masks  # noqa: E402

TDR_RUNS = ROOT / "results/revision_round2/tdr_benchmark/per_seed"
PRIMARY = ROOT / "results/paper_production/04_primary/benchmark/per_seed"
MOGA = ROOT / "results/revision_round2/references/moga_nominal/moga_reference.json"
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
SEEDS = (42, 43, 44)
N_INITIAL, BUDGET = 16, 160
OBJECTIVES = ("norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV")
# TDR optimization inequalities as (column, kind, limit); all margins are relative to the limit.
TDR_LIMITS = (("sigma_x_m", "upper", 0.3e-3), ("sigma_y_m", "upper", 0.3e-3),
              ("sigma_xp_rad", "upper", 0.2663e-3), ("sigma_yp_rad", "upper", 0.2663e-3),
              ("sigma_z_m", "upper", 1e-3), ("mean_kinetic_energy_eV", "lower", 200e6),
              ("transmission_fraction", "lower", 0.9999))


def margins(frame: pd.DataFrame) -> pd.DataFrame:
    """Signed relative margins (positive = satisfied) for each TDR inequality."""
    out = {}
    for column, kind, limit in TDR_LIMITS:
        value = frame[column].astype(float)
        out[column] = (limit - value) / limit if kind == "upper" else (value - limit) / limit
    return pd.DataFrame(out, index=frame.index)


def load(path: Path, require_complete: bool) -> pd.DataFrame:
    run = path.parent
    complete = (run / "run_complete.json").exists()
    if complete:
        marker = json.loads((run / "run_complete.json").read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != marker["artifacts"]["evaluations.csv"]:
            raise ValueError(f"Checksum mismatch: {path}")
    elif require_complete:
        raise FileNotFoundError(f"Campaign not complete: {run}")
    else:
        path = run / "evaluations_stream.csv"
    df = pd.read_csv(path)
    df["index"] = df.evaluation_id.str.extract(r"(\d+)$")[0].astype(int)
    df = df.sort_values("index").reset_index(drop=True)
    if complete and (len(df) != BUDGET or not (df["index"].to_numpy() == np.arange(1, BUDGET + 1)).all()):
        raise ValueError(f"Unexpected ledger {path}")
    masks = profile_masks(df)
    for name in ("kls_tdr_optimization", "production", "napac2025"):
        df[name] = masks[name].to_numpy()
    return with_margins(df)


def with_margins(df: pd.DataFrame) -> pd.DataFrame:
    # Transmission is 1 in every observation, so its 1e-4 relative margin would always rank
    # as the closest; the worst margin is taken over the six beam diagnostics.
    m = margins(df)
    beam = m.drop(columns="transmission_fraction")
    df = df.assign(worst_margin=beam.min(axis=1), binding_channel=beam.idxmin(axis=1))
    return pd.concat([df, m.add_prefix("margin_")], axis=1)


def nondominated(points: np.ndarray) -> np.ndarray:
    keep = np.ones(len(points), dtype=bool)
    for i, p in enumerate(points):
        if np.any(np.all(points <= p, axis=1) & np.any(points < p, axis=1)):
            keep[i] = False
    return keep


def run_row(df: pd.DataFrame, method: str, seed: int) -> dict:
    post = df[df["index"] > N_INITIAL]
    tdr = df[df.kls_tdr_optimization]
    best = df.loc[df.worst_margin.idxmax()]
    return {"method": method, "seed": seed, "n": len(df), "complete": len(df) == BUDGET,
            "tdr_feasible": int(df.kls_tdr_optimization.sum()),
            "tdr_feasible_post_init": int(post.kls_tdr_optimization.sum()),
            "production_feasible": int(df.production.sum()), "napac_feasible": int(df.napac2025.sum()),
            "first_tdr_feasible_index": int(tdr["index"].min()) if len(tdr) else None,
            "best_worst_margin": float(best.worst_margin), "best_worst_margin_id": best.evaluation_id,
            "best_worst_margin_channel": best.binding_channel,
            **{f"best_tdr_{name}": float(tdr[name].min()) if len(tdr) else None for name in OBJECTIVES}}


def violation_shares(df: pd.DataFrame, method: str, seed: int) -> list[dict]:
    post = df[df["index"] > N_INITIAL]
    m = post[[f"margin_{column}" for column, _, _ in TDR_LIMITS]]
    rows = [{"method": method, "seed": seed, "channel": column, "n": len(post),
             "violated_fraction": float((m[f"margin_{column}"] <= 0).mean()),
             "binding_fraction": float((post.binding_channel == column).mean()),
             "only_violation_fraction": float(((m[f"margin_{column}"] <= 0)
                                              & ((m > 0).sum(axis=1) == len(TDR_LIMITS) - 1)).mean())}
            for column, _, _ in TDR_LIMITS]
    return rows


def analyze(require_complete: bool = True):
    runs, rows, shares, manifest, feasible = {}, [], [], [], []
    for seed in SEEDS:
        path = TDR_RUNS / f"constrained_qlognehvi_seed_{seed}" / "evaluations.csv"
        if not path.parent.exists():
            if require_complete:
                raise FileNotFoundError(path.parent)
            continue
        runs[("tdr_constrained_qlognehvi", seed)] = load(path, require_complete)
    for method in METHODS:
        for seed in SEEDS:
            runs[(method, seed)] = load(PRIMARY / f"{method}_seed_{seed}" / "evaluations.csv", True)
    for (method, seed), df in runs.items():
        rows.append(run_row(df, method, seed))
        shares.extend(violation_shares(df, method, seed))
        manifest.append({"method": method, "seed": seed, "n": len(df)})
        tdr = df[df.kls_tdr_optimization]
        feasible.append(tdr.assign(method=method, seed=seed))
        if method == "tdr_constrained_qlognehvi":
            agree = int((df.kls_tdr_optimization == df.physically_feasible.astype(bool)).sum())
            manifest[-1]["recorded_label_agreement"] = agree
    feasible = pd.concat(feasible, ignore_index=True)
    columns = ["method", "seed", "evaluation_id", *OBJECTIVES, "worst_margin", "binding_channel",
               "production", "napac2025"]
    front = feasible[columns].copy()
    front["pooled_nondominated"] = nondominated(front[list(OBJECTIVES)].to_numpy()) if len(front) else []
    if MOGA.exists():
        record = json.loads(MOGA.read_text())["execution_details"]
        moga = with_margins(pd.DataFrame([{**record["objectives"], **record["diagnostics"]}]))
        point = moga[list(OBJECTIVES)].to_numpy()[0]
        front["dominates_moga_reference"] = [bool(np.all(p <= point) and np.any(p < point))
                                             for p in front[list(OBJECTIVES)].to_numpy()]
        rows.append({"method": "moga_derived_reference", "seed": None, "n": 1,
                     "best_worst_margin": float(moga.worst_margin.iloc[0]),
                     "best_worst_margin_channel": moga.binding_channel.iloc[0]})
    table = pd.DataFrame(rows)
    counts = ["seed", "tdr_feasible", "tdr_feasible_post_init", "production_feasible", "napac_feasible",
              "first_tdr_feasible_index"]
    table[counts] = table[counts].astype("Int64")
    return table, pd.DataFrame(shares), front, manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-incomplete", action="store_true", help="Preview on running campaigns.")
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE)
    args = parser.parse_args(argv)
    table, shares, front, manifest = analyze(not args.allow_incomplete)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "r2_tdr_campaign_runs.csv", index=False)
    shares.to_csv(out / "r2_tdr_campaign_violations.csv", index=False)
    front.to_csv(out / "r2_tdr_campaign_feasible.csv", index=False)
    (out / "r2_tdr_campaign_metadata.json").write_text(json.dumps({
        "analysis": "C2-01 TDR-constrained campaigns; descriptive comparison with TDR-reclassified primary runs",
        "configuration": "configs/revision_tdr_200MeV.yaml", "seeds": list(SEEDS), "budget": BUDGET,
        "tdr_limits": [list(limit) for limit in TDR_LIMITS], "inputs": manifest,
        "preview": bool(args.allow_incomplete)}, indent=2, sort_keys=True) + "\n")
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
