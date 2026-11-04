import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_revision_round6_workers as check  # noqa: E402
import evaluate_revision_round6_resolution as resolution  # noqa: E402
import evaluate_revision_round6_scaling as scaling  # noqa: E402
import prepare_revision_round6 as prepare  # noqa: E402

SPEC = {"nominal_reproduction_rtol": 1e-9, "nominal_reproduction_atol": 1e-12}


def values(scale=1.0):
    measured = {name: scale*(k+1.0) for k, name in enumerate(resolution.QUANTITIES)}
    return {"task": {"objectives": measured, "diagnostics": {}, "runtime_s": 200.0*scale}}


def test_amendment_raises_the_ceiling_without_changing_the_frozen_specification():
    amendment = json.loads((prepare.EVIDENCE/"r6_execution_amendment_01.json").read_text())
    spec = json.loads(resolution.SPEC.read_text())
    assert spec["workers_total"] == amendment["superseded"]["workers_total"] == 2
    assert prepare.execution_workers() == amendment["workers_total"] == 22
    assert amendment["spec_sha256"] == prepare.sha(resolution.SPEC)
    assert scaling.campaign_config(spec, "raw", 42).execution.retries == 0


def test_amendment_for_another_specification_is_refused(tmp_path, monkeypatch):
    (tmp_path/"r6_specification.json").write_text("{}")
    (tmp_path/"r6_execution_amendment_01.json").write_text('{"spec_sha256": "other", "workers_total": 22}')
    monkeypatch.setattr(prepare, "EVIDENCE", tmp_path)
    with pytest.raises(ValueError, match="frozen specification"):
        prepare.execution_workers()


def test_subset_is_evenly_spaced_and_deterministic():
    frame = pd.DataFrame({"setting_id": [f"s{k:03d}" for k in range(100, 0, -1)]})
    chosen = check.subset(frame, 3)
    assert chosen.setting_id.tolist() == ["s001", "s050", "s100"]
    assert check.subset(frame, 3).equals(chosen)


def test_compare_and_receipt_report_agreement_and_refuse_a_difference():
    assert check.compare(values(), values(), SPEC) == 0.0
    with pytest.raises(ValueError, match="Worker-count mismatch"):
        check.compare(values(1.001), values(), SPEC)
    result = check.receipt(values(), {"task": {"runtime_s": 100.0}}, 22, 0.0)
    assert result["median_runtime_ratio"] == 2.0 and result["reproduced"] and result["workers"] == 22


def test_execute_uses_all_workers_in_its_own_directory_and_is_not_resumed(tmp_path):
    spec = json.loads(resolution.SPEC.read_text())
    frame = pd.read_csv(resolution.MANIFEST)
    study = tmp_path/"study"
    (study/"template").mkdir(parents=True)
    records = check.execute(tmp_path/"check", study, spec, frame, 2, mock=True)
    assert len(records) == 2 and all(key.endswith("__production") for key in records)
    with pytest.raises(ValueError, match="not resumed"):
        check.execute(tmp_path/"check", study, spec, frame, 2, mock=True)
