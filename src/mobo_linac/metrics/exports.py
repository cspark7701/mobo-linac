"""Run artifact export: candidate history, training views, Pareto fronts, metrics and metadata.

``RunArtifactWriter`` writes every per-run artifact atomically (one serialization per alias)
and publishes the completion marker only after all required files exist.
"""
from pathlib import Path
from typing import Dict, List, Union

import numpy as np
import pandas as pd
import torch

from mobo_linac.conventions import reporting_metadata
from mobo_linac.diagnostics import DIAGNOSTIC_NAMES
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.artifacts import write_completion_marker
from mobo_linac.io.results import get_train_tensors, get_training_observations, result_row, rows_to_dataframe
from mobo_linac.metrics.front import pareto_mask
from mobo_linac.metrics.hypervolume import HypervolumeTracker
from mobo_linac.metrics.reporting import compute_campaign_metrics_history
from mobo_linac.result_schema import ResultSchema
from mobo_linac.utils.durable import atomic_json, atomic_write_text


class RunArtifactWriter:
    """pareto.csv always aliases all-valid points; feasibility has its own file."""
    def __init__(self, run_dir, config):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.schema = ResultSchema.from_config(config)
        self.required = []
        # Evaluation records are immutable once journaled, so their CSV row and JSON form
        # are converted once and reused by every later iteration export.
        self._cache = {}

    def _converted(self, result):
        key = (result.run_id, result.evaluation_id)
        cached = self._cache.get(key)
        if cached is None or cached[0] is not result:
            cached = (result, result_row(result, self.schema), result.to_dict())
            self._cache[key] = cached
        return cached

    def invalidate_completion(self):
        (self.run_dir / "run_complete.json").unlink(missing_ok=True)

    def write(self, results, tracker, elapsed_wall_times=None,
              elapsed_wall_time_s=None, reference_policy="initial_design", timing_scope=None, extra_columns=None):
        """Write every run artifact; the fixed-reference tracker is required so that
        hypervolume.csv always has the explicit reporting schema."""
        if tracker is None:
            raise TypeError("RunArtifactWriter.write requires the fixed-reference HypervolumeTracker.")
        self.invalidate_completion()
        self.required = []
        def csv(names, frame):
            text = frame.to_csv(index=False)  # aliases share one serialization
            for name in ([names] if isinstance(names, str) else names):
                atomic_write_text(self.run_dir / name, text)
                self.required.append(name)
        converted = [self._converted(result) for result in results]
        frame = rows_to_dataframe([row for _, row, _ in converted], self.schema)
        for name, values in (extra_columns or {}).items():
            if name in frame.columns or len(values) != len(results):
                raise ValueError("Extra artifact columns must be distinct and align with records.")
            frame[name] = values
        history = self.run_dir / "candidate_history.json"
        # Failure records may hold NaN diagnostics; JSON history records them as NaN.
        atomic_json(history, [record for _, _, record in converted], allow_nan=True)
        self.required.append(history.name)
        csv(("candidate_history.csv", "evaluations.csv"), frame)
        observed = get_training_observations(results, config=self.schema)
        x, y, feasible = observed.train_X, observed.train_Y, observed.feasible
        identities = observed.evaluation_ids
        csv("train_X.csv", pd.DataFrame(x.numpy(), columns=self.schema.design_columns))
        csv("train_Y.csv", pd.DataFrame(y.numpy(), columns=self.schema.model_columns))
        valid = frame[frame.simulation_valid == True]
        csv("objectives_physical.csv", valid[list(self.schema.physical_columns)])
        csv("objectives_model.csv", valid[list(self.schema.model_columns)])
        csv("constraints.csv", frame[["evaluation_id", "run_id", *DIAGNOSTIC_NAMES, "physically_feasible"]])
        csv("failures.csv", frame[(frame.simulation_valid != True) | (frame.physically_feasible != True)])
        def pareto(rows):
            xs, ys = x[rows], y[rows]
            mask = pareto_mask(ys)
            data = np.hstack([xs[mask].numpy(), self.schema.transform(ys[mask]).numpy()])
            frame = pd.DataFrame(data, columns=self.schema.design_columns + self.schema.physical_columns)
            kept = [identities[index] for index, keep in zip(rows.nonzero().flatten().tolist(), mask.tolist()) if keep]
            # Rows carry their evaluation identity so readers join exactly to the history.
            frame.insert(0, "evaluation_id", [evaluation_id for _, evaluation_id in kept])
            frame.insert(0, "run_id", [run_id for run_id, _ in kept])
            return frame
        all_points = pareto(torch.ones(len(identities), dtype=torch.bool))
        csv(("pareto.csv", "pareto_all.csv"), all_points)
        csv("pareto_feasible.csv", pareto(feasible))
        csv("hypervolume.csv", tracker.to_dataframe())
        meta = reporting_metadata(self.config, tracker.reporting_ref_point.tolist(), reference_policy)
        meta["timing_scope"] = timing_scope or ("active_sessions" if elapsed_wall_time_s is not None else "unknown")
        atomic_json(self.run_dir / "reporting_metadata.json", meta)
        self.required.append("reporting_metadata.json")
        metrics = compute_campaign_metrics_history(results, self.schema.scales,
                    meta["reporting_ref_point_normalized"], elapsed_wall_times)
        if len(metrics) and elapsed_wall_time_s is not None:
            metrics.loc[metrics.index[-1], "total_wallclock_s"] = elapsed_wall_time_s
        csv("metrics_history.csv", metrics)
        return {"json": history, "csv": self.run_dir / "candidate_history.csv"}

    def complete(self, evaluation_count, elapsed_wall_time_s, extra_required=()):
        """Publish only after every required dataset, checkpoint and requested plot exists."""
        self.invalidate_completion()
        write_completion_marker(self.run_dir, evaluation_count, elapsed_wall_time_s,
                                list(dict.fromkeys(self.required + list(extra_required))))


def save_evaluation_results(
    results: List[EvaluationResult],
    run_dir: Union[str, Path],
    *,
    config,
    reporting_ref_point,
    reference_policy: str = "explicit",
) -> Dict[str, Path]:
    """Save candidate history, Pareto fronts and fixed-reference metrics for a record set,
    tracked as a single cumulative iteration against an explicit reporting reference."""
    tracker = HypervolumeTracker(reporting_ref_point, config)
    _, y, feasible = get_train_tensors(results, config=config)
    tracker.track_iteration(0, y, feasible)
    return RunArtifactWriter(run_dir, config).write(results, tracker, reference_policy=reference_policy)
