#!/usr/bin/env python3
"""Round2 revision runs for named reference settings (consolidated tasks C2-07 and C2-08).

1. Re-evaluate the MOGA-derived nominal setting once with the production pipeline.
2. Apply the archived lattice-jitter protocol (50 trials, common seed 42) to that setting.
3. Apply the same protocol to the two primary observations that pass the TDR optimization
   inequalities, classified against the TDR profile.

No archived production output is modified; every result goes under ``--output-dir``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from mobo_linac.config import load_config
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase, EvaluationTask
from mobo_linac.execution.mock import MockEvaluator
from mobo_linac.io.run_data import read_run_data
from mobo_linac.robustness.evaluator import RobustnessEvaluator
from mobo_linac.result_schema import ResultSchema

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_CONFIG = ROOT / "configs/publication_200MeV.yaml"
TDR_CONFIG = ROOT / "configs/revision_tdr_200MeV.yaml"
PRIMARY = ROOT / "results/paper_production/04_primary/benchmark/per_seed"
MOGA_DECK = Path("/home/cspark/Work/projects/linac/beam_tracking/astra.in")
MOGA_NOTEBOOK = Path("/home/cspark/Work/projects/linac/beam_tracking/linac_optimization-parallel2.ipynb")
# Values printed by the notebook's rerun of the MOGA-derived deck (cells 12 and 15).
MOGA_NOTEBOOK_VALUES = {"norm_emit_x_m_rad": 3.4728e-6, "norm_emit_y_m_rad": 3.2968e-6,
                        "sigma_energy_eV": 394.19e3, "mean_kinetic_energy_eV": 200.19e6}
# Primary observations that pass the TDR optimization inequalities (evidence/c01_tdr_candidates.csv).
TDR_CANDIDATES = (("tdr_candidate_a", "constrained_qlognehvi_seed_44", "eval_000079"),
                  ("tdr_candidate_b", "constrained_qlognehvi_seed_51", "eval_000099"))
JITTER_TRIALS = 50
JITTER_SEED = 42  # The archived representatives used seed 42 with common random numbers.


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _SingleEvaluation(CandidateEvaluatorBase):
    def generate_evaluation_plan(self, candidates):
        return [EvaluationTask(task_id=role, role=role, parameters=list(parameters),
                               metadata={"role": role, "purpose": "round2_reference_evaluation"})
                for role, parameters in candidates]


def moga_parameters(config) -> list:
    """The configured nominal vector, after checking it is the MOGA-derived deck."""
    deck = ROOT / config.simulation.input_template
    if MOGA_DECK.exists() and sha256(MOGA_DECK) != sha256(deck):
        raise ValueError(f"{MOGA_DECK} no longer matches {deck}; the nominal is not the MOGA-derived deck.")
    return [variable.nominal_value for variable in config.design_variables]


def evaluate_moga(config, output_dir: Path, evaluator=None) -> EvaluationResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    study = _SingleEvaluation(config=config, base_output_dir=output_dir, num_workers=1,
                              timeout=config.execution.timeout_sec)
    tasks = study.generate_evaluation_plan([("moga_derived_nominal", moga_parameters(config))])
    outcome = study.evaluate_plan_parallel(tasks, evaluator=evaluator, run_id="round2_moga_reference")[0]
    result = outcome.evaluated_result
    schema = ResultSchema.from_config(config)
    record = {
        "role": "moga_derived_nominal",
        "parameters": dict(zip([v.name for v in config.design_variables], result.x_physical)),
        "result": result.to_dict(),
        "objectives": dict(zip(schema.physical_columns, result.objectives_physical or [])),
        "execution_details": outcome.execution_details,
        "previous_record": {"source": str(MOGA_NOTEBOOK), "cells": [12, 15], "values": MOGA_NOTEBOOK_VALUES},
        "deck": {"moga_deck": str(MOGA_DECK), "moga_deck_sha256": sha256(MOGA_DECK) if MOGA_DECK.exists() else None,
                 "template_sha256": sha256(ROOT / config.simulation.input_template)},
    }
    (output_dir / "moga_reference.json").write_text(json.dumps(record, indent=2, sort_keys=True, default=str))
    return result


def tdr_candidates(config) -> list:
    chosen = []
    for role, run, evaluation_id in TDR_CANDIDATES:
        matches = [r for r in read_run_data(PRIMARY / run).results if r.evaluation_id == evaluation_id]
        if len(matches) != 1:
            raise ValueError(f"Expected one recorded {evaluation_id} in {run}")
        chosen.append((role, matches[0]))
    return chosen


def jitter(config, candidates, roles, output_dir: Path, workers: int, evaluator=None) -> list:
    output_dir.mkdir(parents=True, exist_ok=True)
    study = RobustnessEvaluator(config=config, base_output_dir=output_dir, num_workers=workers,
                                timeout=config.execution.timeout_sec)
    summaries = study.evaluate_candidates(candidates, num_perturbations=JITTER_TRIALS, seed=JITTER_SEED,
                                          roles=roles, evaluator=evaluator, run_id=output_dir.name)
    (output_dir / "jitter_summary.json").write_text(json.dumps(summaries, indent=2, sort_keys=True, default=str))
    return summaries


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/revision_round2/references")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--mock-evaluator", action="store_true", help="Rehearse the plumbing without ASTRA.")
    args = parser.parse_args(argv)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"{args.output_dir} exists; outputs are immutable, choose a new directory.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    production, tdr = load_config(PRODUCTION_CONFIG), load_config(TDR_CONFIG)
    mock = (lambda config: MockEvaluator(config=config)) if args.mock_evaluator else (lambda config: None)

    moga = evaluate_moga(production, args.output_dir / "moga_nominal", mock(production))
    jitter(production, [moga], ["moga_derived_nominal"], args.output_dir / "moga_jitter", args.workers,
           mock(production))
    chosen = tdr_candidates(production)
    jitter(tdr, [result for _, result in chosen], [role for role, _ in chosen],
           args.output_dir / "tdr_candidate_jitter", args.workers, mock(tdr))
    (args.output_dir / "plan.json").write_text(json.dumps({
        "production_config_sha256": sha256(PRODUCTION_CONFIG), "tdr_config_sha256": sha256(TDR_CONFIG),
        "jitter_trials": JITTER_TRIALS, "jitter_seed": JITTER_SEED, "mock": args.mock_evaluator,
        "tdr_candidates": [dict(zip(("role", "run", "evaluation_id"), c)) for c in TDR_CANDIDATES],
        "tdr_constraints": asdict(tdr.constraints)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
