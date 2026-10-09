"""Argument adapters for recorded campaign comparison and audited verification."""
from datetime import datetime
from pathlib import Path
import time
from typing import Any, List, Tuple
import torch
from mobo_linac.config import load_config
from mobo_linac.metrics.hypervolume import HypervolumeTracker
from mobo_linac.io.run_data import read_run_data, read_comparable_runs
from mobo_linac.metrics.publication import (
    compute_target_distance, TARGET_EMIT_X_M_RAD, TARGET_EMIT_Y_M_RAD, TARGET_SIGMA_E_EV,
    generate_comparison_report, generate_three_phase_report,
)
from mobo_linac.plotting.publication import plot_pareto_front_comparison, plot_verification_comparison

def run_campaign_variant(
    variant_name: str,
    config,
    reporting_ref_point: torch.Tensor,
    use_constraint_filtering: bool = True,
    num_initial_samples: int = 16,
    num_batches: int = 6,
    batch_size: int = 4,
    num_workers: int = 4,
    seed: int = 42,
    base_results_dir: str = "results",
    device: str = "auto",
) -> Tuple[Path, List[Any], HypervolumeTracker, float]:
    """Runs a campaign variant (Phase 2 unconstrained or Phase 3 constrained) using MoboCampaignRunner."""
    from mobo_linac.campaigns.runner import MoboCampaignRunner

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{variant_name}_{timestamp}"
    run_dir = Path(base_results_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.time()

    runner = MoboCampaignRunner(
        config=config,
        run_name=variant_name,
        output_dir=run_dir,
        num_initial_samples=num_initial_samples,
        num_batches=num_batches,
        batch_size=batch_size,
        num_workers=num_workers,
        seed=seed,
        acq_type="qLogNEHVI",
        constrained=use_constraint_filtering,
        export_plots=True,
        device=device,
        reporting_ref_point=reporting_ref_point.tolist(),
    )
    results, tracker, _ = runner.run()

    t_end = time.time()
    wall_clock_sec = t_end - t_start

    return run_dir, results, tracker, wall_clock_sec



def verify_pareto_candidates(results, config, output_dir, mock_evaluator=None, num_workers=None):
    """Use the shared audited rerun service, including explicit mock statuses."""
    from mobo_linac.verification.verifier import run_verification_pipeline
    records, _, _ = run_verification_pipeline(results, config=config,
        output_dir=Path(output_dir) / "verification", mock_evaluator=mock_evaluator, num_workers=num_workers)
    return [dict(record, status=record["verification_status"]) for record in records]


def load_phase_results(phase_dir, config):
    return read_run_data(phase_dir, config=config).results


import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-Phase Linac MOBO Comparison & Pareto Verification Script")
    parser.add_argument("--phase1-dir", type=str, default="results/full_production/phase1_scalarized", help="Phase 1 results directory")
    parser.add_argument("--phase2-dir", type=str, default="results/full_production/phase2_unconstrained", help="Phase 2 results directory")
    parser.add_argument("--phase3-dir", type=str, default="results/full_production/phase3_constrained", help="Phase 3 results directory")
    parser.add_argument("--output-dir", type=str, default="results/full_production/analysis", help="Output analysis directory")
    parser.add_argument("--config", type=str, default="configs/mobo_200MeV.yaml", help="Path to config file")
    parser.add_argument("--num-workers", type=int, default=None, help="Verification workers (default: configuration)")
    return parser.parse_args()



def main():
    args = parse_args()
    config = load_config(args.config)
    output_dir = Path(args.output_dir)
    read_comparable_runs([args.phase1_dir, args.phase2_dir, args.phase3_dir])
    output_dir.mkdir(parents=True, exist_ok=True)

    p1_dir = Path(args.phase1_dir)
    p2_dir = Path(args.phase2_dir)
    p3_dir = Path(args.phase3_dir)

    print(f"Loading results from:")
    print(f"  Phase 1: {p1_dir}")
    print(f"  Phase 2: {p2_dir}")
    print(f"  Phase 3: {p3_dir}")

    res_p1 = load_phase_results(p1_dir, config)
    res_p2 = load_phase_results(p2_dir, config)
    res_p3 = load_phase_results(p3_dir, config)

    # 1. Plot Pareto Front Comparison (Phase 1 vs Phase 2 vs Phase 3)
    fig_dir = output_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    plot_pareto_front_comparison(p2_dir, p3_dir, fig_dir / "pareto_front_comparison.png", phase1_dir=p1_dir)

    # 2. Pareto Candidate Verification on Phase 3
    verification_records = verify_pareto_candidates(res_p3 if res_p3 else res_p2, config, output_dir, num_workers=args.num_workers)
    plot_verification_comparison(output_dir / "verification" / "verification_summary.csv",
                                 fig_dir / "verification_rerun_comparison.png")

    # 3. Generate comprehensive 3-Phase Report
    generate_three_phase_report(
        p1_dir=p1_dir, res_p1=res_p1,
        p2_dir=p2_dir, res_p2=res_p2,
        p3_dir=p3_dir, res_p3=res_p3,
        verification_records=verification_records,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
