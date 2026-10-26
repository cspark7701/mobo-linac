"""Read-only C05 audit. Run with the production linac-opt Python from repo root."""
import csv, hashlib, inspect, json
from collections import Counter
from pathlib import Path
import botorch, gpytorch, torch
from botorch.acquisition.multi_objective.logei import qLogNoisyExpectedHypervolumeImprovement
from botorch.acquisition.logei import qLogNoisyExpectedImprovement
from botorch.utils.safe_math import fatmoid
from botorch.utils.objective import compute_smoothed_feasibility_indicator
from botorch.acquisition.acquisition import MCSamplerMixin

BASE = Path('results/paper_production/04_primary/benchmark')
OUT = Path('docs/paper/revisions/evidence')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_csv(name, rows):
    with (OUT/name).open('w', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
manifest=list(csv.DictReader((BASE/'campaign_manifest.csv').open()))
records=[]; artifacts=[]; proposals=[]; reference_checks=0; source_checks=[]; fit=Counter(); names={'objectives':['norm_emit_x','norm_emit_y','sigma_energy'],'constraints':['sigma_x','sigma_y','sigma_xp','sigma_yp','sigma_z','mean_kinetic_energy','transmission'],'model':['scalarized_cost']}
for run in sorted(BASE.joinpath('per_seed').iterdir()):
    if not run.is_dir(): continue
    history=json.loads((run/'proposal_history.json').read_text())
    marker=json.loads((run/'run_complete.json').read_text())
    for name in ('config.json','proposal_history.json'):
        assert sha(run/name)==marker['artifacts'][name]
        source_checks.append({'path':str(run/name),'sha256':sha(run/name)})
    environment=(run/'environment.txt').read_text()
    assert f'BoTorch version: {botorch.__version__}' in environment
    assert f'GPyTorch version: {gpytorch.__version__}' in environment
    for h in history:
        if h['batch_idx']:
            md=h['metadata'];att=md['attempts']
            proposals.append({'run_id':run.name,'batch':h['batch_idx'],'method':md['method'],'device':md['device'],'attempts':len(att),'num_restarts':att[0]['num_restarts'],'raw_samples':att[0]['raw_samples'],'maxiter':att[0]['options']['maxiter'],'batch_limit':att[0]['options']['batch_limit'],'reference_basis':md.get('acquisition_reference',{}).get('basis','not_applicable')})
    for path in sorted((run/'gp_checkpoint').glob('model_iter_*.pt')):
        a=torch.load(path,map_location='cpu',weights_only=True)
        if 'objectives' in a:
            idx=a['metadata']['proposal_iteration']
            ys=torch.cat([c['metadata']['train_Y'] for c in a['objectives']['channels']],dim=-1)
            expected=ys.min(dim=0).values-.05*(ys.max(dim=0).values-ys.min(dim=0).values+1e-8)
            actual=torch.tensor(history[idx]['metadata']['acquisition_reference']['point_model'],dtype=torch.double)
            assert torch.allclose(expected,actual,rtol=1e-12,atol=1e-12)
            reference_checks+=1
        artifacts.append({'path':str(path),'sha256':sha(path),'kind':a['kind']})
        for group in ('objectives','constraints','model'):
            payload=a.get(group)
            if not payload: continue
            for i,c in enumerate(payload['channels']):
                md=c['metadata'];state=c['state'];y=md['train_Y'];n=y.shape[0];std=y.std().item() if n>1 else 0
                trans_std=state['outcome_transform.stdvs'].item();v=md['train_Yvar'].flatten();effective=c['standardized_noise'].flatten()
                assert y.dtype==torch.float64
                for f in c['fit_outcomes']:fit[(run.name.split('_seed')[0],f['status'])]+=1
                records.append({'run_id':run.name,'artifact':path.name,'group':group,'channel':names[group][i],'n':n,'observed_std':std,'transform_std':trans_std,'mean_only':std<1e-8,'requested_raw_variance':v[0].item(),'requested_standardized_variance':v[0].item()/trans_std**2,'effective_standardized_variance_min':effective.min().item(),'effective_standardized_variance_max':effective.max().item(),'fit_status':c['fit_outcomes'][0]['status'],'fit_errors':json.dumps(c['fit_outcomes'][0]['errors'])})
write_csv('c05_channels.csv',records);write_csv('c05_artifacts.csv',artifacts);write_csv('c05_proposals.csv',proposals)
transitions=[]
for r in [-10.,-2.,-1.,-.1,0.,.1,1.,2.,10.]:
    t=torch.tensor(r,dtype=torch.double)
    transitions.append({'residual_over_eta':r,'fatmoid_feasibility':fatmoid(-t).item(),'ordinary_logistic_for_comparison':torch.sigmoid(-t).item()})
write_csv('c05_transitions.csv',transitions)
# Illustrative raw physical diagnostic values: actual fatmoid rather than logistic.
physical=[]
for name,threshold,values,unit in [('sigma_x',.001,[0.,.0005,.001,.0011,.002],'m'),('energy_upper',205e6,[205e6-.001,205e6,205e6+.001,205e6+1.],'eV'),('transmission_lower',.9,[1.,.9,.8999,.899],'fraction')]:
    for value in values:
        residual=threshold-value if 'lower' in name else value-threshold
        physical.append({'channel':name,'diagnostic':value,'unit':unit,'residual':residual,'eta':.001,'fatmoid_feasibility':fatmoid(torch.tensor(-residual/.001,dtype=torch.double)).item()})
write_csv('c05_physical_transitions.csv',physical)
files=['src/mobo_linac/acquisition/mobo.py','src/mobo_linac/campaigns/strategies.py','src/mobo_linac/models/gp.py','src/mobo_linac/models/pipeline.py','src/mobo_linac/models/artifacts.py','src/mobo_linac/constraints.py','src/mobo_linac/metrics/hypervolume.py']
for obj in [qLogNoisyExpectedHypervolumeImprovement,qLogNoisyExpectedImprovement,compute_smoothed_feasibility_indicator,fatmoid,MCSamplerMixin]:files.append(inspect.getfile(obj))
sources=[{'path':p,'sha256':sha(p)} for p in sorted(set(files))]
summary={'botorch':botorch.__version__,'gpytorch':gpytorch.__version__,'torch':torch.__version__,'campaigns':len(manifest),'saved_model_artifacts':len(artifacts),'verified_acquisition_references':reference_checks,'completion_verified_sources':source_checks,'saved_channel_fits':len(records),'proposal_batches':len(proposals),'proposal_methods':dict(Counter(x['method'] for x in proposals)),'fit_status_by_algorithm':{f'{k[0]}:{k[1]}':v for k,v in sorted(fit.items())},'acquisition_defaults_inferred_from_matching_installed_version':{'qLogNEHVI_mc':list(qLogNoisyExpectedHypervolumeImprovement._default_sample_shape),'qLogNEI_mc':list(qLogNoisyExpectedImprovement._default_sample_shape),'eta':.001,'fat':True,'tau_relu':1e-6,'mobo_tau_max':.001,'scalar_tau_max':.01,'prune_baseline':True},'mean_only_channels':dict(Counter(x['channel'] for x in records if x['mean_only'])),'effective_noise_floor_double':gpytorch.settings.min_fixed_noise.value(torch.double),'source_files':sources,'limitations':['Acquisition objects and sampler base samples were not persisted; sample counts, smoothing and pruning are reconstructed from explicit call sites and the installed BoTorch version matching all archived environment files. Actual retained baseline cardinalities cannot be recovered from these artifacts.','Saved config.json includes nominal campaign defaults; actual budgets and workers must be read from campaign_manifest.csv and proposal history.','No production artifacts are changed and no simulations or surrogate fitting are performed.']}
(OUT/'c05_audit.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('source_files','limitations','completion_verified_sources')},indent=2))
