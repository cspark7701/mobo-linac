import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_revision_convergence as analysis  # noqa: E402
import evaluate_revision_convergence as driver  # noqa: E402

BASE = {"norm_emit_x_m_rad": 3.0e-6, "norm_emit_y_m_rad": 3.0e-6, "sigma_energy_eV": 4.0e5,
        "sigma_x_m": 0.299e-3, "sigma_y_m": 0.25e-3, "sigma_xp_rad": 0.1e-3, "sigma_yp_rad": 0.2e-3,
        "sigma_z_m": 0.95e-3, "mean_kinetic_energy_eV": 200.2e6, "transmission_fraction": 1.0}


def write_runs(directory: Path, shift: dict) -> None:
    """Two settings at every level; ``shift`` adds an offset to sigma_x per level."""
    lines = []
    for role in ("a", "b"):
        for level in driver.LEVELS:
            objectives = {k: BASE[k] for k in analysis.OBJECTIVES}
            diagnostics = {k: BASE[k] for k in analysis.DIAGNOSTICS}
            diagnostics["sigma_x_m"] += shift.get(level, 0.0)
            lines.append(json.dumps({"role": role, "level": level, "status": "SUCCESS", "simulation_valid": True,
                                     "runtime_s": driver.LEVELS[level][1] * 10.0, "run": None,
                                     "evaluation_id": None, "objectives": objectives,
                                     "diagnostics": diagnostics}))
    stream = directory / "convergence_results.jsonl"
    stream.write_text("\n".join(lines) + "\n")
    (directory / "complete.json").write_text(json.dumps(
        {"tasks": len(lines), "results_sha256": hashlib.sha256(stream.read_bytes()).hexdigest()}))


def test_levels_change_one_factor_or_both_combined_and_run_longest_first():
    assert set(driver.LEVELS["grid_64"][0]) == set(driver.GRID)
    assert driver.LEVELS["step_quarter"][0] == {"newrun:h_max": 0.0025, "newrun:h_min": 0.00025}
    fine = driver.LEVELS["combined_fine"][0]
    assert fine["newrun:distribution"] == "qr40k.ini" and fine["charge:nrad"] == 64 and fine["newrun:h_max"] == 0.0025
    assert driver.LEVELS["production"][0] == {}
    plan = driver._ConvergencePlan.__new__(driver._ConvergencePlan)
    tasks = plan.generate_evaluation_plan([("s", None, None, [0.0] * 6)])
    assert len(tasks) == len(driver.LEVELS) and tasks[0].metadata["level"] == "combined_fine"
    assert next(t for t in tasks if t.metadata["level"] == "production").namelist_overrides is None


def test_source_input_reproduces_the_production_recipe():
    deck = driver.SOURCE_INPUT.format(name="x.ini", particles=40000, quasi=".T")
    assert "IPart=40000" in deck and "Noise_reduc=.T" in deck and "2DGaussian" in deck
    assert sum(not quasi for _, quasi in driver.SOURCES.values()) == 5


def test_residuals_summary_and_classification(tmp_path):
    write_runs(tmp_path, {"combined_fine": 2e-6, "grid_64": -1e-6, "source_rand10k_1": 1e-6,
                          "source_rand10k_2": -1e-6})
    frame = analysis.load_runs(tmp_path)
    long = analysis.residuals(frame)
    table = analysis.summary(long).set_index(["role", "quantity"])
    row = table.loc[("a", "sigma_x_m")]
    assert row.delta_fine == pytest.approx(2e-6)
    assert row.max_abs_single_factor == pytest.approx(1e-6) and row.max_single_factor_level == "grid_64"
    assert row.source_random_std == pytest.approx(pd.Series([1e-6, -1e-6, 0, 0, 0]).std())
    assert table.loc[("a", "sigma_energy_eV")].delta_fine == 0
    classes = analysis.classification(frame).set_index(["role", "level"])
    assert classes.loc[("a", "production"), "kls_tdr_optimization"]
    assert not classes.loc[("a", "combined_fine"), "kls_tdr_optimization"]
    assert classes.loc[("a", "combined_fine"), "kls_tdr_optimization_changed"]
    assert classes.loc[("a", "combined_fine"), "tdr_margin_sigma_x_m"] == pytest.approx(-1e-6)
    assert classes.loc[("a", "combined_fine"), "production"]


def test_load_runs_rejects_a_changed_stream(tmp_path):
    write_runs(tmp_path, {})
    with (tmp_path / "convergence_results.jsonl").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="Checksum"):
        analysis.load_runs(tmp_path)
