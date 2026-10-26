"""Check metric definitions independently of production observations."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest

spec=importlib.util.spec_from_file_location('revision_fronts',Path(__file__).parents[1]/'scripts/analyze_revision_fronts.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_dominance_duplicates_and_tradeoffs():
    points=np.array([[1,2,1],[2,1,1],[2,2,2],[1,2,1]])
    np.testing.assert_array_equal(m.nondominated(points),[[1,2,1],[2,1,1]])
    assert m.coverage(np.array([[1,1,1]]),m.nondominated(points))==1
    assert m.coverage(m.nondominated(points),np.array([[1,1,1]]))==0


def test_metrics_minimization_and_empty_conventions():
    ref=np.array([[1.,2.,3.],[2.,1.,3.]])
    assert m.additive_epsilon(ref,ref)==0
    assert m.igd_plus(ref,ref)==0
    assert m.additive_epsilon(ref+2,ref)==2
    assert m.igd_plus(ref+2,ref)==pytest.approx(np.sqrt(12))
    empty=np.empty((0,3))
    assert np.isinf(m.additive_epsilon(empty,ref))
    assert np.isinf(m.igd_plus(empty,ref))
    assert m.coverage(empty,ref)==0
    assert np.isnan(m.coverage(ref,empty))
    with pytest.raises(ValueError):m.igd_plus(ref,empty)


def test_exact_hypervolume_overlap_and_clipping():
    a=np.array([[1,2,1],[2,1,1]])
    assert m.hypervolume(a,np.array([3,3,3]))==6
    assert m.hypervolume(np.r_[a,[[1,2,1],[4,0,0]]],np.array([3,3,3]))==6
    assert m.hypervolume(np.empty((0,3)),np.array([3,3,3]))==0
