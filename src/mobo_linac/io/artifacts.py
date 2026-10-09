"""Run completion marker: the final published-artifact checksums of a run."""
import hashlib
import json
from pathlib import Path

from mobo_linac.utils.durable import atomic_json


def write_completion_marker(run_dir, evaluation_count, elapsed_wall_time_s, files):
    """Publish ``run_complete.json`` with checksums of every required artifact."""
    run_dir = Path(run_dir)
    checksums = {name: hashlib.sha256((run_dir / name).read_bytes()).hexdigest() for name in files}
    atomic_json(run_dir / "run_complete.json", {
        "schema_version": 1, "status": "completed", "evaluation_count": evaluation_count,
        "elapsed_wall_time_s": elapsed_wall_time_s, "artifacts": checksums,
    })


def validate_run_completion(run_dir):
    """Check the final marker against persisted artifacts without trusting filenames."""
    path = Path(run_dir)
    try:
        marker = json.loads((path / "run_complete.json").read_text())
        if marker.get("schema_version") != 1 or marker.get("status") != "completed" or not marker.get("artifacts"):
            return False
        for name, checksum in marker["artifacts"].items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                return False
            if hashlib.sha256((path / relative).read_bytes()).hexdigest() != checksum:
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False
