"""Reconcile durable proposals, completed checkpoints, and streamed completions."""


from mobo_linac.campaigns.state import prepare_resume_state
from mobo_linac.io.journal import load_streaming_records, same_evaluation
from mobo_linac.io.checkpoint import load_run_checkpoint, run_directory


def load_resume_candidate(target):
    """Prefer a pending proposal only when it extends the completed checkpoint."""
    directory = run_directory(target)
    completed = load_run_checkpoint(target)
    if completed is not None and completed.proposals.pending_proposal is not None:
        completed = load_run_checkpoint(directory)
    pending_path = directory / "checkpoints" / "pending_batch.pt"
    pending = load_run_checkpoint(pending_path) if pending_path.exists() else None
    if pending is not None:
        if pending.proposals.pending_proposal is None:
            raise ValueError("Pending checkpoint lacks a proposal.")
        if completed is None or completed.proposals.pending_proposal is not None:
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
            if (pending.config != completed.config or pending.campaign.run_id != completed.campaign.run_id
                    or pending.campaign.optimization_mode != completed.campaign.optimization_mode
                    or pending.campaign.scalar_weights != completed.campaign.scalar_weights
                    or pending.campaign.seed != completed.campaign.seed
                    or pending.campaign.total_eval_budget != completed.campaign.total_eval_budget
                    or pending.campaign.acquisition_mode != completed.campaign.acquisition_mode
                    or pending.campaign.device != completed.campaign.device
                    or pending.progress.initial_design != completed.progress.initial_design):
                raise ValueError("Pending proposal and completed checkpoint disagree.")
            if len(pending.results) > len(completed.results) or any(
                not same_evaluation(left, right)
                for left, right in zip(pending.results, completed.results)
            ):
                raise ValueError("Pending proposal base history disagrees with checkpoint.")
            if pending.iteration >= 0 and (
                pending.metrics.reporting_ref_point != completed.metrics.reporting_ref_point
                or pending.metrics.reporting_scales != completed.metrics.reporting_scales
                or pending.progress.evaluation_batches != completed.progress.evaluation_batches[:len(pending.results)]
                or pending.metrics.metric_history != completed.metrics.metric_history[:pending.iteration + 1]
            ):
                raise ValueError("Pending proposal base metrics disagree with checkpoint.")

    if completed is not None and pending is not None and completed.proposals.proposal_history is not None and pending.proposals.proposal_history is not None:
        base_history = [entry for entry in pending.proposals.proposal_history if entry["batch_idx"] <= pending.iteration]
        completed_prefix = [entry for entry in completed.proposals.proposal_history if entry["batch_idx"] <= pending.iteration]
        if base_history != completed_prefix:
            raise ValueError("Pending proposal history disagrees with completed checkpoint.")
        if state.proposals.pending_proposal is None:
            batch = pending.proposals.pending_proposal["batch_idx"]
            pending_entry = [entry for entry in pending.proposals.proposal_history if entry["batch_idx"] == batch]
            completed_entry = [entry for entry in completed.proposals.proposal_history if entry["batch_idx"] == batch]
            if pending_entry != completed_entry:
                raise ValueError("Stale pending proposal metadata disagrees with completed checkpoint.")

    records = load_streaming_records(directory)
    known = {}
    positions = {}
    for result, batch in zip(state.results, state.progress.evaluation_batches):
        position = positions.get(batch, 0)
        positions[batch] = position + 1
        known[result.evaluation_id] = (result, batch, position)
    active = state.proposals.pending_proposal
    proposed = {} if active is None else {
        identity: (index, candidate)
        for index, (identity, candidate) in enumerate(zip(active["evaluation_ids"], active["candidates"]))
    }
    recovered = {}
    for record in records:
        result = record.result
        if result.run_id != state.campaign.run_id:
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
        proposal = pending.proposals.pending_proposal
        for identity, candidate in zip(proposal["evaluation_ids"], proposal["candidates"]):
            if identity not in known or known[identity][0].x_physical != candidate:
                raise ValueError("Stale pending proposal is not covered by the completed checkpoint.")
        if proposal["batch_idx"] > state.iteration:
            raise ValueError("Stale pending batch is not completed.")
    return recovered
