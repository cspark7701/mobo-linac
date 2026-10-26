#!/usr/bin/env python3
"""C04 paired inference, using C03 derived data and immutable stage-04 observations."""
from __future__ import annotations
import argparse
from itertools import combinations, product
import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from analyze_revision_fronts import METHODS,load_runs

ENDPOINTS=('feasible_fraction','epsilon','igd_plus','hv_25')


def exact_signed_rank(differences):
    d=np.asarray(differences,float)
    if not np.isfinite(d).all():
        raise ValueError('Paired inference requires finite differences')
    d=d[d != 0]
    if not len(d):
        return 1.
    ranks=rankdata(np.abs(d),method='average')
    observed=abs(np.dot(np.sign(d),ranks))
    possible=np.array(list(product((-1,1),repeat=len(d))))@ranks
    return float(np.mean(abs(possible)>=observed-1e-12))


def holm(pvalues):
    p=np.asarray(pvalues,float)
    order=np.argsort(p,kind='stable')
    adjusted=np.minimum(1.,np.maximum.accumulate((len(p)-np.arange(len(p)))*p[order]))
    result=np.empty_like(p)
    result[order]=adjusted
    return result


def analyze(runs_path,out):
    histories=pd.read_csv(out/'c03_run_histories.csv')
    terminal=histories[histories.evaluations==160]
    runs,groups,manifest=load_runs(runs_path)
    source_metadata=json.loads((out/'c03_metadata.json').read_text())
    old_hashes={x['run']:x['sha256'] for x in source_metadata['input_manifest']}
    if old_hashes != {x['run']:x['sha256'] for x in manifest}:
        raise ValueError('C03 histories do not match the current archived evaluation inputs')
    rng=np.random.default_rng(20261026)
    indices=rng.integers(0,len(groups),size=(10000,len(groups)))
    results=[]
    differences=[]
    for metric in ENDPOINTS:
        wide=terminal.pivot(index='group',columns='method',values=metric).sort_index()
        assert len(wide)==10 and not wide.isna().any().any()
        for first,second in combinations(METHODS,2):
            d=(wide[first]-wide[second]).to_numpy()
            boot=d[indices].mean(1)
            lo,hi=np.quantile(boot,[.025,.975])
            results.append({'endpoint':metric,'first_method':first,'second_method':second,'mean_difference':d.mean(),'ci_lower':lo,'ci_upper':hi,'p_exact_signed_rank':exact_signed_rank(d),'n_positive':int(sum(d>0)),'n_negative':int(sum(d<0)),'n_zero':int(sum(d==0))})
            differences.extend({'endpoint':metric,'first_method':first,'second_method':second,'group':g,'difference':value} for g,value in zip(wide.index,d))
    result=pd.DataFrame(results)
    result['p_holm_12']=holm(result.p_exact_signed_rank)
    result.to_csv(out/'c04_paired_effects.csv',index=False)
    pd.DataFrame(differences).to_csv(out/'c04_paired_differences.csv',index=False)
    initial=[]
    for (method,group),(df,vals,feasible) in runs.items():
        first=np.flatnonzero(feasible)
        initial.append({'method':method,'group':group,'initial_feasible_count':int(feasible[:16].sum()),'initial_has_feasible':bool(feasible[:16].any()),'first_feasible_evaluation':int(first[0]+1) if len(first) else None,'post_initial_feasible_count':int(feasible[16:].sum()),'post_initial_feasible_fraction':float(feasible[16:].mean())})
    init=pd.DataFrame(initial)
    init.to_csv(out/'c04_initialization.csv',index=False)
    metadata={'input_sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('c03_metadata.json','c03_run_histories.csv')},'protocol':'c04_protocol.md','bootstrap_resamples':10000,'analysis_rng':20261026,'groups':groups,'n_groups':len(groups),'endpoints':ENDPOINTS,'family_size':12,'test':'exact two-sided signed-rank with zero exclusion and tied midranks','multiplicity':'Holm','effect':'mean paired first minus second','initial_groups_feasible':int(init[init.method==METHODS[0]].initial_has_feasible.sum()),'post_initial_median_fractions':init.groupby('method').post_initial_feasible_fraction.median().to_dict()}
    (out/'c04_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(result.to_string(index=False))
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',type=Path,default=Path('results/paper_production/04_primary/benchmark/per_seed'))
    parser.add_argument('--output',type=Path,default=Path('docs/paper/revisions/evidence'))
    args=parser.parse_args()
    analyze(args.runs,args.output)
