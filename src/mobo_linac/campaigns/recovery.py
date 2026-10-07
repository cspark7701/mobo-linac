"""Reconcile durable proposals, completed checkpoints, and streamed completions."""

from pathlib import Path

from mobo_linac.campaigns.state import prepare_resume_state
from mobo_linac.io.journal import load_streaming_records, same_evaluation
from mobo_linac.io.results import load_run_checkpoint


def resume_directory(target):
    path = Path(target)
    if path.is_file():
        return path.parent.parent if path.parent.name in ("checkpoints", "gp_checkpoint") else path.parent
    return path


def load_resume_candidate(target):
    """Prefer a pending proposal only when it extends the completed checkpoint."""
    directory = resume_directory(target)
    completed = load_run_checkpoint(target)
    if completed is not None and completed.pending_proposal is not None:
        completed = load_run_checkpoint(directory)
    pending_path = directory / "checkpoints" / "pending_batch.pt"
    pending = load_run_checkpoint(pending_path) if pending_path.exists() else None
    if pending is not None:
        if pending.pending_proposal is None:
            raise ValueError("Pending checkpoint lacks a proposal.")
        if completed is None or completed.pending_proposal is not None:
            if pending.iteration != -1:
                raise ValueError("Pending proposal lacks its completed base checkpoint.")
            return pending, None, pending
        if pending.iteration > completed.iteration:
            raise ValueError("Pending proposal is ahead of its completed base checkpoint.")
        if pending.iteration == completed.iteration:
            return pending, completed, pending
    return completed, completed, pending


def reconcile_resume(state, completed, pending, config, directory, legacy_weights=None):
    """Validate all durable identities before any repair, submission, or export write."""
    if completed is not None:
        completed = prepare_resume_state(completed, config, legacy_weights)
    if pending is not None:
        pending = prepare_resume_state(pending, config, legacy_weights)
        if completed is not None:
            if (pending.config != completed.config or pending.run_id != completed.run_id
                    or pending.optimization_mode != completed.optimization_mode
                    or pending.scalar_weights != completed.scalar_weights
                    or pending.seed != completed.seed
                    or pending.total_eval_budget != completed.total_eval_budget
                    or pending.acquisition_mode != completed.acquisition_mode
                    or pending.device != completed.device
                    or pending.initial_design != completed.initial_design):
                raise ValueError("Pending proposal and completed checkpoint disagree.")
            if len(pending.results) > len(completed.results) or any(
                not same_evaluation(left, right)
                for left, right in zip(pending.results, completed.results)
            ):
                raise ValueError("Pending proposal base history disagrees with checkpoint.")
            if pending.iteration >= 0 and (
                pending.reporting_ref_point != completed.reporting_ref_point
                or pending.reporting_scales != completed.reporting_scales
                or pending.evaluation_batches != completed.evaluation_batches[:len(pending.results)]
                or pending.metric_history != completed.metric_history[:pending.iteration + 1]
            ):
                raise ValueError("Pending proposal base metrics disagree with checkpoint.")

    records = load_streaming_records(directory)
    known = {}
    positions = {}
    for result, batch in zip(state.results, state.evaluation_batches):
        position = positions.get(batch, 0)
        positions[batch] = position + 1
        known[result.evaluation_id] = (result, batch, position)
    active = state.pending_proposal
    proposed = {} if active is None else {
        identity: (index, candidate)
        for index, (identity, candidate) in enumerate(zip(active["evaluation_ids"], active["candidates"]))
    }
    recovered = {}
    for record in records:
        result = record.result
        if result.run_id != state.run_id:
            raise ValueError("Journal run identity disagrees with checkpoint.")
        identity = result.evaluation_id
        if identity in known:
            original, batch, position = known[identity]
            if (not same_evaluation(original, result)
                    or record.batch_idx not in (None, batch)
                    or record.candidate_idx not in (None, position)):
                raise ValueError("Journal completion conflicts with completed checkpoint.")
        elif identity in proposed:
            position, candidate = proposed[identity]
            if (result.x_physical != candidate or record.batch_idx not in (None, active["batch_idx"])
                    or record.candidate_idx not in (None, position)):
                raise ValueError("Journal completion conflicts with pending proposal.")
            recovered[identity] = result
        else:
            raise ValueError("Journal contains work without a durable pending proposal; refusing to discard or replay it.")

    if pending is not None and active is None:
        proposal = pending.pending_proposal
        for identity, candidate in zip(proposal["evaluation_ids"], proposal["candidates"]):
            if identity not in known or known[identity][0].x_physical != candidate:
                raise ValueError("Stale pending proposal is not covered by the completed checkpoint.")
        if proposal["batch_idx"] > state.iteration:
            raise ValueError("Stale pending batch is not completed.")
    return recovered
