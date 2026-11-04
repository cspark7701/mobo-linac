import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_revision_round6_rf_phase as rf  # noqa: E402

DECK = """C_pos(2) = 1.0\nC_pos(3)=2.0\nC_pos(4) = 3.0\nC_pos(5)=4.0
phi(2) = -40.0\nphi(3) = -40.0\nphi(4) = 310.0\nphi(5) = 310.0\n"""


def attempt(root):
    root.mkdir(parents=True)
    (root/"astra.in").write_text(DECK)
    # energy gains of 10, 20, 30 and 40 MeV; the bunch length falls from 1.0 to 0.9 mm
    z = np.array([[1.0, 0, 4, 1.0], [2.0, 0, 14, 0.975], [3.0, 0, 34, 0.95], [4.0, 0, 64, 0.925], [16.2, 0, 104, 0.9]])
    np.savetxt(root/"astra.Zemit.001", z)


def test_fit_crest_recovers_a_known_crest_from_a_narrow_window():
    phase = np.linspace(-43.0, -35.0, 30)
    fit = rf.fit_crest(phase, 47.0*np.cos(np.radians(phase+27.0)))
    assert fit["crest_deg"] == pytest.approx(-27.0)
    assert fit["amplitude_MeV"] == pytest.approx(47.0)
    assert fit["residual_rms_MeV"] == pytest.approx(0.0, abs=1e-9)


def test_setting_row_reads_gains_and_lengths_at_the_structure_edges(tmp_path):
    attempt(tmp_path/"a")
    row = rf.setting_row(tmp_path/"a")
    assert row["injection_energy_MeV"] == 4 and row["exit_energy_MeV"] == 104
    assert [row[f"{name}_gain_MeV"] for name in rf.STRUCTURES] == [10, 20, 30, 40]
    assert row["ACC3_phase_deg"] == 310.0 and row["ACC4_end_length_mm"] == 0.9


def test_analyze_wraps_the_offset_from_crest_and_gives_length_ratios():
    phase = np.linspace(280.0, 340.0, 20)
    frame = pd.DataFrame({"injection_energy_MeV": 4.0, "entry_length_mm": 1.0}, index=phase)
    for name, crest in zip(rf.STRUCTURES, (-30.0, -40.0, -50.0, -60.0)):
        frame[f"{name}_phase_deg"] = phase
        frame[f"{name}_gain_MeV"] = 50*np.cos(np.radians(phase-crest))
        frame[f"{name}_end_length_mm"] = 0.98
    result = rf.analyze(frame, dict.fromkeys(rf.STRUCTURES, 310.0))
    assert result["structures"]["ACC3"]["nominal_minus_crest_deg"] == pytest.approx(0.0)
    assert result["length_ratio_to_entry"]["ACC2_end"]["median"] == pytest.approx(0.98)


def test_main_writes_the_evidence(tmp_path, monkeypatch):
    for k in (1, 2):
        attempt(tmp_path/f"work/eval_x{k}__production/attempt_a")
    output = tmp_path/"fit.json"
    assert rf.main(["--work-dir", str(tmp_path/"work"), "--output", str(output)]) == 0
    assert json.loads(output.read_text())["settings"] == 2
