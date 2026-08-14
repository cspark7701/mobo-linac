"""
Unified MOBO Campaign Runner for mobo_linac.

Consolidates optimization loop execution across CLI commands, scripts,
and interactive notebooks.
"""

from datetime import datetime
import os
from pathlib import Path
import platform
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
from mobo_linac.config import MoboConfig, load_config
from mobo_linac.constraints import get_botorch_constraint_functions
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.execution.parallel import BatchEvaluator
from mobo_linac.models.gp import fit_gp_models
from mobo_linac.io.results import (
    DESIGN_VAR_COLUMNS,
    MODEL_OBJ_COLUMNS,
    PHYSICAL_OBJ_COLUMNS,
    get_constraint_tensors,
    get_train_tensors,
    load_run_checkpoint,
    results_to_dataframe,
    save_evaluation_results,
    save_run_checkpoint,
)
from mobo_linac.metrics.hypervolume import (
    HypervolumeTracker,
    compute_reference_point,
)
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
        config: Union[str, Path, MoboConfig] = "configs/mobo_200MeV.yaml",
        run_name: str = "mobo",
        base_results_dir: Union[str, Path] = "results",
        output_dir: Optional[Union[str, Path]] = None,
        num_initial_samples: int = 16,
        num_batches: int = 6,
        batch_size: int = 4,
        num_workers: Optional[int] = None,
        seed: int = 42,
        acq_type: str = "qLogNEHVI",
        constrained: bool = False,
        optimization_mode: str = "unconstrained_mobo",
        scalar_weights: Optional[Sequence[float]] = None,
        export_plots: bool = True,
        export_env_info: bool = True,
        resume: bool = False,
        resume_from: Optional[Union[str, Path]] = None,
        evaluator: Optional[Any] = None,
        device: Optional[Union[str, torch.device]] = None,
    ):
        if device is None or (isinstance(device, str) and device.lower() in ("auto", "")):
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        elif isinstance(device, str):
            self.device = torch.device(device if (device != "cuda" or torch.cuda.is_available()) else "cpu")
        else:
            self.device = device

        if isinstance(config, (str, Path)):
            config_path = Path(config)
            if not config_path.exists():
                config_path = Path("configs/mobo_200MeV.yaml")
            self.config = load_config(config_path)
            self.config_path = config_path
        else:
            self.config = config
            self.config_path = None

        self.run_name = run_name
        self.base_results_dir = Path(base_results_dir)
        self.num_initial_samples = num_initial_samples
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

        if output_dir:
            self.run_dir = Path(output_dir)
            self.run_id = self.run_dir.name
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.run_id = f"{run_name}_{timestamp}"
            self.run_dir = self.base_results_dir / self.run_id

        self.run_dir.mkdir(parents=True, exist_ok=True)

        if num_workers is not None:
            self.num_workers = num_workers
        else:
            self.num_workers = self.config.execution.max_workers

        torch.manual_seed(self.seed)
        np.random.seed(self.seed)
        torch.set_default_dtype(torch.double)

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
        if self.optimization_mode == "scalarized_bo":
            mode_str = f"Scalarized BO (weights={self.scalar_weights.tolist()})"
        elif self.constrained:
            mode_str = "Constrained MOBO (Feasibility-Aware)"
        else:
            mode_str = "Unconstrained MOBO"

        print(f"=== Starting Optimization Campaign: {self.run_id} ({mode_str}) ===")
        print(
            f"Initial samples: {self.num_initial_samples}, "
            f"Batches: {self.num_batches}, Batch size: {self.batch_size}, "
            f"Workers: {self.num_workers}, Acquisition: {self.acq_type}, "
            f"Mode: {self.optimization_mode}"
        )

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

        start_iteration = 1
        results: List[EvaluationResult] = []

        # Check for checkpoint resume
        if self.resume or self.resume_from:
            target_ckpt = self.resume_from or self.run_dir
            ckpt_data = load_run_checkpoint(target_ckpt)
            if not ckpt_data:
                raise FileNotFoundError(f"No valid checkpoint found to resume at '{target_ckpt}'")

            # Check config compatibility
            ckpt_cfg_dict = ckpt_data.get("config")
            if isinstance(ckpt_cfg_dict, dict) and "parameters" in ckpt_cfg_dict:
                ckpt_params = ckpt_cfg_dict["parameters"]
                curr_params = self.config.to_dict().get("parameters", {})
                if len(ckpt_params) != len(curr_params):
                    raise ValueError(f"Incompatible checkpoint configuration: parameter count mismatch ({len(ckpt_params)} vs {len(curr_params)})")

            results = ckpt_data["results"]
            completed_iteration = int(ckpt_data.get("iteration", 0))
            start_iteration = completed_iteration + 1
            print(f"Resuming campaign '{self.run_id}' from iteration {start_iteration} ({len(results)} existing evaluations)...")

            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)

            stored_ref_point = ckpt_data.get("reporting_ref_point")
            if stored_ref_point is not None:
                reporting_ref_point = torch.tensor(stored_ref_point, dtype=torch.double)
            else:
                reporting_ref_point = compute_reference_point(train_Y, offset_ratio=0.10)

            # Restore PyTorch & NumPy random states if saved in checkpoint
            t_state = ckpt_data.get("torch_rng_state")
            if t_state is not None:
                if isinstance(t_state, torch.Tensor):
                    torch.set_rng_state(t_state.cpu())
                elif isinstance(t_state, (bytes, bytearray)):
                    torch.set_rng_state(torch.frombuffer(t_state, dtype=torch.uint8))

            n_state = ckpt_data.get("numpy_rng_state")
            if n_state is not None and isinstance(n_state, (list, tuple)) and len(n_state) == 5:
                try:
                    np.random.set_state((
                        str(n_state[0]),
                        np.array(n_state[1], dtype=np.uint32),
                        int(n_state[2]),
                        int(n_state[3]),
                        float(n_state[4]),
                    ))
                except Exception:
                    pass

            # Advance Sobol engine random state past initial and completed iterations
            sobol_engine.draw(self.num_initial_samples)
            for _ in range(1, start_iteration):
                sobol_engine.draw(self.batch_size)

            tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point, config=self.config)



            # Re-track hypervolume history
            stored_hvs = ckpt_data.get("hypervolumes")
            if stored_hvs and len(stored_hvs) == completed_iteration + 1:
                # Use stored hypervolume values directly
                for it_idx, hv_val in enumerate(stored_hvs):
                    n_pts = self.num_initial_samples + it_idx * self.batch_size
                    curr_y = train_Y[:n_pts] if train_Y.shape[0] >= n_pts else train_Y
                    curr_mask = train_feas_mask[:n_pts] if train_feas_mask.shape[0] >= n_pts else train_feas_mask
                    tracker.track_iteration(it_idx, curr_y, curr_mask)
            else:
                tracker.track_iteration(0, train_Y[:self.num_initial_samples], train_feas_mask[:self.num_initial_samples])
                for it_idx in range(1, start_iteration):
                    n_pts = self.num_initial_samples + it_idx * self.batch_size
                    curr_y = train_Y[:n_pts] if train_Y.shape[0] >= n_pts else train_Y
                    curr_mask = train_feas_mask[:n_pts] if train_feas_mask.shape[0] >= n_pts else train_feas_mask
                    tracker.track_iteration(it_idx, curr_y, curr_mask)
        else:
            sobol_samples = sobol_engine.draw(self.num_initial_samples).to(dtype=torch.double)
            lower_b, upper_b = bounds[0], bounds[1]
            initial_candidates = (lower_b + (upper_b - lower_b) * sobol_samples).tolist()

            raw_initial = evaluator.evaluate_batch(initial_candidates, run_id=self.run_id)
            results = [create_evaluation_result(r, self.config) for r in raw_initial]

            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)

            reporting_ref_point = compute_reference_point(train_Y, offset_ratio=0.10)
            tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point, config=self.config)

            tracker.track_iteration(0, train_Y, train_feas_mask)
            save_evaluation_results(results, self.run_dir, tracker.to_dataframe()["feasible_hypervolume"].tolist())
            tracker.save_csv(self.run_dir / "hypervolume.csv")

            ckpt_dir = self.run_dir / "checkpoints"
            ckpt_dir.mkdir(parents=True, exist_ok=True)
            ckpt_acq_mode = "scalarized_qLogNEI" if self.optimization_mode == "scalarized_bo" else self.acq_type
            save_run_checkpoint(
                iteration=0,
                results=results,
                hypervolumes=tracker.to_dataframe()["feasible_hypervolume"].tolist(),
                checkpoint_path=ckpt_dir / "checkpoint_iter_00.pt",
                acquisition_mode=ckpt_acq_mode,
                config=self.config,
                reporting_ref_point=reporting_ref_point,
                seed=self.seed,
                batch_size=self.batch_size,
                constrained=self.constrained,
            )

        lower_b, upper_b = bounds[0], bounds[1]

        for iteration in range(start_iteration, self.num_batches + 1):
            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)

            if train_X.shape[0] < 2:
                new_sobol = sobol_engine.draw(self.batch_size).to(dtype=torch.double)
                next_cand_list = (lower_b + (upper_b - lower_b) * new_sobol).tolist()
            elif self.optimization_mode == "scalarized_bo":
                # Scalarized single-objective GP surrogate with qLogNEI
                weights_dev = self.scalar_weights.to(dtype=torch.double, device=self.device)
                train_X_dev = train_X.to(dtype=torch.double, device=self.device)
                train_Y_dev = train_Y.to(dtype=torch.double, device=self.device)
                scalar_Y = (train_Y_dev * weights_dev).sum(dim=-1, keepdim=True)

                input_transform = Normalize(d=bounds.shape[1], bounds=bounds.to(device=self.device))
                gp = SingleTaskGP(
                    train_X=train_X_dev,
                    train_Y=scalar_Y,
                    input_transform=input_transform,
                    outcome_transform=Standardize(m=1),
                )
                fit_gp_models(ModelListGP(gp))

                acq_func = qLogNoisyExpectedImprovement(
                    model=gp,
                    X_baseline=train_X_dev,
                    prune_baseline=True,
                )
                exec_cfg = self.config.execution
                candidates, _ = optimize_acqf(
                    acq_function=acq_func,
                    bounds=bounds.to(device=self.device),
                    q=self.batch_size,
                    num_restarts=getattr(exec_cfg, "acqf_num_restarts", 20),
                    raw_samples=getattr(exec_cfg, "acqf_raw_samples", 128),
                    options={
                        "batch_limit": getattr(exec_cfg, "acqf_batch_limit", 5),
                        "maxiter": getattr(exec_cfg, "acqf_maxiter", 200),
                    },
                )
                next_cand_list = candidates.cpu().tolist()
            else:
                pipeline = SurrogatePipeline(
                    bounds=bounds,
                    covar_type=self.config.model.covar_type,
                    noise_mode=self.config.model.noise_mode,
                    fixed_noise_val=self.config.model.fixed_noise_variance,
                    relative_noise_ratio=self.config.model.relative_noise_ratio,
                    min_noise_variance=self.config.model.min_noise_variance,
                    objective_noise_variances=self.config.model.objective_noise_variances,
                    device=self.device,
                )

                if self.constrained:
                    train_constraints = get_constraint_tensors(results, exclude_invalid=True)
                    pipeline.fit(train_X, train_Y, train_constraints)
                    if pipeline.constraint_model is not None:
                        gp_model = ModelListGP(*pipeline.objective_model.models, *pipeline.constraint_model.models)
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
                    batch_size=self.batch_size,
                    num_restarts=getattr(exec_cfg, "acqf_num_restarts", 20),
                    raw_samples=getattr(exec_cfg, "acqf_raw_samples", 1024),
                    maxiter=getattr(exec_cfg, "acqf_maxiter", 200),
                    batch_limit=getattr(exec_cfg, "acqf_batch_limit", 5),
                    device=self.device,
                )
                next_cand_list = next_cand_tensor.tolist()


            start_eval_id = len(results) + 1
            eval_ids = [start_eval_id + i for i in range(len(next_cand_list))]

            raw_batch = evaluator.evaluate_batch(next_cand_list, run_id=self.run_id, eval_ids=eval_ids)
            batch_results = [create_evaluation_result(r, self.config) for r in raw_batch]
            results.extend(batch_results)

            train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
            hv_record = tracker.track_iteration(iteration, train_Y, train_feas_mask)

            print(
                f"Iter {iteration:02d}/{self.num_batches:02d} | "
                f"Evaluations: {len(results):02d} | "
                f"Valid: {train_X.shape[0]:02d} | "
                f"Feasible: {hv_record['num_feasible_points']:02d} | "
                f"HV: {hv_record['feasible_hypervolume']:.6e}"
            )

            save_evaluation_results(results, self.run_dir, tracker.to_dataframe()["feasible_hypervolume"].tolist())
            tracker.save_csv(self.run_dir / "hypervolume.csv")

            ckpt_dir = self.run_dir / "checkpoints"
            ckpt_dir.mkdir(parents=True, exist_ok=True)
            ckpt_path = ckpt_dir / f"checkpoint_iter_{iteration:02d}.pt"
            ckpt_acq_mode = "scalarized_qLogNEI" if self.optimization_mode == "scalarized_bo" else self.acq_type
            save_run_checkpoint(
                iteration=iteration,
                results=results,
                hypervolumes=tracker.to_dataframe()["feasible_hypervolume"].tolist(),
                checkpoint_path=ckpt_path,
                acquisition_mode=ckpt_acq_mode,
                config=self.config,
                reporting_ref_point=reporting_ref_point,
                seed=self.seed,
                batch_size=self.batch_size,
                constrained=self.constrained,
            )


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
        print(f"Output saved in: {self.run_dir.resolve()}")

        return results, tracker, self.run_dir
