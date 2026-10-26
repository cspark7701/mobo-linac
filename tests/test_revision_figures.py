"""Survey histories restart per campaign and include rejected/invalid evaluations."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

def test_cumulative_feasibility_is_per_campaign(monkeypatch):
    folder=Path(__file__).parents[1]/'scripts';monkeypatch.syspath_prepend(str(folder))
    spec=importlib.util.spec_from_file_location('revision_figures',folder/'prepare_revision_figures.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    a=pd.DataFrame({'simulation_valid':[True,False,True],'physically_feasible':[True,False,False]})
    b=pd.DataFrame({'simulation_valid':[True,True],'physically_feasible':[False,True]})
    np.testing.assert_allclose(m.cumulative_feasible(a),[1,.5,1/3])
    np.testing.assert_allclose(m.cumulative_feasible(b),[0,.5])
