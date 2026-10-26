#!/usr/bin/env python3
"""Reclassify immutable primary observations under documented acceptance profiles."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

METHODS = ('constrained_qlognehvi', 'unconstrained_qlognehvi', 'scalarized_bo')


def profile_masks(df):
    """Published subsets deliberately omit unspecified/ambiguous diagnostics."""
    valid = df.simulation_valid.eq(True)
    x, y = df.sigma_x_m, df.sigma_y_m
    xp, yp = df.sigma_xp_rad, df.sigma_yp_rad
    z, energy, transmission = df.sigma_z_m, df.mean_kinetic_energy_eV, df.transmission_fraction
    spread = df.sigma_energy_eV
    cols = ['sigma_x_m','sigma_y_m','sigma_xp_rad','sigma_yp_rad','sigma_z_m',
            'mean_kinetic_energy_eV','transmission_fraction','sigma_energy_eV']
    finite = np.isfinite(df[cols].to_numpy()).all(axis=1)
    base = valid & finite
    tdr = (base & (x < .3e-3) & (y < .3e-3) & (xp < .2663e-3) & (yp < .2663e-3)
           & (z < 1e-3) & (energy > 200e6) & (transmission > .9999))
    return {
        'kls_tdr_optimization': tdr,
        'kls_tdr_optimization_plus_spread': tdr & (spread / energy <= .005),
        'production': base & (x <= 1e-3) & (y <= 1e-3) & (xp <= 1e-3) & (yp <= 1e-3)
                      & (z <= 1e-3) & (energy >= 195e6) & (energy <= 205e6) & (transmission >= .9),
        # Strict inequalities follow the NAPAC text; energy band interpreted inclusively.
        'napac2025': base & (x < .3e-3) & (y < .3e-3) & (xp < .3e-3) & (yp < .3e-3)
                      & (z < 1e-3) & (energy >= 195e6) & (energy <= 205e6) & (transmission > .9999),
        # Necessary, not sufficient: omit geometric emittance and ambiguous pulse duration.
        'jinst2024_necessary_subset': base & (x < .2e-3) & (y < .2e-3)
                      & (energy >= 200e6) & (spread / energy <= .002) & (transmission > .9999),
        # Table 2's scalar transverse size interpreted as requiring both planes.
        # Geometric emittance intentionally omitted; normalized emittance is not substituted.
        'jkps2025_necessary_subset': base & (x <= .2e-3) & (y <= .2e-3)
                      & (z <= .9e-3) & (energy >= 200e6) & (spread <= .5e6),
    }


def analyze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    records, manifest, configs, tdr_candidates = [], [], [], []
    for method in METHODS:
        paths = sorted(root.glob(f'{method}_seed_*/evaluations.csv'))
        if len(paths) != 10:
            raise ValueError(f'Expected ten campaigns for {method}')
        for path in paths:
            df = pd.read_csv(path)
            if len(df) != 160 or not df.evaluation_id.is_unique:
                raise ValueError(f'Unexpected evaluation ledger: {path}')
            if not (path.parent/'run_complete.json').exists():
                raise ValueError(f'Missing completion marker: {path.parent}')
            marker=json.loads((path.parent/'run_complete.json').read_text())
            for name in ('evaluations.csv','config.json'):
                if hashlib.sha256((path.parent/name).read_bytes()).hexdigest() != marker['artifacts'][name]:
                    raise ValueError(f'Completion checksum mismatch: {path.parent/name}')
            masks = profile_masks(df)
            cols=['run_id','evaluation_id','norm_emit_x_m_rad','norm_emit_y_m_rad','sigma_energy_eV',
                  'sigma_x_m','sigma_y_m','sigma_xp_rad','sigma_yp_rad','sigma_z_m',
                  'mean_kinetic_energy_eV','transmission_fraction']
            for candidate in df.loc[masks['kls_tdr_optimization'],cols].to_dict('records'):
                candidate['relative_rms_energy_spread']=candidate['sigma_energy_eV']/candidate['mean_kinetic_energy_eV']
                candidate['relative_spread_specification_pass']=candidate['relative_rms_energy_spread'] <= .005
                tdr_candidates.append(candidate)
            np.testing.assert_array_equal(masks['production'], df.physically_feasible)
            record = {'method':method,'run':path.parent.name,'evaluations':len(df),
                      'valid':int(df.simulation_valid.sum()),
                      **{name:int(mask.sum()) for name,mask in masks.items()},
                      'size_x_below_0p2mm':int((df.sigma_x_m < .2e-3).sum()),
                      'size_y_below_0p2mm':int((df.sigma_y_m < .2e-3).sum())}
            records.append(record)
            cfg = json.loads((path.parent/'config.json').read_text())
            configs.append(cfg['constraints'])
            for filename in ['evaluations.csv','config.json','run_complete.json']:
                source=path.parent/filename
                manifest.append({'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    assert all(c == configs[0] for c in configs)
    pd.DataFrame(tdr_candidates,columns=cols+['relative_rms_energy_spread','relative_spread_specification_pass']).to_csv(out/'c01_tdr_candidates.csv',index=False)
    pd.DataFrame(records).to_csv(out/'c01_reclassification_by_run.csv',index=False)
    totals = pd.DataFrame(records).groupby('method').sum(numeric_only=True).reset_index()
    totals.to_csv(out/'c01_reclassification_totals.csv',index=False)
    (out/'c01_metadata.json').write_text(json.dumps({'classification':'post-hoc; original labels preserved',
        'profiles': {'production':'Archived config, all eight inequalities',
            'kls_tdr_optimization':'Korea-4GSR TDR 4GSR-I-DE-TDR-001 (October 2025), Table 2.1.4.6, printed p.2-104: all seven strict inequalities; no upper energy cutoff',
            'kls_tdr_optimization_plus_spread':'TDR Table 2.1.4.6 plus relative RMS energy spread <=0.5% from Table 2.1.4.4; not full specification verification',
            'napac2025':'WECN03 Constraints and Feasibility; strict size/divergence/length/transmission limits',
            'jinst2024_necessary_subset':'P01023 Sec4.1/Table4, omit ambiguous pulse duration and geometric emittance',
            'jkps2025_necessary_subset':'Table2, omit geometric emittance; both transverse sizes required'},
        'published_profile_caveat':'Subset success is not full-profile feasibility; zero successes exclude full-profile success under the stated interpretations. TDR optimization success is not full machine acceptance: geometric emittance, pulse FWHM, pulse-to-pulse stability and downstream matching are not checked.',
        'tdr_source': {'report':'4GSR-I-DE-TDR-001','edition':'October 2025',
            'landing_page':'https://kls.kbsi.re.kr/eng/sub0305/view/id/63794',
            'url':'https://kls.kbsi.re.kr/_files/board/20260420/f0935668f91c7c3292fd1e843c1a9a25.pdf',
            'sha256':'47b4218ace4bc8c1a5f166fb5523c7dd63e4962b5882217c1fac90a28126f40d',
            'table_pages':{'2.1.4.4':{'printed':'2-98','pdf_one_based':115},'2.1.4.6':{'printed':'2-104','pdf_one_based':121},'2.1.4.9':{'printed':'2-108','pdf_one_based':125}}},
        'production_constraints':configs[0], 'inputs':manifest},indent=2)+'\n')
    print(totals.to_string(index=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('results/paper_production/04_primary/benchmark/per_seed'))
    parser.add_argument('--output',type=Path,default=Path('docs/paper/revisions/evidence'))
    args=parser.parse_args()
    analyze(args.root,args.output)
