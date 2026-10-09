"""One writer for iteration/final artifacts, scientific metadata and completion."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from mobo_linac.metrics.front import pareto_mask
from mobo_linac.diagnostics import DIAGNOSTIC_NAMES
from mobo_linac.io.durable import atomic_json, atomic_write_text
from mobo_linac.result_schema import ResultSchema
from mobo_linac.io.results import get_training_observations, result_row, rows_to_dataframe
from mobo_linac.metrics.reporting import compute_campaign_metrics_history, reporting_metadata


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
        files = list(dict.fromkeys(self.required + list(extra_required)))
        checksums = {name: hashlib.sha256((self.run_dir / name).read_bytes()).hexdigest() for name in files}
        atomic_json(self.run_dir / "run_complete.json", {
            "schema_version": 1, "status": "completed", "evaluation_count": evaluation_count,
            "elapsed_wall_time_s": elapsed_wall_time_s, "artifacts": checksums,
        })


def validate_run_completion(run_dir):
    """Check the final marker against persisted artifacts without trusting filenames."""
    path = Path(run_dir)
    try:
        marker = json.loads((path / "run_complete.json").read_text())
        if marker.get("schema_version") != 1 or marker.get("status") != "completed" or not marker.get("artifacts"):
            return False
        for name, checksum in marker["artifacts"].items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                return False
            if hashlib.sha256((path / relative).read_bytes()).hexdigest() != checksum:
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False
