import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_revision_sobol_uncertainty as uncertainty  # noqa: E402

BASE = {"sigma_x_m": 0.5e-3, "sigma_y_m": 0.5e-3, "sigma_xp_rad": 0.5e-3, "sigma_yp_rad": 0.5e-3,
        "sigma_z_m": 0.9e-3, "mean_kinetic_energy_eV": 200e6, "transmission_fraction": 1.0}


def test_run_level_summary_uses_runs_as_units():
    rows = []
    for arm in uncertainty.METHODS:
        for k, seed in enumerate(uncertainty.SEEDS):
            for i in range(1, 21):
                ok = i <= 16 and i == 1 or i > 16 and i - 16 <= k % 2 + 1
                rows.append({**BASE, "arm": arm, "seed": seed, "index_in_run": i, "simulation_valid": True,
                             "sigma_x_m": 0.5e-3 if ok else 2e-3})
    table = uncertainty.per_run(pd.DataFrame(rows))
    assert set(table.population) == {"shared_initial_design", *(f"{m}_post_initialization" for m in uncertainty.METHODS)}
    result = uncertainty.summary(table).set_index("population")
    initial = result.loc["shared_initial_design"]
    assert initial.runs == 10 and initial.n == 160 and initial.feasible == 10 and initial.run_sd == 0
    sobol = result.loc["sobol_post_initialization"]
    assert sobol.run_min == pytest.approx(0.25) and sobol.run_max == pytest.approx(0.5)
    assert sobol.bootstrap_lower <= sobol.run_mean <= sobol.bootstrap_upper
