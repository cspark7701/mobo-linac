#!/usr/bin/env python3
"""Post-hoc C03 Pareto analysis of immutable stage-04 primary campaigns."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

METHODS = ('constrained_qlognehvi', 'unconstrained_qlognehvi', 'scalarized_bo')
LABELS = ('Constraint-aware MOBO', 'Unconstrained MOBO', 'Scalarized BO')
OBJECTIVES = ('norm_emit_x_m_rad', 'norm_emit_y_m_rad', 'sigma_energy_eV')
SCALES = np.array([1e-6, 1e-6, 1e6])
VARIABLES = ('solenoid_field_T', 'quad_1_gradient_T_m', 'quad_2_gradient_T_m',
             'gun_phase_deg', 'acc1_acc2_phase_deg', 'acc3_acc4_phase_deg')


def nondominated(points):
    points = np.unique(np.asarray(points, dtype=float).reshape(-1, 3), axis=0)
    if not len(points):
        return points
    return points[~np.any(np.all(points[:, None] <= points[None, :], axis=2)
                         & np.any(points[:, None] < points[None, :], axis=2), axis=0)]


def additive_epsilon(a, reference):
    if not len(reference):
        raise ValueError('An empirical reference must not be empty')
    return float(np.max(np.min(np.max(a[:, None] - reference[None, :], axis=2), axis=0))) if len(a) else np.inf


def igd_plus(a, reference):
    if not len(reference):
        raise ValueError('An empirical reference must not be empty')
    return float(np.mean(np.min(np.linalg.norm(np.maximum(a[:, None] - reference[None, :], 0), axis=2), axis=0))) if len(a) else np.inf


def coverage(a, b):
    if not len(b):
        return np.nan
    return float(np.mean(np.any(np.all(a[:, None] <= b[None, :], axis=2), axis=0))) if len(a) else 0.


def hypervolume(a, reference):
    """Exact 3D union volume by slicing, in minimization coordinates."""
    a = nondominated(a)
    a = a[np.all(a < reference, axis=1)]
    if not len(a):
        return 0.
    xs = np.unique(np.r_[a[:, 0], reference[0]])
    volume = 0.
    for left, right in zip(xs[:-1], xs[1:]):
        yz = a[a[:, 0] <= left, 1:]
        ys = np.unique(np.r_[yz[:, 0], reference[1]])
        area = sum((hi-lo) * (reference[2]-np.min(yz[yz[:, 0] <= lo, 1]))
                   for lo, hi in zip(ys[:-1], ys[1:]))
        volume += (right-left)*area
    return float(volume)


def load_runs(root):
    runs, manifest = {}, []
    for method in METHODS:
        for path in sorted(root.glob(f'{method}_seed_*/evaluations.csv')):
            group = path.parent.name.rsplit('_seed_', 1)[1]
            df = pd.read_csv(path).sort_values('evaluation_id', kind='stable').reset_index(drop=True)
            assert len(df) == 160 and df.evaluation_id.is_unique
            assert df.evaluation_id.tolist() == [f'eval_{i:06}' for i in range(1, 161)]
            marker = json.loads((path.parent / 'run_complete.json').read_text())
            assert hashlib.sha256(path.read_bytes()).hexdigest() == marker['artifacts']['evaluations.csv']
            vals = df[list(OBJECTIVES)].to_numpy(float)/SCALES
            feasible = df.simulation_valid.to_numpy(bool) & df.physically_feasible.to_numpy(bool) & np.isfinite(vals).all(axis=1)
            runs[(method, group)] = (df, vals, feasible)
            manifest.append({'run':path.parent.name, 'path':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'valid':int(df.simulation_valid.sum()),'feasible':int(feasible.sum())})
    groups = sorted({group for _, group in runs})
    assert len(groups) == 10 and len(runs) == 30
    for group in groups:
        initial = runs[(METHODS[0], group)][0].loc[:15, list(VARIABLES)].to_numpy()
        initial_y = runs[(METHODS[0], group)][1][:16]
        for method in METHODS[1:]:
            np.testing.assert_array_equal(initial, runs[(method, group)][0].loc[:15, list(VARIABLES)].to_numpy())
            np.testing.assert_array_equal(initial_y, runs[(method, group)][1][:16])
            np.testing.assert_array_equal(runs[(METHODS[0], group)][2][:16],runs[(method, group)][2][:16])
    return runs, groups, manifest


def analyze(root, out, figures):
    out.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    runs, groups, manifest = load_runs(root)
    reference = nondominated(np.vstack([v[f] for _,v,f in runs.values()]))
    pd.DataFrame(reference,columns=['emit_x_um_rad','emit_y_um_rad','sigma_energy_MeV']).to_csv(out/'c03_empirical_reference.csv', index=False)
    nadir, span = reference.max(0), np.ptp(reference, axis=0)
    hvrefs = {f'hv_{int(offset*100)}':nadir + offset*span for offset in (.1,.25,.5)}
    metadata={'analysis':'post hoc/exploratory', 'objective_names':OBJECTIVES,'scales_SI':SCALES.tolist(),'reference_size':len(reference),'reference_nadir':nadir.tolist(),'reference_span':span.tolist(),'HV_references':{k:v.tolist() for k,v in hvrefs.items()},'initial_evaluations':16,'batch_size':8,'total_budget':160,'input_manifest':manifest,'protocol':'c03_protocol.md'}
    (out/'c03_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    rows, cover_rows, attain_rows = [], [], []
    terminal = {}
    for (method, group), (df, vals, feasible) in runs.items():
        heldout = nondominated(np.vstack([v[f] for (m,g),(_,v,f) in runs.items() if g != group]))
        for n in range(16,161,8):
            a=nondominated(vals[:n][feasible[:n]])
            row={'method':method,'group':group,'evaluations':n,'feasible_count':int(feasible[:n].sum()),'feasible_fraction':float(feasible[:n].mean()),'front_size_unique':len(a),'epsilon':additive_epsilon(a,reference),'igd_plus':igd_plus(a,reference)}
            for key,ref in hvrefs.items():
                row[key]=hypervolume(a,ref)
                row[f'{key}_excluded']=int(np.sum(~np.all(a<ref,axis=1)))
            for delta in (.05,.10,.25,.50):
                attained=np.any(np.all(a[:,None] <= (reference+delta)[None],axis=2),axis=0) if len(a) else np.zeros(len(reference),bool)
                row[f'attainment_{delta:.2f}']=float(attained.mean())
                if n == 160:
                    attain_rows.extend({'method':method,'group':group,'delta':delta,'target_id':j,'attained':int(value)} for j,value in enumerate(attained))
            if n == 160:
                row['igd_plus_leave_group_out']=igd_plus(a,heldout)
                terminal[(method,group)] = a
            rows.append(row)
    for group in groups:
        for ma in METHODS:
            for mb in METHODS:
                if ma != mb:
                    cover_rows.append({'group':group,'dominating_method':ma,'target_method':mb,'directional_coverage':coverage(terminal[(ma,group)],terminal[(mb,group)])})
    traces=pd.DataFrame(rows)
    traces.to_csv(out/'c03_run_histories.csv',index=False)
    pd.DataFrame(cover_rows).to_csv(out/'c03_directional_coverage.csv',index=False)
    pd.DataFrame(attain_rows).to_csv(out/'c03_attainment.csv',index=False)
    end=traces[traces.evaluations==160]
    summaries=[]
    for method in METHODS:
        for metric in ['feasible_fraction','front_size_unique','epsilon','igd_plus','igd_plus_leave_group_out',*hvrefs,'attainment_0.10']:
            x=end.loc[end.method==method,metric].to_numpy(float)
            summaries.append({'method':method,'metric':metric,'median':np.median(x),'q25':np.quantile(x,.25),'q75':np.quantile(x,.75),'min':np.min(x),'max':np.max(x)})
    pd.DataFrame(summaries).to_csv(out/'c03_terminal_summary.csv',index=False)
    # No connected objective-space fronts: these lines show metric histories only.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=['#0072B2','#D55E00','#009E73']
    fig,axes=plt.subplots(1,3,figsize=(12,3.4),layout='constrained')
    for ax,metric,label in zip(axes,['epsilon','igd_plus','hv_25'],['Additive epsilon (lower is better)','IGD+ (lower is better)','Exploratory HV, +25% span']):
        for method,name,color in zip(METHODS,LABELS,colors):
            y=traces[traces.method==method].pivot(index='evaluations',columns='group',values=metric)
            # Keep empty fronts as infinite when aggregating; gaps represent nonfinite summaries.
            median=np.median(y.to_numpy(),axis=1)
            lower=np.quantile(y.to_numpy(),.25,axis=1,method='inverted_cdf')
            upper=np.quantile(y.to_numpy(),.75,axis=1,method='inverted_cdf')
            median=np.where(np.isfinite(median),median,np.nan)
            lower=np.where(np.isfinite(lower),lower,np.nan)
            upper=np.where(np.isfinite(upper),upper,np.nan)
            ax.plot(y.index,median,label=name,color=color)
            ax.fill_between(y.index,lower,upper,color=color,alpha=.15)
        ax.set(xlabel='Evaluations',ylabel=label)
        ax.grid(alpha=.25)
    axes[0].legend(fontsize=7)
    fig.savefig(figures/'revision_front_quality.pdf')
    plt.close(fig)
    # Target-based empirical attainment matrix; no interpolated front curves.
    fig,axes=plt.subplots(1,3,figsize=(12,3.2),layout='constrained')
    att=pd.DataFrame(attain_rows)
    for ax,method,name in zip(axes,METHODS,LABELS):
        heat=att[att.method==method].groupby(['delta','target_id']).attained.mean().unstack()
        im=ax.imshow(heat,vmin=0,vmax=1,aspect='auto',origin='lower',cmap='viridis')
        ax.set(title=name,xlabel='Empirical-front target index',yticks=range(4),yticklabels=[.05,.10,.25,.50],ylabel='Target relaxation (scaled units)')
    fig.colorbar(im,ax=axes,label='Empirical attainment probability')
    fig.savefig(figures/'revision_attainment.pdf')
    plt.close(fig)
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',type=Path,default=Path('results/paper_production/04_primary/benchmark/per_seed'))
    parser.add_argument('--output',type=Path,default=Path('docs/paper/revisions/evidence'))
    parser.add_argument('--figures',type=Path,default=Path('docs/paper/figures'))
    args=parser.parse_args()
    analyze(args.runs,args.output,args.figures)
