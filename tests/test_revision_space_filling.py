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


def test_sobol_quality_scores_against_the_unchanged_reference(analysis, tmp_path, monkeypatch):
    monkeypatch.setattr(analysis, "SEEDS", (1, 2))
    pd.DataFrame({"emit_x_um_rad": [1.0, 2.0], "emit_y_um_rad": [2.0, 1.0],
                  "sigma_energy_MeV": [0.5, 0.5]}).to_csv(tmp_path / "c03_empirical_reference.csv", index=False)
    pipelines = [{"method": m, "group": g, "evaluations": 160, "front_size_unique": 3,
                  "epsilon": 0.1 * g, "igd_plus": 0.05 * g} for m in analysis.METHODS for g in (1, 2)]
    pd.DataFrame(pipelines).to_csv(tmp_path / "c03_run_histories.csv", index=False)
    arms = {seed: pd.DataFrame({"norm_emit_x_m_rad": [1.5e-6, 3e-6], "norm_emit_y_m_rad": [2.5e-6, 3e-6],
                                "sigma_energy_eV": [0.5e6, 0.4e6], "category": ["feasible", "energy_only"]})
            for seed in (1, 2)}
    table, effects = analysis.sobol_quality(arms, tmp_path)
    sobol = table[table.method == "sobol"].iloc[0]
    # The only feasible Sobol point (1.5, 2.5, 0.5) needs a shift of 1.5 to cover (2, 1, 0.5).
    assert sobol.front_size_unique == 1 and sobol.epsilon == pytest.approx(1.5)
    assert sobol.reference_points_dominated == 0
    row = effects[(effects.metric == "epsilon") & (effects.first_method == analysis.METHODS[0])].iloc[0]
    assert row.mean_difference == pytest.approx(0.15 - 1.5) and row.n_negative == 2
