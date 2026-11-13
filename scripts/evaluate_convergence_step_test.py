#!/usr/bin/env python3
"""Step 3a of the emittance-convergence follow-up: step size versus space-charge update.

At 64 cells and 160k particles, on the 15 step 2 settings (rq_protocol.md), it tracks:
- half, quarter and eighth step with the template's space-charge reuse (Max_count=10);
- half and quarter step with the field recomputed every step (Max_count=1);
- three half-step replicates from the step 2 160k source rotated about z.

``prepare`` builds the template from the step 2 template (its hashes are checked), writes
the rotated sources and the specification. ``run`` executes the frozen plan after the
specification is committed. A gate runs first: ``half_mc10`` repeats step 2's
``half_g64_n160k`` exactly and must match it. No result is used to choose levels.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

import evaluate_convergence_matrix as cm
from mobo_linac.config import load_config
from mobo_linac.execution.candidate_evaluator import EvaluationTask
from mobo_linac.execution.mock import MockEvaluator
from evaluate_revision_convergence import build_template
from evaluate_revision_round6_resolution import ResolutionPlan, append_record, read_records, result_value
from analyze_revision_convergence import QUANTITIES
from prepare_revision_round6 import CONTROLS, ROOT, sha

FOLLOWUP = cm.FOLLOWUP
SPEC = FOLLOWUP / 'rq_specification.json'
SETTINGS = cm.SETTINGS  # the step 2 settings file, reused unchanged and checked by hash
RM_SPEC = cm.SPEC
RM_RESULTS = cm.OUTPUT
OUTPUT = ROOT / 'results/convergence_step_test'
GATE = 'half_mc10'
RM_GATE_LEVEL = 'half_g64_n160k'
REFERENCE_FEASIBILITY_LEVEL = 'half_g64_n640k'
ANGLES = {'rot1': 40.0, 'rot2': 80.0, 'rot3': 160.0}
STEPS = {'half': (0.005, 0.0005), 'quarter': (0.0025, 0.00025), 'eighth': (0.00125, 0.000125)}
STATIC = ['gun.dat', 'PAL_SOL_A.dat', 'TWS_Sband.dat', 'pal_photo2.ini', 'astra.in', 'qr160k.ini', 'qr160k.gen.in']
# Longest first after the gate; Max_count=1 cost measured by the pre-freeze probe.
ORDER = ['eighth_mc10', 'quarter_mc1', 'quarter_mc10', 'half_mc1', 'half_mc10_rot1', 'half_mc10_rot2',
         'half_mc10_rot3']
WORKERS = 22
BOOTSTRAP_SEED = 20261113


def overrides(step, max_count=None, source='qr160k.ini'):
    out = cm.overrides('half', 64, 160)
    out['newrun:h_max'], out['newrun:h_min'] = STEPS[step]
    out['newrun:distribution'] = source
    if max_count is not None:
        out['charge:max_count'] = max_count
    return out


def levels():
    out = {GATE: overrides('half'), 'half_mc1': overrides('half', 1), 'quarter_mc10': overrides('quarter'),
           'quarter_mc1': overrides('quarter', 1), 'eighth_mc10': overrides('eighth')}
    out.update({f'half_mc10_{k}': overrides('half', source=f'qr160k_{k}.ini') for k in ANGLES})
    return out


def rotate_source(source: Path, target: Path, angle_deg: float):
    """Rotate (x, y) and (px, py) of every ordinary particle about z; the reference particle
    (first line) and probe particles (flag -3) are kept unchanged. Returns the invariants."""
    data = np.loadtxt(source)
    out = data.copy()
    c, s = np.cos(np.radians(angle_deg)), np.sin(np.radians(angle_deg))
    rows = np.ones(len(data), dtype=bool)
    rows[0] = False
    rows &= data[:, 9] != -3
    for i, j in [(0, 1), (3, 4)]:
        out[rows, i] = c * data[rows, i] - s * data[rows, j]
        out[rows, j] = s * data[rows, i] + c * data[rows, j]
    with target.open('w') as handle:
        for row in out:
            handle.write(' '.join(f'{v:18.10E}' for v in row[:8]) + f' {int(row[8]):3d} {int(row[9]):3d}\n')
    return check_rotation(source, target, angle_deg)


def _invariants(data):
    body = data[1:][data[1:, 9] != -3]
    x, y, px, py = body[:, 0], body[:, 1], body[:, 3], body[:, 4]
    return {'r2': np.mean(x ** 2 + y ** 2), 'p2': np.mean(px ** 2 + py ** 2), 'rp': np.mean(x * px + y * py),
            'lz': np.mean(x * py - y * px), 'charge': body[:, 7].sum(), 'z': body[:, 2].sum(),
            'pz': body[:, 5].sum(), 'clock': body[:, 6].sum(), 'n': float(len(body))}


def check_rotation(source: Path, target: Path, angle_deg: float, rtol=1e-9):
    a, b = np.loadtxt(source), np.loadtxt(target)
    if a.shape != b.shape or np.array_equal(a, b):
        raise ValueError(f'Rotated source is not a distinct file of the same shape: {target.name}')
    if not np.array_equal(a[0], b[0]) or not np.array_equal(a[a[:, 9] == -3], b[b[:, 9] == -3]):
        raise ValueError(f'Reference or probe particles changed: {target.name}')
    if not np.array_equal(a[:, [2, 5, 6, 7, 8, 9]], b[:, [2, 5, 6, 7, 8, 9]]):
        raise ValueError(f'Longitudinal columns changed: {target.name}')
    ia, ib = _invariants(a), _invariants(b)
    # The correlations are near zero at the cathode; compare them on the scale sqrt(<r^2><p^2>).
    scale = {'rp': np.sqrt(ia['r2'] * ia['p2']), 'lz': np.sqrt(ia['r2'] * ia['p2'])}
    for key in ia:
        if not np.isclose(ia[key], ib[key], rtol=rtol, atol=rtol * scale.get(key, 0.0)):
            raise ValueError(f'Rotation invariant {key} changed: {target.name}')
    return {'angle_deg': angle_deg, **{k: float(v) for k, v in ib.items()}}


def make_tasks(settings, spec, names=None):
    names = names or [GATE, *ORDER]
    return [EvaluationTask(task_id=f'{row.setting_id}__{level}', role=row.setting_id,
                           parameters=[float(getattr(row, k)) for k in CONTROLS],
                           namelist_overrides=dict(spec['levels'][level]),
                           metadata={'role': row.setting_id, 'level': level, 'run': row.run,
                                     'evaluation_id': row.evaluation_id, 'purpose': 'convergence_step_test'})
            for level in names for row in settings.itertuples()]


def check_gate(settings, records, rm_records, spec):
    """The gate level must reproduce step 2's half_g64_n160k record of the same setting."""
    for row in settings.itertuples():
        new = records.get(f'{row.setting_id}__{GATE}')
        old = rm_records[f'{row.setting_id}__{RM_GATE_LEVEL}']
        if not new or not new['simulation_valid']:
            raise ValueError(f'Invalid gate run: {row.setting_id}')
        a = {**(new.get('objectives') or {}), **(new.get('diagnostics') or {})}
        b = {**(old.get('objectives') or {}), **(old.get('diagnostics') or {})}
        for key in QUANTITIES:
            if key not in a or not np.isclose(float(a[key]), float(b[key]), rtol=spec['gate_rtol'],
                                              atol=spec['gate_atol']):
                raise ValueError(f'Gate reproduction mismatch: {row.setting_id}, {key}')


def feasible_strata(rm_records, settings):
    """Feasibility at step 2's reference level; fixed in the specification before any run."""
    return {row.setting_id: bool(rm_records[f'{row.setting_id}__{REFERENCE_FEASIBILITY_LEVEL}']
                                 ['physically_feasible']) for row in settings.itertuples()}


def prepare(out=OUTPUT, spec_path=SPEC, settings_path=SETTINGS, rm_spec=RM_SPEC, rm_results=RM_RESULTS, mock=False):
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output exists; outputs are immutable.')
    step2 = json.loads(rm_spec.read_text())
    complete = json.loads((rm_results / 'complete.json').read_text())
    if sha(rm_results / 'results.jsonl') != complete['results_sha256'] or complete['spec_sha256'] != sha(rm_spec):
        raise ValueError('Step 2 results do not match their completion record.')
    if sha(settings_path) != step2['settings_sha256']:
        raise ValueError('Settings differ from the step 2 settings.')
    if step2['levels'][RM_GATE_LEVEL] != levels()[GATE]:
        raise ValueError('Gate level no longer matches step 2.')
    template = out / 'template'
    template.mkdir(parents=True)
    for name in STATIC:
        shutil.copy2(rm_results / 'template' / name, template / name)
        if sha(template / name) != step2['template_sha256'][name]:
            raise ValueError(f'Step 2 template file changed: {name}')
    rotations = {f'qr160k_{k}.ini': rotate_source(template / 'qr160k.ini', template / f'qr160k_{k}.ini', angle)
                 for k, angle in ANGLES.items()}
    config = load_config(ROOT / 'configs/publication_200MeV.yaml')
    build_template(config, template, {'qr160k.ini': None, **rotations})
    for name in STATIC:  # build_template recopies the production files; they must still match step 2
        if sha(template / name) != step2['template_sha256'][name]:
            raise ValueError(f'Template file differs from step 2: {name}')
    settings = pd.read_csv(settings_path)
    rm_records = read_records(rm_results / 'results.jsonl')
    spec = {'version': 1, 'settings_file': str(settings_path.relative_to(ROOT)) if settings_path.is_relative_to(ROOT)
            else settings_path.name, 'settings_sha256': sha(settings_path),
            'rm_specification_sha256': sha(rm_spec), 'rm_results_sha256': complete['results_sha256'],
            'levels': levels(), 'order_after_gate': ORDER, 'gate_level': GATE, 'gate_reference_level': RM_GATE_LEVEL,
            'gate_rtol': 1e-9, 'gate_atol': 1e-12, 'rotation_angles_deg': ANGLES, 'rotation_invariants': rotations,
            'feasible_at_reference': feasible_strata(rm_records, settings),
            'reference_feasibility_level': REFERENCE_FEASIBILITY_LEVEL,
            'workers_total': WORKERS, 'threads_per_process': 1, 'tracking_timeout_s': 86400,
            'minimum_free_disk_GiB': 100, 'tracking_attempts': len(settings) * len(levels()),
            'objective_tolerance_relative': 0.01, 'systematic_interval_limit_relative': 0.02,
            'adequacy_share': 0.8, 'noise_band_sd_multiple': 2.0, 'mechanism_update_threshold': 0.7,
            'mechanism_step_threshold': 0.3, 'mechanism_min_denominator_relative': 0.001,
            'bootstrap_resamples': 2000, 'bootstrap_seed': BOOTSTRAP_SEED,
            'template_sha256': {p.name: sha(p) for p in sorted(template.iterdir()) if p.is_file()}, 'mock': mock}
    spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True) + '\n')
    return spec


def execute(out=OUTPUT, spec_path=SPEC, settings_path=SETTINGS, rm_results=RM_RESULTS, mock=False, resume=False):
    spec = json.loads(spec_path.read_text())
    if not mock:
        cm.require_committed([spec_path, settings_path])
    if spec['mock'] != mock:
        raise ValueError('Specification and execution mode differ.')
    if sha(settings_path) != spec['settings_sha256']:
        raise ValueError('Settings checksum mismatch.')
    for name, digest in spec['template_sha256'].items():
        if sha(out / 'template' / name) != digest:
            raise ValueError(f'Template checksum mismatch: {name}')
    if sha(rm_results / 'results.jsonl') != spec['rm_results_sha256']:
        raise ValueError('Step 2 journal changed since the freeze.')
    settings = pd.read_csv(settings_path)
    journal = out / 'results.jsonl'
    if journal.exists() and not resume:
        raise ValueError('Journal exists; require --resume.')
    pending = out / 'pending.json'
    records = read_records(journal)
    if pending.exists():
        unfinished = set(json.loads(pending.read_text())) - set(records)
        if unfinished:
            raise ValueError('Interrupted attempts require explicit recovery: ' + str(sorted(unfinished)[:3]))
        pending.unlink()
    rm_records = read_records(rm_results / 'results.jsonl')
    sources = [k for k in spec['template_sha256'] if k.startswith('qr160k') and k.endswith('.ini')]
    config = load_config(ROOT / 'configs/publication_200MeV.yaml')
    config = replace(config, simulation=replace(config.simulation, template_dir=str((out / 'template').resolve()),
                                                static_files=[*config.simulation.static_files, *sources]),
                     execution=replace(config.execution, max_workers=spec['workers_total'], retries=0))
    if not (out / 'plan.json').exists():
        (out / 'plan.json').write_text(json.dumps({
            'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'spec_sha256': sha(spec_path), 'started_unix': time.time(), 'mock': mock}, indent=2) + '\n')
    for phase, names in [('gate', [GATE]), ('levels', spec['order_after_gate'])]:
        if phase == 'levels' and not mock:
            check_gate(settings, records, rm_records, spec)
        tasks = [t for t in make_tasks(settings, spec, names) if t.task_id not in records]
        if not tasks:
            continue
        if shutil.disk_usage(out).free < spec['minimum_free_disk_GiB'] * 1024 ** 3:
            raise RuntimeError('Insufficient disk space; preserve evidence and pause.')
        pending.write_text(json.dumps([t.task_id for t in tasks]) + '\n')
        plan = ResolutionPlan(config, base_output_dir=out / 'runs', num_workers=spec['workers_total'],
                              timeout=spec['tracking_timeout_s'], template_dir=out / 'template')
        plan.evaluate_plan_parallel(tasks, evaluator=MockEvaluator(config=config) if mock else None,
                                    on_task_complete=lambda outcome: append_record(journal, result_value(outcome)),
                                    run_id='convergence_step_test')
        records = read_records(journal)
        if any(t.task_id not in records for t in tasks):
            raise ValueError('Incomplete phase; retain pending evidence.')
        pending.unlink()
    expected = {t.task_id for t in make_tasks(settings, spec, [GATE, *spec['order_after_gate']])}
    if set(records) != expected:
        raise ValueError('Journal does not match the frozen plan.')
    (out / 'complete.json').write_text(json.dumps({'tasks': len(records), 'results_sha256': sha(journal),
                                                   'spec_sha256': sha(spec_path), 'mock': mock}, indent=2) + '\n')
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'run'])
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
        os.environ[name] = '1'
    if args.stage == 'prepare':
        prepare(args.output_dir)
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        execute(args.output_dir, resume=args.resume)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
