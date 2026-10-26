"""Checks for reliability bounds and two-sided energy-margin interpretation."""
import importlib.util
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

@pytest.fixture
def analysis(monkeypatch):
    folder=Path(__file__).parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(folder))
    spec=importlib.util.spec_from_file_location('revision_robustness',folder/'analyze_revision_robustness.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_exact_no_failure_bounds(analysis):
    low,high,one=analysis.binomial_bounds(50,50)
    assert low==pytest.approx(.025**(1/50))
    assert high==1
    assert 1-one==pytest.approx(1-.05**(1/50))
    assert .058 < 1-one < .059


def test_all_failure_and_invalid_counts(analysis):
    low,high,one=analysis.binomial_bounds(0,50)
    assert low==one==0
    assert high==pytest.approx(1-.025**(1/50))
    with pytest.raises(ValueError):analysis.binomial_bounds(1,0)


def test_energy_threshold_margins_are_not_half_band_margins(analysis):
    diagnostics=pd.DataFrame([dict(sigma_x_m=0,sigma_y_m=0,sigma_xp_rad=0,sigma_yp_rad=0,
        sigma_z_m=0,mean_kinetic_energy_eV=e,transmission_fraction=1) for e in [196e6,204e6]])
    metrics,margins=analysis.summarize_trials([[1,1,1],[1,1,1]],diagnostics,[1,1,1],[True,True],[True,True])
    assert margins['mean_kinetic_energy_eV:lower']==pytest.approx(1/195)
    assert margins['mean_kinetic_energy_eV:upper']==pytest.approx(1/205)
    assert metrics['worst_channel']=='mean_kinetic_energy_eV:upper'
    assert metrics['score']==pytest.approx(1+1/205)
