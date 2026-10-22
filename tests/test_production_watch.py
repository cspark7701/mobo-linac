"""Production watch dispatch preserves other schedules and recovery boundaries."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def module():
    spec = importlib.util.spec_from_file_location(
        "production_watch", Path(__file__).resolve().parents[1] / "tools/production_watch.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_install_replaces_only_own_cron_entry():
    tool = module()
    old = "# user jobs\n0 * * * * backup\n0 0 * * * old # monitor\n0 1 * * * other # another-monitor\n"
    expected = "# user jobs\n0 * * * * backup\n0 1 * * * other # another-monitor\n"
    assert tool.replace_entry(old, "monitor") == expected
    assert tool.replace_entry(old, "monitor", "new # monitor") == expected + "new # monitor\n"


@pytest.mark.parametrize("code, status", [(0, "queued"), (1, "delivery_failed")])
def test_dispatch_queues_existing_thread_and_records_failure(tmp_path, monkeypatch, code, status):
    tool = module()
    config = {"python": "/python", "codex": "/codex", "project": str(tmp_path),
              "config_path": str(tmp_path / "config.json"), "thread": "existing-thread"}
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        assert kwargs["cwd"] == str(tmp_path)
        return SimpleNamespace(returncode=code, stdout="queued" if code == 0 else "", stderr="")

    monkeypatch.setattr(tool.subprocess, "run", run)
    if code:
        with pytest.raises(RuntimeError, match="delivery failed"):
            tool.dispatch(config, tmp_path / "config.json")
    else:
        tool.dispatch(config, tmp_path / "config.json")
    result = json.loads((tmp_path / "last_dispatch.json").read_text())
    assert result["status"] == status
    assert commands[0][:6] == ["/codex", "queue", "--remote", "unix://", "--approve-for-me", "--thread"]
    assert "existing-thread" in commands[0]
    prompt = commands[0][-1]
    assert "Do not git push" in prompt
    assert "Do not stop a healthy run" in prompt
    assert "WORKERS=8 DEVICE=cuda:0" in prompt


def test_final_paper_preparation_is_local_and_push_remains_blocked(tmp_path):
    tool = module()
    config = {"python": "/python", "project": str(tmp_path), "config_path": str(tmp_path / "config.json"),
              "prepare_paper_after_stage07": True}
    prompt = tool.monitor_prompt(config)
    assert "scripts/reproduce_paper.sh with explicit stage-05" in prompt
    assert "commit the related paper updates" in prompt
    assert "Do not git push" in prompt
    assert "automatic approval review rejected unattended" in prompt
    assert "actual prepared commit/files and destination" in prompt
    assert "request precise final push approval" in prompt
    assert "including already-unpublished ancestor commits" in prompt
