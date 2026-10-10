"""
Scalarized Multi-Weight Suite Module for mobo_linac.

Runs the configured Phase 1 weighted-sum cases (``scalarized_cases`` in the
configuration), aggregates their measured histories, and exports the case table.
Each case's seed is the base seed plus its configured ``seed_offset``, so a case gives
the same result whether it runs alone or within the full suite.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import torch

from mobo_linac.campaigns.runner import campaign_runner
from mobo_linac.campaign_options import Acquisition, normalize_scalar_weights, validate_campaign_options
from mobo_linac.config import MoboConfig, config_from_dict, load_config
from mobo_linac.io.artifacts import validate_run_completion
from mobo_linac.metrics.exports import RunArtifactWriter
from mobo_linac.utils.durable import atomic_csv, atomic_json
from mobo_linac.io.checkpoint import load_run_checkpoint
from mobo_linac.io.results import get_train_tensors, load_evaluation_results
from mobo_linac.metrics.hypervolume import HypervolumeTracker
from mobo_linac.conventions import validate_campaign_compatibility

from mobo_linac.utils.logger import get_logger
from mobo_linac.io.run_data import read_run_data
from mobo_linac.metrics.latex import generate_phase1_cases_latex_table
from mobo_linac.metrics.publication import scalarized_case_statistics

logger = get_logger(__name__)

SEED_POLICIES = ("case_offset", "legacy_subset_index")


def get_scalarized_case(config: MoboConfig, case_id: str):
    """Configured scalarization case by id."""
    if case_id not in config.scalarized_cases:
        raise ValueError(f"Unknown scalarized case '{case_id}'. Configured cases: {list(config.scalarized_cases)}")
    case = config.scalarized_cases[case_id]
    normalize_scalar_weights(case.weights, len(config.objectives))
    return case


def case_seed(config: MoboConfig, case_id: str, base_seed: int, position: int, policy: str = "case_offset") -> int:
    """Seed for a case: stable configured offset, or the archived subset-position rule."""
    if policy not in SEED_POLICIES:
        raise ValueError(f"Unsupported suite seed policy: {policy}")
    if policy == "legacy_subset_index":
        return base_seed + 100 * position
    return base_seed + get_scalarized_case(config, case_id).seed_offset


def _recorded_case(path: Path) -> Tuple[List[float], int]:
    """Weights and seed recorded by the case's own campaign checkpoint."""
    checkpoint = load_run_checkpoint(path)
    if checkpoint is None or checkpoint.campaign.scalar_weights is None or checkpoint.campaign.seed is None:
        raise ValueError(f"Scalarized case {path} lacks recorded weights/seed; it cannot be aggregated.")
    return [float(w) for w in checkpoint.campaign.scalar_weights], int(checkpoint.campaign.seed)


def aggregate_scalarized_cases(
    base_dir: Union[str, Path],
    case_dirs: Optional[Sequence[Union[str, Path]]] = None,
) -> Dict[str, Any]:
    """
    Aggregate completed scalarized cases into one dataset.

    Produces in base_dir: ``cases_summary.csv/json`` (weights and seeds read from each
    case's checkpoint), merged histories, Pareto fronts, and ``hypervolume.csv`` with one
    row per case boundary: the union of all cases' observations up to and including that
    case, against the shared recorded reporting reference.
    """
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    if case_dirs is not None:
        discovered = [(Path(p).name, Path(p)) for p in case_dirs if Path(p).is_dir()]
    else:
        discovered = [(sub.name, sub) for sub in sorted(base_path.iterdir())
                      if sub.is_dir() and (sub / "evaluations.csv").exists()]
        if not discovered and (base_path / "evaluations.csv").exists():
            discovered = [(base_path.name, base_path)]

    convention = None
    aggregate_config = None
    for _, path in discovered:
        meta_path = path / "reporting_metadata.json"
        if not meta_path.exists():
            raise ValueError("Scalarized aggregation requires explicit reporting metadata; archived runs are not inferred.")
        if not validate_run_completion(path):
            raise ValueError("Scalarized aggregation requires completed, unchanged run artifacts.")
        meta = json.loads(meta_path.read_text())
        validate_campaign_compatibility(meta, meta)
        if convention is not None:
            validate_campaign_compatibility(convention, meta)
        convention = meta
        if aggregate_config is None:
            aggregate_config = config_from_dict(json.loads((path / "config.json").read_text()))
    if aggregate_config is not None:
        # Configured case order first, then any additional recorded cases.
        order = {case_id: index for index, case_id in enumerate(aggregate_config.scalarized_cases)}
        discovered.sort(key=lambda item: (order.get(item[0], len(order)), item[0]))

    summary_rows = []
    for case_key, case_path in discovered:
        run = read_run_data(case_path)
        stats = scalarized_case_statistics(run)
        weights, seed = _recorded_case(case_path)
        case = run.config.scalarized_cases.get(case_key)
        summary_rows.append({
            "case_id": case_key,
            "name": case.label if case else case_key,
            "description": case.description if case else "",
            "weights": json.dumps(weights),
            "seed": seed,
            **{f"w_{obj.name}": weight for obj, weight in zip(run.config.objectives, weights)},
            "num_evaluations": stats["n_eval"],
            "num_valid": stats["n_valid"],
            "num_feasible": stats["n_feas"],
            "feasible_fraction_pct": round(stats["feas_pct"], 2),
            # Objective extrema in physical (SI) units: all-valid Pareto and feasible observations.
            "objective_order": json.dumps([obj.explicit_name for obj in run.config.objectives]),
            "objective_units": json.dumps({obj.explicit_name: obj.unit for obj in run.config.objectives}),
            **{f"min_{name}": value for name, value in stats["all_valid_extrema"].items()},
            **{f"min_feasible_{name}": None if np.isnan(value) else value
               for name, value in stats["feasible_extrema"].items()},
            "final_feasible_hv": round(stats["final_hv"], 6),
        })

    atomic_csv(base_path / "cases_summary.csv", pd.DataFrame(summary_rows))
    atomic_json(base_path / "cases_summary.json", summary_rows)

    if discovered:
        records, case_labels = [], []
        tracker = HypervolumeTracker(convention["reporting_ref_point"], aggregate_config)
        for case, path in discovered:
            loaded = load_evaluation_results(path / "evaluations.csv", aggregate_config)
            records.extend(loaded)
            case_labels.extend([case] * len(loaded))
            _, y, feasible = get_train_tensors(records, config=aggregate_config)
            tracker.track_iteration(len(tracker.history), y, feasible)
        writer = RunArtifactWriter(base_path, aggregate_config)
        writer.write(records, tracker, reference_policy="shared_suite_reference", timing_scope="unknown_aggregate_wall_time", extra_columns={"case": case_labels})
        aggregate_config.save_json(base_path / "config.json")
        aggregate_config.save_yaml(base_path / "config.yaml")
        writer.complete(len(records), None, ["config.json", "config.yaml", "cases_summary.csv", "cases_summary.json"])

    return {
        "num_cases": len(summary_rows),
        "cases": [r["case_id"] for r in summary_rows],
        "total_evaluations": sum(r["num_evaluations"] for r in summary_rows),
        "total_feasible": sum(r["num_feasible"] for r in summary_rows),
    }


def run_scalarized_suite(
    config: Optional[Union[str, Path]] = None,
    n_iterations: int = 20,
    batch_size: int = 8,
    num_initial_samples: int = 16,
    num_workers: Optional[int] = 4,
    seed: int = 42,
    output_dir: Union[str, Path] = "results/full_production/phase1_scalarized",
    device: str = "auto",
    cases_to_run: Optional[Sequence[str]] = None,
    resume: bool = False,
    evaluator: Optional[Any] = None,
    export_paper_table_dir: Optional[Union[str, Path]] = None,
    reporting_ref_point: Optional[Sequence[float]] = None,
    seed_policy: str = "case_offset",
) -> Dict[str, Any]:
    """
    Execute the configured scalarized cases and aggregate them.

    Args:
        config: Path to the configuration (its ``scalarized_cases`` define the suite).
        n_iterations: BO iterations per case.
        batch_size: Candidate proposal batch size q per iteration.
        num_initial_samples: Sobol initialization points per case.
        num_workers: Parallel workers for ASTRA.
        seed: Base seed; a case uses ``seed + seed_offset`` (``case_offset`` policy).
            ``legacy_subset_index`` reproduces archived runs that used ``seed + 100 * position``.
        output_dir: Base output directory (cases saved under subdirectories).
        device: PyTorch device ('auto', 'cuda', 'cpu').
        cases_to_run: Case ids to run; defaults to every configured case.
        resume: Whether to resume existing case runs from checkpoints.
        evaluator: Optional custom evaluator (e.g. a mock evaluator for testing).
        export_paper_table_dir: Optional directory to copy phase1_cases_table.tex to.
        reporting_ref_point: Optional fixed model-space reference shared by all cases.

    Returns:
        Aggregation metadata dictionary.
    """
    config = load_config(config) if not isinstance(config, MoboConfig) else config
    validate_campaign_options(num_initial_samples=num_initial_samples, num_batches=n_iterations,
                              batch_size=batch_size, num_workers=num_workers, seed=seed)
    if not config.scalarized_cases:
        raise ValueError("The configuration defines no scalarized_cases.")
    target_cases = list(cases_to_run) if cases_to_run else list(config.scalarized_cases)
    for case_id in target_cases:
        get_scalarized_case(config, case_id)
    seeds = {case_id: case_seed(config, case_id, seed, position, seed_policy)
             for position, case_id in enumerate(target_cases)}
    if max(seeds.values()) >= 2**32:
        raise ValueError("Suite case seeds must be less than 2**32.")
    if reporting_ref_point is not None:
        ref = torch.as_tensor(reporting_ref_point, dtype=torch.double)
        if ref.shape != (len(config.objectives),) or not torch.isfinite(ref).all():
            raise ValueError("Reporting reference must match finite configured objectives.")
    base_out = Path(output_dir)
    base_out.mkdir(parents=True, exist_ok=True)

    logger.info(f"Scalarized suite cases: {target_cases} (seed policy {seed_policy}); "
                f"{n_iterations} iterations of q={batch_size} after {num_initial_samples} initial samples; output {base_out}")

    shared_reference = list(reporting_ref_point) if reporting_ref_point is not None else None
    for index, case_id in enumerate(target_cases):
        case = config.scalarized_cases[case_id]
        logger.info(f"[{index + 1}/{len(target_cases)}] Case '{case_id}' ({case.label}): weights {case.weights}, seed {seeds[case_id]}")
        options = {"num_initial_samples": num_initial_samples, "num_batches": n_iterations, "batch_size": batch_size,
                   "num_workers": num_workers, "seed": seeds[case_id], "acquisition": Acquisition.qLogNEI.value}
        runner = campaign_runner(config, options, optimization_mode="scalarized_bo", run_name=f"scalarized_{case_id}",
                                 output_dir=base_out / case_id, scalar_weights=case.weights,
                                 reporting_ref_point=shared_reference, resume=resume, evaluator=evaluator, device=device)
        _, tracker, _ = runner.run()
        if shared_reference is None:
            shared_reference = tracker.reporting_ref_point.tolist()

    agg_meta = aggregate_scalarized_cases(base_out)
    logger.info(f"Aggregated {agg_meta['num_cases']} cases -> {agg_meta['total_evaluations']} evaluations")
    generate_phase1_cases_latex_table(base_out / "cases_summary.csv", base_out / "phase1_cases_table.tex")
    if export_paper_table_dir is not None:
        paper_tab = Path(export_paper_table_dir) / "phase1_cases_table.tex"
        generate_phase1_cases_latex_table(base_out / "cases_summary.csv", paper_tab)
        logger.info(f"Exported LaTeX summary table to {paper_tab}")
    return agg_meta
