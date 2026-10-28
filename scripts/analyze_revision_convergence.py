#!/usr/bin/env python3
"""C2-12: numerical-resolution residuals of the reported settings.

Reads the convergence runs written by ``scripts/evaluate_revision_convergence.py``. For each
setting and quantity it reports the change from the production level to every refined level,
the spread over regenerated 10k sources, and whether the production, NAPAC and TDR
classifications and the TDR margins survive refinement. The production-level rerun is also
compared with the archived value of the same setting.
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
from analyze_revision_acceptance import profile_masks  # noqa: E402
from analyze_revision_tdr_campaigns import TDR_LIMITS, margins  # noqa: E402

RUNS = ROOT / "results/revision_round2/convergence"
MOGA = ROOT / "results/revision_round2/references/moga_nominal/moga_reference.json"
# Run names and evaluation ids repeat between the primary and TDR-constrained campaigns, so the
# ledger is chosen by role, as in the driver.
PRIMARY = "results/paper_production/04_primary/benchmark/per_seed"
TDR_RUNS = "results/revision_round2/tdr_benchmark/per_seed"
TDR_CAMPAIGN_ROLE = "tdr_campaign_closest"
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
OBJECTIVES = ("norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV")
DIAGNOSTICS = ("sigma_x_m", "sigma_y_m", "sigma_xp_rad", "sigma_yp_rad", "sigma_z_m",
               "mean_kinetic_energy_eV", "transmission_fraction")
QUANTITIES = OBJECTIVES + DIAGNOSTICS
RANDOM_SOURCES = tuple(f"source_rand10k_{i}" for i in range(1, 6))
PROFILES = ("production", "napac2025", "kls_tdr_optimization")


def load_runs(directory: Path) -> pd.DataFrame:
    """One row per (setting, level) with flat objective and diagnostic columns."""
    stream = directory / "convergence_results.jsonl"
    marker = json.loads((directory / "complete.json").read_text())
    if hashlib.sha256(stream.read_bytes()).hexdigest() != marker["results_sha256"]:
        raise ValueError(f"Checksum mismatch: {stream}")
    rows = []
    for line in stream.read_text().splitlines():
        record = json.loads(line)
        values = {**(record.get("objectives") or {}), **(record.get("diagnostics") or {})}
        rows.append({"role": record["role"], "level": record["level"], "status": record["status"],
                     "simulation_valid": bool(record["simulation_valid"]), "runtime_s": record["runtime_s"],
                     "run": record.get("run"), "evaluation_id": record.get("evaluation_id"),
                     **{q: float(values[q]) if values.get(q) is not None else np.nan for q in QUANTITIES}})
    frame = pd.DataFrame(rows)
    if len(frame) != marker["tasks"] or frame.duplicated(["role", "level"]).any():
        raise ValueError("Incomplete or duplicated convergence results")
    return frame


def archived(frame: pd.DataFrame, root: Path = ROOT) -> pd.DataFrame:
    """Archived production values of each setting, from its run ledger or the MOGA record."""
    rows = []
    for role, run, evaluation_id in frame[["role", "run", "evaluation_id"]].drop_duplicates().itertuples(index=False):
        if run is None or (isinstance(run, float) and np.isnan(run)):
            record = json.loads(MOGA.read_text())["execution_details"]
            values = {**record["objectives"], **record["diagnostics"]}
        else:
            base = TDR_RUNS if role == TDR_CAMPAIGN_ROLE else PRIMARY
            ledger = root / base / run / "evaluations.csv"
            values = pd.read_csv(ledger).set_index("evaluation_id").loc[evaluation_id].to_dict()
        rows.append({"role": role, **{q: float(values[q]) for q in QUANTITIES}})
    return pd.DataFrame(rows).set_index("role")


def residuals(frame: pd.DataFrame) -> pd.DataFrame:
    """Long table of each level's change from the production level."""
    base = frame[frame.level == "production"].set_index("role")
    rows = []
    for record in frame.itertuples(index=False):
        for q in QUANTITIES:
            reference, value = base.at[record.role, q], getattr(record, q)
            rows.append({"role": record.role, "level": record.level, "quantity": q, "value": value,
                         "production": reference, "delta": value - reference,
                         "delta_rel": (value - reference) / reference if reference else np.nan})
    return pd.DataFrame(rows)


def summary(long: pd.DataFrame) -> pd.DataFrame:
    """Per setting and quantity: fine-level change, largest single-factor change, source spread."""
    rows = []
    for (role, q), group in long.groupby(["role", "quantity"], sort=False):
        by = group.set_index("level")
        single = by.drop(index=[*RANDOM_SOURCES, "source_qr10k", "production", "combined_medium", "combined_fine"],
                         errors="ignore")
        random = by.loc[[lvl for lvl in RANDOM_SOURCES if lvl in by.index], "value"]
        rows.append({"role": role, "quantity": q, "production": by.at["production", "value"],
                     "delta_fine": by.delta.get("combined_fine", np.nan),
                     "delta_medium": by.delta.get("combined_medium", np.nan),
                     "delta_rel_fine": by.delta_rel.get("combined_fine", np.nan),
                     "max_abs_single_factor": single.delta.abs().max() if len(single) else np.nan,
                     "max_single_factor_level": single.delta.abs().idxmax() if len(single) else None,
                     "delta_regenerated_qr10k": by.delta.get("source_qr10k", np.nan),
                     "source_random_std": random.std(ddof=1) if len(random) > 1 else np.nan,
                     "source_random_mean_delta": random.mean() - by.at["production", "value"] if len(random) else np.nan})
    return pd.DataFrame(rows)


def classification(frame: pd.DataFrame) -> pd.DataFrame:
    """Profile membership and signed TDR margins (physical units) at every level."""
    masks = profile_masks(frame)
    rel = margins(frame)
    out = frame[["role", "level"]].copy()
    for name in PROFILES:
        out[name] = masks[name].to_numpy()
    for column, kind, limit in TDR_LIMITS:
        out[f"tdr_margin_{column}"] = rel[column].to_numpy() * limit
    beam = rel.drop(columns="transmission_fraction")
    out["tdr_worst_rel_margin"] = beam.min(axis=1).to_numpy()
    out["tdr_worst_channel"] = beam.idxmin(axis=1).to_numpy()
    base = out[out.level == "production"].set_index("role")
    for name in PROFILES:
        out[f"{name}_changed"] = out[name].to_numpy() != base.loc[out.role, name].to_numpy()
    return out


def analyze(directory: Path = RUNS):
    frame = load_runs(directory)
    if not frame.simulation_valid.all():
        raise ValueError(f"Invalid runs: {frame.loc[~frame.simulation_valid, ['role', 'level']].values.tolist()}")
    long = residuals(frame)
    record = archived(frame)
    base = frame[frame.level == "production"].set_index("role")[list(QUANTITIES)]
    reproduction = (base - record.loc[base.index]).abs().max(axis=1).rename("max_abs_diff_from_archive")
    return frame, long, summary(long), classification(frame), reproduction


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, default=RUNS)
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE)
    args = parser.parse_args(argv)
    frame, long, table, classes, reproduction = analyze(args.runs)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    long.to_csv(out / "r2_convergence_values.csv", index=False)
    table.to_csv(out / "r2_convergence_summary.csv", index=False)
    classes.to_csv(out / "r2_convergence_classification.csv", index=False)
    plan = json.loads((args.runs / "plan.json").read_text())
    (out / "r2_convergence_metadata.json").write_text(json.dumps({
        "analysis": "C2-12 numerical-resolution residuals of the reported settings",
        "runs": str(args.runs.relative_to(ROOT)) if args.runs.is_relative_to(ROOT) else str(args.runs),
        "levels": plan["levels"], "sources": plan["sources"], "source_input": plan["source_input"],
        "settings": [{k: s[k] for k in ("role", "run", "evaluation_id")} for s in plan["settings"]],
        "runtime_s_by_level": frame.groupby("level").runtime_s.median().round(1).to_dict(),
        "production_rerun_max_abs_diff_from_archive": reproduction.to_dict()},
        indent=2, sort_keys=True) + "\n")
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
