"""Validation and random-state restoration for campaign checkpoints and proposals."""

from copy import deepcopy
from dataclasses import asdict
import math
import random
from typing import Optional, Sequence
import warnings

import numpy as np
import torch

from mobo_linac.campaign_options import OPTIMIZATION_MODES, Acquisition, decode_acquisition
from mobo_linac.config import MoboConfig, config_from_dict
from mobo_linac.io.checkpoint import CheckpointState
from mobo_linac.io.results import get_train_tensors
from mobo_linac.metrics.hypervolume import HypervolumeTracker, compute_reference_point
from mobo_linac.result_schema import ResultSchema


def prepare_resume_state(
    checkpoint: CheckpointState,
    config: MoboConfig,
    legacy_scalar_weights: Optional[Sequence[float]] = None,
) -> CheckpointState:
    """Check configuration, migrate legacy assumptions, then validate; never writes run artifacts."""
    state = deepcopy(checkpoint)
    check_configuration_compatibility(state, config)
    if state.migrated_from == "1.0":
        migrate_legacy_v1_state(state, config, legacy_scalar_weights)
    validate_structure(state)
    validate_consistency(state, config)
    return state


def check_configuration_compatibility(state: CheckpointState, config: MoboConfig) -> None:
    """The saved scientific configuration must match the resuming one (worker count may differ)."""
    if not isinstance(state.config, dict):
        raise ValueError("Checkpoint lacks the saved configuration required for safe resume.")
    # Display labels/units are not scientific settings; archived layouts are migrated first.
    current = config.scientific_dict()
    saved = config_from_dict(state.config).scientific_dict()
    for section in ("design_variables", "objectives", "constraints", "model", "tracking"):
        if saved.get(section) != current[section]:
            raise ValueError(f"Incompatible checkpoint configuration: {section} changed.")
    saved_execution = saved["execution"]
    for name in current["execution"]:
        if name == "max_workers":
            continue
        if saved_execution.get(name) != current["execution"][name]:
            raise ValueError(f"Incompatible checkpoint configuration: execution.{name} changed.")


def migrate_legacy_v1_state(state: CheckpointState, config: MoboConfig,
                            legacy_scalar_weights: Optional[Sequence[float]]) -> None:
    """Fill v1 gaps that need the configuration (weights, Sobol position, reference, metrics)."""
    if state.campaign.num_initial_samples is None or state.progress.evaluation_batches is None or state.campaign.seed is None:
        raise ValueError("Legacy checkpoint cannot infer initial design/batch membership/seed safely.")
    if state.campaign.optimization_mode == "scalarized_bo":
        if legacy_scalar_weights is None:
            raise ValueError("Legacy scalarized checkpoint omitted weights; supply explicit legacy scalar weights.")
        weights = np.asarray(legacy_scalar_weights, dtype=float)
        if not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() <= 0:
            raise ValueError("Legacy scalar weights must be finite, nonnegative, with positive sum.")
        state.campaign.scalar_weights = (weights / weights.sum()).tolist()
    else:
        state.campaign.scalar_weights = [1.0 / len(config.objectives)] * len(config.objectives)
    # Only the old runner's low-data Sobol branch consumed this stream after initialization.
    draws = state.campaign.num_initial_samples
    for iteration in range(1, state.iteration + 1):
        prior = [r for r, batch in zip(state.results, state.progress.evaluation_batches) if batch < iteration]
        if get_train_tensors(prior, config=config)[0].shape[0] < 2:
            draws += state.progress.evaluation_batches.count(iteration)
    state.progress.sobol_state = {"seed": state.campaign.seed, "dimension": len(config.design_variables), "num_generated": draws}
    state.metrics.reporting_scales = list(ResultSchema.from_config(config).scales)
    if state.metrics.reporting_ref_point is None:
        initial_y = get_train_tensors(state.results[:state.campaign.num_initial_samples], config=config)[1]
        state.metrics.reporting_ref_point = compute_reference_point(initial_y, config=config).tolist()
    tracker = HypervolumeTracker(state.metrics.reporting_ref_point, config)
    for iteration in range(state.iteration + 1):
        prefix = [r for r, batch in zip(state.results, state.progress.evaluation_batches) if batch <= iteration]
        _, y, feasible = get_train_tensors(prefix, config=config)
        tracker.track_iteration(iteration, y, feasible)
    state.metrics.metric_history = tracker.history
    state.metrics.hypervolumes = [record["feasible_hypervolume"] for record in tracker.history]
    state.campaign.device = "cpu"
    state.rng.cuda_rng_states = []
    warnings.warn(
        state.migration_notes[-1] + " Resume is best effort; original scalar weights must be supplied "
        "and legacy GPU continuation cannot be reproduced.",
        RuntimeWarning,
    )


def _bootstrap(state: CheckpointState) -> bool:
    """A pending first batch with no completed iteration yet."""
    return state.iteration == -1 and state.proposals.pending_proposal is not None


def validate_structure(state: CheckpointState) -> None:
    """Required values present, with the right types and admissible ranges."""
    bootstrap = _bootstrap(state)
    required = [("campaign", name) for name in ("run_id", "optimization_mode", "scalar_weights",
                                                "num_initial_samples", "device", "seed", "batch_size")]
    required += [("progress", "initial_design"), ("progress", "sobol_state"), ("progress", "evaluation_batches"),
                 ("metrics", "metric_history"), ("metrics", "reporting_scales"),
                 ("rng", "torch_rng_state"), ("rng", "numpy_rng_state")]
    if not bootstrap:
        required.append(("metrics", "reporting_ref_point"))
    if state.migrated_from != "1.0":
        required += [("campaign", "planned_num_batches"), ("campaign", "num_workers"),
                     ("rng", "python_rng_state"), ("rng", "cuda_rng_states")]
    missing = [name for group, name in required if getattr(getattr(state, group), name) is None]
    if missing:
        raise ValueError(f"Incomplete campaign checkpoint: missing {', '.join(missing)}.")
    for value, name in ((state.iteration, "iteration"), (state.campaign.num_initial_samples, "num_initial_samples"),
                        (state.campaign.batch_size, "batch_size"), (state.campaign.seed, "seed")):
        if type(value) is not int:
            raise ValueError(f"Invalid checkpoint integer field: {name}.")
    if state.campaign.planned_num_batches is not None and (
        type(state.campaign.planned_num_batches) is not int or state.campaign.planned_num_batches < state.iteration
    ):
        raise ValueError("Invalid checkpoint planned iteration count.")
    if state.campaign.num_workers is not None and (type(state.campaign.num_workers) is not int or state.campaign.num_workers < 1):
        raise ValueError("Invalid checkpoint worker count.")
    if (state.iteration < 0 and not bootstrap) or state.campaign.num_initial_samples < 1 or state.campaign.batch_size < 1:
        raise ValueError("Invalid checkpoint iteration or sample counts.")
    if state.campaign.optimization_mode not in OPTIMIZATION_MODES:
        raise ValueError("Invalid checkpoint optimization mode.")
    if state.campaign.constrained != (state.campaign.optimization_mode == "constrained_mobo"):
        raise ValueError("Checkpoint mode and constrained flag disagree.")
    try:
        acquisition = decode_acquisition(state.campaign.acquisition_mode)
    except ValueError:
        raise ValueError("Invalid checkpoint acquisition mode.") from None
    if (state.campaign.optimization_mode == "scalarized_bo") != (acquisition is Acquisition.qLogNEI):
        raise ValueError("Checkpoint scalarized acquisition is inconsistent.")
    if state.progress.elapsed_wall_time_s is not None and (not math.isfinite(state.progress.elapsed_wall_time_s) or state.progress.elapsed_wall_time_s < 0):
        raise ValueError("Invalid checkpoint elapsed wall time.")
    if state.progress.evaluation_elapsed_s is not None:
        if len(state.progress.evaluation_elapsed_s) != len(state.results) or any(value is not None and (not math.isfinite(value) or value < 0) for value in state.progress.evaluation_elapsed_s):
            raise ValueError("Invalid checkpoint evaluation wall times.")
    state.rng.validate()


def validate_consistency(state: CheckpointState, config: MoboConfig) -> None:
    """History, metrics, design, proposals and pending batch agree with each other and the config."""
    bootstrap = _bootstrap(state)
    weights = np.asarray(state.campaign.scalar_weights, dtype=float)
    if (weights.shape != (len(config.objectives),) or not np.isfinite(weights).all()
            or (weights < 0).any() or not np.isclose(weights.sum(), 1.0)):
        raise ValueError("Invalid checkpoint scalar weights.")
    if state.metrics.reporting_scales != list(ResultSchema.from_config(config).scales):
        raise ValueError("Incompatible checkpoint reporting scales.")
    if not bootstrap and (len(state.metrics.reporting_ref_point) != len(config.objectives)
            or not all(math.isfinite(v) for v in state.metrics.reporting_ref_point)):
        raise ValueError("Invalid checkpoint reporting reference point.")
    batches = state.progress.evaluation_batches
    if (len(batches) != len(state.results) or any(type(b) is not int for b in batches)
            or batches != sorted(batches) or set(batches) != set(range(state.iteration + 1))
            or (not bootstrap and batches.count(0) != state.campaign.num_initial_samples)):
        raise ValueError("Invalid checkpoint evaluation batch membership.")
    if any(r.run_id != state.campaign.run_id for r in state.results):
        raise ValueError("Checkpoint evaluation records disagree with run identity.")
    if len({r.evaluation_id for r in state.results}) != len(state.results):
        raise ValueError("Checkpoint contains duplicate evaluation identities.")
    design = np.asarray(state.progress.initial_design, dtype=float)
    if design.shape != (state.campaign.num_initial_samples, len(config.design_variables)) or not np.isfinite(design).all():
        raise ValueError("Invalid checkpoint initial design.")
    for parameters, result in zip(state.progress.initial_design, state.results[:state.campaign.num_initial_samples]):
        if parameters != result.x_physical:
            raise ValueError("Checkpoint initial design does not match evaluation history.")
    sobol = state.progress.sobol_state
    if (sobol.get("dimension") != len(config.design_variables) or sobol.get("seed") != state.campaign.seed
            or type(sobol.get("num_generated")) is not int or sobol["num_generated"] < state.campaign.num_initial_samples):
        raise ValueError("Invalid checkpoint Sobol state.")
    if len(state.metrics.metric_history) != state.iteration + 1:
        raise ValueError("Invalid checkpoint metric history length.")
    for iteration, record in enumerate(state.metrics.metric_history):
        prefix = [r for r, batch in zip(state.results, batches) if batch <= iteration]
        _, y, feasible = get_train_tensors(prefix, config=config)
        if (record.get("iteration") != iteration
                or record.get("reporting_ref_point_model") != state.metrics.reporting_ref_point
                or record.get("num_valid_points") != y.shape[0]
                or record.get("num_feasible_points") != int(feasible.sum())):
            raise ValueError("Checkpoint metric history disagrees with batch membership or reporting reference.")
        for metric in ("all_point_hypervolume", "feasible_hypervolume"):
            if not math.isfinite(record.get(metric, float("nan"))) or record[metric] < 0:
                raise ValueError("Invalid checkpoint hypervolume metric.")
    if state.metrics.hypervolumes != [r["feasible_hypervolume"] for r in state.metrics.metric_history]:
        raise ValueError("Checkpoint hypervolumes disagree with metric history.")
    if state.campaign.total_eval_budget is not None and state.campaign.total_eval_budget < len(state.results):
        raise ValueError("Checkpoint evaluation count exceeds its total budget.")
    if bootstrap and (state.results or state.metrics.metric_history or state.metrics.reporting_ref_point is not None):
        raise ValueError("Invalid initial pending-proposal base state.")
    if state.proposals.proposal_history is not None:
        if not isinstance(state.proposals.proposal_history, list):
            raise ValueError("Invalid checkpoint proposal history.")
        indices = [item.get("batch_idx") for item in state.proposals.proposal_history if isinstance(item, dict)]
        maximum = state.iteration + (1 if state.proposals.pending_proposal is not None else 0)
        if (len(indices) != len(state.proposals.proposal_history) or any(type(index) is not int or not 0 <= index <= maximum for index in indices)
                or indices != sorted(set(indices)) or any(not isinstance(item.get("metadata"), dict) for item in state.proposals.proposal_history)):
            raise ValueError("Invalid checkpoint proposal history.")
        if state.proposals.pending_proposal is not None and "metadata" in state.proposals.pending_proposal:
            if not state.proposals.proposal_history or state.proposals.proposal_history[-1] != {"batch_idx": state.proposals.pending_proposal["batch_idx"], "metadata": state.proposals.pending_proposal["metadata"]}:
                raise ValueError("Pending proposal metadata disagrees with checkpoint history.")
    if state.proposals.pending_proposal is not None:
        validate_pending_proposal(state, config)


def validate_pending_proposal(state: CheckpointState, config: MoboConfig) -> None:
    pending = state.proposals.pending_proposal
    if not isinstance(pending, dict) or pending.get("version") != "1.0":
        raise ValueError("Unsupported pending proposal schema.")
    batch = pending.get("batch_idx")
    if type(batch) is not int or batch != state.iteration + 1:
        raise ValueError("Pending batch does not follow completed checkpoint.")
    candidates = np.asarray(pending.get("candidates"), dtype=float)
    expected = state.campaign.num_initial_samples if batch == 0 else state.campaign.batch_size
    if batch > 0 and state.campaign.total_eval_budget is not None:
        expected = min(expected, state.campaign.total_eval_budget - len(state.results))
    if (expected < 1 or candidates.shape != (expected, len(config.design_variables))
            or not np.isfinite(candidates).all()):
        raise ValueError("Invalid pending candidate design/count.")
    bounds = config.get_parameter_bounds_tensor().numpy()
    if (candidates < bounds[0]).any() or (candidates > bounds[1]).any():
        raise ValueError("Pending candidates exceed configured bounds.")
    ids = pending.get("evaluation_ids")
    expected_ids = [f"eval_{len(state.results) + i + 1:06d}" for i in range(expected)]
    if ids != expected_ids:
        raise ValueError("Pending candidate identities do not follow evaluation history.")
    if batch == 0 and pending["candidates"] != state.progress.initial_design:
        raise ValueError("Pending initial design disagrees with checkpoint.")
    if batch > state.campaign.planned_num_batches:
        raise ValueError("Pending batch exceeds the campaign plan.")


def restore_rng_state(state: CheckpointState) -> None:
    state.rng.restore()


def resolve_resume_device(state: CheckpointState, requested_device) -> torch.device:
    """The saved device (explicit requests must match it), with a CUDA RNG topology check."""
    from mobo_linac.utils import get_device

    def canonical(device, saved=False):
        value = torch.device(device)
        if value.type == "cuda":
            index = value.index
            if index is None:
                index = 0 if saved or not torch.cuda.is_available() else torch.cuda.current_device()
            return (value.type, index)
        return (value.type, None)

    saved_type, saved_index = canonical(state.campaign.device, saved=True)
    automatic = requested_device is None or str(requested_device).strip().lower() in ("auto", "")
    requested = torch.device(saved_type, saved_index) if automatic else str(requested_device).strip().lower()
    if canonical(requested) != (saved_type, saved_index):
        raise ValueError("Resume device differs from checkpoint; deterministic CPU/GPU migration is unsupported.")
    device = get_device(requested, allow_cpu_fallback=False)
    if device.type == "cuda":
        cuda_states = state.rng.cuda_rng_states or []
        if not torch.cuda.is_available() or len(cuda_states) != torch.cuda.device_count():
            raise ValueError("Checkpoint CUDA RNG topology is unavailable or incompatible.")
        if canonical(device)[1] >= torch.cuda.device_count():
            raise ValueError("Checkpoint CUDA device is unavailable.")
        try:
            for index, rng in enumerate(cuda_states):
                torch.Generator(device=f"cuda:{index}").set_state(rng.cpu())
        except RuntimeError as error:
            raise ValueError(f"Invalid checkpoint CUDA RNG state: {error}") from error
    return device
