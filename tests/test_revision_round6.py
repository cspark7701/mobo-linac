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
