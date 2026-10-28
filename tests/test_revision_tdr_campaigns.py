import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def analysis(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("tdr_campaigns", ROOT / "scripts/analyze_revision_tdr_campaigns.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame(**overrides):
    row = {"sigma_x_m": 0.29e-3, "sigma_y_m": 0.25e-3, "sigma_xp_rad": 0.1e-3, "sigma_yp_rad": 0.27e-3,
           "sigma_z_m": 0.95e-3, "mean_kinetic_energy_eV": 200.2e6, "transmission_fraction": 1.0}
    row.update(overrides)
    return pd.DataFrame([row])


def test_margins_are_signed_and_relative(analysis):
    m = analysis.margins(frame()).iloc[0]
    assert m.sigma_x_m == pytest.approx(1 / 30)
    assert m.sigma_yp_rad == pytest.approx((0.2663 - 0.27) / 0.2663)
    assert m.mean_kinetic_energy_eV == pytest.approx(0.001)
    assert m.transmission_fraction == pytest.approx(1e-4, rel=1e-3)


def test_worst_margin_ignores_transmission(analysis):
    out = analysis.with_margins(frame(sigma_yp_rad=0.2e-3))
    assert out.binding_channel.iloc[0] == "mean_kinetic_energy_eV"
    assert out.worst_margin.iloc[0] == pytest.approx(0.001)


def test_nondominated(analysis):
    points = np.array([[1, 1, 1], [2, 2, 2], [0, 3, 1], [1, 1, 1]])
    assert analysis.nondominated(points).tolist() == [True, False, True, True]
