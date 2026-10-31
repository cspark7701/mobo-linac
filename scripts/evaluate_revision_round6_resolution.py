#!/usr/bin/env python3
"""Execute the frozen round6 numerical study with immutable evidence and two workers."""
from __future__ import annotations
import argparse
from dataclasses import replace
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import numpy as np
import pandas as pd
from mobo_linac.config import load_config
from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase, EvaluationTask
from mobo_linac.execution.mock import MockEvaluator
from evaluate_revision_convergence import make_sources, build_template, record
from prepare_revision_round6 import CONTROLS, ROOT, EVIDENCE, sha
from analyze_revision_convergence import QUANTITIES

SPEC = EVIDENCE / 'r6_specification.json'
MANIFEST = EVIDENCE / 'r6_sampling_manifest.csv'


def validate_inputs(spec, manifest=MANIFEST):
    if sha(manifest) != spec['sample_manifest_sha256']:
        raise ValueError('Frozen sample manifest checksum mismatch.')
    for name, digest in spec['input_sha256'].items():
        if sha(ROOT/name) != digest:
            raise ValueError(f'Frozen input checksum mismatch: {name}')
    frame = pd.read_csv(manifest)
    if frame.setting_id.duplicated().any() or len(frame) != spec['sample_size']:
        raise ValueError('Duplicate or incomplete selected identities.')
    for run, rows in frame.groupby('run'):
        ledger = pd.read_csv(ROOT/'results/paper_production/04_primary/benchmark/per_seed'/run/'evaluations.csv')
        if ledger.evaluation_id.duplicated().any():
            raise ValueError('Duplicate historical evaluation identity.')
        ledger = ledger.set_index('evaluation_id')
        for row in rows.itertuples():
            expected = ledger.loc[row.evaluation_id, CONTROLS].to_numpy(dtype=float)
            actual = np.array([getattr(row,k) for k in CONTROLS])
            if not np.allclose(expected, actual, rtol=0, atol=1e-12):
                raise ValueError(f'Historical control mismatch: {row.setting_id}')
    return frame


def read_records(path):
    records = {}
    if not path.exists():
        return records
    for line in path.read_text().splitlines():
        envelope = json.loads(line)
        value = envelope['record']
        payload = json.dumps(value, sort_keys=True, allow_nan=False)
        if hashlib.sha256(payload.encode()).hexdigest() != envelope['sha256']:
            raise ValueError('Result journal checksum mismatch.')
        key = value['task_id']
        if key in records:
            raise ValueError('Duplicate result identity; do not silently choose one.')
        records[key] = value
    return records


def json_measurements(value):
    """Represent unavailable/nonfinite measurements as null without inventing values."""
    if isinstance(value, dict):
        return {key: json_measurements(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_measurements(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def append_record(path, value):
    value = json_measurements(value)
    payload = json.dumps(value, sort_keys=True, allow_nan=False)
    envelope = {'record': value, 'sha256': hashlib.sha256(payload.encode()).hexdigest()}
    with path.open('a') as handle:
        handle.write(json.dumps(envelope, sort_keys=True)+'\n')
        handle.flush()
        os.fsync(handle.fileno())


class ResolutionPlan(CandidateEvaluatorBase):
    def generate_evaluation_plan(self, candidates):
        return candidates


def make_tasks(frame, spec, levels):
    return [EvaluationTask(
        task_id=f'{row.setting_id}__{level}', role=row.setting_id,
        parameters=[getattr(row,k) for k in CONTROLS],
        namelist_overrides=spec['levels'][level] or None,
        metadata={'role':row.setting_id, 'level':level, 'run':row.run,
                  'evaluation_id':row.evaluation_id, 'purpose':'round6_resolution'})
        for level in levels for row in frame.itertuples()]


def check_nominal(frame, records, spec):
    for run, group in frame.groupby('run'):
        ledger = pd.read_csv(ROOT/'results/paper_production/04_primary/benchmark/per_seed'/run/'evaluations.csv').set_index('evaluation_id')
        for row in group.itertuples():
            result = records[f'{row.setting_id}__production']
            if not result['simulation_valid']:
                raise ValueError(f'Invalid nominal reproduction: {row.setting_id}')
            values = {**(result.get('objectives') or {}), **(result.get('diagnostics') or {})}
            for key in QUANTITIES:
                if key not in values or not np.isclose(float(values[key]),float(ledger.loc[row.evaluation_id,key]),
                    rtol=spec['nominal_reproduction_rtol'],atol=spec['nominal_reproduction_atol']):
                    raise ValueError(f'Nominal reproduction mismatch: {row.setting_id}, {key}')


def execute(out, spec, frame, resume=False, mock=False, stage='all'):
    identity = {'spec_sha256':sha(SPEC),'manifest_sha256':sha(MANIFEST),'mock':mock}
    plan_path = out/'plan.json'
    if out.exists() and any(out.iterdir()):
        if not resume or not plan_path.exists():
            raise ValueError('Output exists; require an intact plan and explicit --resume.')
        existing = json.loads(plan_path.read_text())
        if any(existing.get(k)!=v for k,v in identity.items()):
            raise ValueError('Resume plan identity mismatch.')
    else:
        out.mkdir(parents=True,exist_ok=True)
        config = load_config(ROOT/'configs/publication_200MeV.yaml')
        template = out/'template';template.mkdir()
        sources = {'qr20k.ini':(20000,True),'qr40k.ini':(40000,True)}
        if mock:
            # Mock rehearsals never invoke the physical source generator.
            for name in sources:
                shutil.copy2(ROOT/'pal_photo2.ini',template/name)
        else:
            make_sources(template,Path(config.simulation.executable).with_name('generator'),sources)
        build_template(config,template,sources)
        identity.update({'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                         'created_unix':time.time(),'workers':2,
                         'template_sha256':{p.name:sha(p) for p in template.iterdir() if p.is_file()},
                         'environment':subprocess.check_output(['uname','-a'],text=True).strip()})
        plan_path.write_text(json.dumps(identity,indent=2,sort_keys=True)+'\n')
    existing = json.loads(plan_path.read_text())
    for name,digest in existing['template_sha256'].items():
        if sha(out/'template'/name)!=digest:
            raise ValueError('Retained template checksum mismatch.')
    config = load_config(ROOT/'configs/publication_200MeV.yaml')
    config = replace(config,simulation=replace(config.simulation,template_dir=str((out/'template').resolve()),
                       static_files=[*config.simulation.static_files,'qr20k.ini','qr40k.ini']),
                     execution=replace(config.execution,max_workers=2,retries=0))
    journal=out/'results.jsonl'; records=read_records(journal)
    expected={t.task_id for t in make_tasks(frame,spec,list(spec['levels']))}
    if not set(records)<=expected:
        raise ValueError('Unexpected task in result journal.')
    pending=out/'pending.json'
    if pending.exists():
        unfinished=set(json.loads(pending.read_text()))-set(records)
        if unfinished:
            raise ValueError('Interrupted attempts require explicit evidence recovery; refusing automatic rerun: '+str(sorted(unfinished)[:3]))
        pending.unlink()
    for phase,levels in [('nominal',['production']),('refinement',[k for k in spec['levels'] if k!='production'])]:
        if phase=='refinement':
            if not mock:
                check_nominal(frame,records,spec)
            if stage=='nominal':
                break
        tasks=[t for t in make_tasks(frame,spec,levels) if t.task_id not in records]
        if not tasks:
            continue
        if shutil.disk_usage(out).free < spec['minimum_free_disk_GiB']*1024**3:
            raise RuntimeError('Insufficient disk space; preserve evidence and pause.')
        pending.write_text(json.dumps([t.task_id for t in tasks])+'\n')
        plan=ResolutionPlan(config,base_output_dir=out/'runs',num_workers=2,
                            timeout=spec['tracking_timeout_s'],template_dir=out/'template')
        def complete(outcome):
            value=record(outcome)
            value['physically_feasible']=outcome.evaluated_result.physically_feasible
            category=outcome.evaluated_result.failure_category
            value['failure_category']=getattr(category,'value',category)
            value['failure_reason']=outcome.evaluated_result.failure_reason
            append_record(journal,value)
        plan.evaluate_plan_parallel(tasks,evaluator=MockEvaluator(config=config) if mock else None,
                                    on_task_complete=complete,run_id='round6_resolution')
        records=read_records(journal)
        if any(t.task_id not in records for t in tasks):
            raise ValueError('Incomplete phase; retain pending evidence.')
        pending.unlink()
    if not mock:
        check_nominal(frame,records,spec)
    if set(records)==expected:
        (out/'complete.json').write_text(json.dumps({'tasks':len(records),'results_sha256':sha(journal),
            'spec_sha256':sha(SPEC),'mock':mock},indent=2)+'\n')
    else:
        (out/'nominal_complete.json').write_text(json.dumps({'tasks':len(records),'results_sha256':sha(journal)},indent=2)+'\n')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/revision_round6/resolution')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--wait-for-workers',action='store_true')
    parser.add_argument('--mock-evaluator',action='store_true')
    parser.add_argument('--stage',choices=['nominal','all'],default='all')
    args=parser.parse_args(argv)
    spec=json.loads(SPEC.read_text());frame=validate_inputs(spec)
    lockdir=ROOT/'results/revision_round6';lockdir.mkdir(parents=True,exist_ok=True)
    with (lockdir/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|(0 if args.wait_for_workers else fcntl.LOCK_NB))
        execute(args.output_dir,spec,frame,args.resume,args.mock_evaluator,args.stage)

if __name__=='__main__':
    main()
