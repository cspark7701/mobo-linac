"""Validation and random-state restoration for campaign checkpoints and proposals."""

from copy import deepcopy
from dataclasses import asdict
import math
import random
from typing import Optional, Sequence
import warnings

import numpy as np
import torch

from mobo_linac.config import MoboConfig, config_from_dict
from mobo_linac.io.results import CheckpointState, get_train_tensors
from mobo_linac.metrics.hypervolume import HypervolumeTracker, compute_reference_point
from mobo_linac.result_schema import ResultSchema


def prepare_resume_state(
    checkpoint: CheckpointState,
    config: MoboConfig,
    legacy_scalar_weights: Optional[Sequence[float]] = None,
) -> CheckpointState:
    """Migrate explicit legacy assumptions, then validate without writing run artifacts."""
    state = deepcopy(checkpoint)
    if not isinstance(state.config, dict):
        raise ValueError("Checkpoint lacks the saved configuration required for safe resume.")
    current = asdict(config)
    for section in ("design_variables", "objectives", "constraints", "model"):
        if asdict(config_from_dict(state.config)).get(section) != current[section]:
            raise ValueError(f"Incompatible checkpoint configuration: {section} changed.")
    for name in current["execution"]:
        if name == "max_workers":
            continue
        if state.config.get("execution", {}).get(name) != current["execution"][name]:
            raise ValueError(f"Incompatible checkpoint configuration: execution.{name} changed.")

    if state.version == "1.0":
        if state.num_initial_samples is None or state.evaluation_batches is None or state.seed is None:
            raise ValueError("Legacy checkpoint cannot infer initial design/batch membership/seed safely.")
        if state.optimization_mode == "scalarized_bo":
            if legacy_scalar_weights is None:
                raise ValueError("Legacy scalarized checkpoint omitted weights; supply explicit legacy scalar weights.")
            weights = np.asarray(legacy_scalar_weights, dtype=float)
            if not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() <= 0:
                raise ValueError("Legacy scalar weights must be finite, nonnegative, with positive sum.")
            state.scalar_weights = (weights / weights.sum()).tolist()
        else:
            state.scalar_weights = [1.0 / len(config.objectives)] * len(config.objectives)
        # Only the old runner's low-data Sobol branch consumed this stream after initialization.
        draws = state.num_initial_samples
        for iteration in range(1, state.iteration + 1):
            prior = [r for r, batch in zip(state.results, state.evaluation_batches) if batch < iteration]
            if get_train_tensors(prior, config=config)[0].shape[0] < 2:
                draws += state.evaluation_batches.count(iteration)
        state.sobol_state = {"seed": state.seed, "dimension": len(config.design_variables), "num_generated": draws}
        state.reporting_scales = list(ResultSchema.from_config(config).scales)
        if state.reporting_ref_point is None:
            initial_y = get_train_tensors(state.results[:state.num_initial_samples], config=config)[1]
            state.reporting_ref_point = compute_reference_point(initial_y, config=config).tolist()
        tracker = HypervolumeTracker(state.reporting_ref_point, config)
        for iteration in range(state.iteration + 1):
            prefix = [r for r, batch in zip(state.results, state.evaluation_batches) if batch <= iteration]
            _, y, feasible = get_train_tensors(prefix, config=config)
            tracker.track_iteration(iteration, y, feasible)
        state.metric_history = tracker.history
        state.hypervolumes = [record["feasible_hypervolume"] for record in tracker.history]
        state.device = "cpu"
        state.cuda_rng_states = []
        warnings.warn(
            state.migration_notes[-1] + " Resume is best effort; original scalar weights must be supplied "
            "and legacy GPU continuation cannot be reproduced.",
            RuntimeWarning,
        )

    bootstrap = state.iteration == -1 and state.pending_proposal is not None
    required = (
        "run_id", "optimization_mode", "scalar_weights", "num_initial_samples", "initial_design",
        "sobol_state", "evaluation_batches", "metric_history", "reporting_scales", "device",
        "seed", "batch_size", "torch_rng_state", "numpy_rng_state",
    )
    if not bootstrap:
        required += ("reporting_ref_point",)
    if state.version == "2.0":
        required += ("planned_num_batches", "num_workers", "python_rng_state", "cuda_rng_states")
    missing = [name for name in required if getattr(state, name) is None]
    if missing:
        raise ValueError(f"Incomplete campaign checkpoint: missing {', '.join(missing)}.")
    for name in ("iteration", "num_initial_samples", "batch_size", "seed"):
        if type(getattr(state, name)) is not int:
            raise ValueError(f"Invalid checkpoint integer field: {name}.")
    if state.planned_num_batches is not None and (
        type(state.planned_num_batches) is not int or state.planned_num_batches < state.iteration
    ):
        raise ValueError("Invalid checkpoint planned iteration count.")
    if state.num_workers is not None and (type(state.num_workers) is not int or state.num_workers < 1):
        raise ValueError("Invalid checkpoint worker count.")
    if (state.iteration < 0 and not bootstrap) or state.num_initial_samples < 1 or state.batch_size < 1:
        raise ValueError("Invalid checkpoint iteration or sample counts.")
    if state.optimization_mode not in ("scalarized_bo", "constrained_mobo", "unconstrained_mobo"):
        raise ValueError("Invalid checkpoint optimization mode.")
    if state.constrained != (state.optimization_mode == "constrained_mobo"):
        raise ValueError("Checkpoint mode and constrained flag disagree.")
    if state.optimization_mode == "scalarized_bo":
        if state.acquisition_mode not in ("scalarized_qLogNEI", "qLogNEI"):
            raise ValueError("Checkpoint scalarized acquisition is inconsistent.")
    elif state.acquisition_mode not in ("qLogNEHVI", "qLogEHVI", "qEHVI", "qNEHVI"):
        raise ValueError("Invalid checkpoint acquisition mode.")
    if state.elapsed_wall_time_s is not None and (not math.isfinite(state.elapsed_wall_time_s) or state.elapsed_wall_time_s < 0):
        raise ValueError("Invalid checkpoint elapsed wall time.")
    if state.evaluation_elapsed_s is not None:
        if len(state.evaluation_elapsed_s) != len(state.results) or any(value is not None and (not math.isfinite(value) or value < 0) for value in state.evaluation_elapsed_s):
            raise ValueError("Invalid checkpoint evaluation wall times.")
    weights = np.asarray(state.scalar_weights, dtype=float)
    if (weights.shape != (len(config.objectives),) or not np.isfinite(weights).all()
            or (weights < 0).any() or not np.isclose(weights.sum(), 1.0)):
        raise ValueError("Invalid checkpoint scalar weights.")
    if state.reporting_scales != list(ResultSchema.from_config(config).scales):
        raise ValueError("Incompatible checkpoint reporting scales.")
    if not bootstrap and (len(state.reporting_ref_point) != len(config.objectives)
            or not all(math.isfinite(v) for v in state.reporting_ref_point)):
        raise ValueError("Invalid checkpoint reporting reference point.")
    batches = state.evaluation_batches
    if (len(batches) != len(state.results) or any(type(b) is not int for b in batches)
            or batches != sorted(batches) or set(batches) != set(range(state.iteration + 1))
            or (not bootstrap and batches.count(0) != state.num_initial_samples)):
        raise ValueError("Invalid checkpoint evaluation batch membership.")
    if any(r.run_id != state.run_id for r in state.results):
        raise ValueError("Checkpoint evaluation records disagree with run identity.")
    if len({r.evaluation_id for r in state.results}) != len(state.results):
        raise ValueError("Checkpoint contains duplicate evaluation identities.")
    design = np.asarray(state.initial_design, dtype=float)
    if design.shape != (state.num_initial_samples, len(config.design_variables)) or not np.isfinite(design).all():
        raise ValueError("Invalid checkpoint initial design.")
    for parameters, result in zip(state.initial_design, state.results[:state.num_initial_samples]):
        if parameters != result.x_physical:
            raise ValueError("Checkpoint initial design does not match evaluation history.")
    sobol = state.sobol_state
    if (sobol.get("dimension") != len(config.design_variables) or sobol.get("seed") != state.seed
            or type(sobol.get("num_generated")) is not int or sobol["num_generated"] < state.num_initial_samples):
        raise ValueError("Invalid checkpoint Sobol state.")
    if len(state.metric_history) != state.iteration + 1:
        raise ValueError("Invalid checkpoint metric history length.")
    for iteration, record in enumerate(state.metric_history):
        prefix = [r for r, batch in zip(state.results, batches) if batch <= iteration]
        _, y, feasible = get_train_tensors(prefix, config=config)
        if (record.get("iteration") != iteration
                or record.get("reporting_ref_point_model") != state.reporting_ref_point
                or record.get("num_valid_points") != y.shape[0]
                or record.get("num_feasible_points") != int(feasible.sum())):
            raise ValueError("Checkpoint metric history disagrees with batch membership or reporting reference.")
        for metric in ("all_point_hypervolume", "feasible_hypervolume"):
            if not math.isfinite(record.get(metric, float("nan"))) or record[metric] < 0:
                raise ValueError("Invalid checkpoint hypervolume metric.")
    if state.hypervolumes != [r["feasible_hypervolume"] for r in state.metric_history]:
        raise ValueError("Checkpoint hypervolumes disagree with metric history.")
    if state.total_eval_budget is not None and state.total_eval_budget < len(state.results):
        raise ValueError("Checkpoint evaluation count exceeds its total budget.")
    if bootstrap and (state.results or state.metric_history or state.reporting_ref_point is not None):
        raise ValueError("Invalid initial pending-proposal base state.")
    if state.pending_proposal is not None:
        validate_pending_proposal(state, config)
    validate_rng_state(state)
    return state


def validate_pending_proposal(state: CheckpointState, config: MoboConfig) -> None:
    pending = state.pending_proposal
    if not isinstance(pending, dict) or pending.get("version") != "1.0":
        raise ValueError("Unsupported pending proposal schema.")
    batch = pending.get("batch_idx")
    if type(batch) is not int or batch != state.iteration + 1:
        raise ValueError("Pending batch does not follow completed checkpoint.")
    candidates = np.asarray(pending.get("candidates"), dtype=float)
    expected = state.num_initial_samples if batch == 0 else state.batch_size
    if batch > 0 and state.total_eval_budget is not None:
        expected = min(expected, state.total_eval_budget - len(state.results))
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
    if batch == 0 and pending["candidates"] != state.initial_design:
        raise ValueError("Pending initial design disagrees with checkpoint.")
    if batch > state.planned_num_batches:
        raise ValueError("Pending batch exceeds the campaign plan.")


def validate_rng_state(state: CheckpointState) -> None:
    """Check RNG payloads on temporary generators before touching global random state."""
    try:
        torch.Generator().set_state(state.torch_rng_state.cpu())
        np.random.RandomState().set_state(state.numpy_rng_state)
        if state.python_rng_state is not None:
            random.Random().setstate(state.python_rng_state)
        for cuda_state in state.cuda_rng_states or []:
            if cuda_state.dtype != torch.uint8 or cuda_state.ndim != 1 or cuda_state.numel() == 0:
                raise ValueError("Invalid CUDA RNG state tensor.")
    except (TypeError, ValueError, RuntimeError, AttributeError) as error:
        raise ValueError(f"Invalid checkpoint RNG state: {error}") from error


def restore_rng_state(state: CheckpointState) -> None:
    torch.set_rng_state(state.torch_rng_state.cpu())
    np.random.set_state(state.numpy_rng_state)
    if state.python_rng_state is not None:
        random.setstate(state.python_rng_state)
    if state.cuda_rng_states:
        torch.cuda.set_rng_state_all([rng.cpu() for rng in state.cuda_rng_states])
