"""Shared robustness planning, execution and reporting for CLI and script entry points."""

import json
from pathlib import Path

import pandas as pd

from mobo_linac.metrics.latex import generate_robustness_summary_latex_table
from mobo_linac.metrics.selection import select_representatives
from mobo_linac.robustness.evaluator import RobustnessEvaluator, SOURCE_MAPPING_REASON


def run_robustness_workflow(results, config, output_dir, num_perturbations=20,
                            num_workers=4, seed=42, dry_run=False, batch_evaluator=None):
    output_dir = Path(output_dir)
    config.validate()
    if type(num_perturbations) is not int or num_perturbations <= 0:
        raise ValueError("Robustness analysis requires at least one perturbation")
    from mobo_linac.config import validate_campaign_options
    validate_campaign_options(num_initial_samples=1, num_batches=0, batch_size=1,
                              num_workers=num_workers, seed=seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    if dry_run:
        print("[DRY-RUN] Robustness Analysis Plan:")
        print(f"  - Input Candidates: {len(results)}; selection requires observed feasibility")
        print(f"  - Perturbations per Candidate: {num_perturbations}")
        print(f"  - Source jitter unsupported: {SOURCE_MAPPING_REASON}")
        return output_dir
    if not results:
        raise ValueError("Robustness analysis requires measured candidate history; no candidates found")
    selection = select_representatives(results, config)
    selection.write(output_dir / "representatives.json")
    candidates = dict(selection.roles)
    evaluator = RobustnessEvaluator(config=config, base_output_dir=output_dir,
                                     num_workers=num_workers, timeout=config.execution.timeout_sec)
    summaries = []
    for label, candidate in candidates.items():
        # Keep the historical CLI/script seed for each candidate role.
        summaries.extend(evaluator.evaluate_candidates(
            [candidate], roles=[label], num_perturbations=num_perturbations,
            seed=seed, batch_evaluator=batch_evaluator))
    rows = [{key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
             for key, value in summary.items()} for summary in summaries]
    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "robustness_summary.csv", index=False)
    caption = "Machine tolerance robustness with lattice jitter."
    if any(summary["unsupported_channels"] for summary in summaries):
        caption += " Bunch charge, laser spot size and pulse duration jitter are unsupported for the fixed source distribution."
    if any("mock" in summary["execution_kinds"] for summary in summaries):
        caption += " Synthetic mock evaluations."
    generate_robustness_summary_latex_table(
        frame.rename(columns={"candidate_label": "role", "nominal_emit_x": "nominal_emit_x_m_rad",
                              "nominal_sigma_energy": "nominal_sigma_energy_eV"}),
        output_path=output_dir / "robustness_table.tex", caption=caption)
    print(f"Robustness results cover lattice jitter; source jitter is unsupported. Artifacts: {output_dir.resolve()}")
    return output_dir
