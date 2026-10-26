"""C06: offline constraint-unit and smoothing sensitivity on frozen surrogates."""
from pathlib import Path
import hashlib
import json
import warnings
import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr
from botorch.models import ModelListGP
from botorch.sampling.normal import SobolQMCNormalSampler
from botorch.acquisition.multi_objective.logei import qLogNoisyExpectedHypervolumeImprovement
from mobo_linac.models.artifacts import restore_model
from mobo_linac.acquisition.mobo import SliceObjective
from analyze_revision_settings import SIDES

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/paper/revisions/evidence'
RUN=ROOT/'results/paper_production/04_primary/benchmark/per_seed/constrained_qlognehvi_seed_42'
DIAGNOSTICS=['sigma_x_m','sigma_y_m','sigma_xp_rad','sigma_yp_rad','sigma_z_m','mean_kinetic_energy_eV','transmission_fraction']

def residual_functions(normalized=False,display_units=False):
    functions=[]
    for channel,side,threshold in SIDES:
        index=3+DIAGNOSTICS.index(channel)
        factor=1e-6 if channel=='mean_kinetic_energy_eV' else (1. if channel=='transmission_fraction' else 1e3)
        scale=5e6 if channel=='mean_kinetic_energy_eV' else (.1 if channel=='transmission_fraction' else abs(threshold))
        factor=factor if display_units else 1.
        def residual(y,index=index,side=side,threshold=threshold,factor=factor,scale=scale,normalized=normalized):
            value=y[...,index]*factor;limit=threshold*factor
            result=limit-value if side=='lower' else value-limit
            return result/(scale*factor) if normalized else result
        functions.append(residual)
    return functions

def main():
    torch.set_num_threads(1);history=json.loads((RUN/'proposal_history.json').read_text())
    variants=[('original_native',False,False,.001),('raw_display_units',False,True,.001),
              ('normalized_001',True,False,.001),('normalized_01',True,False,.01),
              ('normalized_01_display',True,True,.01),('normalized_1',True,False,.1)]
    rows=[];comparisons=[];sources=[];warning_counts={}
    for iteration in [1,9,18]:
        paths=list((RUN/'gp_checkpoint').glob(f'model_iter_{iteration:02d}_*.pt'));assert len(paths)==1
        path=paths[0];a=torch.load(path,map_location='cpu',weights_only=True)
        sources.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            obj=restore_model(a['objectives']);con=restore_model(a['constraints'])
            model=ModelListGP(*obj.models,*con.models)
            md=a['objectives']['channels'][0]['metadata'];bounds=md['bounds'];train_X=md['train_X']
            unit=torch.quasirandom.SobolEngine(6,scramble=True,seed=7301).draw(32,dtype=torch.double)
            candidates=(bounds[0]+unit*(bounds[1]-bounds[0])).unsqueeze(-2)
            values={}
            for name,normalized,display,eta in variants:
                sampler=SobolQMCNormalSampler(torch.Size([128]),seed=7302)
                acq=qLogNoisyExpectedHypervolumeImprovement(model=model,
                    ref_point=history[iteration]['metadata']['acquisition_reference']['point_model'],
                    X_baseline=train_X,prune_baseline=False,sampler=sampler,objective=SliceObjective(3),
                    constraints=residual_functions(normalized,display),eta=eta)
                with torch.no_grad():value=acq(candidates).numpy()
                assert np.isfinite(value).all();values[name]=value
                rows.extend({'iteration':iteration,'variant':name,'candidate':i,'log_acquisition':float(v)} for i,v in enumerate(value))
                del acq
            for w in caught:
                key=w.category.__name__+': '+str(w.message).split('\n')[0]
                warning_counts[key]=warning_counts.get(key,0)+1
        np.testing.assert_allclose(values['normalized_01'],values['normalized_01_display'],rtol=1e-9,atol=1e-9)
        base=values['original_native'];top=set(np.argsort(base)[-5:])
        for name in values:
            comparisons.append({'iteration':iteration,'variant':name,'spearman_to_original':float(spearmanr(base,values[name]).statistic),
                'top5_overlap_with_original':len(top & set(np.argsort(values[name])[-5:])),
                'top_candidate':int(np.argmax(values[name])),
                'normalized_unit_max_abs_difference':float(np.max(abs(values['normalized_01']-values['normalized_01_display'])))})
        print(f'Iteration {iteration} complete',flush=True)
    pd.DataFrame(rows).to_csv(OUT/'c06_acquisition_values.csv',index=False)
    pd.DataFrame(comparisons).to_csv(OUT/'c06_rank_sensitivity.csv',index=False)
    widths=[]
    for c,side,t in SIDES:
        scale=5e6 if c=='mean_kinetic_energy_eV' else (.1 if c=='transmission_fraction' else abs(t))
        widths.append({'channel':c,'side':side,'original_eta_in_recorded_units':.001,'normalization_scale_in_recorded_units':scale,'normalized_eta_01_physical_width':.01*scale})
    pd.DataFrame(widths).to_csv(OUT/'c06_smoothing_scales.csv',index=False)
    (OUT/'c06_metadata.json').write_text(json.dumps({'scope':'Offline q=1 ranking on 32 fixed Sobol candidates for three frozen snapshots; no optimizer, ASTRA, model refit or production change.',
        'mc_samples':128,'candidate_seed':7301,'sampler_seed':7302,'precision':'float64','device':'cpu',
        'baseline_pruning':False,'pruning_reason':'Keep the full identical historical baseline to isolate residual-unit/smoothing effects; not a replay of production pruning or q=8 proposal optimization.',
        'inputs':sources,'warnings':warning_counts},indent=2)+'\n')
    print(pd.DataFrame(comparisons).to_string(index=False))

if __name__=='__main__':main()
