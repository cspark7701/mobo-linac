#!/usr/bin/env python3
"""Commit a factual completion summary for a successfully verified round6 stage only."""
from __future__ import annotations
import argparse
import json
import subprocess
from prepare_revision_round6 import ROOT, sha
from run_revision_round6_scaling import code_identity
from mobo_linac.io.artifacts import validate_run_completion


def stage_evidence(stage):
    base=ROOT/'results/revision_round6'
    if stage=='validation':
        receipt=base/'validation_complete.json'
        data=json.loads(receipt.read_text())
        if data.get('status')!='passed' or data.get('coverage_required')!=100 or data['code_sha256']!=code_identity():
            raise ValueError('Code validation receipt is invalid or stale.')
        if sha(base/'logs/final_validation.log')!=data['test_log_sha256']:
            raise ValueError('Validation log checksum mismatch.')
        return receipt, 'The complete non-integration test suite passed with the 100% package-line-coverage gate. Lint, documentation sync and supplement manifest checks passed. Physical studies remain separate and unfinished.'
    study='resolution' if stage=='numerical' else 'scaling'
    receipt=base/f'analysis_{study}'/f'r6_{study}_analysis.json'
    data=json.loads(receipt.read_text())
    complete=base/study/'complete.json'
    completion=json.loads(complete.read_text())
    if completion.get('mock') or completion.get('spec_sha256')!=sha(ROOT/'docs/paper/revisions/evidence/r6_specification.json'):
        raise ValueError('Invalid physical study completion.')
    if study=='resolution':
        if completion['results_sha256']!=sha(base/study/'results.jsonl'):
            raise ValueError('Numerical result journal changed.')
    else:
        for name,digest in completion['campaigns'].items():
            if sha(base/study/name)!=digest or not validate_run_completion((base/study/name).parent):
                raise ValueError('Scaling artifact checksums changed.')
    if data['completion_sha256']!=sha(complete):
        raise ValueError('Analysis completion input changed.')
    if not data.get('outputs_sha256'):
        raise ValueError('Missing analyzed-output checksums.')
    for name,digest in data['outputs_sha256'].items():
        if sha(receipt.parent/name)!=digest:
            raise ValueError('Analyzed output checksum mismatch.')
    return receipt, f'The {study} execution and frozen-protocol offline analysis completed. Derived outputs remain under results/revision_round6/analysis_{study} for scientific review and manuscript integration. Completion does not establish convergence, normalized-method superiority, or reviewer acceptance.'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['validation','numerical','scaling'])
    args=parser.parse_args(argv)
    receipt,description=stage_evidence(args.stage)
    digest=sha(receipt)
    folder=ROOT/'docs/exec-plans/completed'
    previous=list(folder.glob(f'TASK_*_r6_{args.stage}_completed.md'))
    if previous:
        if len(previous)!=1 or digest not in previous[0].read_text():
            raise ValueError('Conflicting existing stage completion summary.')
        subprocess.run(['git','ls-files','--error-unmatch',str(previous[0].relative_to(ROOT))],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
        return
    if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!='main':
        raise ValueError('Expected main branch; do not commit into an unrelated checkout.')
    n=max(int(p.name.split('_')[1]) for p in folder.glob('TASK_[0-9][0-9][0-9][0-9][0-9]_*.md'))+1
    path=folder/f'TASK_{n:05d}_r6_{args.stage}_completed.md'
    title=f'Record completed round6 {args.stage} stage'
    with path.open('x') as handle:
        handle.write(f'# Task Completion Summary: Task {n:05d}\n\n## Summary\n{title}.\n\n## Key Changes\n{description}\n\n## Validation Results\nVerified the completion receipt and recorded output hashes.\nReceipt: `{receipt.relative_to(ROOT)}`.\nReceipt SHA-256: `{digest}`.\n\n## Status\nThis stage is complete; remaining scientific integration and final publication checks are not implied. No push performed.\n')
    relative=str(path.relative_to(ROOT))
    subprocess.run(['git','add','--',relative],cwd=ROOT,check=True)
    message=title+'\n\n'+description+'\n\nFiles:\nA '+relative+'\n'
    subprocess.run(['git','commit','--only','-F','-','--',relative],input=message,text=True,cwd=ROOT,check=True)

if __name__=='__main__':
    main()
