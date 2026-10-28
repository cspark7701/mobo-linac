#!/usr/bin/env python3
"""C2-03: space-filling references for the feasible-sampling comparison.

1. Initialization-only reference: the 160 shared scrambled-Sobol initial points (16 per
   matched group), which every pipeline evaluates identically. Not a matched arm.
2. Budget-matched Sobol arm (optional run): 160 points of each group's own scrambled Sobol
   sequence, whose first 16 are that group's shared initial design; no acquisition.

Channel-group violations use the same production-profile definitions as C2-02.
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
from analyze_revision_attribution import (  # noqa: E402
    ACC34_UPPER_QUARTER, METHODS, SEEDS, categorize, load_runs, violations,
)
from analyze_revision_fronts import SCALES, additive_epsilon, igd_plus, nondominated  # noqa: E402
from analyze_revision_robustness import binomial_bounds  # noqa: E402

PRIMARY = ROOT / "results/paper_production/04_primary/benchmark/per_seed"
SOBOL = ROOT / "results/revision_round2/sobol"
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
BOOTSTRAP, RNG_SEED = 10000, 20261027
VARIABLES = ("solenoid_field_T", "quad_1_gradient_T_m", "quad_2_gradient_T_m", "gun_phase_deg",
             "acc1_acc2_phase_deg", "acc3_acc4_phase_deg")


def rates(frame: pd.DataFrame) -> dict:
    return {"n": len(frame), "feasible": int((frame.category == "feasible").sum()),
            "feasible_fraction": float((frame.category == "feasible").mean()),
            "energy_violation_fraction": float(frame.violates_energy.mean()),
            "transverse_violation_fraction": float(frame.violates_transverse.mean()),
            "bunch_length_violation_fraction": float(frame.violates_bunch_length.mean()),
            "acc34_upper_quarter_fraction": float((frame.acc3_acc4_phase_deg > ACC34_UPPER_QUARTER).mean())}


def initial_reference(runs) -> pd.DataFrame:
    rows = []
    initial = pd.concat([runs[(METHODS[0], seed)][lambda d: d.batch == 0] for seed in SEEDS], ignore_index=True)
    entry = {"population": "shared_initial_design", **rates(initial)}
    low, high, _ = binomial_bounds(entry["feasible"], entry["n"])
    entry.update(ci_lower=low, ci_upper=high)
    rows.append(entry)
    for method in METHODS:
        post = pd.concat([runs[(method, seed)][lambda d: d.batch > 0] for seed in SEEDS], ignore_index=True)
        entry = {"population": f"{method}_post_initialization", **rates(post)}
        low, high, _ = binomial_bounds(entry["feasible"], entry["n"])
        entry.update(ci_lower=low, ci_upper=high)
        rows.append(entry)
    return pd.DataFrame(rows)


def load_sobol(runs) -> tuple[dict, list]:
    arms, manifest = {}, []
    for seed in SEEDS:
        run = SOBOL / f"sobol_seed_{seed}"
        path = run / "evaluations.csv"
        if not (run / "run_complete.json").exists():
            raise FileNotFoundError(f"Sobol arm seed {seed} is not complete: {run}")
        marker = json.loads((run / "run_complete.json").read_text())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != marker["artifacts"]["evaluations.csv"]:
            raise ValueError(f"Checksum mismatch: {path}")
        df = pd.read_csv(path)
        df["index"] = df.evaluation_id.str.extract(r"(\d+)$")[0].astype(int)
        df = df.sort_values("index").reset_index(drop=True)
        if len(df) != 160 or not (df["index"].to_numpy() == np.arange(1, 161)).all():
            raise ValueError(f"Unexpected Sobol ledger {path}")
        shared = runs[(METHODS[0], seed)]
        np.testing.assert_allclose(df.loc[:15, list(VARIABLES)].to_numpy(), shared.loc[:15, list(VARIABLES)].to_numpy(),
                                   rtol=0, atol=1e-9)
        limits = json.loads((run / "config.json").read_text())["constraints"]
        v = violations(df, limits)
        df["category"] = categorize(v)
        if not (df.category.eq("feasible") == df.physically_feasible.astype(bool)).all():
            raise ValueError(f"Recomputed feasibility disagrees with recorded labels in {path}")
        df["batch"] = np.where(df["index"] <= 16, 0, (df["index"] - 17) // 8 + 1)
        arms[seed] = pd.concat([df, v.add_prefix("violates_")], axis=1)
        manifest.append({"run": run.name, "sha256": digest})
    return arms, manifest


def sobol_comparison(runs, arms) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for seed in SEEDS:
        for name, frame in [("sobol", arms[seed])] + [(m, runs[(m, seed)]) for m in METHODS]:
            post = frame[frame.batch > 0]
            rows.append({"method": name, "seed": seed, **rates(post)})
    table = pd.DataFrame(rows)
    rng = np.random.default_rng(RNG_SEED)
    index = rng.integers(0, len(SEEDS), size=(BOOTSTRAP, len(SEEDS)))
    effects = []
    for metric in ("feasible_fraction", "energy_violation_fraction", "transverse_violation_fraction"):
        wide = table.pivot(index="seed", columns="method", values=metric).loc[list(SEEDS)]
        for method in METHODS:
            d = (wide[method] - wide["sobol"]).to_numpy(float)
            lo, hi = np.quantile(d[index].mean(axis=1), [0.025, 0.975])
            effects.append({"metric": metric, "first_method": method, "second_method": "sobol",
                            "mean_difference": float(d.mean()), "ci_lower": float(lo), "ci_upper": float(hi),
                            "n_positive": int((d > 0).sum()), "n_negative": int((d < 0).sum())})
    return table, pd.DataFrame(effects)


def paired(table: pd.DataFrame, metric: str, rng) -> list:
    """Bootstrap the mean of (pipeline - Sobol) over the matched groups."""
    wide = table.pivot(index="seed", columns="method", values=metric).loc[list(SEEDS)]
    index = rng.integers(0, len(SEEDS), size=(BOOTSTRAP, len(SEEDS)))
    rows = []
    for method in METHODS:
        d = (wide[method] - wide["sobol"]).to_numpy(float)
        finite = bool(np.isfinite(d).all())
        lo, hi = np.quantile(d[index].mean(axis=1), [0.025, 0.975]) if finite else (np.nan, np.nan)
        rows.append({"metric": metric, "first_method": method, "second_method": "sobol",
                     "mean_difference": float(d.mean()) if finite else np.nan, "ci_lower": float(lo),
                     "ci_upper": float(hi), "n_positive": int((d > 0).sum()), "n_negative": int((d < 0).sum())})
    return rows


def sobol_quality(arms, evidence: Path = EVIDENCE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Post hoc epsilon and IGD+ of each terminal front against the primary empirical reference.

    The reference and the pipelines' terminal values are those of the primary analysis
    (c03_*), so the Sobol arm is scored on the same scale; the reference is not rebuilt.
    """
    reference = pd.read_csv(evidence / "c03_empirical_reference.csv").to_numpy(float)
    histories = pd.read_csv(evidence / "c03_run_histories.csv")
    terminal = histories[histories.evaluations == 160]
    rows = []
    for seed in SEEDS:
        df = arms[seed]
        values = df[["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]].to_numpy(float) / SCALES
        front = nondominated(values[(df.category == "feasible").to_numpy()])
        dominates = (np.any(np.all(front[:, None] <= reference[None], axis=2)
                            & np.any(front[:, None] < reference[None], axis=2), axis=0).sum() if len(front) else 0)
        rows.append({"method": "sobol", "seed": seed, "front_size_unique": len(front),
                     "epsilon": additive_epsilon(front, reference), "igd_plus": igd_plus(front, reference),
                     "reference_points_dominated": int(dominates)})
        for method in METHODS:
            row = terminal[(terminal.method == method) & (terminal.group == seed)].iloc[0]
            rows.append({"method": method, "seed": seed, "front_size_unique": int(row.front_size_unique),
                         "epsilon": float(row.epsilon), "igd_plus": float(row.igd_plus)})
    table = pd.DataFrame(rows)
    rng = np.random.default_rng(RNG_SEED + 1)
    effects = paired(table, "epsilon", rng) + paired(table, "igd_plus", rng)
    return table, pd.DataFrame(effects)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("initial", "sobol", "all"), default="initial")
    args = parser.parse_args(argv)
    runs, manifest = load_runs(PRIMARY)
    metadata = {"analysis": "C2-03 space-filling references; production profile", "inputs": manifest}
    if args.part in ("initial", "all"):
        initial_reference(runs).to_csv(EVIDENCE / "r2_space_filling_initial.csv", index=False)
    if args.part in ("sobol", "all"):
        arms, sobol_manifest = load_sobol(runs)
        table, effects = sobol_comparison(runs, arms)
        table.to_csv(EVIDENCE / "r2_sobol_arm_runs.csv", index=False)
        effects.to_csv(EVIDENCE / "r2_sobol_arm_paired.csv", index=False)
        quality, quality_effects = sobol_quality(arms)
        quality.to_csv(EVIDENCE / "r2_sobol_arm_quality.csv", index=False)
        quality_effects.to_csv(EVIDENCE / "r2_sobol_arm_quality_paired.csv", index=False)
        metadata.update(sobol_quality="post hoc; epsilon and IGD+ against the unchanged primary empirical reference")
        metadata.update(sobol_inputs=sobol_manifest, bootstrap_resamples=BOOTSTRAP, analysis_rng=RNG_SEED)
    target = EVIDENCE / "r2_space_filling_metadata.json"
    previous = json.loads(target.read_text()) if target.exists() else {}
    previous.update(metadata)
    target.write_text(json.dumps(previous, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
