"""Pareto plots must retain 3D trade-offs outside the reporting reference."""

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from mobo_linac.plotting.common import PlotSchema


def module():
    spec = importlib.util.spec_from_file_location(
        "compare_pareto_fronts", Path(__file__).resolve().parents[1] / "scripts/compare_pareto_fronts.py")
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def test_pooling_retains_three_objective_tradeoffs_and_removes_dominated_points(sample_config):
    tool = module()
    schema = PlotSchema.from_config(sample_config)
    columns = [s.column for s in schema.objectives]
    first = pd.DataFrame([[3e-6, 3e-6, .3e6], [4e-6, 4e-6, .6e6]], columns=columns)
    first["evaluation_id"] = ["A", "dominated"]
    second = pd.DataFrame([[2e-6, 4e-6, .4e6]], columns=columns)
    second["evaluation_id"] = ["B"]
    result = tool.pooled_front([first, second], schema)
    # B is worse in y and energy, but better in x, so a 2D filter would lose it.
    # Both A/B are outside the production 1.5-um reference and must remain visible.
    assert set(result.evaluation_id) == {"A", "B"}
    np.testing.assert_allclose(tool.coordinates(result.iloc[[0]], schema), [[3., 3., .3]])
    assert list(first.evaluation_id) == ["A", "dominated"]
