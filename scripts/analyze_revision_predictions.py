"""C11: chronological next-batch validation of saved GP models without refitting."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import warnings
import numpy as np
import pandas as pd
import torch
from mobo_linac.models.artifacts import restore_model
from analyze_revision_settings import OBJECTIVES, SIDES

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/paper/revisions/evidence'
DIAGNOSTICS=['sigma_x_m','sigma_y_m','sigma_xp_rad','sigma_yp_rad','sigma_z_m','mean_kinetic_energy_eV','transmission_fraction']

def summarize(frame):
    rows=[]
    for (method,channel,subset),f in frame.groupby(['method','channel','subset']):
        error=f.observed-f.predicted
        rows.append({'method':method,'channel':channel,'subset':subset,'n':len(f),
            'rmse':float(np.sqrt(np.mean(error**2))),'mae':float(np.mean(abs(error))),
            'coverage95':float(np.mean(abs(error)<=1.959963984540054*f.predictive_std)),
            'api_floor_coverage95':float(np.mean(abs(error)<=1.959963984540054*f.api_predictive_std)),
            'api_floor_applied_n':int(f.api_variance_floor_applied.sum()),
            'rms_standardized_error':float(np.sqrt(np.mean((error/f.predictive_std)**2))),
            'mean_interval_half_width':float(np.mean(1.959963984540054*f.predictive_std))})
    return pd.DataFrame(rows)

def main():
    torch.set_num_threads(1)
    artifact_index=pd.read_csv(OUT/'c05_artifacts.csv')
    rows=[];sources=[];warns=Counter();count=0
    for run,paths in artifact_index.groupby(artifact_index.path.map(lambda p:Path(p).parents[1].name)):
        base=ROOT/Path(paths.iloc[0].path).parents[1]
        df=pd.read_csv(base/'evaluations.csv');cfg=json.loads((base/'config.json').read_text());marker=json.loads((base/'run_complete.json').read_text())
        assert hashlib.sha256((base/'evaluations.csv').read_bytes()).hexdigest()==marker['artifacts']['evaluations.csv']
        names=[v['name'] for v in cfg['design_variables']];method=run.split('_seed_')[0]
        for _,entry in paths.iterrows():
            path=ROOT/entry.path;assert hashlib.sha256(path.read_bytes()).hexdigest()==entry.sha256
            sources.append({'path':entry.path,'sha256':entry.sha256})
            a=torch.load(path,map_location='cpu',weights_only=True);n=len(a['training_ids'])
            assert a['training_ids']==list(zip(df.run_id[:n],df.evaluation_id[:n]))
            future=df.iloc[n:n+8];assert len(future)==8
            assert n==16+8*(a['metadata']['proposal_iteration']-1)
            X=torch.tensor(future[names].to_numpy(),dtype=torch.double)
            groups=['model'] if a['kind']=='gp' else ['objectives']+(['constraints'] if a.get('constraints') else [])
            for group in groups:
                for i,channel in enumerate(a[group]['channels']):
                    md=channel['metadata'];np.testing.assert_allclose(md['train_X'].numpy(),df[names].iloc[:n],rtol=1e-12)
                    if group=='model':
                        name='scalarized_cost';scales=np.array(a['metadata']['reporting_scales']);weights=np.array(a['metadata']['scalar_weights'])
                        target=(df[OBJECTIVES].to_numpy()/scales*weights).sum(axis=1);sign=-1
                    elif group=='objectives':name=OBJECTIVES[i];target=df[name].to_numpy();sign=-1
                    else:name=DIAGNOSTICS[i];target=df[name].to_numpy();sign=1
                    np.testing.assert_allclose(md['train_Y'].flatten().numpy(),sign*target[:n],rtol=1e-10,atol=1e-16)
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always')
                        model=restore_model({'kind':'single','channels':[channel]},device='cpu')
                        with torch.no_grad():
                            posterior=model.posterior(X)
                            mean=sign*posterior.mean.flatten().numpy()
                            api_variance=posterior.variance.flatten().numpy()
                            variance=posterior.distribution.covariance_matrix.diagonal(dim1=-2,dim2=-1).flatten().numpy()
                            if (variance<0).any():raise ValueError('Negative covariance diagonal requires explicit numerical treatment')
                        for w in caught:warns[str(w.category.__name__)+': '+str(w.message).split('\n')[0]]+=1
                    # Fixed likelihood noise is regularization, included for an observation predictive interval.
                    noise=channel['standardized_noise'].flatten().numpy()
                    assert np.allclose(noise,noise[0])
                    scale=channel['state']['outcome_transform.stdvs'].item()
                    std=np.sqrt(variance+float(noise[0])*scale**2)
                    if not np.isfinite(std).all() or (std<=0).any():raise ValueError('Invalid predictive uncertainty')
                    for j,(_,obs) in enumerate(future.iterrows()):
                        r={'method':method,'run_id':run,'batch':a['metadata']['proposal_iteration'],'training_n':n,
                            'evaluation_id':obs.evaluation_id,'channel':name,'subset':'all',
                            'observed':target[n+j],'predicted':mean[j],'predictive_std':std[j],
                            'api_variance_floor_applied':bool(api_variance[j]>variance[j]*(1+1e-10)),
                            'api_predictive_std':float(np.sqrt(api_variance[j]+float(noise[0])*scale**2))}
                        rows.append(r)
                        if group=='constraints':
                            close=False
                            for c,side,t in SIDES:
                                if c==name:
                                    width=.5e6 if c=='mean_kinetic_energy_eV' else .1*abs(t)
                                    close |= abs(target[n+j]-t)<=width
                            if close:rows.append({**r,'subset':'near_boundary'})
                    del model
            count+=1
        print(f'{run}: checked {len(paths)} saved models',flush=True)
    frame=pd.DataFrame(rows);frame.to_csv(OUT/'c11_next_batch_predictions.csv',index=False)
    summary=summarize(frame);summary.to_csv(OUT/'c11_predictive_summary.csv',index=False)
    (OUT/'c11_metadata.json').write_text(json.dumps({'saved_models':count,'precision':'float64','device':'cpu',
        'interval':'Gaussian observation predictive interval from covariance diagonal, with saved effective fixed noise; no refitting. API variance-floor coverage is reported separately.',
        'boundary_subset':'Observed diagnostic within 10% of absolute threshold, except energy within 0.5 MeV of either bound; selected post hoc.',
        'warnings':dict(warns),'inputs':sources},indent=2)+'\n')
    print(summary.to_string(index=False))

if __name__=='__main__':main()
