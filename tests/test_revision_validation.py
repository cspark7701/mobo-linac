import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_revision_validation as validation  # noqa: E402

FEASIBLE = {"sigma_x_m": 0.5e-3, "sigma_y_m": 0.5e-3, "sigma_xp_rad": 0.5e-3, "sigma_yp_rad": 0.5e-3,
            "sigma_z_m": 0.9e-3, "mean_kinetic_energy_eV": 200e6, "transmission_fraction": 1.0}


def ledger(arm, seed, rows):
    frame = pd.DataFrame([{**FEASIBLE, **row} for row in rows])
    frame["evaluation_id"] = [f"eval_{i:06d}" for i in range(1, len(frame) + 1)]
    frame["simulation_valid"] = True
    frame["arm"], frame["seed"], frame["run"] = arm, seed, f"{arm}_seed_{seed}"
    frame["index_in_run"] = range(1, len(frame) + 1)
    return frame


def test_levels_refine_the_fine_level_one_factor_at_a_time():
    fine = validation.LEVELS["fine"][0]
    assert fine["newrun:distribution"] == "qr40k.ini" and fine["charge:nrad"] == 64 and fine["newrun:h_max"] == 0.0025
    assert validation.LEVELS["fine_step16"][0]["newrun:h_max"] == 0.01 / 16
    p80 = validation.LEVELS["fine_p80k"][0]
    assert p80["newrun:distribution"] == "qr80k.ini" and p80["charge:nrad"] == 64
    assert validation.LEVELS["fine_p80k_grid96"][0]["charge:nzf"] == 96
    assert set(validation.LADDER) <= set(validation.LEVELS) and "fine" not in validation.LADDER


def test_plan_runs_longest_levels_first():
    plan = validation._Plan.__new__(validation._Plan)
    plan.levels = validation.LADDER
    tasks = plan.generate_evaluation_plan([("s", None, None, [0.0] * 6)])
    assert len(tasks) == len(validation.LADDER) and tasks[0].metadata["level"] == "fine_p80k_grid96"


def test_feasible_applies_the_bounding_shifts():
    frame = pd.DataFrame([{**FEASIBLE, "sigma_x_m": 1.1e-3}, {**FEASIBLE, "sigma_z_m": 0.995e-3},
                          {**FEASIBLE, "mean_kinetic_energy_eV": 195.02e6}])
    assert not validation.feasible(frame).iloc[0] and validation.feasible(frame, size=0.78).iloc[0]
    assert validation.feasible(frame).iloc[1] and not validation.feasible(frame, bunch=1.01).iloc[1]
    assert validation.feasible(frame).iloc[2] and not validation.feasible(frame, energy=-0.05e6).iloc[2]


def test_nondominated():
    keep = validation.nondominated(np.array([[1, 1, 1], [2, 2, 2], [0, 3, 1], [1, 1, 1]]))
    assert keep.tolist() == [True, False, True, True]


def test_select_sample_strata_are_exclusive_and_reproducible():
    rows = [{}] * validation.N_INIT
    rows += [{"norm_emit_x_m_rad": 1, "norm_emit_y_m_rad": 1, "sigma_energy_eV": 1},   # front
             {"norm_emit_x_m_rad": 2, "norm_emit_y_m_rad": 2, "sigma_energy_eV": 2},   # dominated, clear
             {"sigma_x_m": 1.1e-3},                                                    # boundary
             {"sigma_x_m": 5e-3}, {"sigma_x_m": 6e-3}, {"sigma_x_m": 7e-3}]            # clearly infeasible
    for row in rows:
        row.setdefault("norm_emit_x_m_rad", 3)
        row.setdefault("norm_emit_y_m_rad", 3)
        row.setdefault("sigma_energy_eV", 3)
    data = ledger("arm", 42, rows)
    sample = validation.select_sample(data)
    strata = sample.set_index("index_in_run").stratum
    assert strata[17] == "front" and strata[19] == "boundary"
    assert (sample.stratum == "random").sum() == validation.RANDOM_PER_GROUP
    assert not sample.duplicated("evaluation_id").any()
    assert sample.equals(validation.select_sample(data))
