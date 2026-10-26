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


def test_projected_guides_exclude_projection_dominated_points_but_keep_scatter(sample_config):
    tool = module()
    schema = PlotSchema.from_config(sample_config)
    frame = pd.DataFrame([[3e-6, 3e-6, .3e6], [2e-6, 4e-6, .4e6],
                          [5e-6, 2e-6, .5e6], [4e-6, 4e-6, .2e6]],
                         columns=[s.column for s in schema.objectives])
    frame["evaluation_id"] = ["A", "B", "C", "D"]
    # D remains a genuine 3D trade-off because it improves energy spread,
    # but belongs to neither the x/y envelope nor its connecting guide.
    boundary = tool.projected_envelope(frame, schema, (0, 1))
    assert list(boundary.evaluation_id) == ["B", "A", "C"]
    fig, ax = plt.subplots()
    tool.draw(ax, [tool.Front(tool.ALGORITHMS[0], frame)], schema, pair=(0, 1))
    assert len(ax.collections[0].get_offsets()) == 4
    np.testing.assert_allclose(ax.lines[0].get_xydata(), [[2, 4], [3, 3], [5, 2]])
    plt.close(fig)


def test_projected_envelope_honors_mixed_directions_and_duplicate_coordinates(sample_config):
    from dataclasses import replace
    tool = module()
    schema = PlotSchema.from_config(sample_config)
    schema = replace(schema, objectives=(schema.objectives[0],
                     replace(schema.objectives[1], sign=1), schema.objectives[2]))
    frame = pd.DataFrame([[2e-6, 4e-6, .4e6], [3e-6, 3e-6, .3e6],
                          [4e-6, 5e-6, .2e6], [2e-6, 4e-6, .1e6]],
                         columns=[s.column for s in schema.objectives])
    frame["evaluation_id"] = ["A", "dominated_xy", "B", "same_xy"]
    assert list(tool.projected_envelope(frame, schema, (0, 1)).evaluation_id) == ["A", "B"]
