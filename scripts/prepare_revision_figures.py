"""C15: independent survey histories and readable constraint acceptance views."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle,Patch
from mobo_linac.config import load_config
from mobo_linac.plotting.common import PlotSchema
from compare_constraint_spaces import Campaign,ALGORITHMS,LABELS,STYLES,PHYSICAL,display_domain,plot_bounds,measured_constraints
from prepare_revision_tables import CASES
ROOT=Path(__file__).resolve().parents[1];PAPER=ROOT/'docs/paper';BASE=ROOT/'results/paper_production'
# Round2 C2-07: the re-evaluated MOGA-derived nominal setting, when its record is present.
_MOGA=ROOT/'results/revision_round2/references/moga_nominal/moga_reference.json'
MOGA_REFERENCE=json.loads(_MOGA.read_text())['result']['diagnostics'] if _MOGA.exists() else None


def cumulative_feasible(frame):
    return np.cumsum((frame.simulation_valid & frame.physically_feasible).to_numpy())/np.arange(1,len(frame)+1)

def save(fig,name,png=False):
    fig.savefig(PAPER/'figures'/f'{name}.pdf',bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None})
    if png:fig.savefig(PAPER/'figures'/f'{name}.png',dpi=170,bbox_inches='tight')
    plt.close(fig)

def constraint_view(campaigns,schema,reference=None):
    """``reference``: optional diagnostics of one measured setting, drawn as a black star."""
    specs={s.column:s for s in schema.constraints};bounds=plot_bounds(campaigns,schema)
    fig,axes=plt.subplots(3,1,figsize=(7.2,8.6))
    pairs=[('sigma_x_m','sigma_y_m'),('sigma_xp_rad','sigma_yp_rad'),('mean_kinetic_energy_eV','sigma_z_m')]
    def draw(ax,x,y,local=False):
        ax.set_facecolor('#f7eded')
        xb=(0,1.05) if local else bounds[x.column];yb=(0,1.05) if local else bounds[y.column]
        ax.set(xlim=xb,ylim=yb)
        l,r=display_domain(x,xb);b,t=display_domain(y,yb)
        ax.add_patch(Rectangle((l,b),r-l,t-b,facecolor='#d8efdc',edgecolor='#438b55',lw=.8,zorder=0))
        for campaign in campaigns:
            color,marker=STYLES[ALGORITHMS.index(campaign.algorithm)]
            f=campaign.frame;feasible=f.physically_feasible.to_numpy(bool)
            for mask,filled in [(~feasible,False),(feasible,True)]:
                ax.scatter(f.loc[mask,x.column]/x.scale,f.loc[mask,y.column]/y.scale,
                    s=11 if local else 13,marker=marker,facecolors=color if filled else 'none',edgecolors=color,
                    linewidths=.35,alpha=.8 if filled else .16,zorder=3 if filled else 2)
        if reference is not None:
            ax.scatter(reference[x.column]/x.scale,reference[y.column]/y.scale,marker='*',s=70 if local else 110,
                       color='black',edgecolors='white',linewidths=.5,zorder=6)
        ax.grid(alpha=.35,linestyle=':',lw=.6);ax.set_axisbelow(True)
    for letter,ax,(xn,yn) in zip('abc',axes,pairs):
        x,y=specs[xn],specs[yn];draw(ax,x,y)
        ax.set_xlabel(f'{PHYSICAL[xn].label} [{PHYSICAL[xn].display_unit}]',fontsize=9)
        ax.set_ylabel(f'{PHYSICAL[yn].label} [{PHYSICAL[yn].display_unit}]',fontsize=9)
        ax.text(.015,.94,f'({letter})',transform=ax.transAxes,va='top',fontsize=10)
        ax.tick_params(labelsize=8)
        if letter in 'ab':
            inset=ax.inset_axes([.60,.43,.36,.49]);draw(inset,x,y,True)
            inset.set_xticks([0,.5,1]);inset.set_yticks([0,.5,1]);inset.tick_params(labelsize=7)
            inset.set_title('Acceptance zoom (same units)',fontsize=7)
    handles=[Line2D([],[],color=c,marker=m,ls='',label=label) for label,(c,m) in zip(LABELS,STYLES)]
    handles += [Line2D([],[],color='.2',marker='o',ls='',label='All constraints pass'),Line2D([],[],color='.2',marker='o',mfc='none',ls='',label='At least one fails'),Patch(facecolor='#d8efdc',label='Shown limits satisfied')]
    if reference is not None:
        handles.append(Line2D([],[],color='black',marker='*',ms=9,ls='',label='MOGA-derived nominal'))
    fig.legend(handles=handles,loc='upper center',ncol=3,fontsize=8,frameon=False)
    count=sum(len(c.frame) for c in campaigns)
    assert all(np.all(c.frame.transmission_fraction==1) for c in campaigns)
    fig.text(.5,.015,f'Transmission: all {count:,} observations = 100%; production limit = 90%.',ha='center',fontsize=9)
    fig.subplots_adjust(top=.90,bottom=.085,left=.12,right=.97,hspace=.42)
    return fig

def main():
    manifest=[]
    def read(p):
        digest=hashlib.sha256(p.read_bytes()).hexdigest();marker=json.loads((p.parent/'run_complete.json').read_text())
        assert digest==marker['artifacts']['evaluations.csv'];manifest.append({'path':str(p.relative_to(ROOT)),'sha256':digest})
        return pd.read_csv(p)
    primary={a:[read(p) for p in sorted((BASE/'04_primary/benchmark/per_seed').glob(f'{a}_seed_*/evaluations.csv'))] for a in ALGORITHMS}
    survey=BASE/'05_operating_points/campaign'
    scalar={case:read(survey/'phase1_scalarized'/case/'evaluations.csv') for case in CASES}
    mobo={ALGORITHMS[0]:read(survey/'phase3_constrained/evaluations.csv'),ALGORITHMS[1]:read(survey/'phase2_unconstrained/evaluations.csv')}
    schema=PlotSchema.from_config(load_config(survey/'phase3_constrained/config.json'))
    for scope,groups in [('primary',{a:pd.concat(fs,ignore_index=True) for a,fs in primary.items()}),('survey',{**mobo,ALGORITHMS[2]:pd.concat(list(scalar.values()),ignore_index=True)})]:
        campaigns=[]
        for a,frame in groups.items():
            valid,_=measured_constraints(frame,schema);campaigns.append(Campaign(a,valid))
        reference=MOGA_REFERENCE if scope=='primary' and MOGA_REFERENCE is not None else None
        save(constraint_view(campaigns,schema,reference),scope+'_constraint_spaces',png=True)
    fig,axes=plt.subplots(1,2,figsize=(8,3.8),sharex=True,sharey=True)
    for case,style in zip(CASES,['-', '--', ':', '-.', (0,(3,1,1,1,1,1))]):
        y=cumulative_feasible(scalar[case]);axes[0].plot(np.arange(1,len(y)+1),y,color=STYLES[2][0],ls=style,lw=1.4,label=CASES[case])
    for a,f in mobo.items():
        color,marker=STYLES[ALGORITHMS.index(a)];y=cumulative_feasible(f)
        axes[1].plot(np.arange(1,len(y)+1),y,color=color,marker=marker,markevery=24,ms=4,lw=1.4,label=LABELS[ALGORITHMS.index(a)])
    for ax,label in zip(axes,['(a) Scalarized weightings','(b) MOBO campaigns']):
        ax.set(xlim=(1,176),ylim=(0,1),xlabel='Evaluations within each campaign');ax.text(.04,.96,label,transform=ax.transAxes,va='top',fontsize=10)
        ax.grid(alpha=.35,ls=':');ax.legend(fontsize=7,loc='upper right',bbox_to_anchor=(1,.87))
    axes[0].set_ylabel('Cumulative feasible fraction');fig.tight_layout();save(fig,'survey_feasibility_by_case')
    fig,ax=plt.subplots(figsize=(6.8,3.6));rng=np.random.default_rng(7303);indices=rng.integers(0,10,size=(1000,10))
    for a in ALGORITHMS:
        values=np.array([cumulative_feasible(f) for f in primary[a]]);assert values.shape==(10,160)
        med=np.median(values,axis=0);boot=np.median(values[indices],axis=1);lo,hi=np.percentile(boot,[2.5,97.5],axis=0)
        x=np.arange(1,161);color,marker=STYLES[ALGORITHMS.index(a)]
        ax.fill_between(x,lo,hi,color=color,alpha=.16);ax.plot(x,med,color=color,marker=marker,markevery=24,ms=4,label=LABELS[ALGORITHMS.index(a)])
    ax.set(xlim=(1,160),ylim=(0,1),xlabel='Evaluations per campaign',ylabel='Cumulative feasible fraction');ax.grid(alpha=.35,ls=':');ax.legend(fontsize=8);fig.tight_layout();save(fig,'benchmark_feasibility_comparison')
    (PAPER/'revisions/evidence/c15_metadata.json').write_text(json.dumps({'inputs':manifest,'primary_bootstrap_resamples':1000,'bootstrap_seed':7303,'survey_curve_lengths':{k:len(v) for k,v in scalar.items()},'scope':'Independent per-campaign histories; shaded constraint zooms preserve full-range panels; transmission retained as exact annotation.'},indent=2)+'\n')

if __name__=='__main__':main()
