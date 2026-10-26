"""Equivalent diagnostic units must preserve dimensionless residuals."""
import importlib.util
from pathlib import Path
import pytest
import torch

@pytest.fixture
def analysis(monkeypatch):
    folder=Path(__file__).parents[1]/'scripts';monkeypatch.syspath_prepend(str(folder))
    spec=importlib.util.spec_from_file_location('revision_scaling',folder/'analyze_revision_scaling.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_equivalent_units_preserve_normalized_residuals(analysis):
    y=torch.tensor([[0.,0.,0.,.0011,.0008,.0012,.0009,.00105,196e6,.95]],dtype=torch.double)
    a=torch.stack([f(y) for f in analysis.residual_functions(True,False)])
    b=torch.stack([f(y) for f in analysis.residual_functions(True,True)])
    torch.testing.assert_close(a,b,rtol=1e-12,atol=1e-12)
    assert a[0].item()==pytest.approx(.1)
    assert a[-2].item()==pytest.approx(-1.8)  # upper energy: (196-205)/5

def test_raw_residuals_change_with_units_without_temperature_conversion(analysis):
    y=torch.tensor([[0.,0.,0.,.0011,.0008,.0012,.0009,.00105,196e6,.95]],dtype=torch.double)
    native=[f(y).item() for f in analysis.residual_functions(False,False)]
    display=[f(y).item() for f in analysis.residual_functions(False,True)]
    assert display[0]==pytest.approx(native[0]*1000)
    assert display[-2]==pytest.approx(native[-2]*1e-6)
