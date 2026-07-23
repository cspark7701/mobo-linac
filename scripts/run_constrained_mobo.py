#!/usr/bin/env python3
"""
Phase 3: Constraint-Aware Multi-Objective Bayesian Optimization (Constrained MOBO)
for 200 MeV Linac Injector.
Explicitly models beam quality constraints as Gaussian Process surrogates alongside
objectives (emit_x, emit_y, sigma_energy) using BoTorch (ModelListGP + constrained qLogNEHVI / qEHVI)
and Probability of Feasibility weighting.
"""

import os
import sys
import argparse
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import torch

from botorch.models import SingleTaskGP, ModelListGP
from botorch.models.transforms.input import Normalize
from botorch.models.transforms.outcome import Standardize
from botorch.fit import fit_gpytorch_mll
from gpytorch.mlls import ExactMarginalLogLikelihood
from botorch.optim import optimize_acqf
from botorch.acquisition.multi_objective.monte_carlo import (
    qExpectedHypervolumeImprovement,
    qNoisyExpectedHypervolumeImprovement,
)
from botorch.acquisition.multi_objective.logei import (
    qLogNoisyExpectedHypervolumeImprovement,
)
from botorch.acquisition.multi_objective.objective import IdentityMCMultiOutputObjective
from botorch.utils.multi_objective.box_decompositions.non_dominated import FastNondominatedPartitioning
from botorch.utils.multi_objective.hypervolume import Hypervolume
from botorch.utils.multi_objective.pareto import is_non_dominated

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_astra import run_astra_simulation, get_objectives, get_diagnostics
from mobo_utils import evaluate_constrained_objective, compute_ref_point
from file_io import create_run_directory, save_results, save_checkpoint, load_checkpoint
from plot_utils import (
    plot_hypervolume,
    plot_pareto_objective_space,
    plot_all_constraints,
    plot_objective_evolution
)

# Set PyTorch default dtype to double precision
torch.set_default_dtype(torch.double)


def parse_args():
    parser = argparse.ArgumentParser(description="Run Phase 3 Constrained MOBO for 200 MeV Linac")
    parser.add_argument("--n-iterations", type=int, default=300, help="Total BO iterations")
    parser.add_argument("-q", "--batch-size", type=int, default=8, help="Batch size for q-MOBO")
    parser.add_argument("--num-initial-samples", type=int, default=16, help="Number of initial random samples")
    parser.add_argument("--num-workers", type=int, default=12, help="Number of parallel workers for ASTRA")
    parser.add_argument("--acquisition", type=str, choices=["qLogNEHVI", "qEHVI"], default="qLogNEHVI", help="Acquisition function")
    parser.add_argument("--ratio", type=float, default=0.50, help="Magnet parameter search range ratio (+/- ratio)")
    parser.add_argument("--phase-ratio", type=float, default=0.10, help="RF phase search range ratio (+/- ratio)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=str, default=None, help="Custom output directory (default: results/YYYYMMDD_HHMMSS)")
    parser.add_argument("--resume-checkpoint", type=str, default=None, help="Path to checkpoint file to resume")
    return parser.parse_args()


def set_seed(seed):
    torch.manual_seed(seed)
    np.random.seed(seed)


def get_parameter_bounds(ratio=0.50, phase_ratio=0.10):
    from astra import Astra
    A = Astra("astra.in")
    A.timeout = None
    A.verbose = False
    A.run()

    init_parameters = [
        A["solenoid:maxb(1)"],
        A["quadrupole:q_grad(1)"],
        A["quadrupole:q_grad(2)"],
        A["cavity:phi(1)"],
        A["cavity:phi(2)"],
        A["cavity:phi(4)"],
    ]

    ratio_list = [ratio, ratio, ratio, phase_ratio, phase_ratio, phase_ratio]
    param_bounds_list = []
    for val, r in zip(init_parameters, ratio_list):
        lower_val = val * (1 - r)
        upper_val = val * (1 + r)
        param_bounds_list.append([min(lower_val, upper_val), max(lower_val, upper_val)])

    bounds = torch.tensor(param_bounds_list, dtype=torch.double).T
    return bounds, init_parameters


# Constraint evaluators acting on GP outcome predictions (Y of shape ... x 9)
def c_sigma_x(Y): return Y[..., 3] - 1.0e-3
def c_sigma_y(Y): return Y[..., 4] - 1.0e-3
def c_sigma_xp(Y): return Y[..., 5] - 1.0e-3
def c_sigma_yp(Y): return Y[..., 6] - 1.0e-3
def c_sigma_z(Y): return Y[..., 7] - 1.0e-3
def c_E_min(Y): return 195e6 - Y[..., 8]
def c_E_max(Y): return Y[..., 8] - 205e6

CONSTRAINT_FUNCTIONS = [c_sigma_x, c_sigma_y, c_sigma_xp, c_sigma_yp, c_sigma_z, c_E_min, c_E_max]


def run_constrained_mobo(args):
    set_seed(args.seed)

    if args.output_dir:
        run_dir = args.output_dir
        os.makedirs(os.path.join(run_dir, "gp_checkpoint"), exist_ok=True)
        os.makedirs(os.path.join(run_dir, "figures"), exist_ok=True)
    else:
        run_dir = create_run_directory(base_dir="results")

    checkpoint_file = args.resume_checkpoint or os.path.join(run_dir, "gp_checkpoint", "constrained_mobo_checkpoint.pt")

    config = {
        "phase": 3,
        "mode": "Constraint-Aware MOBO",
        "n_iterations": args.n_iterations,
        "batch_size": args.batch_size,
        "num_initial_samples": args.num_initial_samples,
        "num_workers": args.num_workers,
        "acquisition_mode": args.acquisition,
        "ratio": args.ratio,
        "phase_ratio": args.phase_ratio,
        "seed": args.seed,
        "run_dir": run_dir,
        "timestamp": datetime.now().isoformat()
    }
    with open(os.path.join(run_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)

    bounds, init_params = get_parameter_bounds(ratio=args.ratio, phase_ratio=args.phase_ratio)
    input_transform = Normalize(d=bounds.shape[1], bounds=bounds)

    executor = ThreadPoolExecutor(max_workers=args.num_workers)

    checkpoint = load_checkpoint(checkpoint_file) if os.path.exists(checkpoint_file) else None

    if checkpoint:
        start_iteration = checkpoint["iteration"] + 1
        train_X = checkpoint["train_X"]
        train_Y = checkpoint["train_Y"] # 3 objectives
        train_Y_full = checkpoint.get("train_Y_full", train_Y)
        train_feas_mask = checkpoint["train_feas_mask"]
        hypervolumes = checkpoint["hypervolumes"]
        train_constraints_list = checkpoint["train_constraints_list"]
        print(f"Resuming Phase 3 from iteration {start_iteration + 1} with {train_X.shape[0]} samples.")
    else:
        start_iteration = 0
        hypervolumes = []
        print(f"Generating {args.num_initial_samples} initial samples using Sobol sampling...")

        sobol_engine = torch.quasirandom.SobolEngine(dimension=bounds.shape[1], scramble=True, seed=args.seed)
        sobol_samples = sobol_engine.draw(args.num_initial_samples).to(dtype=torch.double)
        lower_b, upper_b = bounds[0], bounds[1]
        train_X = lower_b + (upper_b - lower_b) * sobol_samples

        print(f"Evaluating {args.num_initial_samples} initial samples across {args.num_workers} parallel workers...")
        eval_results = list(executor.map(evaluate_constrained_objective, train_X))

        train_Y_list, train_Y_full_list, train_feas_list, initial_constraints_list = zip(*eval_results)
        train_Y = torch.stack(train_Y_list) # 3 objectives (negated)
        train_Y_full = torch.stack(train_Y_full_list) # 9 outcomes (3 obj + 6 diagnostics)
        train_feas_mask = torch.stack(train_feas_list)
        train_constraints_list = list(initial_constraints_list)

    feasible_count = train_feas_mask.sum().item()
    print(f"Initial evaluation complete. Feasible samples: {feasible_count} / {train_X.shape[0]}")

    objective_mapping = IdentityMCMultiOutputObjective(outcomes=[0, 1, 2])

    print(f"\nStarting Phase 3 Constrained MOBO loop for {args.n_iterations} iterations (q={args.batch_size}, acquisition={args.acquisition})...")

    for iteration in range(start_iteration, args.n_iterations):
        t0 = time.time()
        print(f"\n--- Phase 3 Iteration {iteration + 1}/{args.n_iterations} ---")

        # In Phase 3, fit 9 GP models on ALL data (both feasible & unfeasible) so constraint surrogates learn boundary surfaces!
        gps = [
            SingleTaskGP(
                train_X,
                train_Y_full[:, i:i+1],
                input_transform=input_transform,
                outcome_transform=Standardize(m=1)
            ) for i in range(9)
        ]
        model = ModelListGP(*gps)

        for m in model.models:
            mll = ExactMarginalLogLikelihood(m.likelihood, m)
            fit_gpytorch_mll(mll)

        # Compute dynamic reference point based on feasible data if available, else all data
        feasible_Y = train_Y[train_feas_mask] if train_feas_mask.sum() > 0 else train_Y
        ref_point = compute_ref_point(feasible_Y)
        print(f"  Dynamic Reference Point (Negated): {ref_point.tolist()}")

        partitioning = FastNondominatedPartitioning(ref_point=ref_point, Y=feasible_Y)

        if args.acquisition == "qEHVI":
            acq_func = qExpectedHypervolumeImprovement(
                model=model,
                ref_point=ref_point.tolist(),
                partitioning=partitioning,
                objective=objective_mapping,
                constraints=CONSTRAINT_FUNCTIONS,
            )
        elif args.acquisition == "qLogNEHVI":
            acq_func = qLogNoisyExpectedHypervolumeImprovement(
                model=model,
                ref_point=ref_point.tolist(),
                X_baseline=train_X,
                objective=objective_mapping,
                constraints=CONSTRAINT_FUNCTIONS,
                prune_baseline=True,
            )
        else:
            raise ValueError(f"Unsupported acquisition: {args.acquisition}")

        print(f"  Optimizing Constrained {args.acquisition} for q={args.batch_size} candidates...")
        candidates, _ = optimize_acqf(
            acq_function=acq_func,
            bounds=bounds,
            q=args.batch_size,
            num_restarts=20,
            raw_samples=128,
            return_best_only=True,
        )

        print(f"  Evaluating candidate batch across {args.num_workers} workers...")
        eval_results = list(executor.map(evaluate_constrained_objective, candidates))

        new_Y_list, new_Y_full_list, new_feas_list, new_constraints_tuples = zip(*eval_results)
        new_Y = torch.stack(new_Y_list)
        new_Y_full = torch.stack(new_Y_full_list)
        new_feas_mask = torch.stack(new_feas_list)

        train_X = torch.cat([train_X, candidates])
        train_Y = torch.cat([train_Y, new_Y])
        train_Y_full = torch.cat([train_Y_full, new_Y_full])
        train_feas_mask = torch.cat([train_feas_mask, new_feas_mask])
        train_constraints_list.extend(list(new_constraints_tuples))

        # Hypervolume calculation on feasible Pareto front
        feasible_Y_current = train_Y[train_feas_mask]
        if feasible_Y_current.shape[0] > 0:
            pareto_mask_feasible = is_non_dominated(feasible_Y_current)
            pareto_Y_feasible = feasible_Y_current[pareto_mask_feasible]
            hv_calc = Hypervolume(ref_point=ref_point)
            current_hv = hv_calc.compute(pareto_Y_feasible)
        else:
            current_hv = 0.0

        hypervolumes.append(current_hv)

        t_iter = time.time() - t0
        print(f"  Iteration {iteration + 1} finished in {t_iter:.2f}s | Batch Feasible: {new_feas_mask.sum().item()}/{args.batch_size} | Feasible Hypervolume: {current_hv:.4f}")

        save_checkpoint(
            iteration=iteration,
            train_X=train_X,
            train_Y=train_Y,
            train_feas_mask=train_feas_mask,
            hypervolumes=hypervolumes,
            train_constraints_list=train_constraints_list,
            acquisition_mode=args.acquisition,
            checkpoint_file=checkpoint_file,
        )

        save_results(
            train_X=train_X,
            train_Y=train_Y,
            run_dir=run_dir,
            hypervolumes=hypervolumes,
            constraints_list=train_constraints_list,
            config=config,
        )

    executor.shutdown()
    print("\nPhase 3 Constrained MOBO Optimization loop completed successfully!")

    save_results(
        train_X=train_X,
        train_Y=train_Y,
        run_dir=run_dir,
        hypervolumes=hypervolumes,
        constraints_list=train_constraints_list,
        config=config,
    )

    try:
        print("Generating summary figures...")
        if len(hypervolumes) > 0:
            plot_hypervolume(hypervolumes, len(hypervolumes), 0)
        plot_pareto_objective_space(train_Y)
        plot_all_constraints(train_constraints_list, train_feas_mask)
    except Exception as e:
        print(f"Note: Figure generation info: {e}")

    feasible_pareto_count = is_non_dominated(train_Y[train_feas_mask]).sum().item() if train_feas_mask.sum() > 0 else 0
    print(f"\nFinal Feasible Pareto front size: {feasible_pareto_count}")
    print(f"All Phase 3 outputs and figures saved under: {run_dir}/")


if __name__ == "__main__":
    args = parse_args()
    run_constrained_mobo(args)
