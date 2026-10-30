import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_revision_shift_scenarios as scenarios  # noqa: E402
from test_revision_resolution_bounds import ledgers  # noqa: E402


def values():
    return pd.DataFrame({"level": ["step_quarter", "step_quarter", "grid_64", "step_quarter"],
                         "quantity": ["sigma_x_m", "sigma_yp_rad", "sigma_x_m", "norm_emit_x_m_rad"],
                         "delta_rel": [0.0119, -0.1, 0.13, 0.5]})


def summary():
    return pd.DataFrame({"quantity": ["sigma_x_m"], "delta_rel_fine": [-0.219]})


def test_upward_scale_uses_the_step_only_level_and_transverse_rows():
    assert scenarios.upward_scale(values()) == 1.012


def test_differential_pairs_lowest_constrained_with_highest_other():
    table = pd.DataFrame([
        {"seed": seed, "method": method, "post_init_feasible_fraction": value}
        for seed in scenarios.SEEDS
        for method, low, high in (("constrained_qlognehvi", 0.4, 0.5), ("unconstrained_qlognehvi", 0.1, 0.3),
                                  ("scalarized_bo", 0.1, 0.45), ("sobol", 0.0, 0.05))
        for value in (low, high)])
    diff = scenarios.differential(table).set_index(["second_method", "seed"]).difference
    assert diff.loc[("unconstrained_qlognehvi", 42)] == pytest.approx(0.1)
    assert diff.loc[("scalarized_bo", 42)] == pytest.approx(-0.05)
    assert diff.loc[("sobol", 51)] == pytest.approx(0.35)


def test_analysis_and_cli_write_the_r4_evidence(tmp_path, monkeypatch):
    up_table, up_pairs, diff, result = scenarios.analyze(ledgers(), summary(), values())
    assert set(up_table.size_scale) == {1.012}
    assert len(up_table) == 9 * len(scenarios.METHODS) * len(scenarios.SEEDS)
    # baselines violate sigma_x in half their evaluations, also after the 1.2 % increase
    assert result["upward_post_init_difference_nominal"][
        "constrained_qlognehvi - unconstrained_qlognehvi"] == pytest.approx(0.5)
    assert result["upward_all_groups_positive"] is True
    # the 0.78 scale recovers the baselines, so the differential case is not positive
    assert result["differential"]["constrained_qlognehvi - scalarized_bo"]["n_positive"] == 0
    monkeypatch.setattr(scenarios, "load_ledgers", ledgers)
    monkeypatch.setattr(scenarios.pd, "read_csv",
                        lambda path: values() if Path(path) == scenarios.VALUES else summary())
    assert scenarios.main(["--output-dir", str(tmp_path)]) == 0
    metadata = json.loads((tmp_path / "r4_shift_scenarios_metadata.json").read_text())
    assert metadata["upward_scale"] == 1.012 and "not re-tracking" in metadata["note"]
    for name in ("upward_runs.csv", "upward_paired.csv", "differential.csv"):
        assert (tmp_path / f"r4_shift_scenarios_{name}").exists()
