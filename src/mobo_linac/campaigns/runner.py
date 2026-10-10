"""
Unified MOBO Campaign Runner for mobo_linac.

``MoboCampaignRunner`` resolves the campaign plan (configuration defaults, explicit
options, or a checkpoint on resume) without touching process-global state;
``CampaignLoop`` owns one session's explicit loop state and runs the initial design,
proposal, evaluation and durable commit steps.
"""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import random
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import torch

from mobo_linac import __version__
from mobo_linac.astra.runner import resolve_template_dir
from mobo_linac.astra.workdir import format_eval_id
from mobo_linac.campaign_options import Acquisition, normalize_scalar_weights, validate_campaign_options
from mobo_linac.campaigns.recovery import load_resume_candidate, reconcile_resume
from mobo_linac.campaigns.reporting import finalize_campaign
from mobo_linac.campaigns.state import (
    CampaignOverrides,
    merge_with_checkpoint,
    prepare_resume_state,
    resolve_resume_device,
    restore_rng_state,
)
from mobo_linac.campaigns.storage import commit_checkpoint, persist_model
from mobo_linac.campaigns.strategies import make_strategy
from mobo_linac.config import CampaignSettings, MoboConfig, config_from_dict, load_config
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution.contracts import evaluate_requests
from mobo_linac.execution.parallel import ProcessPoolEvaluator
from mobo_linac.requests import EvaluationRequest
from mobo_linac.io.artifacts import validate_run_completion
from mobo_linac.metrics.exports import RunArtifactWriter
from mobo_linac.io.checkpoint import (
    CampaignSpec,
    CheckpointState,
    MetricState,
    ProgressState,
    ProposalState,
    RngState,
    run_directory,
    save_run_checkpoint,
)
from mobo_linac.utils.durable import atomic_json, atomic_write_text
from mobo_linac.io.journal import EvaluationJournal
from mobo_linac.io.results import get_train_tensors, get_training_observations
from mobo_linac.metrics.hypervolume import HypervolumeTracker, compute_reference_point
from mobo_linac.conventions import reporting_metadata, validate_campaign_compatibility
from mobo_linac.models.artifacts import save_model_artifact
from mobo_linac.result_schema import ResultSchema
from mobo_linac.utils import get_device, get_logger, run_log

logger = get_logger(__name__)


@contextmanager
def campaign_numeric_scope(seed: int):
    """Seed the global generators for a campaign session and use double precision inside it.

    The previous default dtype is restored on exit. Generator states are campaign state:
    after a session they continue from the campaign (as recorded in its checkpoint).
    """
    previous_dtype = torch.get_default_dtype()
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.set_default_dtype(torch.double)
    try:
        yield
    finally:
        torch.set_default_dtype(previous_dtype)


def campaign_figures():
    """Figure registrations exported at finalization: ``(file stem, plot(results, tracker, config, path))``.

    Plotting (Matplotlib) is imported only here, so the campaign engine imports without it.
    """
    from mobo_linac.plotting import (
        plot_constraint_diagnostics,
        plot_hypervolume_progress,
        plot_objective_evolution,
        plot_pareto_front,
    )
    return [
        ("hypervolume_progress", lambda results, tracker, config, path: plot_hypervolume_progress(tracker.to_dataframe(), path)),
        ("pareto_front", lambda results, tracker, config, path: plot_pareto_front(results, path, config=config)),
        ("objective_evolution", lambda results, tracker, config, path: plot_objective_evolution(results, path, config=config)),
        ("constraint_diagnostics", lambda results, tracker, config, path: plot_constraint_diagnostics(results, config, path)),
    ]


class MoboCampaignRunner:
    """Resolve a campaign plan and run it (``run()``); construction has no global side effects."""

    def __init__(
        self,
        config: Optional[Union[str, Path, MoboConfig]] = None,
        run_name: str = "mobo",
        base_results_dir: Union[str, Path] = "results",
        output_dir: Optional[Union[str, Path]] = None,
        num_initial_samples: Optional[int] = None,
        num_batches: Optional[int] = None,
        batch_size: Optional[int] = None,
        num_workers: Optional[int] = None,
        seed: Optional[int] = None,
        acq_type: Optional[str] = None,
        constrained: bool = False,
        optimization_mode: Optional[str] = None,
        scalar_weights: Optional[Sequence[float]] = None,
        export_plots: bool = True,
        export_env_info: bool = True,
        resume: bool = False,
        resume_from: Optional[Union[str, Path]] = None,
        evaluator: Optional[Any] = None,
        reporting_ref_point: Optional[Sequence[float]] = None,
        device: Optional[Union[str, torch.device]] = None,
        total_eval_budget: Optional[int] = None,
    ):
        resuming = bool(resume or resume_from)
        self.overrides = CampaignOverrides(
            num_initial_samples=num_initial_samples, num_batches=num_batches, batch_size=batch_size, seed=seed,
            optimization_mode=optimization_mode, acquisition=acq_type,
            scalar_weights=None if scalar_weights is None else tuple(scalar_weights),
            total_eval_budget=total_eval_budget, num_workers=num_workers,
            constrained=bool(constrained) or optimization_mode == "constrained_mobo")
        self._requested_reporting_ref = reporting_ref_point
        self._requested_device = device
        self._config_explicit = config is not None
        self.device = get_device(device)
        if isinstance(config, (str, Path)) or (config is None and not resuming):
            self.config = load_config(config)
            self.config_path = self.config.source_path
        else:
            self.config = config
            self.config_path = getattr(config, "source_path", None)
        if self.config is not None:
            self.config.validate()
        self._resolve_plan(optimization_mode or "unconstrained_mobo", constrained, resuming)
        self.run_name = run_name
        self.base_results_dir = Path(base_results_dir)
        self.export_plots = export_plots
        self.export_env_info = export_env_info
        self.resume = resume
        self.resume_from = resume_from
        self.custom_evaluator = evaluator
        self._resolve_run_directory(output_dir, run_name, resuming)

    def _resolve_plan(self, optimization_mode: str, constrained: bool, resuming: bool) -> None:
        """Explicit options, else the configuration's campaign defaults (a resume restores saved values)."""
        requested = self.overrides
        defaults = self.config.campaign if self.config is not None else CampaignSettings()
        pick = lambda value, default: default if value is None else value
        self.num_initial_samples = pick(requested.num_initial_samples, defaults.num_initial_samples)
        self.num_batches = pick(requested.num_batches, defaults.num_batches)
        self.batch_size = pick(requested.batch_size, defaults.batch_size)
        self.seed = pick(requested.seed, defaults.seed)
        self.acq_type = pick(requested.acquisition, Acquisition.qLogNEI.value if optimization_mode == "scalarized_bo"
                             else defaults.acquisition)
        self.total_eval_budget = requested.total_eval_budget
        # On resume an omitted mode comes from the checkpoint; infer it from the acquisition for validation.
        validation_mode = optimization_mode
        if resuming and requested.optimization_mode is None and self.acq_type == Acquisition.qLogNEI.value:
            validation_mode = "scalarized_bo"
        validate_campaign_options(num_initial_samples=self.num_initial_samples, num_batches=self.num_batches,
                                  batch_size=self.batch_size, num_workers=requested.num_workers, seed=self.seed,
                                  acq_type=self.acq_type, optimization_mode=validation_mode,
                                  total_eval_budget=self.total_eval_budget)
        if self.total_eval_budget is not None and not resuming:
            required = (self.total_eval_budget - self.num_initial_samples + self.batch_size - 1) // self.batch_size
            if self.num_batches != required:
                raise ValueError("num_batches must cover total_eval_budget exactly (including a final partial batch).")
        if optimization_mode == "scalarized_bo" and constrained:
            raise ValueError("scalarized_bo does not support constrained=True.")
        if optimization_mode == "scalarized_bo":
            self.optimization_mode, self.constrained = "scalarized_bo", False
        elif requested.constrained:
            self.optimization_mode, self.constrained = "constrained_mobo", True
        else:
            self.optimization_mode, self.constrained = "unconstrained_mobo", False
        count = (len(self.config.objectives) if self.config is not None
                 else len(requested.scalar_weights) if requested.scalar_weights is not None else 3)
        self.scalar_weights = normalize_scalar_weights(requested.scalar_weights, count)
        if self._requested_reporting_ref is not None and self.config is not None:
            ref = torch.as_tensor(self._requested_reporting_ref, dtype=torch.double)
            if ref.shape != (count,) or not torch.isfinite(ref).all():
                raise ValueError("Reporting reference must match finite configured objectives.")
        if self.config is not None and self.num_batches > 0 and self.config.model.noise_mode == "measured_fixed":
            model = self.config.model
            if model.fixed_noise_variance is None and (self.constrained or self.optimization_mode == "scalarized_bo"
                                                       or model.objective_noise_variances is None):
                raise ValueError("This measured_fixed campaign requires explicit fixed noise for all fitted channels.")
        self.num_workers = (requested.num_workers if requested.num_workers is not None
                            else self.config.execution.max_workers if self.config is not None else None)

    def _resolve_run_directory(self, output_dir, run_name: str, resuming: bool) -> None:
        if self.resume_from and output_dir is None:
            self.run_dir = run_directory(self.resume_from)
        elif output_dir:
            self.run_dir = Path(output_dir)
        else:
            self.run_dir = self.base_results_dir / f"{run_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # The run identity is the run directory name (evaluation directories live below it).
        self.run_id = self.run_dir.name
        if not resuming:
            self.run_dir.mkdir(parents=True, exist_ok=True)

    def _prepare_resume(self) -> CheckpointState:
        """Validate checkpoints, pending work, and the journal before destination writes."""
        target = self.resume_from or self.run_dir
        checkpoint, completed, pending = load_resume_candidate(target)
        if checkpoint is None:
            raise FileNotFoundError(f"No valid checkpoint found to resume at '{target}'")
        if not self._config_explicit:
            self.config = config_from_dict(checkpoint.config)
            if self.config.simulation.template_dir is None:
                # Archived checkpoints predate the simulation section: take the code inputs
                # (not the scientific settings) from the default configuration.
                self.config.simulation = load_config().simulation
                logger.warning("Checkpoint configuration lacks simulation paths; using the default configuration's.")
        weights = None if self.overrides.scalar_weights is None else list(self.overrides.scalar_weights)
        state = prepare_resume_state(checkpoint, self.config, weights)
        if state.campaign.run_id != self.run_dir.name:
            raise ValueError("Resume must use the original run identity/directory; renamed or forked runs need a separate workflow.")
        self._apply_spec(merge_with_checkpoint(state, self.overrides, self.config))
        self.device = resolve_resume_device(state, self._requested_device)
        self._recovered_completions = reconcile_resume(state, completed, pending, self.config, self.run_dir, weights)
        return state

    def _apply_spec(self, spec: CampaignSpec) -> None:
        self.run_id = spec.run_id
        self.num_initial_samples = spec.num_initial_samples
        self.seed = spec.seed
        self.optimization_mode = spec.optimization_mode
        self.constrained = spec.constrained
        self.acq_type = spec.acquisition_mode
        self.scalar_weights = torch.tensor(spec.scalar_weights, dtype=torch.double)
        self.batch_size = spec.batch_size
        self.total_eval_budget = spec.total_eval_budget
        self.num_workers = spec.num_workers
        self.num_batches = spec.planned_num_batches

    def campaign_spec(self) -> CampaignSpec:
        # Scalarized checkpoints keep their recorded alias of qLogNEI (decode_acquisition maps it back).
        acquisition = "scalarized_qLogNEI" if self.optimization_mode == "scalarized_bo" else self.acq_type
        return CampaignSpec(
            run_id=self.run_id, optimization_mode=self.optimization_mode, acquisition_mode=acquisition,
            constrained=self.constrained, seed=self.seed, scalar_weights=self.scalar_weights.tolist(),
            num_initial_samples=self.num_initial_samples, batch_size=self.batch_size,
            planned_num_batches=self.num_batches, num_workers=self.num_workers,
            total_eval_budget=self.total_eval_budget, device=str(self.device))

    def export_environment_info(self, target_path: Path) -> None:
        """Exports system and dependency version metadata."""
        import botorch
        import gpytorch

        lines = [
            f"mobo_linac version: {__version__}",
            f"Python version: {platform.python_version()}",
            f"PyTorch version: {torch.__version__}",
            f"BoTorch version: {botorch.__version__}",
            f"GPyTorch version: {gpytorch.__version__}",
            f"NumPy version: {np.__version__}",
            f"Pandas version: {pd.__version__}",
            f"ASTRA_BIN: {os.environ.get('ASTRA_BIN', 'Not initialized; see attempt manifests')}",
            f"GENERATOR_BIN: {os.environ.get('GENERATOR_BIN', 'Not initialized; see attempt manifests')}",
            f"Platform: {platform.platform()}",
            f"Timestamp: {datetime.now().isoformat()}",
        ]
        atomic_write_text(target_path, "\n".join(lines) + "\n")

    def build_evaluator(self):
        if self.custom_evaluator is not None:
            return self.custom_evaluator
        return ProcessPoolEvaluator(
            self.config,
            base_results_dir=self.run_dir.parent,  # evaluations live in <base>/<run_id>/ = run_dir
            template_dir=resolve_template_dir(self.config),
            max_workers=self.num_workers,
        )

    def run(self) -> Tuple[List[EvaluationResult], HypervolumeTracker, Path]:
        """Executes the optimization campaign."""
        with campaign_numeric_scope(self.seed):
            resume_state = self._prepare_resume() if (self.resume or self.resume_from) else None
            if resume_state is None and ((self.run_dir / "evaluations_stream.jsonl").exists()
                                         or (self.run_dir / "checkpoints" / "pending_batch.pt").exists()):
                raise ValueError("Existing campaign journal/proposal requires resume, not a fresh run.")
            self.config.validate()
            with run_log(self.run_dir):  # the validated run directory receives the session log
                return CampaignLoop(self, resume_state).run()


def campaign_runner(config: MoboConfig, options: Dict[str, Any], *, optimization_mode: str = "unconstrained_mobo",
                    run_name: str = "mobo", output_dir=None, base_results_dir: Union[str, Path] = "results",
                    scalar_weights=None, constrained: bool = False, total_eval_budget: Optional[int] = None,
                    evaluator=None, device="auto", reporting_ref_point=None, resume: bool = False,
                    export_plots: bool = True) -> MoboCampaignRunner:
    """The one constructor of fresh campaign runners from resolved options.

    ``options`` holds ``num_initial_samples``, ``num_batches``, ``batch_size``, ``num_workers``,
    ``seed`` and ``acquisition`` (see ``campaign_options.resolve_campaign_options``). The CLI
    run modes, the scalarized suite, validation campaigns and benchmarks all use it.
    """
    return MoboCampaignRunner(
        config=config, run_name=run_name, base_results_dir=base_results_dir, output_dir=output_dir,
        num_initial_samples=options["num_initial_samples"], num_batches=options["num_batches"],
        batch_size=options["batch_size"], num_workers=options["num_workers"], seed=options["seed"],
        acq_type=options["acquisition"], optimization_mode=optimization_mode, constrained=constrained,
        scalar_weights=scalar_weights, total_eval_budget=total_eval_budget, evaluator=evaluator, device=device,
        reporting_ref_point=reporting_ref_point, resume=resume, export_plots=export_plots)


class CampaignLoop:
    """One campaign session with explicit loop state (no closures over mutable locals)."""

    def __init__(self, runner: MoboCampaignRunner, resume_state: Optional[CheckpointState]):
        self.runner = runner
        self.config = runner.config
        self.run_dir = runner.run_dir
        self.resume_state = resume_state
        self.schema = ResultSchema.from_config(self.config)
        self.bounds = self.config.get_parameter_bounds_tensor()
        self.pending_path = self.run_dir / "checkpoints" / "pending_batch.pt"
        self.started = time.perf_counter()
        self.elapsed_base = (resume_state.progress.elapsed_wall_time_s or 0.0) if resume_state else 0.0
        self.elapsed_by_id: Dict[str, Optional[float]] = {}
        if resume_state is not None:
            self.elapsed_by_id = dict(zip((r.evaluation_id for r in resume_state.results),
                                          resume_state.progress.evaluation_elapsed_s or [None] * len(resume_state.results)))
        self.results: List[EvaluationResult] = []
        self.evaluation_batches: List[int] = []
        self.initial_design: List[List[float]] = []
        self.tracker: Optional[HypervolumeTracker] = None
        self.reporting_ref_point: Optional[torch.Tensor] = None
        self.proposal_history = deepcopy(resume_state.proposals.proposal_history or []) if resume_state else []
        self.model_artifact = resume_state.model_artifact if resume_state is not None else None
        self.sobol = torch.quasirandom.SobolEngine(dimension=self.bounds.shape[1], scramble=True, seed=runner.seed)
        self.strategy = make_strategy(runner.optimization_mode, config=self.config, device=runner.device,
                                      scalar_weights=runner.scalar_weights, constrained=runner.constrained,
                                      acq_type=runner.acq_type, bounds=self.bounds, persist_model=self.persist_model)

    def elapsed(self) -> float:
        return self.elapsed_base + time.perf_counter() - self.started

    def run(self) -> Tuple[List[EvaluationResult], HypervolumeTracker, Path]:
        runner = self.runner
        self.prepare_outputs()
        self.evaluator = runner.build_evaluator()
        self.journal = EvaluationJournal(self.run_dir, self.config)  # validated and repaired once per session
        start = self.restore() if self.resume_state is not None and self.resume_state.iteration >= 0 else None
        if start is None:
            self.run_initial_design()
            start = 1
        for iteration in range(start, runner.num_batches + 1):
            batch_size = runner.batch_size
            if runner.total_eval_budget is not None:
                batch_size = min(batch_size, runner.total_eval_budget - len(self.results))
                if batch_size <= 0:
                    break
            logger.info(f"--- Iteration {iteration:02d}/{runner.num_batches:02d} ---")
            candidates, metadata = self.propose(iteration, batch_size)
            batch = self.evaluate(candidates, iteration, metadata)
            self.results.extend(batch)
            self.evaluation_batches.extend([iteration] * len(batch))
            self.record_iteration(iteration)
            self.commit(iteration)
        self.export()
        finalize_campaign(self.writer, self.results, self.tracker, self.run_dir, self.config, self.proposal_history,
                          runner.export_plots, self.elapsed(), campaign_figures())
        logger.info(f"=== Campaign Complete: {runner.run_id} ===")
        logger.info(f"Total Evaluations: {len(self.results)}")
        logger.info(f"Output saved in: {self.run_dir.resolve()}")
        return self.results, self.tracker, self.run_dir

    def prepare_outputs(self) -> None:
        """Check reporting compatibility, open the artifact writer and record a fresh run's inputs."""
        runner, resume_state = self.runner, self.resume_state
        requested_ref = runner._requested_reporting_ref
        if requested_ref is not None:
            requested = torch.as_tensor(requested_ref, dtype=torch.double)
            if requested.shape != (len(self.schema.signs),) or not torch.isfinite(requested).all():
                raise ValueError("Reporting reference must match finite configured objectives.")
            saved_ref = resume_state.metrics.reporting_ref_point if resume_state is not None else None
            if saved_ref is not None and requested.tolist() != saved_ref:
                raise ValueError("Incompatible resume reporting reference.")
        saved_meta = self.run_dir / "reporting_metadata.json"
        previous_meta = None
        if resume_state is not None and resume_state.metrics.reporting_ref_point is not None and saved_meta.exists():
            previous_meta = json.loads(saved_meta.read_text())
            validate_campaign_compatibility(previous_meta, reporting_metadata(self.config, resume_state.metrics.reporting_ref_point))
        if resume_state is not None and validate_run_completion(self.run_dir):
            marker = json.loads((self.run_dir / "run_complete.json").read_text())
            self.elapsed_base = max(self.elapsed_base, marker.get("elapsed_wall_time_s") or 0.0)
        self.writer = RunArtifactWriter(self.run_dir, self.config)
        self.writer.invalidate_completion()
        self.reference_policy = "explicit" if requested_ref is not None else "initial_design"
        if previous_meta is not None:
            self.reference_policy = previous_meta.get("reference_policy", self.reference_policy)
        self.timing_scope = ("active_sessions" if resume_state is None or resume_state.progress.elapsed_wall_time_s is not None
                             else "observed_resume_session")
        mode = (f"Scalarized BO (weights={runner.scalar_weights.tolist()})" if runner.optimization_mode == "scalarized_bo"
                else "Constrained MOBO (Feasibility-Aware)" if runner.constrained else "Unconstrained MOBO")
        logger.info(f"=== Starting Optimization Campaign: {runner.run_id} ({mode}) ===")
        logger.info(f"Initial samples: {runner.num_initial_samples}, Batches: {runner.num_batches}, "
                    f"Batch size: {runner.batch_size}, Workers: {runner.num_workers}, "
                    f"Acquisition: {runner.acq_type}, Mode: {runner.optimization_mode}")
        if resume_state is None:
            if runner.export_env_info:
                runner.export_environment_info(self.run_dir / "environment.txt")
            self.config.save_yaml(self.run_dir / "config.yaml")
            self.config.save_json(self.run_dir / "config.json")
            atomic_json(self.run_dir / "config_source.json", {
                "resolved_path": str(runner.config_path) if runner.config_path else None,
                "source": "file" if runner.config_path else "in_memory",
                "template_dir": self.config.simulation.template_dir,
                "executable": self.config.simulation.executable})

    def restore(self) -> int:
        """Adopt a completed checkpoint's loop state; returns the first iteration to run."""
        state = self.resume_state
        self._restore_session(state)
        self.results = state.results
        self.evaluation_batches = list(state.progress.evaluation_batches)
        self.reporting_ref_point = torch.tensor(state.metrics.reporting_ref_point, dtype=torch.double)
        self.tracker = HypervolumeTracker(reporting_ref_point=self.reporting_ref_point, config=self.config)
        self.tracker.history = deepcopy(state.metrics.metric_history)
        logger.info(f"Resuming campaign '{self.runner.run_id}' from iteration {state.iteration + 1} "
                    f"({len(self.results)} existing evaluations)...")
        return state.iteration + 1

    def _restore_session(self, state: CheckpointState) -> None:
        """Journal view, stale pending file, initial design, Sobol position and generator states."""
        if len(self.journal):
            self.journal.write_csv()
        if state.proposals.pending_proposal is None and self.pending_path.exists():
            self.pending_path.unlink()  # Checkpoint won the durable commit before interruption.
        self.initial_design = deepcopy(state.progress.initial_design)
        self.sobol.fast_forward(state.progress.sobol_state["num_generated"])
        restore_rng_state(state)

    def run_initial_design(self) -> None:
        """Evaluate the Sobol initial design (or recover its pending batch) and fix the reporting reference."""
        runner = self.runner
        logger.info(f"--- Step 0: Initial Design (Sobol Sampling: {runner.num_initial_samples} samples) ---")
        metadata = None
        if self.resume_state is None:
            start = self.sobol.num_generated
            samples = self.sobol.draw(runner.num_initial_samples).to(dtype=torch.double)
            lower, upper = self.bounds[0], self.bounds[1]
            self.initial_design = (lower + (upper - lower) * samples).tolist()
            metadata = {"method": "initial_sobol", "device": "cpu", "attempts": [], "fallback_reason": None,
                        "sobol": {"seed": runner.seed, "start": start, "end": self.sobol.num_generated}}
        else:
            self._restore_session(self.resume_state)
        self.results = self.evaluate(self.initial_design, 0, metadata)
        self.evaluation_batches = [0] * len(self.results)
        _, train_Y, feasible = get_train_tensors(self.results, exclude_invalid=True, config=self.config)
        self.reporting_ref_point = compute_reference_point(
            train_Y, offset_ratio=self.config.execution.reporting_reference_offset,
            default_ref_point=runner._requested_reporting_ref, config=self.config)
        self.tracker = HypervolumeTracker(reporting_ref_point=self.reporting_ref_point, config=self.config)
        self.record_iteration(0)
        self.commit(0)

    def propose(self, iteration: int, batch_size: int):
        """The durable pending batch on recovery, Sobol while data are scarce, else the strategy's proposal."""
        pending = self.resume_state.proposals.pending_proposal if self.resume_state is not None else None
        if pending is not None and pending["batch_idx"] == iteration:
            return deepcopy(pending["candidates"]), None
        training = get_training_observations(self.results, exclude_invalid=True,
                                             require_diagnostics=self.runner.constrained, config=self.config)
        if training.train_X.shape[0] < 2:
            start = self.sobol.num_generated
            samples = self.sobol.draw(batch_size).to(dtype=torch.double)
            lower, upper = self.bounds[0], self.bounds[1]
            return (lower + (upper - lower) * samples).tolist(), {
                "method": "low_data_sobol", "device": "cpu", "attempts": [],
                "fallback_reason": "fewer than two observed training rows",
                "sobol": {"seed": self.runner.seed, "start": start, "end": self.sobol.num_generated}}
        return self.strategy.propose(training, iteration, batch_size, self.sobol)

    def evaluate(self, candidates: List[List[float]], batch_idx: int, metadata=None) -> List[EvaluationResult]:
        """Durably propose (or recover) a batch, evaluate missing candidates and journal each completion."""
        active = self.resume_state.proposals.pending_proposal if self.resume_state is not None else None
        if active is not None and active["batch_idx"] == batch_idx:
            proposal = active
            if candidates != proposal["candidates"]:
                raise ValueError("Recovery candidates differ from durable pending proposal.")
            completions = dict(self.runner._recovered_completions)
        else:
            metadata = deepcopy(metadata) if metadata is not None else {
                "method": "external", "device": str(self.runner.device), "attempts": [], "fallback_reason": None}
            proposal = {"version": "1.0", "batch_idx": batch_idx, "candidates": candidates,
                        "evaluation_ids": [format_eval_id(len(self.results) + i + 1) for i in range(len(candidates))],
                        "metadata": metadata}
            self.proposal_history.append({"batch_idx": batch_idx, "metadata": metadata})
            self.commit(batch_idx - 1, pending=proposal)
            completions = {}
        identities = proposal["evaluation_ids"]
        missing = [i for i, identity in enumerate(identities) if identity not in completions]

        def on_complete(completion):
            result = completion.result
            self.journal.append(result, batch_idx=batch_idx, candidate_idx=identities.index(result.evaluation_id))
            completions[result.evaluation_id] = result
            self.elapsed_by_id[result.evaluation_id] = self.elapsed()

        if missing:
            evaluate_requests(self.evaluator, [EvaluationRequest(identities[i], candidates[i]) for i in missing],
                              run_id=self.runner.run_id, config=self.config, on_complete=on_complete)
        if set(completions) != set(identities):
            raise ValueError("Evaluator did not return every submitted candidate completion.")
        self.journal.write_csv()  # derived CSV view refreshed once per batch
        return [completions[identity] for identity in identities]

    def record_iteration(self, iteration: int) -> None:
        """Track fixed-reference hypervolume for the iteration and export the run artifacts."""
        train_X, train_Y, feasible = get_train_tensors(self.results, exclude_invalid=True, config=self.config)
        record = self.tracker.track_iteration(iteration, train_Y, feasible)
        label = "(Initial) " if iteration == 0 else ""
        logger.info(f"Iter {iteration:02d}/{self.runner.num_batches:02d} {label}| Evaluations: {len(self.results):02d} | "
                    f"Valid: {train_X.shape[0]:02d} | Feasible: {record['num_feasible_points']:02d} | "
                    f"HV: {record['feasible_hypervolume']:.6e}")
        self.export()

    def export(self) -> None:
        self.writer.write(self.results, self.tracker,
                          elapsed_wall_times=[self.elapsed_by_id.get(r.evaluation_id) for r in self.results],
                          elapsed_wall_time_s=self.elapsed(), reference_policy=self.reference_policy,
                          timing_scope=self.timing_scope)

    def persist_model(self, model, iteration: int, training, pipeline: bool = False) -> None:
        runner = self.runner
        metadata = {"run_id": runner.run_id, "proposal_iteration": iteration,
                    "optimization_mode": runner.optimization_mode,
                    "objective_schema": [vars(obj) for obj in self.config.objectives],
                    "scalar_weights": runner.scalar_weights.tolist(), "reporting_scales": list(self.schema.scales)}
        self.model_artifact = persist_model(self.run_dir, model, iteration, training.evaluation_ids,
                                            metadata, pipeline=pipeline, save_model=save_model_artifact)

    def snapshot(self, iteration: int, pending=None) -> CheckpointState:
        tracker = self.tracker
        return CheckpointState(
            iteration=iteration, results=self.results, config=asdict(self.config),
            campaign=self.runner.campaign_spec(), rng=RngState.capture(self.runner.device),
            progress=ProgressState(
                initial_design=self.initial_design,
                sobol_state={"seed": self.runner.seed, "dimension": self.bounds.shape[1],
                             "num_generated": self.sobol.num_generated},
                evaluation_batches=self.evaluation_batches, elapsed_wall_time_s=self.elapsed(),
                evaluation_elapsed_s=[self.elapsed_by_id.get(r.evaluation_id) for r in self.results]),
            metrics=MetricState(
                reporting_ref_point=self.reporting_ref_point.tolist() if self.reporting_ref_point is not None else None,
                reporting_scales=list(self.schema.scales),
                metric_history=deepcopy(tracker.history) if tracker is not None else [],
                hypervolumes=[r["feasible_hypervolume"] for r in tracker.history] if tracker is not None else []),
            proposals=ProposalState(proposal_history=deepcopy(self.proposal_history), pending_proposal=pending),
            model_artifact=self.model_artifact,
            migration_notes=self.resume_state.migration_notes if self.resume_state is not None else [],
        )

    def commit(self, iteration: int, pending=None) -> None:
        """Durably write the snapshot (the pending batch, or the completed iteration)."""
        state = self.snapshot(iteration, pending)
        path = self.pending_path if pending is not None else self.run_dir / "checkpoints" / f"checkpoint_iter_{iteration:02d}.pt"
        commit_checkpoint(self.run_dir, self.proposal_history, self.pending_path, pending,
                          save_checkpoint=lambda: save_run_checkpoint(path, state))
