import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_revision_resolution_bounds as bounds  # noqa: E402

BASE = {"sigma_x_m": 0.5e-3, "sigma_y_m": 0.5e-3, "sigma_xp_rad": 0.5e-3, "sigma_yp_rad": 0.5e-3,
        "sigma_z_m": 0.9e-3, "mean_kinetic_energy_eV": 200e6, "transmission_fraction": 1.0}


def ledgers():
    rows = []
    for arm in bounds.METHODS:
        for seed in bounds.SEEDS:
            for i in range(1, 21):
                row = {**BASE, "arm": arm, "seed": seed, "index_in_run": i, "simulation_valid": True}
                if arm != "constrained_qlognehvi" and i % 2:
                    row["sigma_x_m"] = 1.1e-3  # recovered only by the 0.78 size scale
                if i == 20:
                    row["sigma_z_m"] = 0.995e-3  # lost by the +1 % bunch-length shift
                rows.append(row)
    return pd.DataFrame(rows)


def test_size_scales_use_the_largest_observed_reduction():
    summary = pd.DataFrame({"quantity": ["sigma_x_m", "sigma_yp_rad", "norm_emit_x_m_rad"],
                            "delta_rel_fine": [-0.219, -0.05, -0.43]})
    assert bounds.size_scales(summary) == (0.78, 0.89, 1.0)


def test_shifts_reclassify_and_pairs_stay_positive():
    table = bounds.run_table(ledgers(), (0.78, 1.0))
    nominal = table[(table.size_scale == 1.0) & (table.bunch_scale == 1.0) & (table.energy_shift_MeV == 0.0)]
    assert nominal.set_index(["method", "seed"]).loc[("constrained_qlognehvi", 42), "feasible_fraction"] == 1.0
    assert nominal.set_index(["method", "seed"]).loc[("sobol", 42), "feasible_fraction"] == pytest.approx(0.5)
    shrunk = table[(table.size_scale == 0.78) & (table.bunch_scale == 1.01) & (table.energy_shift_MeV == 0.0)]
    assert shrunk.set_index(["method", "seed"]).loc[("sobol", 42), "feasible_fraction"] == pytest.approx(0.95)
    pairs = bounds.paired(table)
    assert not ((pairs.second_method == "sobol") & (pairs.metric == "feasible_fraction")).any()
    result = bounds.summarize(table, pairs)
    assert result["median_feasible_fraction_nominal"]["constrained_qlognehvi"] == 1.0
    assert result["all_groups_positive_post_init"] is False  # equal arms under the 0.78 scale
