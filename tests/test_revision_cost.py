"""Overlap-aware campaign timing must not double-count concurrent workers."""
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('revision_cost',Path(__file__).parents[1]/'scripts/analyze_revision_cost.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_union_nested_overlapping_and_disjoint_intervals():
    assert m.union_duration([(5,8),(0,3),(1,2),(2,6),(10,12)])==10

def test_union_empty_touching_and_negative():
    assert m.union_duration([])==0
    assert m.union_duration([(0,1),(1,2)])==2
    with pytest.raises(ValueError):m.union_duration([(2,1)])
