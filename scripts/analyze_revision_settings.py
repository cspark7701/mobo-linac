"""C08: read-only source, representative, trajectory and constraint audit."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/paper/revisions/evidence'
BASE = ROOT / 'results/paper_production/04_primary/benchmark/per_seed'
ROLE_PATH = ROOT / 'results/paper_production/06_candidate_audit/robustness/representatives.json'
OBJECTIVES = ['norm_emit_x_m_rad', 'norm_emit_y_m_rad', 'sigma_energy_eV']
SIDES = [('sigma_x_m','upper',1e-3),('sigma_y_m','upper',1e-3),
         ('sigma_xp_rad','upper',1e-3),('sigma_yp_rad','upper',1e-3),
         ('sigma_z_m','upper',1e-3),('mean_kinetic_energy_eV','lower',195e6),
         ('mean_kinetic_energy_eV','upper',205e6),('transmission_fraction','lower',.9)]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def source_moments(a):
    # Exclude the reference and status -3 probe records from source moment estimates.
    particles = a[1:][a[1:,9] == -1].copy()
    w = np.abs(particles[:,7]); w /= w.sum()
    def variance(v):
        return np.sum(w * (v-np.sum(w*v))**2)
    def emittance(x,p):
        cov=np.sum(w*(x-np.sum(w*x))*(p-np.sum(w*p)))
        return np.sqrt(max(0.,variance(x)*variance(p)-cov**2))/510998.95
    t=(particles[:,6]+a[0,6])*1e-9
    r=np.hypot(particles[:,0],particles[:,1])
    pz=particles[:,5]+a[0,5]
    kinetic=np.sqrt(particles[:,3]**2+particles[:,4]**2+pz**2+510998.95**2)-510998.95
    return {'ordinary_records_excluding_reference':len(particles),
        'probe_records':int((a[:,9]==-3).sum()),'all_records':len(a),
        'file_charge_magnitude_nC':float(np.abs(a[:,7]).sum()),
        'sigma_x_m':float(np.sqrt(variance(particles[:,0]))),
        'sigma_y_m':float(np.sqrt(variance(particles[:,1]))),
        'sigma_emission_time_s':float(np.sqrt(variance(t))),
        'gaussian_equivalent_fwhm_s':float(np.sqrt(8*np.log(2)*variance(t))),
        'max_radius_m':float(r.max()),'r_p95_m':float(np.percentile(r,95)),
        'norm_emit_x_m_rad':float(emittance(particles[:,0],particles[:,3])),
        'norm_emit_y_m_rad':float(emittance(particles[:,1],particles[:,4])),
        'mean_kinetic_energy_eV':float(np.sum(w*kinetic)),
        'std_kinetic_energy_eV':float(np.sqrt(variance(kinetic))),
        'sigma_px_eV_c':float(np.sqrt(variance(particles[:,3]))),
        'sigma_py_eV_c':float(np.sqrt(variance(particles[:,4])))}

def analyze():
    manifest=[]
    def record(p):
        manifest.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
    frames=[]
    for p in sorted(BASE.glob('*/evaluations.csv')):
        marker=json.loads((p.parent/'run_complete.json').read_text())
        if sha(p)!=marker['artifacts'][p.name]:raise ValueError(p)
        record(p); frames.append(pd.read_csv(p))
    df=pd.concat(frames,ignore_index=True)
    assert len(df)==4800 and df.simulation_valid.all()
    roles=json.loads(ROLE_PATH.read_text())['roles']; record(ROLE_PATH)
    cfg_path=BASE/next(iter(roles.values()))['run_id']/'config.json'
    cfg=json.loads(cfg_path.read_text());record(cfg_path)
    names=[v['name'] for v in cfg['design_variables']]
    representative_rows=[];trajectories=[]
    for role,identity in roles.items():
        row=df[(df.run_id==identity['run_id']) & (df.evaluation_id==identity['evaluation_id'])].iloc[0]
        result={'role':role,**row[['run_id','evaluation_id']+names+OBJECTIVES+[x[0] for x in SIDES if x[1]=='upper']+['transmission_fraction']].to_dict()}
        for channel,side,threshold in SIDES:
            result[channel+':'+side+'_margin']=(threshold-row[channel] if side=='upper' else row[channel]-threshold)/abs(threshold)
        representative_rows.append(result)
        mp=Path(row.manifest_path);m=json.loads(mp.read_text());record(mp)
        arrays={}
        for axis in 'XYZ':
            p=Path(row.work_dir)/f'astra.{axis}emit.001'
            if sha(p)!=m['output_hashes'][p.name]:raise ValueError(p)
            record(p);arrays[axis]=np.loadtxt(p)
        for target in [.5,1.8,5.2,5.3,8.6,8.8,12.4,12.6,16.2]:
            x,y,z=[arrays[a][np.argmin(abs(arrays[a][:,0]-target))] for a in 'XYZ']
            trajectories.append({'role':role,'target_z_m':target,'recorded_z_m':float(x[0]),
                'emit_x_um_rad':float(x[5]),'emit_y_um_rad':float(y[5]),
                'sigma_x_mm':float(x[3]),'sigma_y_mm':float(y[3]),
                'mean_energy_MeV':float(z[2]),'sigma_energy_MeV':float(z[4]*1e-3),
                'linear_z_energy_correlation':float(z[6]/z[4])})
        np.testing.assert_allclose([arrays['X'][-1,5]*1e-6,arrays['Y'][-1,5]*1e-6,arrays['Z'][-1,4]*1e3],row[OBJECTIVES].to_numpy(float),rtol=1e-10)
    input_dir=mp.parent/'inputs'
    source=input_dir/'pal_photo2.ini';record(source)
    if sha(source)!=m['input_hashes'][source.name]:raise ValueError(source)
    source_stats=source_moments(np.loadtxt(source))
    deck=input_dir/'astra.in';record(deck);text=deck.read_text()
    geometry={}
    for key in ['c_pos(1)','c_pos(2)','c_pos(3)','c_pos(4)','c_pos(5)','s_pos(1)','q_pos(1)','q_pos(2)','q_length(1)','q_length(2)','z_trans','zstop']:
        geometry[key]=float(re.search(r'^\s*'+re.escape(key)+r'\s*=\s*([^,\n]+)',text,re.M|re.I)[1])
    counts=[]
    for channel,side,t in SIDES:
        margins=(t-df[channel] if side=='upper' else df[channel]-t)/abs(t)
        counts.append({'channel':channel,'side':side,'threshold':t,'violations':int((margins<0).sum()),'min_margin':margins.min(),'min_value':df[channel].min(),'max_value':df[channel].max()})
    nominal=np.array([v['nominal_value'] for v in cfg['design_variables']])
    matching=np.isclose(df[names].to_numpy(),nominal,rtol=0,atol=1e-10).all(axis=1)
    pd.DataFrame(representative_rows).to_csv(OUT/'c08_representatives.csv',index=False)
    pd.DataFrame(trajectories).to_csv(OUT/'c08_trajectories.csv',index=False)
    pd.DataFrame(counts).to_csv(OUT/'c08_constraint_activity.csv',index=False)
    metadata={'source_moments':source_stats,'geometry_m':geometry,'primary_nominal_matches':int(matching.sum()),
        'scope':'Source moments exclude reference and probes; generation recipe and cathode material unverified. Trajectories are observational, not mechanism-isolation experiments.',
        'inputs':manifest}
    (OUT/'c08_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({k:v for k,v in metadata.items() if k!='inputs'},indent=2))
    print(pd.DataFrame(counts).to_string(index=False))

if __name__=='__main__':analyze()
