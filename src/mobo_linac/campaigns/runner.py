"""
Unified MOBO Campaign Runner for mobo_linac.

Consolidates optimization loop execution across CLI commands, scripts,
and interactive notebooks.
"""

from copy import deepcopy
from datetime import datetime
import os
from pathlib import Path
import platform
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import torch
from botorch.utils.multi_objective.pareto import is_non_dominated

from botorch.acquisition.logei import qLogNoisyExpectedImprovement
from botorch.models import ModelListGP, SingleTaskGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
from botorch.optim import optimize_acqf
from mobo_linac import __version__
from mobo_linac.acquisition.mobo import (
    SliceObjective,
    build_acquisition_function,
    generate_next_candidates,
)
from mobo_linac.config import MoboConfig, config_from_dict, load_config
from mobo_linac.campaigns.state import prepare_resume_state, restore_rng_state
from mobo_linac.constraints import get_botorch_constraint_functions
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.execution.parallel import BatchEvaluator
from mobo_linac.models.gp import build_scalarized_gp_model, fit_gp_models
from mobo_linac.io.results import (
    CheckpointState,
    DESIGN_VAR_COLUMNS,
    MODEL_OBJ_COLUMNS,
    PHYSICAL_OBJ_COLUMNS,
    append_streaming_evaluation,
    get_constraint_tensors,
    get_train_tensors,
    load_run_checkpoint,
    load_streaming_evaluations,
    results_to_dataframe,
    save_evaluation_results,
    save_run_checkpoint,
)
from mobo_linac.metrics.hypervolume import (
    HypervolumeTracker,
    compute_reference_point,
)
from mobo_linac.metrics.reporting import DEFAULT_REPORTING_SCALES
from mobo_linac.models.pipeline import SurrogatePipeline

from mobo_linac.plotting.visualizations import (
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
        device: Optional[Union[str, torch.device]] = None,
        total_eval_budget: Optional[int] = None,
    ):
        self._requested_initial_samples = num_initial_samples
        self._requested_num_batches = num_batches
        self._requested_batch_size = batch_size
        self._requested_seed = seed
        self._requested_mode = optimization_mode
        self._requested_acquisition = acq_type
        self._requested_weights = scalar_weights
        self._requested_budget = total_eval_budget
        self._requested_device = device
        self._requested_num_workers = num_workers
        self._config_explicit = config is not None
        if config is None and not (resume or resume_from):
            config = "configs/mobo_200MeV.yaml"
        num_initial_samples = 16 if num_initial_samples is None else num_initial_samples
        num_batches = 6 if num_batches is None else num_batches
        batch_size = 4 if batch_size is None else batch_size
        seed = 42 if seed is None else seed
        acq_type = "qLogNEHVI" if acq_type is None else acq_type
        optimization_mode = optimization_mode or "unconstrained_mobo"
        if device is None or (isinstance(device, str) and device.lower() in ("auto", "")):
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        elif isinstance(device, str):
            self.device = torch.device(device if (device != "cuda" or torch.cuda.is_available()) else "cpu")
        else:
            self.device = device

        if isinstance(config, (str, Path)):
            config_path = Path(config)
            if not config_path.exists():
                if resume or resume_from:
                    raise FileNotFoundError(f"Requested resume configuration not found: {config_path}")
                config_path = Path("configs/mobo_200MeV.yaml")
            self.config = load_config(config_path)
            self.config_path = config_path
        else:
            self.config = config
            self.config_path = None

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

        if scalar_weights is not None:
            w_tensor = torch.tensor(scalar_weights, dtype=torch.double)
            self.scalar_weights = w_tensor / w_tensor.sum()
        else:
            self.scalar_weights = torch.tensor([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=torch.double)

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
            self.num_workers = self.config.execution.max_workers if self.config is not None else 4

        torch.manual_seed(self.seed)
        np.random.seed(self.seed)
        random.seed(self.seed)
        torch.set_default_dtype(torch.double)

    def _prepare_resume(self) -> "CheckpointState":
        """Resolve and validate a completed checkpoint before any destination writes."""
        target = self.resume_from or self.run_dir
        checkpoint = load_run_checkpoint(target)
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
            weights = torch.as_tensor(self._requested_weights, dtype=torch.double)
            weights = weights / weights.sum()
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
            required = state.iteration + (remaining + self.batch_size - 1) // self.batch_size
            if self._requested_num_batches is None:
                self.num_batches = required
            elif self.num_batches != required:
                raise ValueError("Resume iteration count must consume the saved total budget with the selected batch size.")
        if type(self.num_batches) is not int:
            raise ValueError("Resume iteration target must be an integer.")
        if self.num_batches < state.iteration:
            raise ValueError("Resume iteration target is earlier than the completed checkpoint.")
        requested_device = self._requested_device
        if requested_device is None or str(requested_device).lower() in ("auto", ""):
            self.device = torch.device(state.device)
        else:
            self.device = torch.device(requested_device)
        def canonical_device(device):
            value = torch.device(device)
            return (value.type, value.index or 0) if value.type == "cuda" else (value.type, value.index)
        if canonical_device(self.device) != canonical_device(state.device):
            raise ValueError("Resume device differs from checkpoint; deterministic CPU/GPU migration is unsupported.")
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
            f"ASTRA_BIN: {os.environ.get('ASTRA_BIN', 'Not set')}",
            f"GENERATOR_BIN: {os.environ.get('GENERATOR_BIN', 'Not set')}",
            f"Platform: {platform.platform()}",
            f"Timestamp: {datetime.now().isoformat()}",
        ]
        target_path.write_text("\n".join(lines) + "\n")

    def run(self) -> Tuple[List[EvaluationResult], HypervolumeTracker, Path]:
        """
        Executes the optimization campaign.
        """
        resume_state = self._prepare_resume() if (self.resume or self.resume_from) else None
        if self.optimization_mode == "scalarized_bo":
            mode_str = f"Scalarized BO (weights={self.scalar_weights.tolist()})"
        elif self.constrained:
            mode_str = "Constrained MOBO (Feasibility-Aware)"
        else:
            mode_str = "Unconstrained MOBO"

        print(f"\n=== Starting Optimization Campaign: {self.run_id} ({mode_str}) ===")
        print(
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

        def _evaluate_with_streaming(
            cand_list: List[List[float]],
            e_ids: Optional[List[int]] = None,
            batch_idx: Optional[int] = None,
        ) -> List[EvaluationResult]:
            def _stream_callback(raw_res: Dict[str, Any]):
                try:
                    eval_res = create_evaluation_result(raw_res, self.config)
                    append_streaming_evaluation(self.run_dir, eval_res, batch_idx=batch_idx)
                except Exception:
                    pass

            import inspect
            sig = inspect.signature(evaluator.evaluate_batch)
            if "on_evaluation_complete" in sig.parameters:
                raw_out = evaluator.evaluate_batch(
                    cand_list,
                    run_id=self.run_id,
                    eval_ids=e_ids,
                    on_evaluation_complete=_stream_callback,
                )
            else:
                raw_out = evaluator.evaluate_batch(cand_list, run_id=self.run_id, eval_ids=e_ids)
                for r in raw_out:
                    _stream_callback(r)

            return [create_evaluation_result(r, self.config) for r in raw_out]

        start_iteration = 1
        results: List[EvaluationResult] = []
        evaluation_batches: List[int] = []
        initial_candidates: List[List[float]] = []

        def _persist_checkpoint(iteration: int):
            checkpoint_mode = "scalarized_qLogNEI" if self.optimization_mode == "scalarized_bo" else self.acq_type
            save_run_checkpoint(
                iteration=iteration,
                results=results,
                hypervolumes=[record["feasible_hypervolume"] for record in tracker.history],
                checkpoint_path=self.run_dir / "checkpoints" / f"checkpoint_iter_{iteration:02d}.pt",
                acquisition_mode=checkpoint_mode,
                config=self.config,
                reporting_ref_point=reporting_ref_point,
                seed=self.seed,
                batch_size=self.batch_size,
                constrained=self.constrained,
                campaign_state={
                    "run_id": self.run_id,
                    "optimization_mode": self.optimization_mode,
                    "scalar_weights": self.scalar_weights.tolist(),
                    "num_initial_samples": self.num_initial_samples,
                    "initial_design": initial_candidates,
                    "sobol_state": {"seed": self.seed, "dimension": bounds.shape[1], "num_generated": sobol_engine.num_generated},
                    "evaluation_batches": evaluation_batches,
                    "metric_history": deepcopy(tracker.history),
                    "reporting_scales": list(DEFAULT_REPORTING_SCALES),
                    "planned_num_batches": self.num_batches,
                    "num_workers": self.num_workers,
                    "total_eval_budget": self.total_eval_budget,
                    "device": str(self.device),
                    "cuda_rng_states": torch.cuda.get_rng_state_all() if self.device.type == "cuda" else [],
                    "migration_notes": resume_state.migration_notes if resume_state is not None else [],
                },
            )

        if resume_state is not None:
            results = resume_state.results
            evaluation_batches = list(resume_state.evaluation_batches)
            initial_candidates = deepcopy(resume_state.initial_design)
            start_iteration = resume_state.iteration + 1
            reporting_ref_point = torch.tensor(resume_state.reporting_ref_point, dtype=torch.double)
            tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point, config=self.config)
            tracker.history = deepcopy(resume_state.metric_history)
            sobol_engine.fast_forward(resume_state.sobol_state["num_generated"])
            restore_rng_state(resume_state)
            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
            print(f"\nResuming campaign '{self.run_id}' from iteration {start_iteration} ({len(results)} existing evaluations)...\n")
        else:
            print(f"--- Step 0: Initial Design (Sobol Sampling: {self.num_initial_samples} samples) ---")
            sobol_samples = sobol_engine.draw(self.num_initial_samples).to(dtype=torch.double)
            lower_b, upper_b = bounds[0], bounds[1]
            initial_candidates = (lower_b + (upper_b - lower_b) * sobol_samples).tolist()

            results = _evaluate_with_streaming(initial_candidates, batch_idx=0)
            evaluation_batches = [0] * len(results)

            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)

            reporting_ref_point = compute_reference_point(train_Y, offset_ratio=0.10)
            tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point, config=self.config)

            hv_init = tracker.track_iteration(0, train_Y, train_feas_mask)
            print(
                f"Iter 00/{self.num_batches:02d} (Initial) | "
                f"Evaluations: {len(results):02d} | "
                f"Valid: {train_X.shape[0]:02d} | "
                f"Feasible: {hv_init['num_feasible_points']:02d} | "
                f"HV: {hv_init['feasible_hypervolume']:.6e}\n"
            )

            save_evaluation_results(results, self.run_dir, tracker.to_dataframe()["feasible_hypervolume"].tolist())
            tracker.save_csv(self.run_dir / "hypervolume.csv")

            _persist_checkpoint(0)

        lower_b, upper_b = bounds[0], bounds[1]

        for iteration in range(start_iteration, self.num_batches + 1):
            proposal_batch_size = self.batch_size
            if self.total_eval_budget is not None:
                proposal_batch_size = min(proposal_batch_size, self.total_eval_budget - len(results))
                if proposal_batch_size <= 0:
                    break
            print(f"--- Iteration {iteration:02d}/{self.num_batches:02d} ---")
            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)

            if train_X.shape[0] < 2:
                new_sobol = sobol_engine.draw(proposal_batch_size).to(dtype=torch.double)
                next_cand_list = (lower_b + (upper_b - lower_b) * new_sobol).tolist()
            elif self.optimization_mode == "scalarized_bo":
                # Scalarized single-objective GP surrogate with qLogNEI
                weights_dev = self.scalar_weights.to(dtype=torch.double, device=self.device)
                train_X_dev = train_X.to(dtype=torch.double, device=self.device)
                train_Y_dev = train_Y.to(dtype=torch.double, device=self.device)
                # Scale objectives to dimensionless O(1) space [1 um*rad, 1 um*rad, 1 MeV]
                # so weights reflect true physical trade-off balance
                scales_dev = torch.tensor(DEFAULT_REPORTING_SCALES, dtype=torch.double, device=self.device)
                train_Y_scaled = train_Y_dev / scales_dev
                scalar_Y = (train_Y_scaled * weights_dev).sum(dim=-1, keepdim=True)

                bounds_dev = bounds.to(device=self.device, dtype=torch.double)
                gp = build_scalarized_gp_model(
                    train_X=train_X_dev,
                    train_Y=scalar_Y,
                    bounds=bounds_dev,
                    covar_type=self.config.model.covar_type,
                    noise_mode=self.config.model.noise_mode,
                    fixed_noise_val=self.config.model.fixed_noise_variance,
                    relative_noise_ratio=self.config.model.relative_noise_ratio,
                    min_noise_variance=self.config.model.min_noise_variance,
                    device=self.device,
                )
                fit_gp_models(gp)

                if self.device.type == "cuda" and torch.cuda.is_available():
                    torch.cuda.empty_cache()

                acq_func = qLogNoisyExpectedImprovement(
                    model=gp,
                    X_baseline=train_X_dev,
                    prune_baseline=True,
                )
                exec_cfg = self.config.execution
                b_limit = 1 if self.device.type == "cuda" else getattr(exec_cfg, "acqf_batch_limit", 5)
                candidates, _ = generate_next_candidates(
                    acq_func=acq_func,
                    bounds=bounds_dev,
                    batch_size=proposal_batch_size,
                    num_restarts=getattr(exec_cfg, "acqf_num_restarts", 10),
                    raw_samples=getattr(exec_cfg, "acqf_raw_samples", 1024),
                    maxiter=getattr(exec_cfg, "acqf_maxiter", 200),
                    batch_limit=b_limit,
                    device=self.device,
                    sobol_engine=sobol_engine,
                )
                next_cand_list = candidates.detach().cpu().tolist()
            else:
                pipeline = SurrogatePipeline(
                    bounds=bounds,
                    covar_type=self.config.model.covar_type,
                    noise_mode=self.config.model.noise_mode,
                    fixed_noise_val=self.config.model.fixed_noise_variance,
                    relative_noise_ratio=self.config.model.relative_noise_ratio,
                    min_noise_variance=self.config.model.min_noise_variance,
                    objective_noise_variances=self.config.model.objective_noise_variances,
                    constraints_config=self.config.constraints,
                    device=self.device,
                )

                if self.constrained:
                    train_constraints = get_constraint_tensors(results, exclude_invalid=True)
                    pipeline.fit(train_X, train_Y, train_constraints)
                    if pipeline.constraint_model is not None:
                        gp_model = ModelListGP(*pipeline.objective_model.models, *pipeline.constraint_model.models).to(device=self.device, dtype=torch.double)
                        botorch_constraints = get_botorch_constraint_functions(self.config)
                        objective_slice = SliceObjective(num_objectives=3)
                    else:
                        gp_model = pipeline.objective_model
                        botorch_constraints = None
                        objective_slice = None
                else:
                    pipeline.fit(train_X, train_Y)
                    gp_model = pipeline.objective_model
                    botorch_constraints = None
                    objective_slice = None

                acq_ref_point = compute_reference_point(train_Y, offset_ratio=0.05)

                acq_func = build_acquisition_function(
                    model=gp_model,
                    train_X=train_X,
                    train_Y=train_Y,
                    ref_point=acq_ref_point,
                    train_feas_mask=train_feas_mask,
                    acq_type=self.acq_type,
                    constraints=botorch_constraints,
                    objective=objective_slice,
                )

                exec_cfg = self.config.execution
                next_cand_tensor, _ = generate_next_candidates(
                    acq_func=acq_func,
                    bounds=bounds,
                    batch_size=proposal_batch_size,
                    num_restarts=getattr(exec_cfg, "acqf_num_restarts", 10),
                    raw_samples=getattr(exec_cfg, "acqf_raw_samples", 1024),
                    maxiter=getattr(exec_cfg, "acqf_maxiter", 200),
                    batch_limit=getattr(exec_cfg, "acqf_batch_limit", 5),
                    device=self.device,
                    sobol_engine=sobol_engine,
                )
                next_cand_list = next_cand_tensor.detach().cpu().tolist()


            start_eval_id = len(results) + 1
            eval_ids = [start_eval_id + i for i in range(len(next_cand_list))]

            batch_results = _evaluate_with_streaming(next_cand_list, e_ids=eval_ids, batch_idx=iteration)
            results.extend(batch_results)
            evaluation_batches.extend([iteration] * len(batch_results))

            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
            hv_record = tracker.track_iteration(iteration, train_Y, train_feas_mask)

            print(
                f"Iter {iteration:02d}/{self.num_batches:02d} | "
                f"Evaluations: {len(results):02d} | "
                f"Valid: {train_X.shape[0]:02d} | "
                f"Feasible: {hv_record['num_feasible_points']:02d} | "
                f"HV: {hv_record['feasible_hypervolume']:.6e}\n"
            )

            save_evaluation_results(results, self.run_dir, tracker.to_dataframe()["feasible_hypervolume"].tolist())
            tracker.save_csv(self.run_dir / "hypervolume.csv")

            _persist_checkpoint(iteration)


        # Export CSV datasets
        df_all = results_to_dataframe(results)
        df_all.to_csv(self.run_dir / "evaluations.csv", index=False)
        df_all.to_csv(self.run_dir / "candidate_history.csv", index=False)

        valid_mask = df_all["simulation_valid"] == True
        df_valid = df_all[valid_mask]
        if not df_valid.empty:
            df_valid[PHYSICAL_OBJ_COLUMNS].to_csv(self.run_dir / "objectives_physical.csv", index=False)
            df_valid[MODEL_OBJ_COLUMNS].to_csv(self.run_dir / "objectives_model.csv", index=False)

        diag_cols = [c for c in df_all.columns if any(k in c for k in ["sigma", "energy", "transmission", "feasible"])]
        df_all[diag_cols].to_csv(self.run_dir / "constraints.csv", index=False)

        # Export Pareto sets
        if train_X.shape[0] > 0:
            pareto_mask_all = is_non_dominated(train_Y)
            p_X_all = train_X[pareto_mask_all]
            p_Y_all_phys = -train_Y[pareto_mask_all]
            df_p_all = pd.DataFrame(
                np.hstack([p_X_all.numpy(), p_Y_all_phys.numpy()]),
                columns=DESIGN_VAR_COLUMNS + PHYSICAL_OBJ_COLUMNS,
            )
            df_p_all.to_csv(self.run_dir / "pareto.csv", index=False)
            df_p_all.to_csv(self.run_dir / "pareto_all.csv", index=False)

            if train_feas_mask.sum().item() > 0:
                feas_X = train_X[train_feas_mask]
                feas_Y = train_Y[train_feas_mask]
                pareto_mask_feas = is_non_dominated(feas_Y)
                p_X_feas = feas_X[pareto_mask_feas]
                p_Y_feas_phys = -feas_Y[pareto_mask_feas]
                df_p_feas = pd.DataFrame(
                    np.hstack([p_X_feas.numpy(), p_Y_feas_phys.numpy()]),
                    columns=DESIGN_VAR_COLUMNS + PHYSICAL_OBJ_COLUMNS,
                )
                df_p_feas.to_csv(self.run_dir / "pareto_feasible.csv", index=False)

        df_failures = df_all[(df_all["simulation_valid"] == False) | (df_all["physically_feasible"] == False)]
        df_failures.to_csv(self.run_dir / "failures.csv", index=False)

        # Export Plots
        if self.export_plots:
            figures_dir = self.run_dir / "figures"
            figures_dir.mkdir(parents=True, exist_ok=True)
            plot_hypervolume_progress(tracker.to_dataframe(), figures_dir / "hypervolume_progress.png")
            plot_pareto_front(results, figures_dir / "pareto_front.png")
            plot_objective_evolution(results, figures_dir / "objective_evolution.png")
            plot_constraint_diagnostics(results, figures_dir / "constraint_diagnostics.png")

        print(f"=== Campaign Complete: {self.run_id} ===")
        print(f"Total Evaluations: {len(results)}")
        print(f"Output saved in: {self.run_dir.resolve()}\n")

        return results, tracker, self.run_dir
