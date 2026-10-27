#!/usr/bin/env python3
"""C2-07/C2-08: lattice-jitter checks of the archived representatives and round2 reference runs.

1. Archived primary audit (no new runs): count perturbed samples that Pareto-dominate their
   nominal setting and summarize the mean-energy spread produced by the simulated jitter.
2. RF-amplitude estimate: structure-pair energy gains from the retained ASTRA output of the
   MOGA-derived re-evaluation, scaled by a 0.2 % amplitude error.
3. Round2 reference runs: feasibility of the MOGA-derived setting and of the two TDR-passing
   observations under 50 lattice-jitter trials, classified under the production and TDR
   profiles with exact Clopper-Pearson bounds.
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
from analyze_revision_robustness import binomial_bounds  # noqa: E402

AUDIT = ROOT / "results/paper_production/06_candidate_audit/robustness/robustness_runs"
REFERENCES = ROOT / "results/revision_round2/references"
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
OBJECTIVES = ("norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV")
DIAGNOSTICS = ("sigma_x_m", "sigma_y_m", "sigma_xp_rad", "sigma_yp_rad", "sigma_z_m",
               "mean_kinetic_energy_eV", "transmission_fraction")
AMPLITUDE_ERROR = 0.002  # 0.2 % RMS, the RF-gradient error of the JKPS operating-error model
# Structure entrance positions [m] (astra.in C_pos) and a 2.98 m structure length.
STRUCTURES = {"ACC1": 1.81, "ACC2": 5.61046, "ACC3": 9.41092, "ACC4": 13.21138}
STRUCTURE_LENGTH = 2.98


def records_frame(path: Path) -> pd.DataFrame:
    data = json.loads(path.read_text())
    rows = []
    for record in data["records"]:
        result, meta = record["result"], record["request"]["metadata"]
        row = {"role": meta["candidate_label"], "sample": meta["sample_idx"], "valid": result["simulation_valid"],
               "recorded_feasible": result["physically_feasible"], "execution_kind": record["execution_kind"],
               "simulation_valid": result["simulation_valid"]}
        row.update(dict(zip(OBJECTIVES, result["objectives_physical"] or [np.nan] * 3)))
        row.update({name: result["diagnostics"].get(name, np.nan) for name in DIAGNOSTICS})
        row["sigma_energy_eV"] = row["sigma_energy_eV"]
        rows.append(row)
    return pd.DataFrame(rows)


def dominates(a: np.ndarray, b: np.ndarray) -> bool:
    return bool(np.all(a <= b) and np.any(a < b))


def archived_audit() -> pd.DataFrame:
    paths = sorted(AUDIT.glob("*/robustness_requests.json"))
    if len(paths) != 1:
        raise ValueError(f"Expected one primary audit session, found {len(paths)}")
    frame = records_frame(paths[0])
    summary = pd.read_csv(paths[0].parents[2] / "robustness_summary.csv")
    rows = []
    for role, group in frame.groupby("role", sort=False):
        nominal_row = summary[summary.candidate_label == role].iloc[0]
        nominal = np.array([nominal_row[f"nominal_{name}"] for name in OBJECTIVES])
        values = group[list(OBJECTIVES)].to_numpy(float)
        dominating = np.array([dominates(v, nominal) for v in values])
        better = (values < nominal)
        rows.append({"role": role, "trials": len(group), "valid": int(group.valid.sum()),
                     "feasible": int(group.recorded_feasible.sum()),
                     "dominating_nominal": int(dominating.sum()),
                     "dominating_and_feasible": int((dominating & group.recorded_feasible.to_numpy(bool)).sum()),
                     **{f"better_{name}": int(better[:, i].sum()) for i, name in enumerate(OBJECTIVES)},
                     "mean_energy_std_MeV": float(group.mean_kinetic_energy_eV.std(ddof=0) / 1e6),
                     "min_energy_MeV": float(group.mean_kinetic_energy_eV.min() / 1e6),
                     "mean_degradation_D": float(nominal_row.mean_objective_degradation)})
    return pd.DataFrame(rows)


def amplitude_estimate() -> dict:
    zemit = sorted((REFERENCES / "moga_nominal").rglob("astra.Zemit.001"))
    if not zemit:
        raise FileNotFoundError("Retained ASTRA longitudinal output of the MOGA-derived re-evaluation is missing")
    data = np.loadtxt(zemit[0])
    z, energy = data[:, 0], data[:, 2]
    at = lambda position: float(energy[np.argmin(abs(z - position))])  # noqa: E731
    gains = {name: at(start + STRUCTURE_LENGTH) - at(start) for name, start in STRUCTURES.items()}
    gun = at(STRUCTURES["ACC1"])
    pairs = {"ACC1/2": gains["ACC1"] + gains["ACC2"], "ACC3/4": gains["ACC3"] + gains["ACC4"]}
    return {"source": str(zemit[0].relative_to(ROOT)), "gun_exit_MeV": gun, "structure_gain_MeV": gains,
            "pair_gain_MeV": pairs, "amplitude_error_rms": AMPLITUDE_ERROR,
            "mean_energy_shift_rms_MeV": {
                "independent_pairs": AMPLITUDE_ERROR * float(np.hypot(*pairs.values())),
                "fully_correlated": AMPLITUDE_ERROR * float(sum(pairs.values()) + gun)}}


SESSIONS = {"moga": REFERENCES / "moga_jitter", "tdr": REFERENCES / "tdr_candidate_jitter"}


def reference_runs(names=("moga", "tdr")) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, trials = [], []
    for name in names:
        folder = SESSIONS[name]
        paths = sorted(folder.glob("robustness_runs/*/robustness_requests.json"))
        if len(paths) != 1:
            raise FileNotFoundError(f"Round2 {name} jitter session is not complete in {folder}")
        frame = records_frame(paths[0])
        masks = profile_masks(frame)
        for role, group in frame.groupby("role", sort=False):
            index = group.index
            entry = {"session": name, "role": role, "trials": len(group), "valid": int(group.valid.sum()),
                     "execution_kinds": ",".join(sorted(group.execution_kind.unique()))}
            for profile in ("production", "kls_tdr_optimization", "kls_tdr_optimization_plus_spread"):
                k = int(masks[profile].loc[index].sum())
                low, high, one_sided = binomial_bounds(k, len(group))
                entry.update({f"{profile}_feasible": k, f"{profile}_ci_lower": low, f"{profile}_ci_upper": high,
                              f"{profile}_one_sided_lower": one_sided})
            for objective in OBJECTIVES:
                entry[f"mean_{objective}"] = float(group[objective].mean())
                entry[f"std_{objective}"] = float(group[objective].std(ddof=0))
            entry["mean_energy_std_MeV"] = float(group.mean_kinetic_energy_eV.std(ddof=0) / 1e6)
            # Physical TDR headroom (positive inside the limit) of the worst trial in each channel.
            entry.update({"min_tdr_margin_sigma_x_um": float((0.30e-3 - group.sigma_x_m).min() * 1e6),
                          "min_tdr_margin_sigma_y_um": float((0.30e-3 - group.sigma_y_m).min() * 1e6),
                          "min_tdr_margin_sigma_yp_urad": float((0.2663e-3 - group.sigma_yp_rad).min() * 1e6),
                          "min_tdr_margin_sigma_z_um": float((1e-3 - group.sigma_z_m).min() * 1e6),
                          "min_tdr_margin_energy_MeV": float((group.mean_kinetic_energy_eV - 200e6).min() / 1e6)})
            rows.append(entry)
            trials.append(group.assign(session=name, **{f"pass_{p}": masks[p].loc[index].to_numpy()
                                                         for p in ("production", "kls_tdr_optimization")}))
    return pd.DataFrame(rows), pd.concat(trials, ignore_index=True)


def moga_reference() -> dict:
    record = json.loads((REFERENCES / "moga_nominal/moga_reference.json").read_text())
    frame = pd.DataFrame([{**record["objectives"], **record["result"]["diagnostics"],
                           "simulation_valid": record["result"]["simulation_valid"]}])
    masks = {name: bool(mask.iloc[0]) for name, mask in profile_masks(frame).items()}
    previous = record["previous_record"]["values"]
    return {"objectives": record["objectives"], "diagnostics": record["result"]["diagnostics"],
            "recorded_production_feasible": record["result"]["physically_feasible"], "profiles": masks,
            "reproduces_previous_record": all(np.isclose(record["objectives"][k], previous[k], rtol=1e-6)
                                              for k in OBJECTIVES),
            "relative_rms_energy_spread": record["objectives"]["sigma_energy_eV"]
                                          / record["result"]["diagnostics"]["mean_kinetic_energy_eV"],
            "tdr_vertical_divergence_excess_urad": (record["result"]["diagnostics"]["sigma_yp_rad"] - 0.2663e-3) * 1e6,
            "deck": record["deck"], "previous_record": record["previous_record"]}


def moga_front_comparison() -> pd.DataFrame:
    """Per run: additive epsilon of the feasible front to the MOGA-derived point, and dominance counts.

    Coordinates are micrometre-radian and MeV. A negative epsilon means the run's feasible front
    already weakly dominates the reference point with that slack.
    """
    from analyze_revision_fronts import SCALES, additive_epsilon, load_runs, nondominated
    record = json.loads((REFERENCES / "moga_nominal/moga_reference.json").read_text())
    point = np.array([record["objectives"][name] for name in OBJECTIVES]) / SCALES
    runs, _, _ = load_runs(ROOT / "results/paper_production/04_primary/benchmark/per_seed")
    rows = []
    for (method, group), (_, vals, feasible) in runs.items():
        front = nondominated(vals[feasible])
        dominating = [dominates(v, point) for v in vals[feasible]]
        better_all = np.all(vals[feasible] < point, axis=1) if feasible.any() else np.array([])
        rows.append({"method": method, "group": group, "feasible": int(feasible.sum()),
                     "epsilon_to_reference": additive_epsilon(front, point[None, :]),
                     "feasible_dominating_reference": int(sum(dominating)),
                     "feasible_strictly_better_all": int(better_all.sum()),
                     "feasible_better_emit_x": int((vals[feasible][:, 0] < point[0]).sum()),
                     "feasible_better_emit_y": int((vals[feasible][:, 1] < point[1]).sum()),
                     "feasible_better_sigma_e": int((vals[feasible][:, 2] < point[2]).sum())})
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("archived", "moga-front", "references", "all"), default="all")
    args = parser.parse_args(argv)
    metadata = {"analysis": "C2-07/C2-08 jitter checks", "amplitude_error_rms": AMPLITUDE_ERROR}
    if args.part in ("archived", "all"):
        archived_audit().to_csv(EVIDENCE / "r2_jitter_dominance.csv", index=False)
        metadata["rf_amplitude_estimate"] = amplitude_estimate()
    if args.part in ("moga-front", "all"):
        moga_front_comparison().to_csv(EVIDENCE / "r2_moga_reference_comparison.csv", index=False)
        summary, trials = reference_runs(("moga",))
        summary.to_csv(EVIDENCE / "r2_moga_jitter_summary.csv", index=False)
        trials.to_csv(EVIDENCE / "r2_moga_jitter_trials.csv", index=False)
        metadata["moga_derived_reference"] = moga_reference()
    if args.part in ("references", "all"):
        summary, trials = reference_runs(("tdr",))
        summary.to_csv(EVIDENCE / "r2_tdr_candidate_jitter_summary.csv", index=False)
        trials.to_csv(EVIDENCE / "r2_tdr_candidate_jitter_trials.csv", index=False)
    metadata["reference_inputs"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted(REFERENCES.rglob("robustness_requests.json"))}
    target = EVIDENCE / "r2_jitter_metadata.json"
    previous = json.loads(target.read_text()) if target.exists() else {}
    previous.update(metadata)
    target.write_text(json.dumps(previous, indent=2, sort_keys=True, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
