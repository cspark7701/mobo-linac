from copy import deepcopy
from dataclasses import replace
import json

import pytest
import torch
from botorch.models import ModelListGP
from botorch.sampling.normal import SobolQMCNormalSampler
from mobo_linac.config import load_config
from mobo_linac.constraints import get_botorch_constraint_functions, constraint_residual_metadata, ConstraintEvaluator
from mobo_linac.campaigns.strategies import proposal_random_stream
from mobo_linac.acquisition.mobo import SliceObjective, build_acquisition_function
from mobo_linac.models.gp import build_gp_models


def normalized():
    config=load_config()
    config.execution=replace(config.execution,constraint_residual_mode='normalized')
    return config


@pytest.mark.parametrize('device',['cpu','cuda:0'])
def test_scaled_residuals_keep_boundaries_signs_and_units(device):
    if device.startswith('cuda') and not torch.cuda.is_available():
        pytest.skip('CUDA unavailable')
    config=normalized()
    values=torch.tensor([[0.,0.,0.]+[.0005]*5+[200e6,1.]],dtype=torch.double,device=device)
    funcs=get_botorch_constraint_functions(config)
    assert torch.stack([f(values) for f in funcs]).flatten().tolist()==pytest.approx([-.5]*5+[-1.,-1.,-1.])
    changed=deepcopy(config)
    for name in ['max_sigma_x_m','max_sigma_y_m','max_sigma_xp_rad','max_sigma_yp_rad','max_sigma_z_m']:
        setattr(changed.constraints,name,getattr(changed.constraints,name)*1000)
    changed.constraints.min_mean_kinetic_energy_eV/=1e6
    changed.constraints.max_mean_kinetic_energy_eV/=1e6
    converted=values.clone();converted[:,3:8]*=1000;converted[:,8]/=1e6
    for a,b in zip(funcs,get_botorch_constraint_functions(changed)):
        torch.testing.assert_close(a(values),b(converted))
    for i in range(5):
        boundary=values.clone();boundary[:,3+i]=.001
        assert funcs[i](boundary).item()==0
        boundary[:,3+i]=.0011
        assert funcs[i](boundary).item()>0
    for i,energy in [(5,195e6),(6,205e6)]:
        boundary=values.clone();boundary[:,8]=energy
        assert funcs[i](boundary).item()==0
    boundary=values.clone();boundary[:,9]=.9
    assert funcs[7](boundary).item()==0
    diagnostics=dict(zip(['sigma_x_m','sigma_y_m','sigma_xp_rad','sigma_yp_rad','sigma_z_m',
                         'mean_kinetic_energy_eV','transmission_fraction'],values[0,3:].tolist()))
    assert ConstraintEvaluator(config.constraints).check_feasibility(diagnostics)
    raw=load_config()
    assert ConstraintEvaluator(raw.constraints).check_feasibility(diagnostics)
    meta=constraint_residual_metadata(config)
    assert meta['physical_smoothing_scales']==pytest.approx([1e-6]*5+[5000.,5000.,.0001])


def test_degenerate_normalization_rejected_and_raw_compatible():
    config=normalized();config.constraints.max_mean_kinetic_energy_eV=config.constraints.min_mean_kinetic_energy_eV
    with pytest.raises(ValueError,match='positive physical scales'):
        get_botorch_constraint_functions(config)
    config.execution.constraint_residual_mode='raw'
    assert constraint_residual_metadata(config)['scales']==[1.]*8


@pytest.mark.parametrize('device',['cpu','cuda:0'])
def test_optional_streams_are_repeatable_and_do_not_consume_outer_rng(device):
    d=torch.device(device)
    if d.type=='cuda' and not torch.cuda.is_available():
        pytest.skip('CUDA unavailable')
    torch.manual_seed(77)
    before=torch.get_rng_state().clone()
    with proposal_random_stream(101,d):
        one=torch.rand(4,device=d)
    with proposal_random_stream(101,d):
        two=torch.rand(4,device=d)
    torch.testing.assert_close(one,two)
    assert torch.equal(before,torch.get_rng_state())
    with proposal_random_stream(None,d):
        torch.rand(4)
    assert not torch.equal(before,torch.get_rng_state())


@pytest.mark.parametrize('device',['cpu','cuda:0'])
def test_normalized_q8_acquisition_with_pruning_has_finite_gradient(device):
    if device.startswith('cuda') and not torch.cuda.is_available():
        pytest.skip('CUDA unavailable')
    config=normalized();d=torch.device(device)
    torch.manual_seed(11)
    x=torch.rand(8,6,dtype=torch.double,device=d)
    y=-torch.rand(8,3,dtype=torch.double,device=d)
    diag=torch.cat([(.0002+.0005*x[:,:5]),(197e6+4e6*x[:,5:6]),torch.ones(8,1,device=d,dtype=torch.double)],-1)
    bounds=torch.stack([torch.zeros(6,device=d,dtype=torch.double),torch.ones(6,device=d,dtype=torch.double)])
    gp=build_gp_models(x,torch.cat([y,diag],-1),bounds=bounds,device=d)
    assert isinstance(gp,ModelListGP)
    acq=build_acquisition_function(gp,x,y,torch.tensor([-2.,-2.,-2.],device=d),
        constraints=get_botorch_constraint_functions(config),objective=SliceObjective(3),
        sampler=SobolQMCNormalSampler(torch.Size([16]),seed=42),constraint_temperature=.001)
    proposal=torch.rand(1,8,6,dtype=torch.double,device=d,requires_grad=True)
    value=acq(proposal);value.sum().backward()
    assert torch.isfinite(value).all() and torch.isfinite(proposal.grad).all()
    assert all(t.device==d for t in acq.buffers())


def test_normalized_campaign_checkpoint_restores_convention(tmp_path,monkeypatch):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution.mock import MockEvaluator
    from mobo_linac.acquisition.mobo import ProposalResult
    import mobo_linac.campaigns.strategies as strategies
    config=normalized()
    config.execution=replace(config.execution,acquisition_stream_group=42,acqf_mc_samples=16)
    def propose(**kwargs):
        assert kwargs['batch_size']==8
        assert kwargs['sobol_engine'].seed==242001
        assert kwargs['sobol_engine'].num_generated==0
        return ProposalResult(kwargs['bounds'].mean(0).repeat(8,1),None,{'tier':'test_fallback'})
    monkeypatch.setattr(strategies,'generate_next_candidates',propose)
    out=tmp_path/'run'
    runner=MoboCampaignRunner(config=config,output_dir=out,num_initial_samples=4,num_batches=1,batch_size=8,
        constrained=True,seed=42,num_workers=2,device='cpu',evaluator=MockEvaluator(config=config),
        export_plots=False,export_env_info=False)
    runner.run()
    saved=json.loads((out/'config.json').read_text())
    assert saved['execution']['constraint_residual_mode']=='normalized'
    history=json.loads((out/'proposal_history.json').read_text())
    assert 'normalized' in json.dumps(history) and '142001' in json.dumps(history)
    resumed=MoboCampaignRunner(output_dir=out,resume=True,device='cpu',evaluator=MockEvaluator(config=config),
        export_plots=False,export_env_info=False)
    resumed.run()
    changed=deepcopy(config);changed.execution.constraint_residual_mode='raw'
    with pytest.raises(ValueError,match='constraint_residual_mode'):
        MoboCampaignRunner(config=changed,output_dir=out,resume=True,device='cpu',
            evaluator=MockEvaluator(config=changed),export_plots=False).run()


def test_low_data_proposals_do_not_consume_initial_sobol_stream(tmp_path):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution.mock import MockEvaluator
    from mobo_linac.io.checkpoint import load_run_checkpoint
    config=normalized()
    config.execution=replace(config.execution,acquisition_stream_group=42,acqf_mc_samples=16)
    out=tmp_path/'low_data'
    MoboCampaignRunner(config=config,output_dir=out,num_initial_samples=1,num_batches=1,batch_size=8,
        constrained=True,seed=42,num_workers=2,device='cpu',evaluator=MockEvaluator(config=config),
        export_plots=False,export_env_info=False).run()
    history=json.loads((out/'proposal_history.json').read_text())
    assert '242001' in json.dumps(history) and 'low_data_sobol' in json.dumps(history)
    state=load_run_checkpoint(out/'checkpoints/checkpoint.pt')
    assert state.progress.sobol_state['num_generated']==1
