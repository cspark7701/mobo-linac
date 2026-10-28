"""C14: regenerate manuscript survey tables from feasible observations only."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];PAPER=ROOT/'docs/paper';BASE=ROOT/'results/paper_production/05_operating_points/campaign'
OBJECTIVES=['norm_emit_x_m_rad','norm_emit_y_m_rad','sigma_energy_eV']
CASES={'balanced':'Equal weight','high_brightness':'Emittance emphasis','low_energy_spread':'Spread emphasis','x_dominant':'Horizontal emphasis','y_dominant':'Vertical emphasis'}

def feasible_summary(df):
    feasible=df.loc[df.simulation_valid & df.physically_feasible]
    values=feasible[OBJECTIVES].to_numpy()
    # A point is dominated if any other point is no worse in every objective and strictly better in one.
    nondominated=sum(not np.any(np.all(values<=v,axis=1)&np.any(values<v,axis=1)) for v in values)
    return {'total':len(df),'valid':int(df.simulation_valid.sum()),'feasible':len(feasible),'pareto':nondominated,
            'fraction':len(feasible)/len(df),**{c:float(feasible[c].min()) for c in OBJECTIVES}}

def main():
    summaries=[];inputs=[];frames={}
    def read(p):
        marker=json.loads((p.parent/'run_complete.json').read_text());digest=hashlib.sha256(p.read_bytes()).hexdigest()
        assert digest==marker['artifacts']['evaluations.csv'];inputs.append({'path':str(p.relative_to(ROOT)),'sha256':digest});return pd.read_csv(p)
    for case,label in CASES.items():
        frame=read(BASE/'phase1_scalarized'/case/'evaluations.csv');frames[case]=frame
        # The suite manifest records executed weights rather than relying on friendly labels.
        cases=pd.read_csv(BASE/'phase1_scalarized/cases_summary.csv');r=cases[cases.case_id==case].iloc[0]
        weights=json.loads(r.weights)
        summaries.append({'case':case,'label':label,'weights':weights,**feasible_summary(frame)})
    groups=[pd.concat(list(frames.values()),ignore_index=True),read(BASE/'phase2_unconstrained/evaluations.csv'),read(BASE/'phase3_constrained/evaluations.csv')]
    g=[feasible_summary(df) for df in groups]
    caption='Operating-point survey: all extrema and Pareto sizes use feasible observations; rates use all evaluations. The scalarized suite pools five independent weightings and has five times the total budget of either MOBO campaign. Coordinate minima need not belong to one setting.'
    tex='\\begin{table}[htbp]\n\\centering\\small\n\\caption{'+caption+'}\n\\label{tab:campaign_summary}\n\\begin{tabular}{lrrr}\\toprule\nMetric & Scalarized suite & Unconstrained MOBO & Constrained MOBO \\\\\n\\midrule\n'
    for label,key in [('Evaluations','total'),('Valid simulations','valid'),('Feasible observations','feasible'),('Feasible Pareto size','pareto')]:
        tex+=label+' & '+' & '.join(f'{r[key]:,}' for r in g)+r' \\'+'\n'
    tex+=r'Feasible fraction (\%) & '+' & '.join(f'{100*r["fraction"]:.1f}' for r in g)+r' \\'+'\n'
    for label,c,scale in [(r'Minimum $\varepsilon_{n,x}$ (\si{\micro\metre\radian})',OBJECTIVES[0],1e6),(r'Minimum $\varepsilon_{n,y}$ (\si{\micro\metre\radian})',OBJECTIVES[1],1e6),(r'Minimum $\sigma_E$ (\si{\mega\electronvolt})',OBJECTIVES[2],1e-6)]:
        tex+=label+' & '+' & '.join(f'{r[c]*scale:.4f}' for r in g)+r' \\'+'\n'
    tex+=r'\bottomrule\end{tabular}\end{table}'+'\n';(PAPER/'results_table.tex').write_text(tex)
    tex=r'''\begin{table}[htbp]\centering\small
\caption{Independent scalarized survey cases, each using 176 evaluations. All objective
minima use feasible observations. Emittances are in \si{\micro\metre\radian} and
energy spread in \si{\mega\electronvolt}. Weights act on scale-normalized objectives.}
\label{tab:phase1_cases}
\begin{tabular}{lcrrrr}\toprule
Weighting & $(w_x,w_y,w_E)$ & Feasible & Min. $\varepsilon_{n,x}$ & Min. $\varepsilon_{n,y}$ & Min. $\sigma_E$ \\\midrule
'''
    for r in summaries:
        w=r['weights'];wt=r'$(\frac13,\frac13,\frac13)$' if r['case']=='balanced' else '$('+','.join(f'{x:.2f}' for x in w)+')$'
        tex+=r['label']+' & '+wt+f" & {r['feasible']} & {r[OBJECTIVES[0]]*1e6:.4f} & {r[OBJECTIVES[1]]*1e6:.4f} & {r[OBJECTIVES[2]]*1e-6:.4f}"+r' \\'+'\n'
    tex+=r'\bottomrule\end{tabular}\end{table}'+'\n';(PAPER/'phase1_cases_table.tex').write_text(tex)
    out=PAPER/'revisions/evidence';pd.DataFrame(summaries).to_csv(out/'c14_feasible_case_summary.csv',index=False)
    (out/'c14_metadata.json').write_text(json.dumps({'inputs':inputs,'population':'valid and jointly feasible; original flags unchanged'},indent=2)+'\n')
    print(pd.DataFrame(summaries).to_string(index=False))

if __name__=='__main__':main()
