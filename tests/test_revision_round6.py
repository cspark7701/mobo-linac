import copy
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import prepare_revision_round6 as prepare
import run_revision_round6_resolution as resolution


def population():
    rows=[]
    for i in range(1,9):
        rows.append(dict(arm='constrained_qlognehvi',seed=42,run='constrained_qlognehvi_seed_42',
            evaluation_id=f'eval_{i:06d}',index_in_run=i,physically_feasible=True,
            sigma_x_m=.0005,sigma_y_m=.0005,sigma_xp_rad=.0005,sigma_yp_rad=.0005,
            sigma_z_m=.0005,mean_kinetic_energy_eV=200e6,transmission_fraction=1.,
            **dict(zip(prepare.CONTROLS,[.2,1.,-2.,36.,-40.,310.]))))
    return pd.DataFrame(rows)


def test_sample_is_reproducible_with_known_inclusion_probability():
    first,strata=prepare.select(population())
    second,_=prepare.select(population())
    pd.testing.assert_frame_equal(first,second)
    assert len(first)==2 and (first.inclusion_probability==.25).all()
    assert strata.population.sum()==8 and (strata.population==0).any()
    assert first.evaluation_id.nunique()==2


def test_boundary_and_stage_cover_both_sides():
    f=population()
    f.loc[0,'sigma_x_m']=.00105
    f.loc[1,'sigma_x_m']=.00095
    f.loc[0,'index_in_run']=81
    s=prepare.stratify(f)
    assert s.loc[0,'boundary']==s.loc[1,'boundary']=='near'
    assert s.loc[0,'min_signed_margin']<0<s.loc[1,'min_signed_margin']
    assert s.loc[0,'stage']=='late'


def test_durable_journal_rejects_tampering_and_duplicate_identity(tmp_path):
    p=tmp_path/'journal.jsonl';value={'task_id':'a','simulation_valid':False}
    resolution.append_record(p,value)
    assert resolution.read_records(p)=={'a':value}
    saved=p.read_text()
    p.write_text(saved.replace('false','true'))
    with pytest.raises(ValueError,match='checksum'):
        resolution.read_records(p)
    p.write_text(saved+saved)
    with pytest.raises(ValueError,match='Duplicate'):
        resolution.read_records(p)


def test_task_levels_keep_fixed_source_and_controls():
    spec=json.loads(resolution.SPEC.read_text())
    f=pd.read_csv(resolution.MANIFEST).head(1)
    tasks=resolution.make_tasks(f,spec,['production','fixed_medium','combined_fine'])
    assert tasks[0].namelist_overrides is None
    assert 'newrun:distribution' not in tasks[1].namelist_overrides
    assert tasks[2].namelist_overrides['newrun:distribution']=='qr40k.ini'
    assert all(t.parameters==tasks[0].parameters for t in tasks)
    assert len({t.task_id for t in tasks})==3


def test_mock_run_resume_and_identity_protection(tmp_path):
    spec=copy.deepcopy(json.loads(resolution.SPEC.read_text()))
    f=pd.read_csv(resolution.MANIFEST).head(2)
    spec['minimum_free_disk_GiB']=0
    out=tmp_path/'mock'
    resolution.execute(out,spec,f,mock=True)
    before=(out/'results.jsonl').read_bytes()
    assert len(resolution.read_records(out/'results.jsonl'))==10
    resolution.execute(out,spec,f,mock=True,resume=True)
    assert before==(out/'results.jsonl').read_bytes()
    with pytest.raises(ValueError,match='Output exists'):
        resolution.execute(out,spec,f,mock=True)
    with pytest.raises(ValueError,match='identity mismatch'):
        resolution.execute(out,spec,f,mock=False,resume=True)
    (out/'pending.json').write_text(json.dumps(['unrecorded_attempt']))
    with pytest.raises(ValueError,match='Interrupted attempts'):
        resolution.execute(out,spec,f,mock=True,resume=True)


def test_frozen_inputs_and_controls(tmp_path):
    spec=json.loads(resolution.SPEC.read_text())
    assert len(resolution.validate_inputs(spec))==387
    frame=pd.read_csv(resolution.MANIFEST)
    frame.loc[0,prepare.CONTROLS[0]]+=.1
    changed=tmp_path/'changed.csv';frame.to_csv(changed,index=False)
    with pytest.raises(ValueError,match='manifest checksum'):
        resolution.validate_inputs(spec,changed)
    spec['sample_manifest_sha256']=prepare.sha(changed)
    with pytest.raises(ValueError,match='control mismatch'):
        resolution.validate_inputs(spec,changed)


def test_nominal_gate_rejects_invalid_or_changed_observation():
    spec=json.loads(resolution.SPEC.read_text())
    frame=pd.read_csv(resolution.MANIFEST).head(1);row=frame.iloc[0]
    key=row.setting_id+'__production'
    with pytest.raises(ValueError,match='Invalid nominal'):
        resolution.check_nominal(frame,{key:{'simulation_valid':False}},spec)
    with pytest.raises(ValueError,match='Nominal reproduction mismatch'):
        resolution.check_nominal(frame,{key:{'simulation_valid':True,'objectives':{},'diagnostics':{}}},spec)


def test_scaling_plan_has_matched_budget_and_alternating_order():
    import run_revision_round6_scaling as scaling
    spec=json.loads(resolution.SPEC.read_text())
    allocation=list(scaling.order(spec))
    assert len(allocation)==20
    assert allocation[:4]==[('raw',42),('normalized',42),('normalized',43),('raw',43)]
    raw=scaling.campaign_config(spec,'raw',42)
    normalized=scaling.campaign_config(spec,'normalized',42)
    assert raw.constraints==normalized.constraints
    assert raw.execution.max_workers==normalized.execution.max_workers==2
    assert raw.execution.acquisition_stream_group==normalized.execution.acquisition_stream_group==42
    assert raw.execution.acqf_mc_samples==normalized.execution.acqf_mc_samples==128
    assert raw.execution.acqf_maxiter==200
    with pytest.raises(ValueError,match='frozen allocation'):
        scaling.campaign_config(spec,'normalized',123)


def test_weighted_numerical_estimator_accounts_for_strata_and_failures():
    import analyze_revision_round6 as analysis
    f=pd.DataFrame({'stratum':['a','a','b'],'population':[8,8,2],'selected':[2,2,1],
                    'feasible':[True,False,True],'simulation_valid':[True,False,True]})
    with pytest.raises(ValueError,match='singleton'):
        analysis.weighted_fractions(f)
    f.loc[2,'population']=1
    result=analysis.weighted_fractions(f)
    assert result['fraction']==pytest.approx(5/9)
    assert result['unknown_fraction']==pytest.approx(4/9)
    assert result['physical_upper_if_invalid_pass']==pytest.approx(1.)
    assert result['design_variance']==pytest.approx((8/9)**2*.75*.5/2)
    with pytest.raises(ValueError,match='Incomplete'):
        analysis.weighted_fractions(f.iloc[[0,2]])


def test_paired_summary_preserves_direction_and_group_unit():
    import analyze_revision_round6 as analysis
    wide=pd.DataFrame({'normalized':[.2,.3,.1],'raw':[.4,.4,.3]})
    result=analysis.paired_summary(wide,'normalized','raw',{'analysis_seed':1,'bootstrap_resamples':1000})
    assert result['mean_difference']==pytest.approx(-1/6)
    assert result['positive_groups']==0 and result['ci_upper_conditional']<0


def test_uncertainty_plot_keeps_endpoint_units_separate(tmp_path):
    import analyze_revision_round6 as analysis
    table=pd.DataFrame([
        {'endpoint':'feasible_fraction','mean_difference':-.1,'ci_lower_conditional':-.2,'ci_upper_conditional':0.},
        {'endpoint':'elapsed_wall_time_s','mean_difference':100,'ci_lower_conditional':50,'ci_upper_conditional':200}])
    path=tmp_path/'uncertainty.pdf';analysis.uncertainty_plot(table,path)
    assert path.read_bytes().startswith(b'%PDF')
    table=table.iloc[:1].drop(columns='endpoint').assign(level='fixed_fine',second='scalarized_bo',design_se_conservative=.02)
    analysis.uncertainty_plot(table,path)
    assert path.stat().st_size>1000


def test_numerical_analysis_uses_complete_identities_and_design_weights(tmp_path,monkeypatch):
    import analyze_revision_round6 as analysis
    spec=copy.deepcopy(json.loads(resolution.SPEC.read_text()))
    levels=list(spec['levels']);rows=[]
    for arm in ['constrained_qlognehvi','unconstrained_qlognehvi','scalarized_bo']:
        for seed in [42,43]:
            for i in [1,2]:
                rows.append({'setting_id':f'{arm}_{seed}_{i}','run':f'{arm}_seed_{seed}',
                    'evaluation_id':f'eval_{i:06d}','arm':arm,'seed':seed,'stratum':f'{arm}_{seed}',
                    'population':160,'selected':2,'inclusion_probability':2/160,'physically_feasible':True})
    manifest=pd.DataFrame(rows);manifest_path=tmp_path/'manifest.csv';manifest.to_csv(manifest_path,index=False)
    monkeypatch.setattr(analysis,'MANIFEST',manifest_path)
    records=tmp_path/'results.jsonl'
    for row in rows:
        for level in levels:
            values=dict(zip(analysis.QUANTITIES,[3e-6,4e-6,400000,.0005,.0005,.0005,.0005,.0005,200e6,1.]))
            if level=='fixed_fine':
                values['norm_emit_x_m_rad']*=.9
            resolution.append_record(records,{'task_id':row['setting_id']+'__'+level,'role':row['setting_id'],
                'level':level,'simulation_valid':True,'physically_feasible':row['arm']=='constrained_qlognehvi',
                'runtime_s':1.,'objectives':values,'diagnostics':{}})
    spec['tracking_attempts']=len(rows)*len(levels)
    (tmp_path/'complete.json').write_text(json.dumps({'tasks':spec['tracking_attempts'],'mock':False,
        'spec_sha256':prepare.sha(analysis.SPEC),'results_sha256':prepare.sha(records)}))
    tables=analysis.numerical(tmp_path,spec)
    assert len(tables['resolution_fractions'])==3*2*5
    assert (tables['resolution_paired'].mean_difference==1).all()
    assert tables['resolution_classification'].margin_sigma_x_m.eq(.0005).all()
    tolerances=tables['resolution_tolerances']
    assert not tolerances[(tolerances.quantity=='norm_emit_x_m_rad') &
                          (tolerances.comparison=='fixed_fine - fixed_medium')].within_tolerance.any()
    marker=json.loads((tmp_path/'complete.json').read_text());marker['mock']=True
    (tmp_path/'complete.json').write_text(json.dumps(marker))
    with pytest.raises(ValueError,match='Invalid numerical'):
        analysis.numerical(tmp_path,spec)


def test_analysis_resume_requires_identical_inputs_and_outputs(tmp_path):
    import analyze_revision_round6 as analysis
    source=tmp_path/'source';source.mkdir()
    (source/'complete.json').write_text('{}')
    out=tmp_path/'analysis';out.mkdir()
    data=out/'r6_scaling_runs.csv';data.write_text('arm,value\nraw,0.1\n')
    receipt={'spec_sha256':prepare.sha(analysis.SPEC),
        'completion_sha256':prepare.sha(source/'complete.json'),
        'outputs_sha256':{data.name:prepare.sha(data)}}
    (out/'r6_scaling_analysis.json').write_text(json.dumps(receipt))
    args=['scaling','--input-dir',str(source),'--output-dir',str(out),'--resume']
    analysis.main(args)
    data.write_text('changed')
    with pytest.raises(ValueError,match='output checksum'):
        analysis.main(args)
    (source/'complete.json').write_text('{"changed":true}')
    with pytest.raises(ValueError,match='input identity'):
        analysis.main(args)


def test_stage_commit_preserves_unrelated_staged_files(tmp_path,monkeypatch):
    import subprocess
    import record_revision_round6_stage as stage
    subprocess.run(['git','init','-b','main',str(tmp_path)],check=True,capture_output=True)
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=tmp_path,text=True).strip()
    git('config','user.email','test@example.invalid');git('config','user.name','Test')
    folder=tmp_path/'docs/exec-plans/completed';folder.mkdir(parents=True)
    (folder/'TASK_00001_fixture.md').write_text('fixture\n')
    git('add','.');git('commit','-m','Initial fixture')
    (tmp_path/'unrelated.txt').write_text('unrelated\n');git('add','unrelated.txt')
    receipt=tmp_path/'receipt.json';receipt.write_text('{}')
    monkeypatch.setattr(stage,'ROOT',tmp_path)
    monkeypatch.setattr(stage,'stage_evidence',lambda name:(receipt,'Verified synthetic fixture stage.'))
    stage.main(['validation'])
    assert git('diff','--cached','--name-only')=='unrelated.txt'
    assert git('show','--pretty=','--name-only','HEAD')=='docs/exec-plans/completed/TASK_00002_r6_validation_completed.md'
    before=git('rev-parse','HEAD');stage.main(['validation'])
    assert git('rev-parse','HEAD')==before
    receipt.write_text('{"revalidated":true}')
    stage.main(['validation'])
    assert git('rev-parse','HEAD')!=before
    assert (folder/'TASK_00002_r6_validation_completed.md').exists()
    assert (folder/'TASK_00003_r6_validation_completed.md').exists()
    assert git('diff','--cached','--name-only')=='unrelated.txt'


def test_stage_validation_rejects_stale_receipt(tmp_path,monkeypatch):
    import record_revision_round6_stage as stage
    base=tmp_path/'results/revision_round6';base.mkdir(parents=True)
    (base/'validation_complete.json').write_text(json.dumps({'status':'failed','coverage_required':100}))
    monkeypatch.setattr(stage,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='invalid or stale'):
        stage.stage_evidence('validation')


def test_unavailable_failed_measurements_are_null_not_fabricated(tmp_path):
    import numpy as np
    path=tmp_path/'failed.jsonl'
    resolution.append_record(path,{'task_id':'failed','simulation_valid':False,
        'diagnostics':{'sigma_x_m':float('nan')},'values':[np.float64(float('inf'))]})
    result=resolution.read_records(path)['failed']
    assert result['diagnostics']['sigma_x_m'] is None
    assert result['values']==[None] and result['simulation_valid'] is False
