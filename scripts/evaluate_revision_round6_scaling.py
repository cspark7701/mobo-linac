#!/usr/bin/env python3
"""Run contemporaneous raw/normalized campaigns from the frozen round6 specification."""
from __future__ import annotations
import argparse
from dataclasses import replace
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import time
import pandas as pd
import torch
from mobo_linac.config import load_config
from mobo_linac.campaigns.runner import MoboCampaignRunner
from mobo_linac.constraints import constraint_residual_metadata
from mobo_linac.io.artifacts import validate_run_completion
from prepare_revision_round6 import ROOT, EVIDENCE, CONTROLS, sha

SPEC=EVIDENCE/'r6_specification.json'


def code_identity():
    paths = sorted((ROOT/'src/mobo_linac').rglob('*.py')) + [Path(__file__).resolve()]
    return {str(path.relative_to(ROOT)): sha(path) for path in paths}



def campaign_config(spec, arm, seed):
    if arm not in spec['scaling']['arms'] or seed not in spec['scaling']['seeds']:
        raise ValueError('Campaign is outside the frozen allocation.')
    config=load_config(ROOT/'configs/publication_200MeV.yaml')
    return replace(config,execution=replace(config.execution,
        max_workers=2,retries=0,constraint_residual_mode=arm,
        constraint_temperature=spec['scaling'][arm+'_temperature'],
        acqf_mc_samples=spec['scaling']['posterior_samples'],acquisition_stream_group=seed,
        acqf_num_restarts=spec['scaling']['num_restarts'],acqf_raw_samples=spec['scaling']['raw_samples'],
        acqf_maxiter=spec['scaling']['maxiter']))


def order(spec):
    for seed in spec['scaling']['seeds']:
        for arm in (['raw','normalized'] if seed%2==0 else ['normalized','raw']):
            yield arm,seed


def check_completed(directory, config, spec):
    if not validate_run_completion(directory):
        raise ValueError(f'Invalid campaign completion: {directory}')
    saved=json.loads((directory/'config.json').read_text())
    for key in ['constraint_residual_mode','constraint_temperature','acqf_mc_samples','acquisition_stream_group']:
        if saved['execution'].get(key)!=getattr(config.execution,key):
            raise ValueError(f'Completed campaign convention mismatch: {key}')
    marker=json.loads((directory/'run_complete.json').read_text())
    if marker['evaluation_count']!=spec['scaling']['budget_each']:
        raise ValueError('Completed campaign budget mismatch.')


def check_pair(out,seed,spec):
    frames=[pd.read_csv(out/f'{arm}_seed_{seed}'/'evaluations.csv') for arm in ['raw','normalized']]
    a,b=[f.iloc[:spec['scaling']['initial']][CONTROLS].reset_index(drop=True) for f in frames]
    pd.testing.assert_frame_equal(a,b,check_exact=True)


def run(out,spec,resume=False):
    identity={'spec_sha256':sha(SPEC),'workers_total':2,'device':spec['device'], 'code_sha256':code_identity()}
    manifest=out/'plan.json'
    if out.exists() and any(out.iterdir()):
        if not resume or not manifest.exists():
            raise ValueError('Output exists; require intact plan and explicit --resume.')
        old=json.loads(manifest.read_text())
        if any(old.get(k)!=v for k,v in identity.items()):
            raise ValueError('Scaling plan mismatch.')
    else:
        out.mkdir(parents=True,exist_ok=True)
        identity.update({'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'created_unix':time.time(),'campaign_order':list(order(spec)),
            'conventions':{arm:constraint_residual_metadata(campaign_config(spec,arm,42)) for arm in ['raw','normalized']}})
        manifest.write_text(json.dumps(identity,indent=2,sort_keys=True)+'\n')
    torch.set_num_threads(1)
    if not torch.cuda.is_available():
        raise RuntimeError('Frozen CUDA policy unavailable; do not silently substitute CPU.')
    for arm,seed in order(spec):
        if code_identity()!=identity['code_sha256']:
            raise RuntimeError('Scientific code changed during the matched study; preserve outputs and pause.')
        config=campaign_config(spec,arm,seed)
        directory=out/f'{arm}_seed_{seed}'
        if (directory/'run_complete.json').exists():
            check_completed(directory,config,spec)
            continue
        if shutil.disk_usage(out).free<spec['minimum_free_disk_GiB']*1024**3:
            raise RuntimeError('Insufficient disk space; preserve evidence and pause.')
        partial=directory.exists() and any(directory.iterdir())
        if partial and not resume:
            raise ValueError('Partial campaign requires explicit checkpoint resume.')
        runner=MoboCampaignRunner(config=config,output_dir=directory,
            num_initial_samples=spec['scaling']['initial'],num_batches=spec['scaling']['batches'],
            batch_size=spec['scaling']['batch_size'],total_eval_budget=spec['scaling']['budget_each'],
            num_workers=2,seed=seed,constrained=True,optimization_mode='constrained_mobo',
            acq_type='qLogNEHVI',device=spec['device'],resume=bool(partial),
            reporting_ref_point=[-1.5e-6,-1.5e-6,-1.5e6],export_plots=False)
        runner.run()
        check_completed(directory,config,spec)
        if all((out/f'{a}_seed_{seed}'/'run_complete.json').exists() for a in ['raw','normalized']):
            check_pair(out,seed,spec)
    for seed in spec['scaling']['seeds']:
        check_pair(out,seed,spec)
    receipts={str((out/f'{arm}_seed_{seed}'/'run_complete.json').relative_to(out)):
              sha(out/f'{arm}_seed_{seed}'/'run_complete.json') for arm,seed in order(spec)}
    (out/'complete.json').write_text(json.dumps({'spec_sha256':sha(SPEC),'campaigns':receipts},indent=2)+'\n')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/revision_round6/scaling')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--wait-for-workers',action='store_true')
    args=parser.parse_args(argv);spec=json.loads(SPEC.read_text())
    for name,digest in spec['input_sha256'].items():
        if sha(ROOT/name)!=digest:
            raise ValueError(f'Frozen input mismatch: {name}')
    base=ROOT/'results/revision_round6';base.mkdir(parents=True,exist_ok=True)
    with (base/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|(0 if args.wait_for_workers else fcntl.LOCK_NB))
        run(args.output_dir,spec,args.resume)

if __name__=='__main__':
    main()
