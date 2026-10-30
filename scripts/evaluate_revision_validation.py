#!/usr/bin/env python3
"""Refined-resolution validation of the primary comparison (consolidated round3, route b).

Stage ``ladder`` extends the C2-12 resolution check beyond its fine level (40k quasi-random
particles, 64-cell grids, a quarter of the production step), one factor at a time, for the
same ten reported settings: H/8 and H/16 steps, 80k particles, and 80k particles on 96-cell
grids. It selects the validation level.

Stage ``sample`` re-tracks a predeclared, method-balanced sample of archived observations at
one level. The sample is fixed by ``select_sample`` before any refined result is seen:
- every per-run feasible Pareto point of each arm (constraint-aware, unconstrained and
  scalarized BO, and the Sobol arm);
- every post-initialization observation whose production classification can change under the
  bounding shifts measured by C2-12 (sizes and divergences x0.78-1, bunch length +-1 %,
  energy +-0.05 MeV);
- a stratified random sample of the remaining post-initialization observations.

Production results are never modified; each stage writes a new, immutable directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_revision_convergence import (PRODUCTION_CONFIG, ROOT, SOURCE_INPUT, build_template, grid,
                                           make_sources, record, settings, sha256, source, step)
from mobo_linac.config import load_config
from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase, EvaluationTask
from mobo_linac.execution.mock import MockEvaluator
from mobo_linac.io.run_data import read_run_data
from revision_ledgers import ARMS, N_INIT, SEEDS, feasible, load_ledgers  # noqa: F401

RANDOM_PER_GROUP = 2
SAMPLE_SEED = 20261029
OBJECTIVES = ("norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV")
# Bounding shifts from the C2-12 check (evidence/r2_convergence_summary.csv).
SIZE_SCALE = (0.78, 1.0)
BUNCH_SCALE = (0.99, 1.01)
ENERGY_SHIFT_EV = (-0.05e6, 0.0, 0.05e6)

SOURCES = {"qr40k.ini": (40000, True), "qr80k.ini": (80000, True)}
FINE = {**source("qr40k.ini"), **grid(64), **step(4)}
# level -> (namelist overrides, relative cost); all levels refine the C2-12 fine level.
LEVELS = {
    "fine": (FINE, 1),
    "fine_step8": ({**FINE, **step(8)}, 2),
    "fine_step16": ({**FINE, **step(16)}, 4),
    "fine_p80k": ({**FINE, **source("qr80k.ini")}, 2),
    "fine_p80k_grid96": ({**FINE, **source("qr80k.ini"), **grid(96)}, 6),
}
LADDER = ("fine_step8", "fine_step16", "fine_p80k", "fine_p80k_grid96")


def nondominated(values: np.ndarray) -> np.ndarray:
    keep = np.ones(len(values), bool)
    for i, row in enumerate(values):
        keep[i] = not ((values <= row).all(axis=1) & (values < row).any(axis=1)).any()
    return keep


def select_sample(ledgers: pd.DataFrame, seed: int = SAMPLE_SEED) -> pd.DataFrame:
    """The predeclared validation sample; one row per archived observation, with its stratum."""
    data = ledgers[ledgers.simulation_valid.astype(bool)].copy()
    data["production_feasible"] = feasible(data)
    front = pd.Series(False, index=data.index)
    for _, group in data[data.production_feasible].groupby("run"):
        front[group.index[nondominated(group[list(OBJECTIVES)].to_numpy())]] = True
    shifts = [(s, b, e) for s in SIZE_SCALE for b in BUNCH_SCALE for e in ENERGY_SHIFT_EV]
    labels = pd.concat([feasible(data, *shift) for shift in shifts], axis=1)
    can_flip = labels.any(axis=1) != labels.all(axis=1)
    post = data.index_in_run > N_INIT
    data["stratum"] = None
    data.loc[front, "stratum"] = "front"
    data.loc[post & can_flip & ~front, "stratum"] = "boundary"
    rest = data[post & data.stratum.isna()]
    rng = np.random.default_rng(seed)
    picks = [rng.choice(group.index, size=min(RANDOM_PER_GROUP, len(group)), replace=False)
             for _, group in rest.groupby(["arm", "seed"])]
    data.loc[np.concatenate(picks), "stratum"] = "random"
    sample = data[data.stratum.notna()]
    columns = ["arm", "seed", "run", "evaluation_id", "index_in_run", "stratum", "production_feasible"]
    return sample[columns].sort_values(["arm", "seed", "index_in_run"]).reset_index(drop=True)


def sample_settings(sample: pd.DataFrame, arms: dict = ARMS) -> list:
    """(role, run, evaluation_id, parameters) with the recorded physical controls."""
    chosen = []
    for (arm, run), group in sample.groupby(["arm", "run"], sort=False):
        results = {r.evaluation_id: r for r in read_run_data(arms[arm] / run).results}
        for evaluation_id in group.evaluation_id:
            chosen.append((f"{run}__{evaluation_id}", run, evaluation_id, list(results[evaluation_id].x_physical)))
    return chosen


class _Plan(CandidateEvaluatorBase):
    levels: tuple = ()

    def generate_evaluation_plan(self, candidates):
        tasks = [EvaluationTask(task_id=f"{role}__{level}", role=role, parameters=list(parameters),
                                namelist_overrides=dict(LEVELS[level][0]),
                                metadata={"role": role, "level": level, "run": run, "evaluation_id": evaluation_id,
                                          "purpose": "round3_validation"})
                 for role, run, evaluation_id, parameters in candidates for level in self.levels]
        return sorted(tasks, key=lambda task: -LEVELS[task.metadata["level"]][1])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("ladder", "sample", "select"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--level", choices=list(LEVELS), help="Level of the sample stage.")
    parser.add_argument("--sample", type=Path, help="Predeclared sample CSV (sample stage).")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=48 * 3600, help="Per-run limit in seconds.")
    parser.add_argument("--limit", type=int, help="Track only the first N tasks (pilot).")
    parser.add_argument("--mock-evaluator", action="store_true", help="Rehearse the plumbing without ASTRA.")
    args = parser.parse_args(argv)
    out = args.output_dir
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} exists; outputs are immutable, choose a new directory.")
    out.mkdir(parents=True, exist_ok=True)
    if args.stage == "select":
        sample = select_sample(load_ledgers())
        sample.to_csv(out / "validation_sample.csv", index=False)
        print(sample.groupby(["arm", "stratum"]).size().unstack(fill_value=0).to_string())
        return 0
    production = load_config(PRODUCTION_CONFIG)
    if args.stage == "ladder":
        chosen, levels = settings(production), LADDER
    else:
        if not (args.level and args.sample):
            raise SystemExit("The sample stage needs --level and --sample.")
        chosen, levels = sample_settings(pd.read_csv(args.sample)), (args.level,)
    template = out / "template"
    template.mkdir()
    digests = make_sources(template, Path(production.simulation.executable).with_name("generator"), SOURCES)
    config = build_template(production, template, SOURCES)
    plan = _Plan(config=config, base_output_dir=out / "runs", num_workers=args.workers, timeout=args.timeout,
                 template_dir=template)
    plan.levels = levels
    tasks = plan.generate_evaluation_plan(chosen)[:args.limit]
    (out / "plan.json").write_text(json.dumps({
        "stage": args.stage, "production_config_sha256": sha256(PRODUCTION_CONFIG),
        "astra_sha256": sha256(ROOT / "bin/astra"), "sources": digests, "source_input": SOURCE_INPUT,
        "levels": {k: {"overrides": LEVELS[k][0], "relative_cost": LEVELS[k][1]} for k in levels},
        "sample_sha256": sha256(args.sample) if args.sample else None,
        "settings": [dict(zip(("role", "run", "evaluation_id", "parameters"), c)) for c in chosen],
        "tasks": [t.task_id for t in tasks], "timeout_s": args.timeout, "workers": args.workers,
        "mock": args.mock_evaluator}, indent=2, sort_keys=True, default=str) + "\n")
    stream = out / "validation_results.jsonl"

    def append(outcome):
        with stream.open("a") as handle:
            handle.write(json.dumps(record(outcome), sort_keys=True, default=str) + "\n")

    evaluator = MockEvaluator(config=config) if args.mock_evaluator else None
    plan.evaluate_plan_parallel(tasks, evaluator=evaluator, on_task_complete=append, run_id=f"validation_{args.stage}")
    (out / "complete.json").write_text(json.dumps(
        {"tasks": len(tasks), "results_sha256": hashlib.sha256(stream.read_bytes()).hexdigest()}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
