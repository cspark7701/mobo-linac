import copy
import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_revision_round6_resolution as resolution  # noqa: E402
import recover_revision_round6 as recovery  # noqa: E402


@pytest.fixture
def paused(tmp_path):
    spec = copy.deepcopy(json.loads(resolution.SPEC.read_text()))
    spec["minimum_free_disk_GiB"] = 0
    frame = pd.read_csv(resolution.MANIFEST).head(2)
    study = tmp_path/"study"
    resolution.execute(study, spec, frame, mock=True, stage="nominal")
    records = resolution.read_records(study/"results.jsonl")
    tasks = [t.task_id for t in resolution.make_tasks(frame, spec, list(spec["levels"]))]
    pending = [t for t in tasks if t not in records]
    (study/"pending.json").write_text(json.dumps(pending)+"\n")
    interrupted = pending[:2]
    run = study/"runs/round6_resolution"
    for k, identity in enumerate(interrupted):
        attempt = run/"work"/f"eval_{identity}/attempt_{k}"
        attempt.mkdir(parents=True)
        (attempt/"astra.in").write_text("deck")
        (attempt/"astra.Xemit.001").write_text("1.0 0\n8.5 0\n")
        provenance = run/"provenance"/f"eval_{identity}/attempt_{k}"
        (provenance/"inputs").mkdir(parents=True)
        (provenance/"inputs/astra.in").write_text("deck")
        (provenance/"attempt_started.json").write_text(json.dumps({"attempt_id": f"attempt_{k}", "start_time": "t"}))
    checkpoint = tmp_path/"checkpoint"
    checkpoint.mkdir()
    for name in recovery.FILES:
        shutil.copy2(study/name, checkpoint/name)
    (checkpoint/"pause_manifest.json").write_text(json.dumps({
        "files_sha256": {name: recovery.sha(study/name) for name in recovery.FILES},
        "completed_count": len(records), "interrupted_attempts": dict.fromkeys(interrupted, "work")}))
    marker = tmp_path/"PAUSED.json"
    marker.write_text("{}")
    return study, checkpoint, marker, spec, frame, interrupted, len(pending)


def test_recovery_retains_attempts_appends_records_and_allows_resume(paused):
    study, checkpoint, marker, spec, frame, interrupted, pending = paused
    original = {i: list((study/"runs/round6_resolution/work"/f"eval_{i}").iterdir()) for i in interrupted}
    receipt = recovery.recover(study, checkpoint, marker, spec, frame, mock=True)
    assert receipt["attempts_added"] == 2 and receipt["pending_never_started"] == pending-2
    assert receipt["interrupted_attempts"][interrupted[0]]["last_z_m"] == 8.5
    records = resolution.read_records(study/"results.jsonl")
    assert records[interrupted[1]]["recovery_of_attempt"] == "attempt_1"
    assert all(path.exists() for paths in original.values() for path in paths)
    assert not marker.exists() and (study/"recovery_01/PAUSED_archived.json").exists()
    assert not (study/"pending.json").exists() and (study/"recovery_01/pending_at_pause.json").exists()
    resolution.execute(study, spec, frame, mock=True, resume=True)
    assert len(resolution.read_records(study/"results.jsonl")) == len(frame)*len(spec["levels"])
    assert resolution.read_records(study/"results.jsonl")[interrupted[0]]["recovery_of_attempt"] == "attempt_0"
    with pytest.raises(ValueError, match="Recovery directory exists"):
        recovery.recover(study, checkpoint, marker, spec, frame, mock=True)


def test_changed_snapshot_blocks_recovery(paused):
    study, checkpoint, marker, spec, frame, *_ = paused
    with (study/"results.jsonl").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="Pause snapshot checksum"):
        recovery.recover(study, checkpoint, marker, spec, frame, mock=True)
    assert marker.exists() and not (study/"recovery_01").exists()


def test_unexpected_started_identity_or_finished_attempt_blocks_recovery(paused):
    study, checkpoint, marker, spec, frame, interrupted, _ = paused
    run = study/"runs/round6_resolution"
    finished = run/"provenance"/f"eval_{interrupted[0]}/attempt_0/manifest.json"
    finished.write_text("{}")
    with pytest.raises(ValueError, match="unfinished start"):
        recovery.recover(study, checkpoint, marker, spec, frame, mock=True)
    finished.unlink()
    pending = json.loads((study/"pending.json").read_text())
    (run/"work"/f"eval_{pending[5]}").mkdir()
    with pytest.raises(ValueError, match="Started pending identities"):
        recovery.recover(study, checkpoint, marker, spec, frame, mock=True)
    assert marker.exists()


def test_attempt_that_reached_the_exit_is_not_treated_as_interrupted(paused):
    study, _, _, _, _, interrupted, _ = paused
    run = study/"runs/round6_resolution"
    (run/"work"/f"eval_{interrupted[0]}/attempt_0/astra.Xemit.001").write_text("16.2 0\n")
    with pytest.raises(ValueError, match="reached the exit"):
        recovery.inspect_attempt(run, interrupted[0])
