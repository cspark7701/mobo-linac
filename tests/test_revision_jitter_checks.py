import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def analysis(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("jitter_checks", ROOT / "scripts/analyze_revision_jitter_checks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dominance_requires_one_strict_improvement(analysis):
    assert analysis.dominates(np.array([1, 1, 1]), np.array([1, 2, 1]))
    assert not analysis.dominates(np.array([1, 1, 1]), np.array([1, 1, 1]))
    assert not analysis.dominates(np.array([0, 2, 1]), np.array([1, 1, 1]))


def test_amplitude_estimate_from_structure_gains(analysis, tmp_path, monkeypatch):
    # Linear 50 MeV gain in each 2.98 m structure after a 4 MeV gun.
    z = np.linspace(0, 16.2, 3241)
    energy = np.full_like(z, 4.0)
    for start in analysis.STRUCTURES.values():
        energy += 50.0 * np.clip((z - start) / analysis.STRUCTURE_LENGTH, 0, 1)
    folder = tmp_path / "moga_nominal/work"
    folder.mkdir(parents=True)
    np.savetxt(folder / "astra.Zemit.001", np.column_stack([z, z, energy, z, z, z, z]))
    monkeypatch.setattr(analysis, "REFERENCES", tmp_path)
    monkeypatch.setattr(analysis, "ROOT", tmp_path)
    estimate = analysis.amplitude_estimate()
    assert estimate["pair_gain_MeV"]["ACC1/2"] == pytest.approx(100, abs=0.2)
    assert estimate["mean_energy_shift_rms_MeV"]["independent_pairs"] == pytest.approx(0.002 * np.hypot(100, 100), rel=1e-2)
    assert estimate["mean_energy_shift_rms_MeV"]["fully_correlated"] == pytest.approx(0.002 * 204, rel=1e-2)
