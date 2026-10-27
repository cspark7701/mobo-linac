import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def analysis(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("reference_resampling",
                                                  ROOT / "scripts/analyze_revision_reference_resampling.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_fronts(analysis, shift):
    rng = np.random.default_rng(1)
    fronts = {}
    for group in ("g1", "g2", "g3"):
        for k, method in enumerate(analysis.METHODS):
            points = rng.uniform(1, 2, size=(4, 3)) + (0 if k == 0 else shift)
            fronts[(method, group)] = analysis.nondominated(points)
    return fronts


def test_reference_is_rebuilt_from_the_sampled_groups(analysis):
    fronts = synthetic_fronts(analysis, 0.5)
    full = analysis.indicators(fronts, ["g1", "g2", "g3"])
    single = analysis.indicators(fronts, ["g1"])
    # With one group the pooled reference contains that group's best points only.
    assert single[(analysis.METHODS[0], 0)] != full[(analysis.METHODS[0], 0)]
    # Repeating a group in the sample does not change its indicator values.
    repeated = analysis.indicators(fronts, ["g1", "g1"])
    assert repeated[(analysis.METHODS[0], 0)] == repeated[(analysis.METHODS[0], 1)]


def test_dominating_method_has_better_paired_differences(analysis):
    fronts = synthetic_fronts(analysis, 0.5)
    values = analysis.indicators(fronts, ["g1", "g2", "g3"])
    diffs = analysis.mean_differences(values, 3)
    first, second = analysis.METHODS[0], analysis.METHODS[1]
    assert diffs[("epsilon", first, second)] < 0
    assert diffs[("igd_plus", first, second)] < 0
    assert diffs[("hv_25", first, second)] > 0
