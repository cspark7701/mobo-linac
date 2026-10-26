"""Exact paired-test handling of signs, ties, zeros and multiplicity."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from analyze_revision_pairs import exact_signed_rank,holm


def test_exact_signed_rank_known_extreme_and_symmetry():
    assert exact_signed_rank([1,2,3,4])==.125
    assert exact_signed_rank([-1,-2,-3,-4])==.125
    assert exact_signed_rank([1,-1])==1
    assert exact_signed_rank([0,0,0])==1
    assert exact_signed_rank([0,1,1])==.5
    with pytest.raises(ValueError):exact_signed_rank([1,np.inf])


def test_holm_known_values_and_order():
    np.testing.assert_allclose(holm([.04,.001,.02]),[.04,.003,.04])
    np.testing.assert_allclose(holm([1.,1.,1.]),[1,1,1])
