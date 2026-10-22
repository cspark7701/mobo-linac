"""The paper must preserve informative feasible fronts despite zero reference HV."""

import importlib.util
from pathlib import Path

import pytest


def module():
    spec = importlib.util.spec_from_file_location(
        "primary_paper_table", Path(__file__).resolve().parents[1] / "scripts/generate_primary_paper_table.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def records(tool):
    return [dict(algorithm=a, seed=s, feasible_hv=0., feasible_percent=25.,
                 first_feasible=4, feasible_pareto_size=3, invalid_count=0, wall_hours=2.)
            for a in tool.ALGORITHMS for s in range(42, 52)]


def test_zero_hv_does_not_erase_feasible_pareto_or_invent_p_values():
    tool = module()
    result = tool.summarize(records(tool))
    for value in result["algorithms"].values():
        assert value["feasible_hv"] == {"median": 0., "lower": 0., "upper": 0.}
        assert value["feasible_pareto_size"] == {"median": 3., "lower": 3., "upper": 3.}
    for value in result["paired_hv"].values():
        assert value["test_status"] == "not_applicable_all_differences_zero"
        assert value["nonzero_pairs"] == 0
        assert value["p_value"] is None


def test_missing_paired_seed_is_rejected():
    tool = module()
    with pytest.raises(ValueError, match="identical paired seeds"):
        tool.summarize(records(tool)[:-1])


def test_duplicate_seed_is_rejected():
    tool = module()
    rows = records(tool)
    with pytest.raises(ValueError, match="unique paired seeds"):
        tool.summarize(rows + [rows[0]])
