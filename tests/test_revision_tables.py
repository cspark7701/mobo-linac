"""Feasible-only tables must not admit attractive rejected observations."""
import importlib.util
from pathlib import Path
import pandas as pd
spec=importlib.util.spec_from_file_location('revision_tables',Path(__file__).parents[1]/'scripts/prepare_revision_tables.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_minima_and_nondominance_exclude_rejections():
    df=pd.DataFrame([[True,True,2,3,4],[True,True,3,2,4],[True,True,4,4,5],[True,False,1,1,1]],columns=['simulation_valid','physically_feasible',*m.OBJECTIVES])
    s=m.feasible_summary(df)
    assert s['feasible']==3 and s['pareto']==2 and s['fraction']==.75
    assert [s[c] for c in m.OBJECTIVES]==[2,2,4]
