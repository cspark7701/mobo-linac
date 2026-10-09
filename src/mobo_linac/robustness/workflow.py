"""Shared robustness planning, execution and reporting for CLI and script entry points."""

import json
from pathlib import Path

import pandas as pd

from mobo_linac.utils.durable import atomic_csv
from mobo_linac.utils.logger import get_logger

logger = get_logger(__name__)
from mobo_linac.metrics.latex import generate_robustness_summary_latex_table
from mobo_linac.metrics.selection import select_representatives
from mobo_linac.robustness.evaluator import RobustnessEvaluator, SOURCE_MAPPING_REASON, configured_perturbation_spec
from mobo_linac.campaign_options import validate_campaign_options


def run_robustness_workflow(results, config, output_dir, num_perturbations=20,
                            num_workers=4, seed=42, dry_run=False, evaluator=None, spec=None):
    """Select representatives, evaluate perturbed states and export summaries.

    All representative roles form one plan; per-candidate seeds follow the
    specification's ``seed_policy`` (``common`` reuses ``seed`` for every role).
    """
    output_dir = Path(output_dir)
    config.validate()
    if type(num_perturbations) is not int or num_perturbations <= 0:
        raise ValueError("Robustness analysis requires at least one perturbation")
    validate_campaign_options(num_initial_samples=1, num_batches=0, batch_size=1,
                              num_workers=num_workers, seed=seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = spec or configured_perturbation_spec(config)
    spec.validate_for(config)
    if dry_run:
        logger.info("[DRY-RUN] Robustness Analysis Plan:")
        logger.info(f"  - Input Candidates: {len(results)}; selection requires observed feasibility")
        logger.info(f"  - Perturbations per Candidate: {num_perturbations}")
        logger.info(f"  - Lattice channels: {[c.channel for c in spec.lattice]}; seed policy: {spec.seed_policy}")
        logger.info(f"  - Source jitter unsupported: {SOURCE_MAPPING_REASON}")
        return output_dir
    if not results:
        raise ValueError("Robustness analysis requires measured candidate history; no candidates found")
    selection = select_representatives(results, config)
    selection.write(output_dir / "representatives.json")
    candidates = dict(selection.roles)
    study = RobustnessEvaluator(config=config, base_output_dir=output_dir, num_workers=num_workers,
                                timeout=config.execution.timeout_sec, spec=spec)
    summaries = study.evaluate_candidates(
        list(candidates.values()), roles=list(candidates), num_perturbations=num_perturbations,
        seed=seed, evaluator=evaluator)
    rows = [{key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
             for key, value in summary.items()} for summary in summaries]
    frame = pd.DataFrame(rows)
    atomic_csv(output_dir / "robustness_summary.csv", frame)
    caption = "Machine tolerance robustness with lattice jitter."
    unsupported = sorted({channel for summary in summaries for channel in summary["unsupported_channels"]})
    if unsupported:
        caption += " Source jitter (" + ", ".join(unsupported) + ") is unsupported for the fixed source distribution."
    if any("mock" in summary["execution_kinds"] for summary in summaries):
        caption += " Synthetic mock evaluations."
    generate_robustness_summary_latex_table(
        frame.rename(columns={"candidate_label": "role"}),
        output_path=output_dir / "robustness_table.tex", caption=caption, config=config)
    logger.info(f"Robustness results cover lattice jitter; source jitter is unsupported. Artifacts: {output_dir.resolve()}")
    return output_dir
