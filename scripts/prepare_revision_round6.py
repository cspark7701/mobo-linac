#!/usr/bin/env python3
"""Freeze round6 stratified historical sample and prospective campaign specification."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
import pandas as pd
from revision_ledgers import ARMS, load_ledgers

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/paper/revisions/evidence'
CONTROLS = ['solenoid_field_T', 'quad_1_gradient_T_m', 'quad_2_gradient_T_m',
            'gun_phase_deg', 'acc1_acc2_phase_deg', 'acc3_acc4_phase_deg']
STRATA = ['arm', 'seed', 'physically_feasible', 'stage', 'boundary']
SELECTION_SEED = 20261031


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stratify(frame):
    frame = frame.copy()
    margins = pd.DataFrame({k: (1e-3-frame[k])/1e-3 for k in
                           ['sigma_x_m', 'sigma_y_m', 'sigma_xp_rad', 'sigma_yp_rad', 'sigma_z_m']})
    margins['energy_lower'] = (frame.mean_kinetic_energy_eV-195e6)/5e6
    margins['energy_upper'] = (205e6-frame.mean_kinetic_energy_eV)/5e6
    margins['transmission'] = (frame.transmission_fraction-.9)/.1
    frame['boundary'] = np.where(margins.abs().min(axis=1) <= .1, 'near', 'interior')
    frame['nearest_channel'] = margins.abs().idxmin(axis=1)
    frame['min_signed_margin'] = margins.min(axis=1)
    frame['stage'] = np.where(frame.index_in_run <= 80, 'early', 'late')
    return frame


def select(frame):
    """Independent SRS without replacement within each declared stratum, at most two."""
    frame = stratify(frame)
    rng = np.random.default_rng(SELECTION_SEED)
    rows, strata = [], []
    for keys in itertools.product(sorted(frame.arm.unique()), range(42, 52),
                                  [False, True], ['early', 'late'], ['interior', 'near']):
        mask = np.ones(len(frame), dtype=bool)
        for key, value in zip(STRATA, keys):
            mask &= frame[key].to_numpy() == value
        group = frame.loc[mask].sort_values('evaluation_id')
        count, size = min(2, len(group)), len(group)
        identity = '|'.join(map(str, keys))
        strata.append(dict(zip(STRATA, keys), stratum=identity, population=size, selected=count))
        if count:
            chosen = group.iloc[rng.choice(size, count, replace=False)].copy()
            chosen['stratum'] = identity
            chosen['population'] = size
            chosen['selected'] = count
            chosen['inclusion_probability'] = count/size
            rows.append(chosen)
    return pd.concat(rows, ignore_index=True), pd.DataFrame(strata)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=EVIDENCE)
    args = parser.parse_args(argv)
    out = args.output_dir
    names = ['r6_sampling_manifest.csv', 'r6_sampling_strata.csv', 'r6_specification.json']
    if any((out/n).exists() for n in names):
        raise ValueError('Frozen protocol outputs already exist; never overwrite them.')
    frame = load_ledgers({k: v for k, v in ARMS.items() if k != 'sobol'})
    if len(frame) != 4800 or frame.duplicated(['run', 'evaluation_id']).any():
        raise ValueError('Unexpected primary population.')
    chosen, strata = select(frame)
    chosen['setting_id'] = chosen.run + '__' + chosen.evaluation_id
    columns = ['setting_id', 'run', 'evaluation_id', 'arm', 'seed', 'index_in_run',
               'physically_feasible', 'stage', 'boundary', 'nearest_channel', 'min_signed_margin',
               'stratum', 'population', 'selected', 'inclusion_probability', *CONTROLS]
    out.mkdir(parents=True, exist_ok=True)
    chosen[columns].to_csv(out/names[0], index=False)
    strata.to_csv(out/names[1], index=False)
    inputs = ['configs/publication_200MeV.yaml', 'bin/astra', 'bin/generator',
              'astra.in', 'pal_photo2.ini', 'gun.dat', 'PAL_SOL_A.dat', 'TWS_Sband.dat']
    for arm in sorted(frame.arm.unique()):
        for seed in range(42, 52):
            inputs.append(f'results/paper_production/04_primary/benchmark/per_seed/{arm}_seed_{seed}/evaluations.csv')
    grid = lambda n: {f'charge:{k}': n for k in ['nrad','nlong_in','nxf','nyf','nzf']}
    step = lambda n: {'newrun:h_max': .01/n, 'newrun:h_min': .001/n}
    medium, fine = {**grid(48), **step(2)}, {**grid(64), **step(4)}
    levels = {'production': {}, 'fixed_medium': medium, 'fixed_fine': fine,
              'combined_medium': {**medium, 'newrun:distribution': 'qr20k.ini'},
              'combined_fine': {**fine, 'newrun:distribution': 'qr40k.ini'}}
    specification = {
        'version': 1, 'selection_seed': SELECTION_SEED,
        'population': len(frame), 'sample_size': len(chosen), 'levels': levels,
        'tracking_attempts': len(chosen)*len(levels), 'workers_total': 2,
        'device': 'cuda:0', 'threads_per_process': 1, 'tracking_timeout_s': 86400,
        'sample_manifest_sha256': sha(out/names[0]), 'strata_sha256': sha(out/names[1]),
        'input_sha256': {p: sha(ROOT/p) for p in inputs},
        'nominal_reproduction_rtol': 1e-9, 'nominal_reproduction_atol': 1e-12,
        'refinement_tolerance': {'objectives_relative': .01, 'diagnostics_threshold_fraction': .01,
                                 'energy_absolute_eV': 10000, 'transmission_absolute': .0001},
        'scaling': {'seeds': list(range(42,52)), 'arms': ['raw','normalized'],
                    'budget_each': 160, 'initial':16, 'batch_size':8, 'batches':18,
                    'attempts_total':3200, 'posterior_samples':128,
                    'raw_temperature':.001, 'normalized_temperature':.001,
                    'residual_scales': [1e-3,1e-3,1e-3,1e-3,1e-3,5e6,5e6,.1],
                    'stream_policy': 'initial Sobol seed=group; posterior=100000+1000*group+iteration; '
                                     'proposal=200000+1000*group+iteration; fit=300000+1000*group+iteration',
                    'acquisition': 'qLogNEHVI', 'num_restarts':10,'raw_samples':1024,'maxiter':200,
                    'pilot': 'mock only; no additional physical pilot or tuning'},
        'analysis_seed':20261101,'bootstrap_resamples':10000,
        'no_adaptive_expansion':True, 'optional_scalarized_comparator':False,
        'minimum_free_disk_GiB':100,
    }
    (out/names[2]).write_text(json.dumps(specification, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'sample_size':len(chosen),'tracking_attempts':len(chosen)*len(levels),
                      'scaling_attempts':3200},indent=2))

if __name__ == '__main__':
    main()
