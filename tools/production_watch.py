#!/usr/bin/env python3
"""Queue six-hour production checks in an existing local Codex chat.

Configuration and dispatch logs live under ignored results, not in Git.
This dispatcher never changes simulations; the existing session performs review
and any user-authorized recovery with its normal approval controls.
"""

import argparse
from datetime import datetime, timedelta
import fcntl
import json
from pathlib import Path
import shlex
import subprocess


def save(path, record):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    temporary.replace(path)


def read_crontab():
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode and "no crontab" not in result.stderr:
        raise RuntimeError(result.stderr)
    return result.stdout


def replace_entry(existing, marker, entry=None):
    """Preserve unrelated cron jobs and comments, modifying only our exact tag."""
    lines = [line for line in existing.splitlines() if not line.endswith(f"# {marker}")]
    if entry:
        lines.append(entry)
    return "\n".join(lines) + ("\n" if lines else "")


def write_crontab(contents):
    subprocess.run(["crontab", "-"], input=contents, text=True, check=True)


def monitor_prompt(config):
    return f"""Scheduled six-hour production check authorized by the user for {config['project']}.
Continue the existing task in this chat; do not create another schedule or another agent.
Read AGENTS.md and inspect stages 05_operating_points, 06_candidate_audit, and 07_paper_outputs
under results/paper_production, their logs, markers, completion checksums, evaluation journals,
checkpoints, active process ancestry/cwd, audit statuses, and GPU/disk state. Ignore other projects.
Report progress and failures. Numerical warnings or physical constraint rejections alone do not
constitute execution failures. Do not stop a healthy run or start a duplicate run.
If execution failed, the user has authorized diagnosing it, fixing the relevant code, running
focused checks, saving the next numbered task completion summary, committing related files with
the repository's imperative/paragraphs/Files format, then relaunching/resuming the failed stage.
Use {config['python']} and WORKERS=8 DEVICE=cuda:0. Preserve seeds, physical validation,
budgets, precision, provenance, and completed simulations. Recover from authoritative checkpoints;
never delete or silently overwrite campaign evidence. Partial stage-05 recovery may need per-run
resume rather than the launcher's blanket --resume precondition. Preserve failed audit/report
attempts and use isolated retry outputs when necessary. Do not change physics to make a gate pass.
If stages are idle and prerequisites are complete, continue the user's already-authorized remaining
05→06→07 chain, checking for any existing user shell chain before launching. Commit fixes before
relaunch so clean-tree startup records the correct code. Do not git push or query remote workflows.
Record findings and actions under results/paper_production/monitor and in a task summary committed
with related changes, according to AGENTS.md. Respect any later user instruction to stop.
Once all stages 05–07 finish and their completion/audit/report evidence is verified, stop monitoring:
{shlex.join([config['python'], str(Path(__file__).resolve()), '--config', config['config_path'], '--disable'])}
Normal sandbox and automatic approval review remain enabled; report any blocked recovery honestly.
"""


def install(config, config_path):
    now = datetime.now().astimezone()
    hours = ",".join(str(hour) for hour in sorted({(now.hour + i * 6) % 24 for i in range(4)}))
    command = shlex.join([config["python"], str(Path(__file__).resolve()), "--config", str(config_path)])
    log = shlex.quote(str(config_path.parent / "dispatch.log"))
    entry = f"{now.minute} {hours} * * * {command} >> {log} 2>&1 # {config['cron_marker']}"
    write_crontab(replace_entry(read_crontab(), config["cron_marker"], entry))
    status = {"enabled": True, "installed_at": now.isoformat(), "cron_entry": entry,
              "next_check": (now + timedelta(hours=6)).replace(second=0, microsecond=0).isoformat(),
              "thread": config["thread"], "interval_hours": 6}
    save(config_path.parent / "schedule.json", status)
    print(json.dumps(status, indent=2))


def disable(config, config_path):
    write_crontab(replace_entry(read_crontab(), config["cron_marker"]))
    record = {"enabled": False, "disabled_at": datetime.now().astimezone().isoformat()}
    save(config_path.parent / "schedule.json", record)
    print(json.dumps(record))


def dispatch(config, config_path):
    with (config_path.parent / "dispatch.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("A dispatch is already in progress; skipping")
            return
        command = [config["codex"], "queue", "--remote", "unix://", "--approve-for-me",
                   "--thread", config["thread"], "--message", monitor_prompt(config)]
        record = {"checked_at": datetime.now().astimezone().isoformat(), "thread": config["thread"]}
        try:
            result = subprocess.run(command, cwd=config["project"], capture_output=True, text=True, timeout=120)
            record.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr,
                          status="queued" if result.returncode == 0 else "delivery_failed")
        except (OSError, subprocess.TimeoutExpired) as error:
            record.update(status="delivery_failed", error=str(error))
        save(config_path.parent / "last_dispatch.json", record)
        with (config_path.parent / "dispatch_history.jsonl").open("a") as stream:
            stream.write(json.dumps(record) + "\n")
        print(json.dumps(record, indent=2))
        if record["status"] != "queued":
            raise RuntimeError("Production check delivery failed; see last_dispatch.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--install", action="store_true")
    actions.add_argument("--disable", action="store_true")
    args = parser.parse_args()
    path = args.config.resolve()
    settings = json.loads(path.read_text())
    settings["config_path"] = str(path)
    if args.install:
        install(settings, path)
    elif args.disable:
        disable(settings, path)
    else:
        dispatch(settings, path)
