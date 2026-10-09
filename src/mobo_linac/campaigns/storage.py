"""Durable campaign model and checkpoint commits shared by all strategies."""
import hashlib
from uuid import uuid4
from mobo_linac.utils.durable import atomic_json, unlink_durable


def persist_model(run_dir, model, iteration, training_ids, metadata, *, pipeline, save_model):
    path = run_dir / "gp_checkpoint" / f"model_iter_{iteration:02d}_{uuid4().hex}.pt"
    if pipeline:
        model.save_artifact(path, training_ids=training_ids, metadata=metadata)
    else:
        save_model(model, path, training_ids=training_ids, metadata=metadata)
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "proposal_iteration": iteration}


def commit_checkpoint(run_dir, proposal_history, pending_path, pending, *, save_checkpoint):
    """Commit the authoritative snapshot (``save_checkpoint()``) before removing a recovered pending batch."""
    save_checkpoint()
    if pending is None:
        unlink_durable(pending_path)
    atomic_json(run_dir / "proposal_history.json", proposal_history)
