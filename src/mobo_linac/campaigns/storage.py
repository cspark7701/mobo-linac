"""Durable campaign model and checkpoint commits shared by all strategies."""
import hashlib
import os
from uuid import uuid4
from mobo_linac.io.artifacts import atomic_json


def persist_model(run_dir, model, iteration, training_ids, metadata, *, pipeline, save_model):
    path = run_dir / "gp_checkpoint" / f"model_iter_{iteration:02d}_{uuid4().hex}.pt"
    if pipeline:
        model.save_artifact(path, training_ids=training_ids, metadata=metadata)
    else:
        save_model(model, path, training_ids=training_ids, metadata=metadata)
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "proposal_iteration": iteration}


def commit_checkpoint(run_dir, proposal_history, pending_path, pending, *, save_checkpoint, **snapshot):
    """Commit the authoritative snapshot before removing a recovered pending batch."""
    save_checkpoint(**snapshot)
    if pending is None and pending_path.exists():
        pending_path.unlink()
        directory_fd = os.open(pending_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    atomic_json(run_dir / "proposal_history.json", proposal_history)
