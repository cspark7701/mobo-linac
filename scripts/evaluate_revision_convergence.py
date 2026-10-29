#!/usr/bin/env python3
"""Numerical-resolution check of the reported settings (consolidated round2 task C2-12).

Ten settings are re-tracked at refined numerical settings with the production pipeline:
the MOGA-derived nominal, TDR candidates A and B, the closest observation of the
TDR-constrained campaigns, and the six selected constraint-aware representatives. The production deck uses 10,000 quasi-random macroparticles, a 32x32
cylindrical and 32^3 3D space-charge grid, and H_max = 0.01 ns, H_min = 0.001 ns.

The production source ``pal_photo2.ini`` is reproduced with ASTRA's ``generator`` (see
``SOURCE_INPUT``): its time, radius and momentum marginals agree with the file to print
precision. Refined sources come from the same input with more particles. Source-sampling
noise is measured with regenerated 10k sources: one quasi-random and five pseudo-random
(the generator seeds its random mode from the clock, so each file's SHA-256 is recorded).

Levels change one factor at a time, plus two combined levels; each is applied through
per-run namelist overrides of the production template. No production output is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import asdict, replace
from pathlib import Path

from mobo_linac.config import load_config
from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase, EvaluationTask
from mobo_linac.execution.mock import MockEvaluator
from mobo_linac.io.run_data import read_run_data

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_CONFIG = ROOT / "configs/publication_200MeV.yaml"
PRIMARY = ROOT / "results/paper_production/04_primary/benchmark/per_seed"
TDR_RUNS = ROOT / "results/revision_round2/tdr_benchmark/per_seed"
REPRESENTATIVES = ROOT / "results/paper_production/06_candidate_audit/robustness/representatives.json"
TDR_CANDIDATES = (("tdr_candidate_a", "constrained_qlognehvi_seed_44", "eval_000079"),
                  ("tdr_candidate_b", "constrained_qlognehvi_seed_51", "eval_000099"))
# Closest TDR-campaign observation (evidence/r2_tdr_campaign_runs.csv): misses sigma_x and sigma_y' by 0.4 %.
TDR_CAMPAIGN_CLOSEST = ("tdr_campaign_closest", "constrained_qlognehvi_seed_43", "eval_000122")
PRODUCTION_SOURCE = "pal_photo2.ini"
# Generator input that reproduces the production source (probe particles included).
SOURCE_INPUT = """&INPUT
 FNAME = '{name}'
 IPart={particles}
 Species='electrons'
 Probe=.T
 Noise_reduc={quasi}
 Cathode=.T
 Q_total=1.0E0
 Ref_zpos=0.0E0
 Ref_clock=-0.6383E-3
 Ref_Ekin=0.0E0
 Dist_z='g', sig_clock=2.553E-3, C_sig_clock=4
 Dist_pz='i', LE=0.6E-3, phi_eff=0.0
 Dist_x='2DGaussian', sig_x=1.118E0, C_sig_x=0.8945
 Dist_y='2DGaussian', sig_y=1.118E0, C_sig_y=0.8945
/
"""
# name -> (particles, quasi-random)
SOURCES = {"qr10k.ini": (10000, True), "qr20k.ini": (20000, True), "qr40k.ini": (40000, True),
           **{f"rand10k_{i}.ini": (10000, False) for i in range(1, 6)}}
GRID = ("charge:nrad", "charge:nlong_in", "charge:nxf", "charge:nyf", "charge:nzf")


def grid(n: int) -> dict:
    return {key: n for key in GRID}


def step(divisor: int) -> dict:
    return {"newrun:h_max": 0.01 / divisor, "newrun:h_min": 0.001 / divisor}


def source(name: str) -> dict:
    return {"newrun:distribution": name}


# level -> (namelist overrides, relative cost); the production level re-tracks the archived deck.
LEVELS = {
    "production": ({}, 1),
    "source_qr10k": (source("qr10k.ini"), 1),
    **{f"source_rand10k_{i}": (source(f"rand10k_{i}.ini"), 1) for i in range(1, 6)},
    "particles_20k": (source("qr20k.ini"), 2),
    "particles_40k": (source("qr40k.ini"), 4),
    "grid_48": (grid(48), 3),
    "grid_64": (grid(64), 6),
    "step_half": (step(2), 2),
    "step_quarter": (step(4), 4),
    "combined_medium": ({**source("qr20k.ini"), **grid(48), **step(2)}, 12),
    "combined_fine": ({**source("qr40k.ini"), **grid(64), **step(4)}, 96),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def settings(config) -> list:
    """(role, run, evaluation_id, parameters) for the ten reported settings."""
    chosen = [("moga_derived_nominal", None, None, [v.nominal_value for v in config.design_variables])]
    roles = json.loads(REPRESENTATIVES.read_text())["roles"]
    picks = [(*c, PRIMARY) for c in TDR_CANDIDATES] + [(*TDR_CAMPAIGN_CLOSEST, TDR_RUNS)]
    picks += [(role, ref["run_id"], ref["evaluation_id"], PRIMARY) for role, ref in roles.items()]
    for role, run, evaluation_id, base in picks:
        matches = [r for r in read_run_data(base / run).results if r.evaluation_id == evaluation_id]
        if len(matches) != 1:
            raise ValueError(f"Expected one recorded {evaluation_id} in {run}")
        chosen.append((role, run, evaluation_id, list(matches[0].x_physical)))
    return chosen


def make_sources(directory: Path, generator: Path, sources: dict = SOURCES) -> dict:
    """Generate the source files; returns name -> SHA-256. Pseudo-random files must differ."""
    directory.mkdir(parents=True, exist_ok=True)
    digests = {}
    for name, (particles, quasi) in sources.items():
        deck = directory / f"{Path(name).stem}.gen.in"
        deck.write_text(SOURCE_INPUT.format(name=name, particles=particles, quasi=".T" if quasi else ".F"))
        subprocess.run([str(generator), deck.name], cwd=directory, check=True, capture_output=True)
        digests[name] = sha256(directory / name)
        time.sleep(1.1)  # the random mode is clock-seeded
    random = [digests[name] for name in sources if not sources[name][1]]
    if len(set(random)) != len(random):
        raise RuntimeError("Pseudo-random sources are not distinct; the generator seed did not change.")
    return digests


def build_template(config, directory: Path, sources: dict = SOURCES) -> object:
    """Template with the production deck and maps plus the generated sources."""
    simulation = config.simulation
    production = Path(simulation.template_dir)
    for name in [simulation.input_template, *simulation.static_files]:
        shutil.copy2(production / name, directory / name)
    static = list(simulation.static_files) + list(sources)
    return replace(config, simulation=replace(simulation, template_dir=str(directory), static_files=static))


class _ConvergencePlan(CandidateEvaluatorBase):
    def generate_evaluation_plan(self, candidates):
        tasks = [EvaluationTask(task_id=f"{role}__{level}", role=role, parameters=list(parameters),
                                namelist_overrides=dict(overrides) or None,
                                metadata={"role": role, "level": level, "run": run, "evaluation_id": evaluation_id,
                                          "purpose": "round2_convergence"})
                 for role, run, evaluation_id, parameters in candidates
                 for level, (overrides, _) in LEVELS.items()]
        # Longest runs first so the pool is not left waiting on the fine level.
        return sorted(tasks, key=lambda task: -LEVELS[task.metadata["level"]][1])


def record(outcome) -> dict:
    result = outcome.evaluated_result
    return {"task_id": outcome.task.task_id, **outcome.task.metadata,
            "status": outcome.execution_details.get("status"), "simulation_valid": result.simulation_valid,
            "runtime_s": result.runtime_s, "parameters": list(outcome.task.parameters),
            "namelist_overrides": outcome.task.namelist_overrides,
            "objectives": outcome.execution_details.get("objectives"),
            "diagnostics": outcome.execution_details.get("diagnostics"),
            "eval_dir": outcome.execution_details.get("eval_dir")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/revision_round2/convergence")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=24 * 3600, help="Per-run limit in seconds.")
    parser.add_argument("--roles", nargs="*", help="Restrict to these settings (pilot).")
    parser.add_argument("--levels", nargs="*", choices=list(LEVELS), help="Restrict to these levels (pilot).")
    parser.add_argument("--mock-evaluator", action="store_true", help="Rehearse the plumbing without ASTRA.")
    args = parser.parse_args(argv)
    out = args.output_dir
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} exists; outputs are immutable, choose a new directory.")
    production = load_config(PRODUCTION_CONFIG)
    template = out / "template"
    template.mkdir(parents=True)
    digests = make_sources(template, Path(production.simulation.executable).with_name("generator"))
    config = build_template(production, template)
    chosen = [c for c in settings(production) if not args.roles or c[0] in args.roles]
    plan = _ConvergencePlan(config=config, base_output_dir=out / "runs", num_workers=args.workers,
                            timeout=args.timeout, template_dir=template)
    tasks = [t for t in plan.generate_evaluation_plan(chosen) if not args.levels or t.metadata["level"] in args.levels]
    (out / "plan.json").write_text(json.dumps({
        "production_config_sha256": sha256(PRODUCTION_CONFIG), "astra_sha256": sha256(ROOT / "bin/astra"),
        "production_source_sha256": sha256(ROOT / PRODUCTION_SOURCE), "sources": digests,
        "source_input": SOURCE_INPUT, "levels": {k: {"overrides": v[0], "relative_cost": v[1]} for k, v in LEVELS.items()},
        "settings": [dict(zip(("role", "run", "evaluation_id", "parameters"), c)) for c in chosen],
        "tasks": [t.task_id for t in tasks], "timeout_s": args.timeout, "workers": args.workers,
        "mock": args.mock_evaluator, "simulation": asdict(config.simulation)}, indent=2, sort_keys=True) + "\n")
    stream = out / "convergence_results.jsonl"

    def append(outcome):
        with stream.open("a") as handle:
            handle.write(json.dumps(record(outcome), sort_keys=True, default=str) + "\n")

    evaluator = MockEvaluator(config=config) if args.mock_evaluator else None
    plan.evaluate_plan_parallel(tasks, evaluator=evaluator, on_task_complete=append, run_id="convergence")
    (out / "complete.json").write_text(json.dumps({"tasks": len(tasks), "results_sha256": sha256(stream)},
                                                  indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
