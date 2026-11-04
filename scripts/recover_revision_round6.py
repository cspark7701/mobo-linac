#!/usr/bin/env python3
"""Audited recovery of the round6 numerical study after the user's pause.

Verifies the pause checkpoint against the live evidence and every journal checksum, inspects
the interrupted attempts and confirms that every other pending identity never started. The
interrupted attempts stay in place. ASTRA cannot continue them, so each identity is tracked
again in the isolated ``recovery_01`` directory and its record, naming the interrupted attempt,
is appended to the study journal. The pending list and the pause marker are then archived there.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import shutil
import numpy as np
from mobo_linac.execution.mock import MockEvaluator
from evaluate_revision_round6_resolution import (SPEC, ResolutionPlan, append_record, make_tasks, read_records,
                                                 result_value, study_config, validate_inputs)
from prepare_revision_round6 import EVIDENCE, ROOT, sha

BASE = ROOT/'results/revision_round6'
CHECKPOINT = BASE/'pause_checkpoints/20261101T221548Z'
FILES = ('plan.json', 'pending.json', 'results.jsonl', 'nominal_complete.json')
RECOVERY_WORKERS = 2
EXIT_M = 16.2


def verify_snapshot(study, checkpoint):
    """The checkpoint copy and the live evidence still match the pause manifest."""
    manifest = json.loads((checkpoint/'pause_manifest.json').read_text())
    for name, digest in manifest['files_sha256'].items():
        if sha(checkpoint/name) != digest or sha(study/name) != digest:
            raise ValueError(f'Pause snapshot checksum mismatch: {name}')
    records = read_records(study/'results.jsonl')
    if len(records) != manifest['completed_count']:
        raise ValueError('Journal count differs from the pause manifest.')
    marker = json.loads((study/'nominal_complete.json').read_text())
    lines = (study/'results.jsonl').read_bytes().splitlines(keepends=True)[:marker['tasks']]
    if hashlib.sha256(b''.join(lines)).hexdigest() != marker['results_sha256']:
        raise ValueError('Nominal marker does not match the start of the journal.')
    return manifest, records


def inspect_attempt(run, identity):
    """Evidence that one started attempt was interrupted and that its inputs are intact."""
    attempts = sorted((run/'work'/f'eval_{identity}').glob('attempt_*'))
    if len(attempts) != 1:
        raise ValueError(f'Expected one interrupted attempt: {identity}')
    attempt = attempts[0]
    provenance = run/'provenance'/f'eval_{identity}'/attempt.name
    started = json.loads((provenance/'attempt_started.json').read_text())
    if started['attempt_id'] != attempt.name or (provenance/'manifest.json').exists():
        raise ValueError(f'Attempt record is not an unfinished start: {identity}')
    if sha(attempt/'astra.in') != sha(provenance/'inputs/astra.in'):
        raise ValueError(f'Interrupted input deck differs from its provenance: {identity}')
    if list(attempt.glob('astra.[0-9]*.001')):
        raise ValueError(f'Interrupted attempt has an exit distribution: {identity}')
    last_z = float(np.atleast_2d(np.loadtxt(attempt/'astra.Xemit.001'))[-1, 0])
    if last_z >= EXIT_M:
        raise ValueError(f'Interrupted attempt reached the exit plane: {identity}')
    return {'attempt_id': attempt.name, 'start_time': started['start_time'], 'last_z_m': last_z,
            'astra_in_sha256': sha(attempt/'astra.in')}


def inspect_pending(study, manifest, records):
    pending = set(json.loads((study/'pending.json').read_text()))-set(records)
    run = study/'runs/round6_resolution'
    started = {identity for identity in pending if (run/'work'/f'eval_{identity}').exists()}
    if started != set(manifest['interrupted_attempts']):
        raise ValueError('Started pending identities differ from the pause manifest.')
    return {identity: inspect_attempt(run, identity) for identity in sorted(started)}, len(pending)-len(started)


def recover(study, checkpoint, marker, spec, frame, mock=False):
    out = study/'recovery_01'
    if out.exists():
        raise ValueError('Recovery directory exists; inspect it rather than repeating the recovery.')
    manifest, records = verify_snapshot(study, checkpoint)
    interrupted, never_started = inspect_pending(study, manifest, records)
    plan = json.loads((study/'plan.json').read_text())
    for name, digest in plan['template_sha256'].items():
        if sha(study/'template'/name) != digest:
            raise ValueError('Retained template checksum mismatch.')
    out.mkdir()
    (out/'inspection.json').write_text(json.dumps(interrupted, indent=2, sort_keys=True)+'\n')
    shutil.copy2(study/'pending.json', out/'pending_at_pause.json')
    config = study_config(study, RECOVERY_WORKERS)
    tasks = [t for t in make_tasks(frame, spec, list(spec['levels'])) if t.task_id in interrupted]
    journal = out/'results.jsonl'
    executor = ResolutionPlan(config, base_output_dir=out/'runs', num_workers=RECOVERY_WORKERS,
                              timeout=spec['tracking_timeout_s'], template_dir=study/'template')
    executor.evaluate_plan_parallel(tasks, evaluator=MockEvaluator(config=config) if mock else None,
                                    on_task_complete=lambda o: append_record(journal, result_value(o)),
                                    run_id='round6_resolution_recovery')
    retried = read_records(journal)
    if set(retried) != set(interrupted):
        raise ValueError('Recovery did not account for every interrupted identity; study journal unchanged.')
    before = sha(study/'results.jsonl')
    for identity in sorted(retried):
        append_record(study/'results.jsonl', {**retried[identity], 'recovery_of_attempt': interrupted[identity]['attempt_id']})
    (study/'pending.json').unlink()
    shutil.move(str(marker), out/'PAUSED_archived.json')
    receipt = {'recovery': 1, 'authorized_by': 'author', 'date': '2026-11-04', 'workers': RECOVERY_WORKERS,
               'interrupted_attempts': interrupted, 'interrupted_attempts_retained': True,
               'pending_never_started': never_started, 'attempts_added': len(interrupted),
               'retried': {k: {'simulation_valid': v['simulation_valid'], 'runtime_s': v['runtime_s']} for k, v in retried.items()},
               'journal_sha256_before': before, 'journal_sha256_after': sha(study/'results.jsonl'),
               'journal_records_after': len(read_records(study/'results.jsonl')), 'mock': mock,
               'pending_at_pause_sha256': sha(out/'pending_at_pause.json'), 'spec_sha256': plan['spec_sha256']}
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorized', action='store_true', help='The author authorized the restart.')
    parser.add_argument('--inspect-only', action='store_true', help='Verify and inspect without tracking.')
    args = parser.parse_args(argv)
    study = BASE/'resolution'
    spec = json.loads(SPEC.read_text())
    frame = validate_inputs(spec)
    with (BASE/'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.inspect_only:
            manifest, records = verify_snapshot(study, CHECKPOINT)
            interrupted, never_started = inspect_pending(study, manifest, records)
            print(json.dumps({'records': len(records), 'interrupted': interrupted,
                              'pending_never_started': never_started}, indent=2, sort_keys=True))
            return 0
        if not args.authorized:
            raise SystemExit('Recovery re-tracks and archives the pause marker; pass --authorized.')
        receipt = recover(study, CHECKPOINT, BASE/'PAUSED.json', spec, frame)
    (EVIDENCE/'r6_recovery_01.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
