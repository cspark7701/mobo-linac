"""
Unified MOBO Campaign Runner for mobo_linac.

Consolidates optimization loop execution across CLI commands, scripts,
and interactive notebooks.
"""

from copy import deepcopy
from datetime import datetime
import os
import json
from pathlib import Path
import platform
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import torch

from botorch.acquisition.logei import qLogNoisyExpectedImprovement
from mobo_linac import __version__
from mobo_linac.acquisition.mobo import (
    build_acquisition_function,
    generate_next_candidates,
)
from mobo_linac.config import CampaignSettings, MoboConfig, config_from_dict, load_config, validate_campaign_options, normalize_scalar_weights
from mobo_linac.campaigns.state import prepare_resume_state, restore_rng_state
from mobo_linac.campaigns.recovery import load_resume_candidate, reconcile_resume
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution.parallel import BatchEvaluator
from mobo_linac.execution.contracts import evaluate_requests
from mobo_linac.execution.requests import EvaluationRequest
from mobo_linac.campaigns.strategies import ProposalContext, propose_scalarized, propose_multiobjective
from mobo_linac.campaigns.storage import persist_model, commit_checkpoint
from mobo_linac.campaigns.reporting import finalize_campaign
from mobo_linac.models.artifacts import save_model_artifact
from mobo_linac.models.gp import build_scalarized_gp_model, fit_gp_models
from mobo_linac.io.journal import repair_journal_tail, write_streaming_csv
from mobo_linac.io.results import (
    CheckpointState,
    append_streaming_evaluation,
    get_training_observations,
    get_train_tensors,
    save_run_checkpoint,
)
from mobo_linac.metrics.hypervolume import (
    HypervolumeTracker,
    compute_reference_point,
)
from mobo_linac.result_schema import ResultSchema
from mobo_linac.io.artifacts import RunArtifactWriter, validate_run_completion, atomic_json
from mobo_linac.metrics.reporting import reporting_metadata, validate_campaign_compatibility
import time
from mobo_linac.models.pipeline import SurrogatePipeline
from mobo_linac.utils import get_device, get_logger

logger = get_logger(__name__)

from mobo_linac.plotting import (
    plot_constraint_diagnostics,
    plot_hypervolume_progress,
    plot_objective_evolution,
    plot_pareto_front,
)


class MoboCampaignRunner:
    """
    Unified manager for executing Bayesian Optimization campaigns.
    """

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
        self._requested_initial_samples = num_initial_samples
        self._requested_num_batches = num_batches
        self._requested_batch_size = batch_size
        self._requested_seed = seed
        self._requested_mode = optimization_mode
        self._requested_reporting_ref = reporting_ref_point
        self._requested_acquisition = acq_type
        self._requested_weights = scalar_weights
        self._requested_budget = total_eval_budget
        self._requested_device = device
        self._requested_num_workers = num_workers
        self._config_explicit = config is not None
        optimization_mode = optimization_mode or "unconstrained_mobo"
        self.device = get_device(device)

        if isinstance(config, (str, Path)) or (config is None and not (resume or resume_from)):
            self.config = load_config(config)
            self.config_path = self.config.resolved_path
        else:
            self.config = config
            self.config_path = getattr(config, "resolved_path", None)
        # Omitted options use the configuration's campaign defaults (resume restores saved values).
        defaults = self.config.campaign if self.config is not None else CampaignSettings()
        num_initial_samples = defaults.num_initial_samples if num_initial_samples is None else num_initial_samples
        num_batches = defaults.num_batches if num_batches is None else num_batches
        batch_size = defaults.batch_size if batch_size is None else batch_size
        seed = defaults.seed if seed is None else seed
        if acq_type is None:
            acq_type = "qLogNEI" if optimization_mode == "scalarized_bo" else defaults.acquisition
        if self.config is not None:
            self.config.validate()
        validate_campaign_options(num_initial_samples=num_initial_samples, num_batches=num_batches,
                                  batch_size=batch_size, num_workers=num_workers, seed=seed,
                                  acq_type=acq_type, optimization_mode="scalarized_bo" if (resume or resume_from) and acq_type == "qLogNEI" else optimization_mode,
                                  total_eval_budget=total_eval_budget)

        self.run_name = run_name
        self.base_results_dir = Path(base_results_dir)
        self.num_initial_samples = num_initial_samples
        if total_eval_budget is not None and not (resume or resume_from):
            if batch_size < 1 or num_initial_samples < 1 or total_eval_budget <= num_initial_samples:
                raise ValueError("total_eval_budget must exceed positive initial samples, with batch_size >= 1.")
            required_batches = (total_eval_budget - num_initial_samples + batch_size - 1) // batch_size
            if num_batches != required_batches:
                raise ValueError("num_batches must cover total_eval_budget exactly (including a final partial batch).")
        self.total_eval_budget = total_eval_budget
        self.num_batches = num_batches
        self.batch_size = batch_size
        self.seed = seed
        self.acq_type = acq_type
        self.export_plots = export_plots
        self.export_env_info = export_env_info
        self.resume = resume
        self.resume_from = resume_from
        self.custom_evaluator = evaluator

        if optimization_mode == "scalarized_bo" and constrained:
            raise ValueError("scalarized_bo does not support constrained=True.")

        # Normalize optimization mode and constrained flag
        if optimization_mode == "constrained_mobo" or (constrained and optimization_mode == "unconstrained_mobo"):
            self.optimization_mode = "constrained_mobo"
            self.constrained = True
        elif optimization_mode == "scalarized_bo":
            self.optimization_mode = "scalarized_bo"
            self.constrained = False
        else:
            self.optimization_mode = "unconstrained_mobo"
            self.constrained = False

        objective_count = len(self.config.objectives) if self.config is not None else (len(scalar_weights) if scalar_weights is not None else 3)
        self.scalar_weights = normalize_scalar_weights(scalar_weights, objective_count)
        if self._requested_reporting_ref is not None and self.config is not None:
            ref = torch.as_tensor(self._requested_reporting_ref, dtype=torch.double)
            if ref.shape != (objective_count,) or not torch.isfinite(ref).all():
                raise ValueError("Reporting reference must match finite configured objectives.")
        if self.config is not None and num_batches > 0 and self.config.model.noise_mode == "measured_fixed":
            model = self.config.model
            if model.fixed_noise_variance is None and (self.constrained or self.optimization_mode == "scalarized_bo" or model.objective_noise_variances is None):
                raise ValueError("This measured_fixed campaign requires explicit fixed noise for all fitted channels.")

        if resume_from and output_dir is None:
            source = Path(resume_from)
            if source.is_file():
                source = source.parent.parent if source.parent.name in ("checkpoints", "gp_checkpoint") else source.parent
            self.run_dir = source
            self.run_id = source.name
        elif output_dir:
            self.run_dir = Path(output_dir)
            self.run_id = self.run_dir.name
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.run_id = f"{run_name}_{timestamp}"
            self.run_dir = self.base_results_dir / self.run_id

        if not (resume or resume_from):
            self.run_dir.mkdir(parents=True, exist_ok=True)

        if num_workers is not None:
            self.num_workers = num_workers
        else:
            self.num_workers = self.config.execution.max_workers if self.config is not None else None

        torch.manual_seed(self.seed)
        np.random.seed(self.seed)
        random.seed(self.seed)
        torch.set_default_dtype(torch.double)

    def _prepare_resume(self) -> "CheckpointState":
        """Validate checkpoints, pending work, and the journal before destination writes."""
        target = self.resume_from or self.run_dir
        checkpoint, completed, pending = load_resume_candidate(target)
        if checkpoint is None:
            raise FileNotFoundError(f"No valid checkpoint found to resume at '{target}'")
        if not self._config_explicit:
            self.config = config_from_dict(checkpoint.config)
        state = prepare_resume_state(checkpoint, self.config, self._requested_weights)
        if state.run_id != self.run_dir.name:
            raise ValueError("Resume must use the original run identity/directory; renamed or forked runs need a separate workflow.")
        if self._requested_initial_samples is not None and self._requested_initial_samples != state.num_initial_samples:
            raise ValueError("Incompatible resume initial sample count.")
        if self._requested_seed is not None and self._requested_seed != state.seed:
            raise ValueError("Incompatible resume seed.")
        if self.constrained and not state.constrained:
            raise ValueError("Incompatible resume constrained flag.")
        if self._requested_mode is not None and self._requested_mode != state.optimization_mode:
            raise ValueError("Incompatible resume optimization mode.")
        if self._requested_acquisition is not None:
            saved_acquisition = "qLogNEI" if state.optimization_mode == "scalarized_bo" else state.acquisition_mode
            if self._requested_acquisition not in (saved_acquisition, state.acquisition_mode):
                raise ValueError("Incompatible resume acquisition mode.")
        if state.version == "2.0" and self._requested_weights is not None:
            weights = normalize_scalar_weights(self._requested_weights, len(state.scalar_weights))
            if weights.shape != (len(state.scalar_weights),) or not torch.allclose(weights, torch.tensor(state.scalar_weights, dtype=torch.double)):
                raise ValueError("Incompatible resume scalar weights.")
        if self._requested_budget is not None and self._requested_budget != state.total_eval_budget:
            raise ValueError("Incompatible resume total evaluation budget.")
        self.run_id = state.run_id
        self.num_initial_samples = state.num_initial_samples
        self.seed = state.seed
        self.optimization_mode = state.optimization_mode
        self.constrained = state.constrained
        self.acq_type = "qLogNEI" if state.optimization_mode == "scalarized_bo" else state.acquisition_mode
        self.scalar_weights = torch.tensor(state.scalar_weights, dtype=torch.double)
        self.batch_size = state.batch_size if self._requested_batch_size is None else self._requested_batch_size
        if type(self.batch_size) is not int or self.batch_size < 1:
            raise ValueError("Resume batch size must be a positive integer.")
        self.total_eval_budget = state.total_eval_budget
        if self._requested_num_workers is None:
            self.num_workers = state.num_workers or self.config.execution.max_workers
        if type(self.num_workers) is not int or self.num_workers < 1:
            raise ValueError("Resume worker count must be a positive integer.")
        planned_batches = state.planned_num_batches
        if self._requested_num_batches is None and planned_batches is None:
            raise ValueError("Legacy checkpoint omitted the planned iteration count; specify num_batches/--n-iterations.")
        self.num_batches = planned_batches if self._requested_num_batches is None else self._requested_num_batches
        if self.total_eval_budget is not None:
            remaining = self.total_eval_budget - len(state.results)
            if state.pending_proposal is not None:
                remaining -= len(state.pending_proposal["candidates"])
                required = state.iteration + 1 + (remaining + self.batch_size - 1) // self.batch_size
            else:
                required = state.iteration + (remaining + self.batch_size - 1) // self.batch_size
            if self._requested_num_batches is None:
                self.num_batches = required
            elif self.num_batches != required:
                raise ValueError("Resume iteration count must consume the saved total budget with the selected batch size.")
        if type(self.num_batches) is not int:
            raise ValueError("Resume iteration target must be an integer.")
        minimum_iteration = state.pending_proposal["batch_idx"] if state.pending_proposal else state.iteration
        if self.num_batches < minimum_iteration:
            raise ValueError("Resume iteration target is earlier than the completed checkpoint.")
        requested_device = self._requested_device
        def canonical_device(device, saved=False):
            value = torch.device(device)
            if value.type == "cuda":
                index = value.index
                if index is None:
                    index = 0 if saved or not torch.cuda.is_available() else torch.cuda.current_device()
                return (value.type, index)
            return (value.type, None)
        saved_type, saved_index = canonical_device(state.device, saved=True)
        saved_device = torch.device(saved_type, saved_index)
        automatic = requested_device is None or str(requested_device).strip().lower() in ("auto", "")
        requested = saved_device if automatic else str(requested_device).strip().lower()
        if canonical_device(requested) != (saved_type, saved_index):
            raise ValueError("Resume device differs from checkpoint; deterministic CPU/GPU migration is unsupported.")
        self.device = get_device(requested, allow_cpu_fallback=False)
        if self.device.type == "cuda":
            if not torch.cuda.is_available() or len(state.cuda_rng_states or []) != torch.cuda.device_count():
                raise ValueError("Checkpoint CUDA RNG topology is unavailable or incompatible.")
            if canonical_device(self.device)[1] >= torch.cuda.device_count():
                raise ValueError("Checkpoint CUDA device is unavailable.")
            try:
                for index, rng in enumerate(state.cuda_rng_states):
                    torch.Generator(device=f"cuda:{index}").set_state(rng.cpu())
            except RuntimeError as error:
                raise ValueError(f"Invalid checkpoint CUDA RNG state: {error}") from error
        self._recovered_completions = reconcile_resume(
            state, completed, pending, self.config, self.run_dir, self._requested_weights
        )
        return state

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
        target_path.write_text("\n".join(lines) + "\n")

    def run(self) -> Tuple[List[EvaluationResult], HypervolumeTracker, Path]:
        """
        Executes the optimization campaign.
        """
        resume_state = self._prepare_resume() if (self.resume or self.resume_from) else None
        if resume_state is None and ((self.run_dir / "evaluations_stream.jsonl").exists() or (self.run_dir / "checkpoints" / "pending_batch.pt").exists()):
            raise ValueError("Existing campaign journal/proposal requires resume, not a fresh run.")
        self.config.validate()
        schema = ResultSchema.from_config(self.config)
        if self._requested_reporting_ref is not None:
            requested_ref = torch.as_tensor(self._requested_reporting_ref, dtype=torch.double)
            if requested_ref.shape != (len(schema.signs),) or not torch.isfinite(requested_ref).all():
                raise ValueError("Reporting reference must match finite configured objectives.")
            if resume_state is not None and resume_state.reporting_ref_point is not None and requested_ref.tolist() != resume_state.reporting_ref_point:
                raise ValueError("Incompatible resume reporting reference.")
        started = time.perf_counter()
        elapsed_base = (resume_state.elapsed_wall_time_s or 0.0) if resume_state else 0.0
        elapsed = lambda: elapsed_base + time.perf_counter() - started
        elapsed_by_id = {}
        if resume_state is not None:
            elapsed_by_id = {r.evaluation_id: value for r, value in zip(resume_state.results, resume_state.evaluation_elapsed_s or [None] * len(resume_state.results))}
        saved_meta = self.run_dir / "reporting_metadata.json"
        if resume_state is not None and resume_state.reporting_ref_point is not None and saved_meta.exists():
            previous_meta = json.loads(saved_meta.read_text())
            validate_campaign_compatibility(previous_meta, reporting_metadata(self.config, resume_state.reporting_ref_point))
        else:
            previous_meta = None
        if resume_state is not None and validate_run_completion(self.run_dir):
            marker = json.loads((self.run_dir / "run_complete.json").read_text())
            elapsed_base = max(elapsed_base, marker.get("elapsed_wall_time_s") or 0.0)
        writer = RunArtifactWriter(self.run_dir, self.config)
        writer.invalidate_completion()
        reference_policy = "explicit" if self._requested_reporting_ref is not None else "initial_design"
        if previous_meta is not None:
            reference_policy = previous_meta.get("reference_policy", reference_policy)
        timing_scope = "active_sessions" if resume_state is None or resume_state.elapsed_wall_time_s is not None else "observed_resume_session"
        if self.optimization_mode == "scalarized_bo":
            mode_str = f"Scalarized BO (weights={self.scalar_weights.tolist()})"
        elif self.constrained:
            mode_str = "Constrained MOBO (Feasibility-Aware)"
        else:
            mode_str = "Unconstrained MOBO"

        logger.info(f"\n=== Starting Optimization Campaign: {self.run_id} ({mode_str}) ===")
        logger.info(
            f"Initial samples: {self.num_initial_samples}, "
            f"Batches: {self.num_batches}, Batch size: {self.batch_size}, "
            f"Workers: {self.num_workers}, Acquisition: {self.acq_type}, "
            f"Mode: {self.optimization_mode}\n"
        )

        if resume_state is None:
            if self.export_env_info:
                self.export_environment_info(self.run_dir / "environment.txt")
            self.config.save_yaml(self.run_dir / "config.yaml")
            self.config.save_json(self.run_dir / "config.json")
            (self.run_dir / "config_source.json").write_text(json.dumps({"resolved_path": str(self.config_path) if self.config_path else None, "source": "file" if self.config_path else "in_memory"}, indent=2))

        bounds = self.config.get_parameter_bounds_tensor()

        if self.custom_evaluator is not None:
            evaluator = self.custom_evaluator
        else:
            evaluator = BatchEvaluator(
                base_results_dir=self.run_dir.parent,
                template_dir=".",
                max_workers=self.num_workers,
                timeout=self.config.execution.timeout_sec,
                retries=self.config.execution.retries,
                clean_on_success=self.config.execution.clean_on_success,
                config=self.config,
            )

        sobol_engine = torch.quasirandom.SobolEngine(dimension=bounds.shape[1], scramble=True, seed=self.seed)

        proposal_history = deepcopy(resume_state.proposal_history or []) if resume_state is not None else []

        def _evaluate_with_streaming(
            cand_list: List[List[float]],
            batch_idx: int,
            proposal_metadata=None,
        ) -> List[EvaluationResult]:
            active = resume_state.pending_proposal if resume_state is not None else None
            if active is not None and active["batch_idx"] == batch_idx:
                proposal = active
                if cand_list != proposal["candidates"]:
                    raise ValueError("Recovery candidates differ from durable pending proposal.")
                completions = dict(self._recovered_completions)
            else:
                ids = [f"eval_{len(results) + i + 1:06d}" for i in range(len(cand_list))]
                metadata = deepcopy(proposal_metadata) if proposal_metadata is not None else {
                    "method": "external", "device": str(self.device), "attempts": [], "fallback_reason": None}
                proposal = {"version": "1.0", "batch_idx": batch_idx,
                            "candidates": cand_list, "evaluation_ids": ids, "metadata": metadata}
                proposal_history.append({"batch_idx": batch_idx, "metadata": metadata})
                _persist_checkpoint(batch_idx - 1, pending=proposal)
                completions = {}
            identities = proposal["evaluation_ids"]
            missing_positions = [i for i, identity in enumerate(identities) if identity not in completions]
            missing_ids = [identities[i] for i in missing_positions]
            missing_candidates = [cand_list[i] for i in missing_positions]
            def _stream_callback(completion):
                eval_res = completion.result
                identity = eval_res.evaluation_id
                position = identities.index(identity)
                append_streaming_evaluation(self.run_dir, eval_res, batch_idx=batch_idx,
                                            candidate_idx=position, config=self.config)
                completions[identity] = eval_res
                elapsed_by_id[identity] = elapsed()

            if missing_ids:
                evaluate_requests(evaluator,
                    [EvaluationRequest(identity, candidate) for identity, candidate
                     in zip(missing_ids, missing_candidates)], run_id=self.run_id,
                    config=self.config, on_complete=_stream_callback)
            if set(completions) != set(identities):
                raise ValueError("Evaluator did not return every submitted candidate completion.")
            return [completions[identity] for identity in identities]

        start_iteration = 1
        results: List[EvaluationResult] = []
        evaluation_batches: List[int] = []
        initial_candidates: List[List[float]] = []

        tracker = None
        reporting_ref_point = None
        pending_path = self.run_dir / "checkpoints" / "pending_batch.pt"
        model_artifact = resume_state.model_artifact if resume_state is not None else None

        def _persist_model(model, iteration, training, pipeline=False):
            nonlocal model_artifact
            metadata = {"run_id": self.run_id, "proposal_iteration": iteration,
                        "optimization_mode": self.optimization_mode,
                        "objective_schema": [vars(obj) for obj in self.config.objectives],
                        "scalar_weights": self.scalar_weights.tolist(), "reporting_scales": list(schema.scales)}
            model_artifact = persist_model(self.run_dir, model, iteration, training.evaluation_ids,
                                           metadata, pipeline=pipeline, save_model=save_model_artifact)


        def _persist_checkpoint(iteration: int, pending=None):
            checkpoint_mode = "scalarized_qLogNEI" if self.optimization_mode == "scalarized_bo" else self.acq_type
            commit_checkpoint(self.run_dir, proposal_history, pending_path, pending,
                save_checkpoint=save_run_checkpoint,
                iteration=iteration,
                results=results,
                hypervolumes=[record["feasible_hypervolume"] for record in tracker.history] if tracker is not None else [],
                checkpoint_path=pending_path if pending is not None else self.run_dir / "checkpoints" / f"checkpoint_iter_{iteration:02d}.pt",
                acquisition_mode=checkpoint_mode,
                config=self.config,
                reporting_ref_point=reporting_ref_point,
                seed=self.seed,
                batch_size=self.batch_size,
                constrained=self.constrained,
                campaign_state={
                    "proposal_history": deepcopy(proposal_history),
                    "model_artifact": model_artifact,
                    "run_id": self.run_id,
                    "optimization_mode": self.optimization_mode,
                    "scalar_weights": self.scalar_weights.tolist(),
                    "num_initial_samples": self.num_initial_samples,
                    "initial_design": initial_candidates,
                    "sobol_state": {"seed": self.seed, "dimension": bounds.shape[1], "num_generated": sobol_engine.num_generated},
                    "evaluation_batches": evaluation_batches,
                    "metric_history": deepcopy(tracker.history) if tracker is not None else [],
                    "pending_proposal": pending,
                    "reporting_scales": list(schema.scales),
                    "elapsed_wall_time_s": elapsed(),
                    "evaluation_elapsed_s": [elapsed_by_id.get(r.evaluation_id) for r in results],
                    "planned_num_batches": self.num_batches,
                    "num_workers": self.num_workers,
                    "total_eval_budget": self.total_eval_budget,
                    "device": str(self.device),
                    "cuda_rng_states": torch.cuda.get_rng_state_all() if self.device.type == "cuda" else [],
                    "migration_notes": resume_state.migration_notes if resume_state is not None else [],
                },
            )


        if resume_state is not None:
            repair_journal_tail(self.run_dir)
            if (self.run_dir / "evaluations_stream.jsonl").exists():
                write_streaming_csv(self.run_dir, config=self.config)
            if resume_state.pending_proposal is None and pending_path.exists():
                pending_path.unlink()  # Checkpoint won the durable commit before interruption.
            initial_candidates = deepcopy(resume_state.initial_design)
            sobol_engine.fast_forward(resume_state.sobol_state["num_generated"])
            restore_rng_state(resume_state)

        if resume_state is not None and resume_state.iteration >= 0:
            results = resume_state.results
            evaluation_batches = list(resume_state.evaluation_batches)
            initial_candidates = deepcopy(resume_state.initial_design)
            start_iteration = resume_state.iteration + 1
            reporting_ref_point = torch.tensor(resume_state.reporting_ref_point, dtype=torch.double)
            tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point, config=self.config)
            tracker.history = deepcopy(resume_state.metric_history)
            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True, config=self.config)
            logger.info(f"\nResuming campaign '{self.run_id}' from iteration {start_iteration} ({len(results)} existing evaluations)...\n")
        else:
            logger.info(f"--- Step 0: Initial Design (Sobol Sampling: {self.num_initial_samples} samples) ---")
            if resume_state is None:
                initial_sobol_start = sobol_engine.num_generated
                sobol_samples = sobol_engine.draw(self.num_initial_samples).to(dtype=torch.double)
                lower_b, upper_b = bounds[0], bounds[1]
                initial_candidates = (lower_b + (upper_b - lower_b) * sobol_samples).tolist()

            initial_metadata = {"method": "initial_sobol", "device": "cpu", "attempts": [], "fallback_reason": None,
                                "sobol": {"seed": self.seed, "start": initial_sobol_start, "end": sobol_engine.num_generated}} if resume_state is None else None
            results = _evaluate_with_streaming(initial_candidates, batch_idx=0, proposal_metadata=initial_metadata)
            evaluation_batches = [0] * len(results)

            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True, config=self.config)

            reporting_ref_point = compute_reference_point(
                train_Y, offset_ratio=self.config.execution.reporting_reference_offset,
                default_ref_point=self._requested_reporting_ref, config=self.config)
            tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point, config=self.config)

            hv_init = tracker.track_iteration(0, train_Y, train_feas_mask)
            logger.info(
                f"Iter 00/{self.num_batches:02d} (Initial) | "
                f"Evaluations: {len(results):02d} | "
                f"Valid: {train_X.shape[0]:02d} | "
                f"Feasible: {hv_init['num_feasible_points']:02d} | "
                f"HV: {hv_init['feasible_hypervolume']:.6e}\n"
            )

            writer.write(results, tracker, elapsed_wall_times=[elapsed_by_id.get(r.evaluation_id) for r in results], elapsed_wall_time_s=elapsed(), reference_policy=reference_policy, timing_scope=timing_scope)

            _persist_checkpoint(0)

        lower_b, upper_b = bounds[0], bounds[1]

        for iteration in range(start_iteration, self.num_batches + 1):
            proposal_batch_size = self.batch_size
            if self.total_eval_budget is not None:
                proposal_batch_size = min(proposal_batch_size, self.total_eval_budget - len(results))
                if proposal_batch_size <= 0:
                    break
            logger.info(f"--- Iteration {iteration:02d}/{self.num_batches:02d} ---")
            training = get_training_observations(results, exclude_invalid=True, require_diagnostics=self.constrained, config=self.config)
            train_X, train_Y, train_feas_mask = training.train_X, training.train_Y, training.feasible

            proposal_metadata = None
            if (resume_state is not None and resume_state.pending_proposal is not None
                    and resume_state.pending_proposal["batch_idx"] == iteration):
                next_cand_list = deepcopy(resume_state.pending_proposal["candidates"])
            elif train_X.shape[0] < 2:
                sobol_start = sobol_engine.num_generated
                new_sobol = sobol_engine.draw(proposal_batch_size).to(dtype=torch.double)
                next_cand_list = (lower_b + (upper_b - lower_b) * new_sobol).tolist()
                proposal_metadata = {"method": "low_data_sobol", "device": "cpu", "attempts": [],
                                     "fallback_reason": "fewer than two observed training rows",
                                     "sobol": {"seed": self.seed, "start": sobol_start, "end": sobol_engine.num_generated}}
            else:
                context = ProposalContext(self.config, self.device, self.scalar_weights,
                                          self.constrained, self.acq_type)
                strategy = propose_scalarized if self.optimization_mode == "scalarized_bo" else propose_multiobjective
                next_cand_list, proposal_metadata = strategy(
                    context, training, bounds, schema, iteration, proposal_batch_size,
                    sobol_engine, _persist_model,
                    {"build_scalarized_gp_model": build_scalarized_gp_model,
                     "fit_gp_models": fit_gp_models,
                     "qLogNoisyExpectedImprovement": qLogNoisyExpectedImprovement,
                     "generate_next_candidates": generate_next_candidates,
                     "SurrogatePipeline": SurrogatePipeline,
                     "build_acquisition_function": build_acquisition_function})


            batch_results = _evaluate_with_streaming(next_cand_list, batch_idx=iteration, proposal_metadata=proposal_metadata)
            results.extend(batch_results)
            evaluation_batches.extend([iteration] * len(batch_results))

            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True, config=self.config)
            hv_record = tracker.track_iteration(iteration, train_Y, train_feas_mask)

            logger.info(
                f"Iter {iteration:02d}/{self.num_batches:02d} | "
                f"Evaluations: {len(results):02d} | "
                f"Valid: {train_X.shape[0]:02d} | "
                f"Feasible: {hv_record['num_feasible_points']:02d} | "
                f"HV: {hv_record['feasible_hypervolume']:.6e}\n"
            )

            writer.write(results, tracker, elapsed_wall_times=[elapsed_by_id.get(r.evaluation_id) for r in results], elapsed_wall_time_s=elapsed(), reference_policy=reference_policy, timing_scope=timing_scope)

            _persist_checkpoint(iteration)


        writer.write(results, tracker, elapsed_wall_times=[elapsed_by_id.get(r.evaluation_id) for r in results],
                     elapsed_wall_time_s=elapsed(), reference_policy=reference_policy, timing_scope=timing_scope)

        finalize_campaign(writer, results, tracker, self.run_dir, self.config, proposal_history,
                          self.export_plots, elapsed(),
                          (plot_hypervolume_progress, plot_pareto_front,
                           plot_objective_evolution, plot_constraint_diagnostics))
        logger.info(f"=== Campaign Complete: {self.run_id} ===")
        logger.info(f"Total Evaluations: {len(results)}")
        logger.info(f"Output saved in: {self.run_dir.resolve()}\n")

        return results, tracker, self.run_dir
