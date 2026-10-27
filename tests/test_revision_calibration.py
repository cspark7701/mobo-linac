import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def analysis():
    spec = importlib.util.spec_from_file_location("calibration", ROOT / "scripts/analyze_revision_calibration.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stage_boundaries(analysis):
    assert [analysis.stage_of(b) for b in (1, 6, 7, 12, 13, 18)] == ["early"] * 2 + ["middle"] * 2 + ["late"] * 2
    with pytest.raises(ValueError):
        analysis.stage_of(19)


def test_coverage_rows_counts_hits_per_run(analysis):
    frame = pd.DataFrame({"method": "m", "channel": "c", "run_id": ["a", "a", "b", "b"],
                          "observed": [0.0, 3.0, 0.0, 0.0], "predicted": 0.0, "predictive_std": 1.0})
    row = analysis.coverage_rows(frame, ("method", "channel")).iloc[0]
    assert row.n == 4 and row.runs == 2
    assert row.coverage95 == pytest.approx(0.75)
    assert row.run_coverage_median == pytest.approx(0.75)
    assert row.rmse == pytest.approx(1.5)


def test_summarize_b_separates_modes_and_late_stage(analysis):
    frame = pd.DataFrame({"method": "m", "channel": "c", "run_id": "a", "batch": [1, 13, 1, 13],
                          "stage": ["early", "late"] * 2, "mode": ["fixed"] * 2 + ["inferred"] * 2,
                          "observed": [3.0, 0.0, 0.0, 0.0], "predicted": 0.0, "predictive_std": 1.0,
                          "relative_noise": [1e-6, 1e-6, 1e-3, 2e-3]})
    out = analysis.summarize_b(frame).set_index("mode")
    assert out.loc["fixed", "coverage95"] == pytest.approx(0.5)
    assert out.loc["fixed", "late_coverage95"] == pytest.approx(1.0)
    assert out.loc["inferred", "coverage95"] == pytest.approx(1.0)
    assert out.loc["inferred", "median_relative_noise"] == pytest.approx(1.5e-3)


def test_archived_summary_is_consistent():
    summary = pd.read_csv(ROOT / "docs/paper/revisions/evidence/r2_calibration_refit_summary.csv")
    assert set(summary["mode"]) == {"fixed", "inferred"}
    assert (summary.n == 1440).all()
    wide = summary.pivot_table(index=["method", "channel"], columns="mode", values="coverage95")
    assert np.all(wide.inferred >= wide.fixed)
