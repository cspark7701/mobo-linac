#!/usr/bin/env python3
"""Analyze completed round6 studies without modifying their simulation evidence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from prepare_revision_round6 import ROOT, EVIDENCE, sha
from run_revision_round6_resolution import read_records, QUANTITIES, MANIFEST, SPEC
from run_revision_round6_scaling import campaign_config, check_completed, check_pair


def paired_summary(values, first, second, spec):
    """Paired groups only; the intervals do not include within-group selection uncertainty."""
    differences=values[first]-values[second]
    rng=np.random.default_rng(spec['analysis_seed'])
    samples=rng.choice(differences.to_numpy(),size=(spec['bootstrap_resamples'],len(differences)),replace=True).mean(1)
    low,high=np.quantile(samples,[.025,.975])
    return {'first':first,'second':second,'groups':len(differences),'mean_difference':differences.mean(),
            'ci_lower_conditional':low,'ci_upper_conditional':high,
            'minimum_difference':differences.min(),'positive_groups':int((differences>0).sum())}


def weighted_fractions(frame):
    """Stratified SRS estimates and finite-population design variance, one historical run."""
    n_total=frame.drop_duplicates('stratum').population.sum()
    estimate=variance=unknown=0.
    for _,g in frame.groupby('stratum'):
        population=int(g.population.iloc[0]);selected=int(g.selected.iloc[0])
        if len(g)!=selected:
            raise ValueError('Incomplete sampled stratum.')
        weight=population/n_total
        estimate+=weight*g.feasible.mean()
        unknown+=weight*(~g.simulation_valid).mean()
        if selected<population:
            if selected<2:
                raise ValueError('Sampled singleton variance is not estimable.')
            variance+=weight**2*(1-selected/population)*g.feasible.astype(float).var(ddof=1)/selected
    return {'fraction':estimate,'design_variance':variance,'physical_upper_if_invalid_pass':estimate+unknown,
            'unknown_fraction':unknown,'population':int(n_total),'sample':len(frame)}


def numerical(directory,spec):
    marker=json.loads((directory/'complete.json').read_text())
    if marker.get('mock') or marker['spec_sha256']!=sha(SPEC) or marker['results_sha256']!=sha(directory/'results.jsonl'):
        raise ValueError('Invalid numerical completion receipt.')
    records=read_records(directory/'results.jsonl');manifest=pd.read_csv(MANIFEST)
    if marker['tasks']!=spec['tracking_attempts'] or len(records)!=spec['tracking_attempts']:
        raise ValueError('Incomplete numerical allocation.')
    rows=[]
    for value in records.values():
        quantities={**(value.get('objectives') or {}),**(value.get('diagnostics') or {})}
        rows.append({'setting_id':value['role'],'level':value['level'],'simulation_valid':value['simulation_valid'],
            'feasible':bool(value['simulation_valid'] and value['physically_feasible']),
            'runtime_s':value['runtime_s'],**{key:quantities.get(key,np.nan) for key in QUANTITIES}})
    frame=pd.DataFrame(rows)
    if frame.duplicated(['setting_id','level']).any():
        raise ValueError('Duplicated numerical identity.')
    expected={(s,l) for s in manifest.setting_id for l in spec['levels']}
    if set(zip(frame.setting_id,frame.level))!=expected:
        raise ValueError('Unexpected numerical task allocation.')
    frame=frame.merge(manifest,on='setting_id',validate='many_to_one')
    for key in ['sigma_x_m','sigma_y_m','sigma_xp_rad','sigma_yp_rad','sigma_z_m']:
        frame['margin_'+key]=.001-frame[key]
    frame['margin_energy_lower_eV']=frame.mean_kinetic_energy_eV-195e6
    frame['margin_energy_upper_eV']=205e6-frame.mean_kinetic_energy_eV
    frame['margin_transmission']=frame.transmission_fraction-.9
    rows=[]
    for (arm,seed,level),group in frame.groupby(['arm','seed','level']):
        rows.append({'arm':arm,'seed':seed,'level':level,**weighted_fractions(group)})
    fractions=pd.DataFrame(rows)
    pairs=[]
    for level,group in fractions.groupby('level'):
        wide=group.pivot(index='seed',columns='arm',values='fraction')
        var=group.pivot(index='seed',columns='arm',values='design_variance')
        for other in ['unconstrained_qlognehvi','scalarized_bo']:
            first='constrained_qlognehvi'
            summary=paired_summary(wide,first,other,spec)
            # Sum of SEs bounds the covariance contribution without assuming method independence.
            summary['design_se_conservative']=np.sqrt(((np.sqrt(var[first])+np.sqrt(var[other]))**2).sum())/len(wide)
            pairs.append({'level':level,**summary})
    values=[]
    base=frame[frame.level=='production'].set_index('setting_id')
    for row in frame.itertuples():
        for key in QUANTITIES:
            before=float(base.loc[row.setting_id,key]);after=float(getattr(row,key))
            values.append({'setting_id':row.setting_id,'arm':row.arm,'seed':row.seed,'level':row.level,
                'quantity':key,'production':before,'value':after,'delta':after-before,
                'delta_relative':(after-before)/abs(before) if before else np.nan})
    frame['nominal_feasibility_changed']=frame.feasible!=frame.physically_feasible
    checks=[]
    for low,high in [('fixed_medium','fixed_fine'),('combined_medium','combined_fine')]:
        left=frame[frame.level==low].set_index('setting_id');right=frame[frame.level==high].set_index('setting_id')
        for setting in left.index:
            for key in QUANTITIES:
                before=float(left.loc[setting,key]);after=float(right.loc[setting,key])
                if key in QUANTITIES[:3]:
                    tolerance=abs(before)*spec['refinement_tolerance']['objectives_relative']
                elif key=='mean_kinetic_energy_eV':
                    tolerance=spec['refinement_tolerance']['energy_absolute_eV']
                elif key=='transmission_fraction':
                    tolerance=spec['refinement_tolerance']['transmission_absolute']
                else:
                    tolerance=.001*spec['refinement_tolerance']['diagnostics_threshold_fraction']
                valid=bool(left.loc[setting,'simulation_valid'] and right.loc[setting,'simulation_valid'])
                checks.append({'setting_id':setting,'comparison':high+' - '+low,'quantity':key,
                    'delta':after-before,'tolerance':tolerance,'comparison_valid':valid,
                    'within_tolerance':bool(valid and np.isfinite(after-before) and abs(after-before)<=tolerance)})
    return {'resolution_values':pd.DataFrame(values),'resolution_classification':frame,
            'resolution_fractions':fractions,'resolution_paired':pd.DataFrame(pairs),
            'resolution_tolerances':pd.DataFrame(checks)}


def scaling(directory,spec):
    receipt=json.loads((directory/'complete.json').read_text())
    if receipt['spec_sha256']!=sha(SPEC):
        raise ValueError('Scaling specification mismatch.')
    for name,digest in receipt['campaigns'].items():
        if sha(directory/name)!=digest:
            raise ValueError('Scaling completion checksum mismatch.')
    rows=[];stages=[]
    for seed in spec['scaling']['seeds']:
        check_pair(directory,seed,spec)
        for arm in spec['scaling']['arms']:
            run=directory/f'{arm}_seed_{seed}'
            check_completed(run,campaign_config(spec,arm,seed),spec)
            f=pd.read_csv(run/'evaluations.csv')
            if len(f)!=160 or f.evaluation_id.duplicated().any():
                raise ValueError('Scaling evaluation allocation mismatch.')
            valid=f.simulation_valid.astype(bool);feasible=f.physically_feasible.astype(bool)&valid
            elapsed=json.loads((run/'run_complete.json').read_text())['elapsed_wall_time_s']
            rows.append({'arm':arm,'seed':seed,'feasible_fraction':feasible.mean(),
                'post_init_feasible_fraction':feasible.iloc[16:].mean(),
                'invalid_attempts':int((~valid).sum()),'elapsed_wall_time_s':elapsed})
            for label,part in [('initial',f.iloc[:16]),('early_post',f.iloc[16:80]),('late',f.iloc[80:])]:
                v=part.simulation_valid.astype(bool)
                transverse=(part[['sigma_x_m','sigma_y_m','sigma_xp_rad','sigma_yp_rad']]>.001).any(axis=1)
                energy=(part.mean_kinetic_energy_eV<195e6)|(part.mean_kinetic_energy_eV>205e6)
                other=(part.sigma_z_m>.001)|(part.transmission_fraction<.9)
                stages.append({'arm':arm,'seed':seed,'stage':label,'attempts':len(part),
                    'invalid':int((~v).sum()),'transverse_only':int((v&transverse&~energy&~other).sum()),
                    'energy_only':int((v&energy&~transverse&~other).sum()),
                    'multiple_groups':int((v&((transverse.astype(int)+energy.astype(int)+other.astype(int))>1)).sum()),
                    'other_only':int((v&other&~energy&~transverse).sum()),
                    'feasible':int((v&part.physically_feasible.astype(bool)).sum())})
    runs=pd.DataFrame(rows);pairs=[]
    for endpoint in ['feasible_fraction','post_init_feasible_fraction','elapsed_wall_time_s']:
        wide=runs.pivot(index='seed',columns='arm',values=endpoint)
        pairs.append({'endpoint':endpoint,**paired_summary(wide,'normalized','raw',spec)})
    return {'scaling_runs':runs,'scaling_paired':pd.DataFrame(pairs),'scaling_channels':pd.DataFrame(stages)}


def uncertainty_plot(table, destination):
    """Display group-bootstrap intervals; numerical selection SE is a separate marker."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    frame = table.copy()
    if "endpoint" in frame:
        frame = frame[frame.endpoint != "elapsed_wall_time_s"]
        labels = frame.endpoint.str.replace("_", " ").tolist()
    else:
        labels = (frame.level + ": " + frame.second.str.replace("_", " ")).tolist()
    fig, ax = plt.subplots(figsize=(8, max(3, .4 * len(frame))))
    for position, row in enumerate(frame.itertuples()):
        ax.plot([row.ci_lower_conditional, row.ci_upper_conditional], [position, position], color="C0")
        ax.plot(row.mean_difference, position, "o", color="C0")
        if hasattr(row, "design_se_conservative"):
            ax.plot([row.mean_difference - row.design_se_conservative,
                     row.mean_difference + row.design_se_conservative],
                    [position + .15, position + .15], color="C1", linewidth=2)
    ax.set_yticks(range(len(labels)), labels)
    ax.axvline(0, color="grey", linestyle="--")
    ax.grid(alpha=.25)
    ax.set_xlabel("Paired feasible-fraction difference (first minus second)")
    ax.set_title("Conditional 95% group-bootstrap intervals" +
                 ("; orange: separate design SE" if "design_se_conservative" in frame else ""))
    fig.tight_layout()
    fig.savefig(destination)
    plt.close(fig)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study',choices=['resolution','scaling'])
    parser.add_argument('--input-dir',type=Path)
    parser.add_argument('--output-dir',type=Path,default=EVIDENCE)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args(argv);spec=json.loads(SPEC.read_text())
    source=args.input_dir or ROOT/'results/revision_round6'/args.study
    receipt_path=args.output_dir/f'r6_{args.study}_analysis.json'
    if args.resume and receipt_path.exists():
        receipt=json.loads(receipt_path.read_text())
        if receipt['spec_sha256']!=sha(SPEC) or receipt['completion_sha256']!=sha(source/'complete.json'):
            raise ValueError('Existing analysis input identity changed.')
        outputs=receipt.get('outputs_sha256',{})
        if not outputs or any(sha(args.output_dir/name)!=digest for name,digest in outputs.items()):
            raise ValueError('Existing analysis output checksum mismatch.')
        return
    names=(['resolution_values' ,'resolution_classification','resolution_fractions','resolution_paired','resolution_tolerances']
           if args.study=='resolution' else ['scaling_runs','scaling_paired','scaling_channels'])
    if any((args.output_dir/('r6_'+name+'.csv')).exists() for name in names):
        raise ValueError('Derived evidence already exists; use an isolated output directory.')
    tables=(numerical if args.study=='resolution' else scaling)(source,spec)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for name,table in tables.items():
        table.to_csv(args.output_dir/('r6_'+name+'.csv'),index=False)
    uncertainty_plot(tables[args.study+'_paired'], args.output_dir/f'r6_{args.study}_uncertainty.pdf')
    metadata={'spec_sha256':sha(SPEC),'completion_sha256':sha(source/'complete.json'),
              'study':args.study,'tables':{name:len(table) for name,table in tables.items()},
              'outputs_sha256':{p.name:sha(p) for p in args.output_dir.glob(f'r6_{args.study}_*') if p.suffix in {'.csv','.pdf'}},
              'uncertainty':'Paired bootstrap conditional on sampled observations; numerical-study design uncertainty reported separately. '
                            'No claim of simultaneous coverage, numerical convergence or machine reliability.'}
    (args.output_dir/f'r6_{args.study}_analysis.json').write_text(json.dumps(metadata,indent=2)+'\n')

if __name__=='__main__':
    main()
