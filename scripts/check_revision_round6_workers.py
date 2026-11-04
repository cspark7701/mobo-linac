#!/usr/bin/env python3
"""Check that the round6 worker ceiling leaves completed tracking results unchanged.

Execution amendment 01 raises the ceiling from two to 22 workers. This infrastructure check
re-tracks an evenly spaced subset of already completed production-level settings with all
workers busy, in its own directory, and compares them with the historical ledgers and the
two-worker journal. Its attempts are outside the study budget and yield no new refined outcome.
"""
from __future__ import annotations
import argparse
import fcntl
import json
from pathlib import Path
import numpy as np
from mobo_linac.execution.mock import MockEvaluator
from evaluate_revision_round6_resolution import (MANIFEST, QUANTITIES, SPEC, ResolutionPlan, append_record,
                                                 check_nominal, make_tasks, read_records, result_value,
                                                 study_config, validate_inputs)
from prepare_revision_round6 import EVIDENCE, ROOT, execution_workers, sha

BASE = ROOT/'results/revision_round6'


def subset(frame, count):
    frame = frame.sort_values('setting_id').reset_index(drop=True)
    return frame.iloc[np.linspace(0, len(frame)-1, count, dtype=int)]


def compare(new, old, spec):
    """Largest relative difference from the two-worker journal; mismatches raise."""
    largest = 0.0
    for key, value in new.items():
        before = {**old[key]['objectives'], **old[key]['diagnostics']}
        after = {**value['objectives'], **value['diagnostics']}
        for name in QUANTITIES:
            if not np.isclose(after[name], before[name], rtol=spec['nominal_reproduction_rtol'],
                              atol=spec['nominal_reproduction_atol']):
                raise ValueError(f'Worker-count mismatch: {key}, {name}')
            largest = max(largest, abs(after[name]-before[name])/max(abs(before[name]), 1e-300))
    return largest


def receipt(new, old, workers, largest):
    ratios = [new[key]['runtime_s']/old[key]['runtime_s'] for key in new]
    return {'check': 'round6 worker-count reproduction (infrastructure; outside the study budget)',
            'workers': workers, 'settings': sorted(new), 'reproduced': True,
            'largest_relative_difference': largest,
            'mean_runtime_s': float(np.mean([new[key]['runtime_s'] for key in new])),
            'same_settings_two_worker_mean_runtime_s': float(np.mean([old[key]['runtime_s'] for key in new])),
            'median_runtime_ratio': float(np.median(ratios)), 'spec_sha256': sha(SPEC), 'manifest_sha256': sha(MANIFEST)}


def execute(out, study, spec, frame, workers, mock=False):
    if out.exists():
        raise ValueError('Output exists; a worker check is not resumed.')
    out.mkdir(parents=True)
    config = study_config(study, workers)
    plan = ResolutionPlan(config, base_output_dir=out/'runs', num_workers=workers,
                          timeout=spec['tracking_timeout_s'], template_dir=study/'template')
    journal = out/'results.jsonl'
    tasks = make_tasks(subset(frame, workers), spec, ['production'])
    plan.evaluate_plan_parallel(tasks, evaluator=MockEvaluator(config=config) if mock else None,
                                on_task_complete=lambda outcome: append_record(journal, result_value(outcome)),
                                run_id='round6_worker_check')
    return read_records(journal)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=BASE/'worker_check')
    args = parser.parse_args(argv)
    spec = json.loads(SPEC.read_text())
    frame = validate_inputs(spec)
    workers = execution_workers()
    study = BASE/'resolution'
    with (BASE/'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        new = execute(args.output_dir, study, spec, frame, workers)
    check_nominal(subset(frame, workers), new, spec)
    old = read_records(study/'results.jsonl')
    value = receipt(new, old, workers, compare(new, old, spec))
    (EVIDENCE/'r6_worker_check.json').write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
