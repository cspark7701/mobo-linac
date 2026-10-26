"""C13: recorded execution identities and overlap-aware relative campaign cost."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/paper_production/04_primary/benchmark'
OUT=ROOT/'docs/paper/revisions/evidence'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def union_duration(intervals):
    intervals=sorted(intervals)
    if not intervals:return 0.
    left,right=intervals[0];total=0.
    if right<left:raise ValueError('Negative duration')
    for start,end in intervals[1:]:
        if end<start:raise ValueError('Negative duration')
        if start>right:total+=right-left;left,right=start,end
        else:right=max(right,end)
    return total+right-left

def main():
    manifest=pd.read_csv(BASE/'campaign_manifest.csv')
    scheduler=json.loads((BASE/'scheduler.json').read_text())
    stage=BASE.parent/'step_record_20261019_154752.json';startup=json.loads(stage.read_text())
    rows=[];input_sets=set();executables=set();sources=[]
    for _,entry in manifest.iterrows():
        run=ROOT/entry.run_dir;complete=json.loads((run/'run_complete.json').read_text())
        for name in ['evaluations.csv','config.json','metrics_history.csv','proposal_history.json']:
            assert sha(run/name)==complete['artifacts'][name]
            sources.append({'path':str((run/name).relative_to(ROOT)),'sha256':sha(run/name)})
        df=pd.read_csv(run/'evaluations.csv');cfg=json.loads((run/'config.json').read_text())
        intervals=[];mh=[]
        for _,r in df.iterrows():
            p=Path(r.manifest_path);m=json.loads(p.read_text());mh.append(str(p.relative_to(ROOT))+':'+sha(p))
            t=m['timestamps'];start=datetime.fromisoformat(t['start_time']).timestamp();end=datetime.fromisoformat(t['end_time']).timestamp()
            assert abs((end-start)-r.runtime_s)<.01
            intervals.append((start,end));executables.add(m['executable']['sha256'])
            input_sets.add(tuple(sorted((k,v) for k,v in m['input_hashes'].items() if k!='astra.in')))
        elapsed=float(complete['elapsed_wall_time_s']);union=union_duration(intervals)
        assert 0<union<=elapsed
        history=json.loads((run/'proposal_history.json').read_text())
        devices=sorted({h['metadata']['device'] for h in history if h['batch_idx']})
        assert devices==['cuda:0']
        rows.append({'method':entry.algorithm,'seed':entry.seed,'run_id':run.name,'elapsed_s':elapsed,
            'evaluation_interval_union_s':union,'non_evaluation_interval_s':elapsed-union,
            'non_evaluation_fraction':1-union/elapsed,'worker_runtime_sum_s':df.runtime_s.sum(),
            'workers':entry.workers_per_campaign,'concurrent_campaigns':entry.max_concurrent_campaigns,
            'budget':entry.effective_budget,'initial_points':entry.n_sobol_init,'batch_size':entry.batch_size,
            'device':devices[0],'config_sha256':sha(run/'config.json'),
            'evaluation_manifest_set_sha256':hashlib.sha256('\n'.join(sorted(mh)).encode()).hexdigest()})
    frame=pd.DataFrame(rows);frame.to_csv(OUT/'c13_run_costs.csv',index=False)
    costs=frame.pivot(index='seed',columns='method',values='elapsed_s')
    ratios=[]
    for method in costs:
        v=costs[method]/costs['scalarized_bo']
        ratios.append({'method':method,'paired_ratio_to_scalarized_median':v.median(),'paired_ratio_min':v.min(),'paired_ratio_max':v.max(),
            'median_non_evaluation_fraction':frame.loc[frame.method==method,'non_evaluation_fraction'].median()})
    pd.DataFrame(ratios).to_csv(OUT/'c13_relative_costs.csv',index=False)
    assert len(input_sets)==len(executables)==1
    (OUT/'c13_metadata.json').write_text(json.dumps({'startup':startup,'startup_sha256':sha(stage),
        'scheduler':{k:v for k,v in scheduler.items() if k!='completions'},'scheduler_sha256':sha(BASE/'scheduler.json'),
        'static_input_hashes':dict(next(iter(input_sets))),'executable_sha256':next(iter(executables)),
        'precision':'float64 verified in C05 saved channel data','actual_budgets_source':'campaign_manifest.csv; config stores defaults, proposal history stores applied optimization budgets',
        'timing_definition':'Campaign active-session elapsed; union of archived evaluation intervals counts overlap once. Complement includes fitting, acquisition, export, scheduling and setup; no separately measured fitting/acquisition split is claimed.',
        'inputs':sources},indent=2)+'\n')
    print(pd.DataFrame(ratios).to_string(index=False))

if __name__=='__main__':main()
