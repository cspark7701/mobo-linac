import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def analysis(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("space_filling", ROOT / "scripts/analyze_revision_space_filling.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rates_count_channel_groups(analysis):
    frame = pd.DataFrame({"category": ["feasible", "energy_only", "transverse_only", "feasible"],
                          "violates_energy": [False, True, False, False],
                          "violates_transverse": [False, False, True, False],
                          "violates_bunch_length": [False, False, False, False],
                          "acc3_acc4_phase_deg": [300.0, 330.0, 280.0, 340.0]})
    rates = analysis.rates(frame)
    assert rates["feasible"] == 2 and rates["feasible_fraction"] == 0.5
    assert rates["energy_violation_fraction"] == 0.25 and rates["transverse_violation_fraction"] == 0.25
    assert rates["acc34_upper_quarter_fraction"] == 0.5


@pytest.mark.skipif(not (ROOT / "results/paper_production/04_primary").exists(),
                    reason="archived primary campaigns are not distributed")
def test_initial_reference_matches_archived_counts(analysis):
    runs, _ = analysis.load_runs(analysis.PRIMARY)
    table = analysis.initial_reference(runs).set_index("population")
    assert table.loc["shared_initial_design", "feasible"] == 5
    assert table.loc["shared_initial_design", "n"] == 160
