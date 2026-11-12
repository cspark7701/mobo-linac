#!/usr/bin/env python3
"""Grid x particle convergence matrix for a subsample of the round6 settings.

``prepare`` selects 15 settings from the frozen round6 sample, builds the template with
quasi-random sources (the round6 40k file reused, 160k and 640k generated with the same
deck) and writes the specification. ``run`` executes the frozen plan after the
specification is committed. A reproduction gate runs first: the quarter-step 64-cell
40k level repeats the round6 combined-fine runs exactly and must match them. No result
from the matrix is used to choose levels, settings or tolerances.
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

from mobo_linac.config import load_config
from mobo_linac.execution.candidate_evaluator import EvaluationTask
from mobo_linac.execution.mock import MockEvaluator
from evaluate_revision_convergence import make_sources, build_template
from evaluate_revision_round6_resolution import (ResolutionPlan, append_record, read_records, result_value,
                                                 validate_inputs)
from analyze_revision_convergence import QUANTITIES
from prepare_revision_round6 import CONTROLS, ROOT, EVIDENCE, sha

FOLLOWUP = ROOT / 'docs/paper/revisions/convergence_followup'
SPEC = FOLLOWUP / 'rm_specification.json'
SETTINGS = FOLLOWUP / 'rm_settings.csv'
R6_SPEC = EVIDENCE / 'r6_specification.json'
R6_RESULTS = ROOT / 'results/revision_round6/resolution'
OUTPUT = ROOT / 'results/convergence_matrix'
SEED = 20261112
GRIDS = [32, 48, 64]
PARTICLES = [40, 160, 640]  # thousands
STEPS = {'half': (0.005, 0.0005), 'quarter': (0.0025, 0.00025)}
GATE = 'quarter_g64_n40k'
R6_GATE_LEVEL = 'combined_fine'
WORKERS = 22


def overrides(step, grid, particles):
    h_max, h_min = STEPS[step]
    return {'charge:nlong_in': grid, 'charge:nrad': grid, 'charge:nxf': grid, 'charge:nyf': grid,
            'charge:nzf': grid, 'newrun:distribution': f'qr{particles}k.ini',
            'newrun:h_max': h_max, 'newrun:h_min': h_min}


def levels():
    out = {f'half_g{g}_n{n}k': overrides('half', g, n) for g in GRIDS for n in PARTICLES}
    out[GATE] = overrides('quarter', 64, 40)
    out['quarter_g64_n640k'] = overrides('quarter', 64, 640)
    return out


def relative_cost(level):
    """Ordering key only (longest first); not a runtime prediction."""
    step, grid, particles = level.split('_')
    return (int(particles[1:-1]), int(grid[1:]), step == 'quarter')


def select(manifest_frame, seed=SEED):
    """Per method: one setting from each feasibility x boundary cell, plus one more at random."""
    rng = np.random.default_rng(seed)
    frame = manifest_frame.sort_values('setting_id').reset_index(drop=True)
    chosen = []
    for arm in sorted(frame.arm.unique()):
        rows = frame[frame.arm == arm]
        cells = rows.groupby(['physically_feasible', 'boundary'])
        if len(cells) != 4:
            raise ValueError(f'Expected four nonempty cells for {arm}.')
        picked = []
        for (feasible, boundary), cell in sorted(cells, key=lambda item: item[0]):
            row = cell.iloc[rng.integers(len(cell))]
            picked.append((row.setting_id, f'{feasible}|{boundary}', len(cell)))
        rest = rows[~rows.setting_id.isin([p[0] for p in picked])]
        extra = rest.iloc[rng.integers(len(rest))].setting_id
        for setting_id, cell, size in picked:
            chosen.append({'setting_id': setting_id, 'cell': cell, 'role': 'cell',
                           'inclusion_probability': 1 / size + (1 - 1 / size) / (len(rows) - 4)})
        cell_of = rows.set_index('setting_id').loc[extra]
        size = int(((rows.physically_feasible == cell_of.physically_feasible) &
                    (rows.boundary == cell_of.boundary)).sum())
        chosen.append({'setting_id': extra, 'cell': f'{cell_of.physically_feasible}|{cell_of.boundary}',
                       'role': 'extra', 'inclusion_probability': 1 / size + (1 - 1 / size) / (len(rows) - 4)})
    picked = pd.DataFrame(chosen)
    columns = ['setting_id', 'run', 'evaluation_id', 'arm', 'seed', 'physically_feasible', 'boundary', *CONTROLS]
    return picked.merge(frame[columns], on='setting_id', validate='one_to_one')


def make_tasks(settings, spec, names=None):
    names = names or list(spec['levels'])
    return [EvaluationTask(task_id=f'{row.setting_id}__{level}', role=row.setting_id,
                           parameters=[float(getattr(row, k)) for k in CONTROLS],
                           namelist_overrides=dict(spec['levels'][level]),
                           metadata={'role': row.setting_id, 'level': level, 'run': row.run,
                                     'evaluation_id': row.evaluation_id, 'purpose': 'convergence_matrix'})
            for level in sorted(names, key=relative_cost, reverse=True) for row in settings.itertuples()]


def check_gate(settings, records, r6_records, spec):
    """The gate level must reproduce the round6 combined-fine record of the same setting."""
    for row in settings.itertuples():
        new = records.get(f'{row.setting_id}__{GATE}')
        old = r6_records[f'{row.setting_id}__{R6_GATE_LEVEL}']
        if not new or not new['simulation_valid']:
            raise ValueError(f'Invalid gate run: {row.setting_id}')
        a = {**(new.get('objectives') or {}), **(new.get('diagnostics') or {})}
        b = {**(old.get('objectives') or {}), **(old.get('diagnostics') or {})}
        for key in QUANTITIES:
            if key not in a or not np.isclose(float(a[key]), float(b[key]), rtol=spec['gate_rtol'],
                                              atol=spec['gate_atol']):
                raise ValueError(f'Gate reproduction mismatch: {row.setting_id}, {key}')


def prepare(out=OUTPUT, spec_path=SPEC, settings_path=SETTINGS, mock=False, frame=None, r6_results=R6_RESULTS):
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output exists; outputs are immutable.')
    r6 = json.loads(R6_SPEC.read_text())
    if r6['levels'][R6_GATE_LEVEL] != levels()[GATE]:
        raise ValueError('Gate level no longer matches the round6 combined-fine level.')
    settings = select(validate_inputs(r6) if frame is None else frame)
    config = load_config(ROOT / 'configs/publication_200MeV.yaml')
    template = out / 'template'
    template.mkdir(parents=True)
    r6_template = r6_results / 'template'
    for name in ['qr40k.ini', 'qr40k.gen.in']:
        shutil.copy2(r6_template / name, template / name)
    generated = {'qr160k.ini': (160000, True), 'qr640k.ini': (640000, True)}
    if mock:
        for name in generated:
            shutil.copy2(ROOT / 'pal_photo2.ini', template / name)
    else:
        make_sources(template, Path(config.simulation.executable).with_name('generator'), generated)
    sources = {'qr40k.ini': None, **generated}
    build_template(config, template, sources)
    settings.to_csv(settings_path, index=False, float_format='%.17g')
    spec = {'version': 1, 'selection_seed': SEED, 'settings_sha256': sha(settings_path),
            'r6_specification_sha256': sha(R6_SPEC), 'r6_results_sha256': sha(r6_results / 'results.jsonl'),
            'levels': levels(), 'gate_level': GATE, 'gate_reference_level': R6_GATE_LEVEL,
            'gate_rtol': 1e-9, 'gate_atol': 1e-12, 'workers_total': WORKERS, 'threads_per_process': 1,
            'tracking_timeout_s': 86400, 'minimum_free_disk_GiB': 100, 'tracking_attempts': 15 * len(levels()),
            'objective_tolerance_relative': 0.01, 'adequacy_share': 0.8,
            'template_sha256': {p.name: sha(p) for p in sorted(template.iterdir()) if p.is_file()},
            'r6_qr40k_sha256': sha(r6_template / 'qr40k.ini'), 'mock': mock}
    if spec['template_sha256']['qr40k.ini'] != spec['r6_qr40k_sha256']:
        raise ValueError('The reused 40k source differs from the round6 file.')
    spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True) + '\n')
    return spec


def require_committed(paths):
    for path in paths:
        tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', str(path)], cwd=ROOT, capture_output=True)
        clean = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', str(path)], cwd=ROOT)
        if tracked.returncode or clean.returncode:
            raise ValueError(f'Freeze not committed: {path}')


def execute(out=OUTPUT, spec_path=SPEC, settings_path=SETTINGS, mock=False, resume=False, r6_results=R6_RESULTS):
    spec = json.loads(spec_path.read_text())
    if not mock:
        require_committed([spec_path, settings_path])
    if spec['mock'] != mock:
        raise ValueError('Specification and execution mode differ.')
    if sha(settings_path) != spec['settings_sha256']:
        raise ValueError('Settings checksum mismatch.')
    for name, digest in spec['template_sha256'].items():
        if sha(out / 'template' / name) != digest:
            raise ValueError(f'Template checksum mismatch: {name}')
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
    if not mock and sha(r6_results / 'results.jsonl') != spec['r6_results_sha256']:
        raise ValueError('Round6 journal changed since the freeze.')
    r6_records = read_records(r6_results / 'results.jsonl') if not mock else {}
    config = load_config(ROOT / 'configs/publication_200MeV.yaml')
    config = replace(config, simulation=replace(config.simulation, template_dir=str((out / 'template').resolve()),
                                                static_files=[*config.simulation.static_files, 'qr40k.ini',
                                                              'qr160k.ini', 'qr640k.ini']),
                     execution=replace(config.execution, max_workers=spec['workers_total'], retries=0))
    if not (out / 'plan.json').exists():
        (out / 'plan.json').write_text(json.dumps({
            'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'spec_sha256': sha(spec_path), 'started_unix': time.time(), 'mock': mock}, indent=2) + '\n')
    for phase, names in [('gate', [GATE]), ('matrix', [k for k in spec['levels'] if k != GATE])]:
        if phase == 'matrix' and not mock:
            check_gate(settings, records, r6_records, spec)
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
                                    run_id='convergence_matrix')
        records = read_records(journal)
        if any(t.task_id not in records for t in tasks):
            raise ValueError('Incomplete phase; retain pending evidence.')
        pending.unlink()
    expected = {t.task_id for t in make_tasks(settings, spec)}
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
