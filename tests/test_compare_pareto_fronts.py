"""Pareto plots must retain 3D trade-offs outside the reporting reference."""

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

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


def test_two_d_view_preserves_all_three_objective_pairs_without_3d_axes(sample_config):
    tool = module()
    schema = PlotSchema.from_config(sample_config)
    frame = pd.DataFrame([[3e-6, 3e-6, .3e6], [2e-6, 4e-6, .4e6]],
                         columns=[s.column for s in schema.objectives])
    fig = tool.comparison([tool.Front(tool.ALGORITHMS[0], frame)], schema, "title", "subtitle", two_d=True)
    assert len(fig.axes) == 3
    assert all(ax.name != "3d" for ax in fig.axes)
    assert all(len(ax.collections[0].get_offsets()) == 2 for ax in fig.axes)
    assert [(ax.get_xlabel(), ax.get_ylabel()) for ax in fig.axes] == [
        (tool.axis_label(schema.objectives[i]), tool.axis_label(schema.objectives[j]))
        for i, j in [(0, 1), (0, 2), (1, 2)]]
    plt.close(fig)


def test_scatter_only_retains_points_dominated_in_a_projection(sample_config):
    tool = module()
    schema = PlotSchema.from_config(sample_config)
    frame = pd.DataFrame([[3e-6, 3e-6, .3e6], [2e-6, 4e-6, .4e6],
                          [5e-6, 2e-6, .5e6], [4e-6, 4e-6, .2e6]],
                         columns=[s.column for s in schema.objectives])
    # The last point improves energy spread even though it is dominated in x/y.
    fronts = [tool.Front(tool.ALGORITHMS[0], frame)]
    for fig in [tool.comparison(fronts, schema, "title", "subtitle", two_d=True),
                tool.paper_comparison(fronts, schema)]:
        for ax in fig.axes:
            assert len(ax.lines) == 0
            assert len(ax.collections[0].get_offsets()) == 4
        np.testing.assert_allclose(fig.axes[0].collections[0].get_offsets(),
                                   [[3, 3], [2, 4], [5, 2], [4, 4]])
        plt.close(fig)
