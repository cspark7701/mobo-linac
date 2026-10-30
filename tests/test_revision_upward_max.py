import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_revision_upward_max as upward  # noqa: E402
from test_revision_resolution_bounds import ledgers  # noqa: E402


def values():
    return pd.DataFrame({"role": ["a", "b", "b", "c", "d"],
                         "level": ["step_quarter", "source_rand10k_2", "production", "grid_64", "grid_64"],
                         "quantity": ["sigma_x_m", "sigma_y_m", "sigma_y_m", "norm_emit_x_m_rad", "sigma_xp_rad"],
                         "delta_rel": [0.012, 0.1622, 0.0, 0.5, 0.13]})


def test_largest_increase_scans_all_levels_and_rounds_up():
    top = upward.largest_increase(values())
    assert (top["role"], top["level"], top["quantity"]) == ("b", "source_rand10k_2", "sigma_y_m")
    assert top["scale"] == 1.17
    exact = values().assign(delta_rel=[0.0, 0.17, 0.0, 0.0, 0.0])
    assert upward.largest_increase(exact)["scale"] == 1.17


def test_analysis_and_cli_write_the_r5_evidence(tmp_path, monkeypatch):
    table, pairs, result = upward.analyze(ledgers(), values())
    assert set(table.size_scale) == {1.17}
    # baselines violate sigma_x in half their evaluations, also after the increase
    assert result["post_init_difference_nominal"][
        "constrained_qlognehvi - unconstrained_qlognehvi"] == pytest.approx(0.5)
    assert result["all_groups_positive_post_init"] is False  # baseline-minus-Sobol pairs are equal
    monkeypatch.setattr(upward, "load_ledgers", ledgers)
    monkeypatch.setattr(upward.pd, "read_csv", lambda path: values())
    assert upward.main(["--output-dir", str(tmp_path)]) == 0
    metadata = json.loads((tmp_path / "r5_upward_max_metadata.json").read_text())
    assert metadata["largest_increase"]["scale"] == 1.17 and "not re-tracking" in metadata["note"]
    for name in ("runs.csv", "paired.csv"):
        assert (tmp_path / f"r5_upward_max_{name}").exists()
