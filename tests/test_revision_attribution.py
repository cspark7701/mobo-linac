import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"max_sigma_x_m": 1e-3, "max_sigma_y_m": 1e-3, "max_sigma_xp_rad": 1e-3, "max_sigma_yp_rad": 1e-3,
          "max_sigma_z_m": 1e-3, "min_mean_kinetic_energy_eV": 195e6, "max_mean_kinetic_energy_eV": 205e6,
          "min_transmission": 0.9}


@pytest.fixture
def analysis():
    spec = importlib.util.spec_from_file_location("attribution", ROOT / "scripts/analyze_revision_attribution.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame(**overrides):
    base = dict(sigma_x_m=0.5e-3, sigma_y_m=0.5e-3, sigma_xp_rad=0.5e-3, sigma_yp_rad=0.5e-3, sigma_z_m=0.9e-3,
                mean_kinetic_energy_eV=200e6, transmission_fraction=1.0)
    base.update(overrides)
    return pd.DataFrame([base])


@pytest.mark.parametrize("overrides,expected", [
    ({}, "feasible"),
    ({"mean_kinetic_energy_eV": 194e6}, "energy_only"),
    ({"mean_kinetic_energy_eV": 206e6}, "energy_only"),
    ({"sigma_yp_rad": 1.1e-3}, "transverse_only"),
    ({"sigma_z_m": 1.1e-3}, "bunch_length_only"),
    ({"mean_kinetic_energy_eV": 190e6, "sigma_x_m": 2e-3}, "energy_transverse"),
    ({"mean_kinetic_energy_eV": 190e6, "sigma_z_m": 2e-3}, "energy_bunch_length"),
    ({"sigma_x_m": 2e-3, "sigma_z_m": 2e-3}, "transverse_bunch_length"),
    ({"mean_kinetic_energy_eV": 190e6, "sigma_x_m": 2e-3, "sigma_z_m": 2e-3}, "energy_transverse_bunch_length"),
    ({"transmission_fraction": 0.5, "sigma_x_m": 2e-3}, "transmission"),
    ({"sigma_x_m": 1e-3, "mean_kinetic_energy_eV": 195e6}, "feasible"),  # limits are inclusive
])
def test_exclusive_categories(analysis, overrides, expected):
    assert analysis.categorize(analysis.violations(frame(**overrides), LIMITS)).iloc[0] == expected


def test_gap_divides_exactly_among_categories(analysis):
    rng = np.random.default_rng(0)
    rows = []
    for method in analysis.METHODS:
        for seed in analysis.SEEDS:
            shares = rng.dirichlet(np.ones(len(analysis.CATEGORIES) + 1))
            row = {"method": method, "seed": seed, "feasible_fraction": shares[-1]}
            row.update({f"share_{c}": value for c, value in zip(analysis.CATEGORIES, shares[:-1])})
            rows.append(row)
    table = pd.DataFrame(rows)
    gaps = analysis.gap_decomposition(table)
    for baseline, group in gaps.groupby("baseline"):
        assert group.contribution.sum() == pytest.approx(group.gap.iloc[0])
        assert group.fraction_of_gap.sum() == pytest.approx(1.0)


def test_upper_quarter_boundary(analysis):
    assert analysis.ACC34_UPPER_QUARTER == pytest.approx(325.5561, abs=1e-4)
