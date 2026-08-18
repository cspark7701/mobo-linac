#!/usr/bin/env python3
"""
Robustness and Sensitivity Analysis Production Script for mobo_linac.

Evaluates machine and beam perturbation sensitivity across representative Pareto candidates.
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple
import numpy as np

import pandas as pd
import torch

from mobo_linac.config import load_config
from mobo_linac.evaluation import create_evaluation_result
from mobo_linac.execution.parallel import BatchEvaluator
from mobo_linac.io.results import DESIGN_VAR_COLUMNS, PHYSICAL_OBJ_COLUMNS
from mobo_linac.metrics.latex import generate_robustness_summary_latex_table
from mobo_linac.robustness.evaluator import (
    compute_robustness_summary,
    generate_perturbed_parameters,
    select_representative_pareto_candidates,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Engineering Tolerance & Robustness Analysis"
    )
    parser.add_argument(
        "--pareto-csv",
        type=str,
        default=None,
        help="Path to pareto.csv file containing non-dominated candidates",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/mobo_200MeV.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/robustness",
        help="Output directory for robustness artifacts",
    )
    parser.add_argument(
        "--num-workers",
        "-w",
        type=int,
        default=4,
        help="Number of parallel worker processes",
    )
    parser.add_argument(
        "--num-perturbations",
        type=int,
        default=20,
        help="Number of perturbed parameter samples per candidate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    return parser.parse_args()


def find_pareto_csv(user_path_str: Optional[str]) -> Optional[Path]:
    """Finds pareto.csv supporting files, directories, and subdirectories."""
    search_paths = []
    if user_path_str:
        p = Path(user_path_str)
        search_paths.append(p)
        if p.is_dir():
            search_paths.append(p / "pareto.csv")
            search_paths.extend(list(p.rglob("pareto.csv")))
            search_paths.extend(list(p.rglob("pareto_feasible.csv")))

    fallbacks = [
        Path("results/full_production/phase3_constrained/pareto.csv"),
        Path("results/full_production/phase3_constrained"),
        Path("results/phase3_constrained"),
        Path("results/pareto.csv"),
        Path("results"),
    ]
    for fb in fallbacks:
        search_paths.append(fb)
        if fb.is_dir():
            search_paths.append(fb / "pareto.csv")
            search_paths.extend(list(fb.rglob("pareto.csv")))
            search_paths.extend(list(fb.rglob("pareto_feasible.csv")))

    for candidate in search_paths:
        if candidate.is_file() and candidate.exists() and candidate.stat().st_size > 0:
            return candidate

    return None


def run_robustness_analysis(args: argparse.Namespace) -> Path:
    config = load_config(args.config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find pareto.csv dynamically
    pareto_path = find_pareto_csv(args.pareto_csv)

    print(f"=== Starting Robustness & Sensitivity Analysis ===")
    print(f"  Config:        {args.config}")
    print(f"  Pareto CSV:    {pareto_path}")
    print(f"  Output Dir:    {output_dir}")
    print(f"  Perturbations: {args.num_perturbations}")
    print(f"  Workers:       {args.num_workers}")


    if pareto_path is None or not pareto_path.exists():
        pareto_csv_path = find_pareto_csv(getattr(args, "pareto_csv", None))
    else:
        pareto_csv_path = pareto_path


    results = []
    if pareto_csv_path and pareto_csv_path.exists():
        print(f"Loading Pareto candidates from {pareto_csv_path}...")
        df = pd.read_csv(pareto_csv_path)
        for idx, row in df.iterrows():
            design_x = [row[col] for col in DESIGN_VAR_COLUMNS if col in row and not pd.isna(row[col])]
            if len(design_x) != 6:
                continue

            raw_res = {
                "eval_id": idx + 1,
                "status": "SUCCESS",
                "parameters": design_x,
                "design_parameters": dict(zip(DESIGN_VAR_COLUMNS, design_x)),
                "objectives": {
                    "norm_emit_x": float(row.get("norm_emit_x_m_rad", 1.0e-6)),
                    "norm_emit_y": float(row.get("norm_emit_y_m_rad", 1.0e-6)),
                    "sigma_energy": float(row.get("sigma_energy_eV", 1.0e6)),
                },
                "diagnostics": {
                    "norm_emit_x_m_rad": float(row.get("norm_emit_x_m_rad", 1.0e-6)),
                    "norm_emit_y_m_rad": float(row.get("norm_emit_y_m_rad", 1.0e-6)),
                    "sigma_energy_eV": float(row.get("sigma_energy_eV", 1.0e6)),
                    "sigma_x_m": float(row.get("sigma_x_m", 0.5e-3)),
                    "sigma_y_m": float(row.get("sigma_y_m", 0.5e-3)),
                    "sigma_xp_rad": float(row.get("sigma_xp_rad", 0.5e-3)),
                    "sigma_yp_rad": float(row.get("sigma_yp_rad", 0.5e-3)),
                    "sigma_z_m": float(row.get("sigma_z_m", 0.5e-3)),
                    "mean_kinetic_energy_eV": float(row.get("mean_kinetic_energy_eV", 200.0e6)),
                    "transmission_fraction": float(row.get("transmission_fraction", 1.0)),
                },
            }
            res = create_evaluation_result(raw_res, config)
            results.append(res)

    if not results:
        print("WARNING: No Pareto candidates found for robustness analysis. Creating dummy candidate for analysis.")
        dummy_x = [0.15, 1.0, -2.0, 35.0, -40.0, 320.0]
        raw_res = {
            "eval_id": 1,
            "status": "SUCCESS",
            "parameters": dummy_x,
            "design_parameters": dict(zip(DESIGN_VAR_COLUMNS, dummy_x)),
            "objectives": {"norm_emit_x": 1.0e-6, "norm_emit_y": 1.0e-6, "sigma_energy": 0.5e6},
            "diagnostics": {"transmission_fraction": 1.0},
        }
        results.append(create_evaluation_result(raw_res, config))

    rep_candidates = select_representative_pareto_candidates(results)

    if getattr(args, "dry_run", False):
        print(f"[DRY-RUN] Robustness Analysis Plan:")
        print(f"  - Output Directory: {output_dir.resolve()}")
        print(f"  - Candidates ({len(rep_candidates)}): {list(rep_candidates.keys())}")
        print(f"  - Perturbations per Candidate: {args.num_perturbations}")
        print(f"  - Total Planned Evaluations: {len(rep_candidates) * args.num_perturbations}")
        return output_dir

    mock_eval = getattr(args, "mock_evaluator", None)
    if mock_eval is not None:
        evaluator = mock_eval
    else:
        evaluator = BatchEvaluator(
            base_results_dir=output_dir / "work",
            template_dir=".",
            max_workers=args.num_workers,
            timeout=config.execution.timeout_sec,
        )

    summaries = []
    for label, candidate_res in rep_candidates.items():
        nom_x = candidate_res.x_physical
        perturbed_xs = generate_perturbed_parameters(
            nominal_x=nom_x,
            num_perturbations=args.num_perturbations,
            seed=args.seed,
        )

        raw_perturbed = evaluator.evaluate_batch(perturbed_xs, run_id=f"robust_{label}")
        perturbed_results = [create_evaluation_result(r, config) for r in raw_perturbed]

        summary = compute_robustness_summary(label, candidate_res, perturbed_results)
        summaries.append(summary)
        print(f"  ✓ Candidate '{label}': Feasibility P = {summary['probability_of_feasibility']:.2f}, Robust Score = {summary['robust_score']:.3f}")

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(output_dir / "robustness_summary.csv", index=False)
    tex_path = generate_robustness_summary_latex_table(summary_df, output_path=output_dir / "robustness_table.tex")
    print(f"  ✓ Exported LaTeX table -> {output_dir / 'robustness_table.tex'}")
    print(f"=== Robustness Analysis Complete -> Saved in {output_dir.resolve()} ===")
    return output_dir


if __name__ == "__main__":
    args = parse_args()
    run_robustness_analysis(args)
