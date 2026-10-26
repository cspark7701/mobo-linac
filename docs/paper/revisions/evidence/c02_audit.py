"""Read-only audit of archived phase controls and numerical settings; no ASTRA runs."""
from pathlib import Path
import csv, hashlib, json, re
from collections import Counter
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent
BASE = ROOT / 'results/paper_production/04_primary/benchmark/per_seed'
PHASES = ['gun_phase_deg', 'acc1_acc2_phase_deg', 'acc3_acc4_phase_deg']
FIELDS = ['auto_phase','nrad','nlong_in','nxf','nyf','nzf','lmirror','l2d_3d','z_trans','h_max','h_min']
def setting(text,key):
    m = re.search(r'^\s*'+re.escape(key)+r'\s*=\s*([^\n,]+)',text,re.M|re.I)
    return m[1].strip().lower() if m else None
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
rows=[]; settings=Counter(); coupled=Counter(); inputs=0; source_files={}; configs=[]
for run in sorted(BASE.iterdir()):
    if not (run/'evaluations.csv').exists(): continue
    cfg=json.loads((run/'config.json').read_text())
    configs.append({'path':str((run/'config.json').relative_to(ROOT)),'sha256':sha(run/'config.json'),'variables':cfg['design_variables'][3:]})
    rs=list(csv.DictReader((run/'evaluations.csv').open()))
    for r in rs:
        r['method']=run.name.rsplit('_seed_',1)[0]; r['campaign']=run.name
        rows.append(r)
        manifest=Path(r['manifest_path']); local=ROOT/str(manifest).split('/mobo-linac/',1)[1]
        ip=local.parent/'inputs/astra.in'
        t=ip.read_text(); inputs+=1
        settings[tuple(setting(t,k) for k in FIELDS)]+=1
        coupled[(setting(t,'phi(2)')==setting(t,'phi(3)'),setting(t,'phi(4)')==setting(t,'phi(5)'))]+=1
    sf=ip.parent/'pal_photo2.ini'
    source_files[run.name]={'sha256':sha(sf),'lines':sum(1 for _ in sf.open()),'path':str(sf.relative_to(ROOT))}
ref=configs[0]['variables']; assert all(c['variables']==ref for c in configs)
bounds=[{'name':v['name'],'nominal_deg':v['nominal_value'],'lower_deg':v['lower_bound'],'upper_deg':v['upper_bound'],'half_width_deg':(v['upper_bound']-v['lower_bound'])/2,'width_deg':v['upper_bound']-v['lower_bound'],'wrapped_nominal_deg':(v['nominal_value']+180)%360-180} for v in ref]
rolepath=ROOT/'results/paper_production/06_candidate_audit/robustness/representatives.json'
roles=json.loads(rolepath.read_text())['roles']; representatives=[]
for role,identity in roles.items():
    r=next(r for r in rows if r['run_id']==identity['run_id'] and r['evaluation_id']==identity['evaluation_id'])
    representatives.append({'role':role,**identity,'phases_deg':{k:float(r[k]) for k in PHASES},'offset_from_nominal_deg':{k:float(r[k])-ref[j]['nominal_value'] for j,k in enumerate(PHASES)}})
bins=[]
lo,hi=ref[2]['lower_bound'],ref[2]['upper_bound']
for method in sorted({r['method'] for r in rows}):
    for i in range(8):
        left=lo+(hi-lo)*i/8;right=lo+(hi-lo)*(i+1)/8
        group=[r for r in rows if r['method']==method and left<=float(r[PHASES[2]]) and (float(r[PHASES[2]])<right or i==7 and float(r[PHASES[2]])<=right)]
        feasible=sum(r['physically_feasible']=='True' for r in group)
        energy=sum(195e6<=float(r['mean_kinetic_energy_eV'])<=205e6 for r in group)
        bins.append({'method':method,'bin':i+1,'lower_deg':left,'upper_deg':right,'evaluations':len(group),'feasible':feasible,'energy_in_band':energy})
report={'schema_version':1,'scope':'existing-data descriptive audit only; no crest calibration, altered-domain performance or numerical convergence inferred','campaigns':len(configs),'evaluations':len(rows),'archived_inputs_checked':inputs,'phase_bounds':bounds,'coupling_counts':[{'acc1_acc2_equal':k[0],'acc3_acc4_equal':k[1],'count':n} for k,n in coupled.items()],'numerical_settings':[{'settings':dict(zip(FIELDS,k)),'count':n} for k,n in settings.items()],'source_distribution_copies':source_files,'recorded_initial_particle_counts':dict(Counter(r['n_particles_initial'] for r in rows)),'configuration_sources':configs,'representative_phases':representatives,'acc3_acc4_coverage_bins':bins,'initial_distribution_sha256_variants':sorted({s['sha256'] for s in source_files.values()})}
(OUT/'c02_phase_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Checked {inputs} inputs across {len(configs)} campaigns; settings variants {len(settings)}; source variants {len(report["initial_distribution_sha256_variants"])}')
