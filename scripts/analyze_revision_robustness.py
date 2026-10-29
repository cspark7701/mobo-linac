"""Independently audit retained primary/survey robustness trials; never rerun ASTRA."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from scipy.stats import beta
from analyze_revision_settings import SIDES, OBJECTIVES

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/paper/revisions/evidence'
AUDITS={'primary':ROOT/'results/paper_production/06_candidate_audit/robustness',
        'survey':ROOT/'results/paper_production/05_operating_points/campaign/analysis/robustness'}
LABELS={'min_emit_x':'Horizontal extreme','min_emit_y':'Vertical extreme','min_sigma_energy':'Spread extreme',
        'knee_point':'Ideal-distance point','balanced':'Centroid-distance point','crowding_distance_max':'Crowding-distance point'}

def binomial_bounds(k,n,alpha=.05):
    if n<=0 or not 0<=k<=n:raise ValueError('Require 0 <= k <= n and n > 0')
    return (float(beta.ppf(alpha/2,k,n-k+1)) if k else 0.,
            float(beta.ppf(1-alpha/2,k+1,n-k)) if k<n else 1.,
            float(beta.ppf(alpha,k,n-k+1)) if k else 0.)

def summarize_trials(values,diagnostics,nominal,valid,feasible):
    values=np.asarray(values,float);nominal=np.asarray(nominal,float)
    # Existing evidence contains no invalid results: fail rather than silently omit any.
    if not np.all(valid) or not np.isfinite(values).all():raise ValueError('Invalid trial requires explicit missing-data handling')
    channels={c+':'+side: ((t-diagnostics[c] if side=='upper' else diagnostics[c]-t)/abs(t)) for c,side,t in SIDES}
    margins=pd.DataFrame(channels)
    np.testing.assert_array_equal((margins>=0).all(axis=1),feasible)
    minima=margins.min();worst=minima.idxmin();mu=float(minima[worst]);d=float(np.mean(values.mean(axis=0)/nominal))
    probability=float(np.mean(feasible));score=probability*max(.5,1+mu)/max(1,d)
    return {'probability':probability,'D':d,'mu_min':mu,'worst_channel':worst,'score':score},minima

def main():
    summaries=[];objectives=[];physical=[];inputs=[];audit_details={}
    def record(p):
        inputs.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    for audit,base in AUDITS.items():
        paths=list((base/'robustness_runs').glob('*/robustness_requests.json'))
        if len(paths)!=1:raise ValueError('Select authoritative attempt explicitly')
        p=paths[0];record(p);request=json.loads(p.read_text());records=request['records']
        saved_path=p.with_name('robustness_summary.json');record(saved_path)
        saved=json.loads(saved_path.read_text())['summaries']
        spec=request['perturbation_specification'];groups={}
        for r in records:groups.setdefault(r['request']['metadata']['candidate_label'],[]).append(r)
        assert len(groups)==6 and len(records)==300
        assert len({tuple(rs[0]['request']['metadata']['nominal_parameters']) for rs in groups.values()})==6
        assert len({tuple(r['result']['x_physical']) for r in records})==300
        common_deltas=[]
        for label,rs in groups.items():
            previous=next(s for s in saved if s['candidate_label']==label)
            values=np.array([r['result']['objectives_physical'] for r in rs])
            diagnostics=pd.DataFrame([r['result']['diagnostics'] for r in rs])
            nominal=np.array([previous['nominal_'+c] for c in OBJECTIVES])
            valid=[r['result']['simulation_valid'] for r in rs];feasible=[r['result']['physically_feasible'] for r in rs]
            metrics,minimum=summarize_trials(values,diagnostics,nominal,valid,feasible)
            for ours,old in [('probability','probability_of_feasibility'),('D','mean_objective_degradation'),('mu_min','worst_constraint_margin'),('score','robust_score')]:
                np.testing.assert_allclose(metrics[ours],previous[old],rtol=1e-12,atol=1e-14)
            assert metrics['worst_channel']==previous['worst_constraint_channel']
            lo,hi,one=binomial_bounds(sum(feasible),len(rs))
            summaries.append({'audit':audit,'role':label,'run_id':previous['run_id'],'evaluation_id':previous['evaluation_id'],
                'n':len(rs),'k':sum(feasible),**metrics,'cp95_lower':lo,'cp95_upper':hi,'one_sided95_failure_upper':1-one})
            for i,c in enumerate(OBJECTIVES):
                stats={'mean':values[:,i].mean(),'std':values[:,i].std(),'p5':np.percentile(values[:,i],5),'p95':np.percentile(values[:,i],95)}
                for k,v in stats.items():np.testing.assert_allclose(v,previous[k+'_'+c],rtol=1e-12)
                objectives.append({'audit':audit,'role':label,'objective':c,'nominal':nominal[i],**stats,'mean_ratio':stats['mean']/nominal[i]})
            for c,side,t in SIDES:
                raw=(t-diagnostics[c] if side=='upper' else diagnostics[c]-t).min()
                physical.append({'audit':audit,'role':label,'channel':c,'side':side,'threshold':t,'minimum_physical_margin':raw,'threshold_normalized_margin':minimum[c+':'+side],
                    'energy_half_band_normalized_margin':raw/5e6 if c=='mean_kinetic_energy_eV' else np.nan})
            deltas=[]
            for r in rs:
                meta=r['request']['metadata'];result=r['result'];np.testing.assert_array_equal(r['request']['parameters'],result['x_physical'])
                assert r['execution_kind']=='astra'
                deltas.append([meta['channel_deltas'][ch['channel']] for ch in spec['lattice']])
                manifest=Path(result['manifest_path']);record(manifest);m=json.loads(manifest.read_text())
                for name in ['astra.Xemit.001','astra.Yemit.001','astra.Zemit.001']:
                    op=Path(result['work_dir'])/name
                    if hashlib.sha256(op.read_bytes()).hexdigest()!=m['output_hashes'][name]:raise ValueError(op)
                ip=manifest.parent/'inputs/astra.in'
                if hashlib.sha256(ip.read_bytes()).hexdigest()!=m['input_hashes']['astra.in']:raise ValueError(ip)
            common_deltas.append(deltas)
        for d in common_deltas[1:]:np.testing.assert_array_equal(common_deltas[0],d)
        audit_details[audit]={'trials':len(records),'distinct_vectors':300,'common_random_numbers_verified':True,
            'specification':spec,'interpretation':'Six separate 50-trial designs; no pooled reliability estimate. Pair phases are common controls; different channels independently sampled.'}
    pd.DataFrame(summaries).to_csv(OUT/'c10_design_statistics.csv',index=False)
    pd.DataFrame(objectives).to_csv(OUT/'c10_objective_statistics.csv',index=False)
    pd.DataFrame(physical).to_csv(OUT/'c10_constraint_margins.csv',index=False)
    (OUT/'c10_metadata.json').write_text(json.dumps({'audits':audit_details,'inputs':inputs},indent=2)+'\n')
    tex=r'''\begin{table}[htbp]
\centering
\caption{Primary lattice-jitter results, evaluated against the production profile. Each setting
has 50 feasible outcomes in 50 trials; its two-sided exact 95\% binomial interval is
$[0.929,1]$. $D$ is the mean objective ratio and $\mu_{\min}$ is the minimum
threshold-normalized margin; neither is a reliability probability. All values are at the production tracking resolution (Sec.~\ref{sec:problem}).}
\label{tab:robustness_summary}
\begin{tabular}{lrrl}\toprule
Setting & $D$ & $\mu_{\min}$ & Limiting inequality \\\midrule
'''
    channel_labels={'sigma_z_m:upper':r'$\sigma_z$ upper','mean_kinetic_energy_eV:lower':r'$E$ lower','mean_kinetic_energy_eV:upper':r'$E$ upper'}
    for r in summaries:
        if r['audit']=='primary':tex+=LABELS[r['role']]+f" & {r['D']:.4f} & {r['mu_min']:.5f} & "+channel_labels.get(r['worst_channel'],r['worst_channel'])+r' \\'+'\n'
    tex+=r'\bottomrule\end{tabular}\end{table}'+'\n'
    (ROOT/'docs/paper/robustness_table.tex').write_text(tex)
    print(pd.DataFrame(summaries)[['audit','role','D','mu_min','score','cp95_lower']].to_string(index=False))

if __name__=='__main__':main()
