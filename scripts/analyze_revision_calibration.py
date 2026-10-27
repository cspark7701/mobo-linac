#!/usr/bin/env python3
"""C2-05: interpret next-batch surrogate accuracy by stage and region, and test fixed noise.

Part A summarizes the existing C11 next-batch prediction records by optimization stage
(batches 1-6, 7-12, 13-18) and by whether the predicted observation was feasible under the
production profile, with run-level variation. Part B (optional, offline, no ASTRA) refits
every archived pre-proposal training set twice with the production surrogate builder,
once with the production fixed noise and once with inferred homoscedastic noise, and
repeats the chronological next-batch coverage check. Only the noise setting differs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
PRIMARY = ROOT / "results/paper_production/04_primary/benchmark/per_seed"
METHODS = ("constrained_qlognehvi", "unconstrained_qlognehvi", "scalarized_bo")
OBJECTIVES = ("norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV")
# Transmission is constant in every primary run, so it carries no predictive test.
DIAGNOSTICS = ("sigma_x_m", "sigma_y_m", "sigma_xp_rad", "sigma_yp_rad", "sigma_z_m", "mean_kinetic_energy_eV")
STAGES = ((1, 6, "early"), (7, 12, "middle"), (13, 18, "late"))
Z95 = 1.959963984540054
N_INITIAL, BATCH, BATCHES = 16, 8, 18


def stage_of(batch: int) -> str:
    for low, high, name in STAGES:
        if low <= batch <= high:
            return name
    raise ValueError(f"Batch {batch} outside 1-{BATCHES}")


def ledgers() -> dict:
    frames = {}
    for method in METHODS:
        for seed in range(42, 52):
            run = PRIMARY / f"{method}_seed_{seed}"
            path = run / "evaluations.csv"
            marker = json.loads((run / "run_complete.json").read_text())
            if hashlib.sha256(path.read_bytes()).hexdigest() != marker["artifacts"]["evaluations.csv"]:
                raise ValueError(f"Checksum mismatch: {path}")
            frames[run.name] = (pd.read_csv(path), json.loads((run / "config.json").read_text()))
    return frames


def coverage_rows(frame: pd.DataFrame, keys) -> pd.DataFrame:
    rows = []
    for key, group in frame.groupby(list(keys)):
        error = group.observed - group.predicted
        per_run = group.assign(hit=(error.abs() <= Z95 * group.predictive_std)).groupby("run_id").hit.mean()
        rows.append(dict(zip(keys, key if isinstance(key, tuple) else (key,)),
                         n=len(group), runs=int(per_run.size),
                         coverage95=float((error.abs() <= Z95 * group.predictive_std).mean()),
                         run_coverage_median=float(per_run.median()),
                         run_coverage_q25=float(per_run.quantile(0.25)),
                         run_coverage_q75=float(per_run.quantile(0.75)),
                         rmse=float(np.sqrt((error ** 2).mean())),
                         rms_standardized_error=float(np.sqrt(((error / group.predictive_std) ** 2).mean()))))
    return pd.DataFrame(rows)


def part_a(frames: dict) -> pd.DataFrame:
    """Stage- and region-resolved summaries of the existing C11 records (no refitting)."""
    records = pd.read_csv(EVIDENCE / "c11_next_batch_predictions.csv")
    records = records[records.subset == "all"].copy()
    feasible = {(run, row.evaluation_id): bool(row.physically_feasible)
                for run, (df, _) in frames.items() for row in df.itertuples()}
    records["stage"] = records.batch.map(stage_of)
    records["region"] = [("feasible" if feasible[(r, e)] else "infeasible")
                         for r, e in zip(records.run_id, records.evaluation_id)]
    by_stage = coverage_rows(records, ("method", "channel", "stage")).assign(region="all")
    by_region = coverage_rows(records, ("method", "channel", "region")).assign(stage="all")
    late = coverage_rows(records[records.stage == "late"], ("method", "channel", "region")).assign(stage="late")
    return pd.concat([by_stage, by_region, late], ignore_index=True)


def predict(model, X, noise_orig: float):
    with torch.no_grad():
        posterior = model.posterior(X)
        mean = posterior.mean.flatten().cpu().numpy()
        variance = posterior.distribution.covariance_matrix.diagonal(dim1=-2, dim2=-1).flatten().cpu().numpy()
    return mean, np.sqrt(np.clip(variance, 0, None) + noise_orig)


def fit_channel(train_X, train_Y, future_X, bounds, settings, mode, device="cpu"):
    from mobo_linac.models.gp import build_output_gp, fit_gp_models
    chosen = settings if mode == "fixed" else replace(settings, noise_mode="inferred", fixed_noise_variance=None,
                                                      objective_noise_variances=None)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gp = build_output_gp(train_X, train_Y, bounds, chosen, device=device)
        fit_gp_models(gp)
        future_X = future_X.to(device=gp.train_inputs[0].device)
    scale = float(gp.outcome_transform.stdvs.item())
    if mode == "fixed":
        noise_orig = float(gp.likelihood.noise.mean().item()) * scale ** 2
    else:
        noise_orig = float(gp.likelihood.noise.item()) * scale ** 2
    mean, std = predict(gp, future_X, noise_orig)
    return mean, std, noise_orig, float(train_Y.var(unbiased=True).item())


def part_b(frames: dict, limit_runs=None, device="cpu") -> pd.DataFrame:
    """Refit every pre-proposal training set with fixed and inferred noise (offline)."""
    from mobo_linac.config import config_from_dict
    from mobo_linac.models.gp import SurrogateSettings
    rows = []
    for index, (run, (df, cfg_dict)) in enumerate(frames.items()):
        if limit_runs is not None and index >= limit_runs:
            break
        config = config_from_dict(cfg_dict)
        method = run.split("_seed_")[0]
        names = [v.name for v in config.design_variables]
        bounds = torch.tensor([[v.lower_bound for v in config.design_variables],
                               [v.upper_bound for v in config.design_variables]], dtype=torch.double)
        settings = SurrogateSettings.from_config(config.model)
        X = torch.tensor(df[names].to_numpy(), dtype=torch.double)
        if method == "scalarized_bo":
            scales = np.array([1e-6, 1e-6, 1e6])
            channels = {"scalarized_cost": -(df[list(OBJECTIVES)].to_numpy() / scales / 3.0).sum(axis=1)}
            per_output = {"scalarized_cost": settings.for_output(None)}
        else:
            channels = {name: -df[name].to_numpy() for name in OBJECTIVES}
            per_output = {name: settings.for_output(i) for i, name in enumerate(OBJECTIVES)}
            if method == "constrained_qlognehvi":
                for name in DIAGNOSTICS:
                    channels[name] = df[name].to_numpy()
                    per_output[name] = settings.for_output(None)
        for batch in range(1, BATCHES + 1):
            n = N_INITIAL + BATCH * (batch - 1)
            future = X[n:n + BATCH]
            for channel, values in channels.items():
                y = torch.tensor(values[:n], dtype=torch.double).unsqueeze(-1)
                sign = -1.0 if channel in OBJECTIVES or channel == "scalarized_cost" else 1.0
                for mode in ("fixed", "inferred"):
                    mean, std, noise, variance = fit_channel(X[:n], y, future, bounds, per_output[channel], mode,
                                                                  device)
                    for j in range(BATCH):
                        rows.append({"method": method, "run_id": run, "batch": batch, "stage": stage_of(batch),
                                     "evaluation_id": df.evaluation_id.iloc[n + j], "channel": channel,
                                     "mode": mode, "observed": sign * values[n + j], "predicted": sign * mean[j],
                                     "predictive_std": std[j], "noise_variance": noise,
                                     "relative_noise": noise / variance if variance > 0 else float("nan"),
                                     "feasible": bool(df.physically_feasible.iloc[n + j])})
        print(f"refit {run}", flush=True)
    return pd.DataFrame(rows)


def summarize_b(frame: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (method, channel, mode), group in frame.groupby(["method", "channel", "mode"]):
        error = group.observed - group.predicted
        late = group[group.stage == "late"]
        late_error = late.observed - late.predicted
        out.append({"method": method, "channel": channel, "mode": mode, "n": len(group),
                    "coverage95": float((error.abs() <= Z95 * group.predictive_std).mean()),
                    "late_coverage95": float((late_error.abs() <= Z95 * late.predictive_std).mean()),
                    "rmse": float(np.sqrt((error ** 2).mean())),
                    "late_rmse": float(np.sqrt((late_error ** 2).mean())),
                    "median_relative_noise": float(group.drop_duplicates(["run_id", "batch"]).relative_noise.median())})
    return pd.DataFrame(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("a", "b", "both"), default="a")
    parser.add_argument("--limit-runs", type=int, default=None, help="Refit only the first N runs (testing).")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--device", default="cpu", help="PyTorch device for the offline refits.")
    args = parser.parse_args(argv)
    torch.set_num_threads(args.threads)
    frames = ledgers()
    if args.part in ("a", "both"):
        part_a(frames).to_csv(EVIDENCE / "r2_calibration_stages.csv", index=False)
    if args.part in ("b", "both"):
        refit = part_b(frames, args.limit_runs, args.device)
        refit.to_csv(EVIDENCE / "r2_calibration_refit_predictions.csv.gz", index=False)
        summarize_b(refit).to_csv(EVIDENCE / "r2_calibration_refit_summary.csv", index=False)
    (EVIDENCE / "r2_calibration_metadata.json").write_text(json.dumps({
        "analysis": "C2-05; part A uses existing C11 records; part B refits archived training sets offline",
        "stages": {name: [low, high] for low, high, name in STAGES},
        "interval": "Gaussian 95% observation interval; latent covariance diagonal plus likelihood noise",
        "refit_modes": {"fixed": "production deterministic fixed noise",
                        "inferred": "homoscedastic Gaussian likelihood noise fitted by marginal likelihood"},
        "excluded_channels": {"transmission_fraction": "constant in all primary runs"},
        "refit_device": args.device,
        "input_sha256": {"c11_next_batch_predictions.csv": hashlib.sha256(
            (EVIDENCE / "c11_next_batch_predictions.csv").read_bytes()).hexdigest()},
    }, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
