"""One writer for iteration/final artifacts, scientific metadata and completion."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import torch
from botorch.utils.multi_objective.pareto import is_non_dominated
from mobo_linac.diagnostics import DIAGNOSTIC_NAMES
from mobo_linac.result_schema import ResultSchema
from mobo_linac.io.results import get_train_tensors, results_to_dataframe
from mobo_linac.metrics.reporting import compute_campaign_metrics_history, reporting_metadata


def atomic_json(path, data):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


class RunArtifactWriter:
    """pareto.csv always aliases all-valid points; feasibility has its own file."""
    def __init__(self, run_dir, config):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.schema = ResultSchema.from_config(config)
        self.required = []

    def invalidate_completion(self):
        (self.run_dir / "run_complete.json").unlink(missing_ok=True)

    def write(self, results, tracker=None, hypervolumes=None, elapsed_wall_times=None,
              elapsed_wall_time_s=None, reference_policy="initial_design", timing_scope=None, extra_columns=None):
        self.invalidate_completion()
        self.required = []
        def csv(name, frame):
            frame.to_csv(self.run_dir / name, index=False)
            self.required.append(name)
        frame = results_to_dataframe(results, self.schema)
        for name, values in (extra_columns or {}).items():
            if name in frame.columns or len(values) != len(results):
                raise ValueError("Extra artifact columns must be distinct and align with records.")
            frame[name] = values
        history = self.run_dir / "candidate_history.json"
        history.write_text(json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8")
        self.required.append(history.name)
        csv("candidate_history.csv", frame)
        csv("evaluations.csv", frame)
        x, y, feasible = get_train_tensors(results, config=self.schema)
        csv("train_X.csv", pd.DataFrame(x.numpy(), columns=self.schema.design_columns))
        csv("train_Y.csv", pd.DataFrame(y.numpy(), columns=self.schema.model_columns))
        valid = frame[frame.simulation_valid == True]
        csv("objectives_physical.csv", valid[list(self.schema.physical_columns)])
        csv("objectives_model.csv", valid[list(self.schema.model_columns)])
        csv("constraints.csv", frame[["evaluation_id", "run_id", *DIAGNOSTIC_NAMES, "physically_feasible"]])
        csv("failures.csv", frame[(frame.simulation_valid != True) | (frame.physically_feasible != True)])
        def pareto(xs, ys):
            mask = is_non_dominated(ys) if len(ys) else torch.zeros(0, dtype=torch.bool)
            data = np.hstack([xs[mask].numpy(), self.schema.transform(ys[mask]).numpy()])
            return pd.DataFrame(data, columns=self.schema.design_columns + self.schema.physical_columns)
        all_points = pareto(x, y)
        csv("pareto.csv", all_points)
        csv("pareto_all.csv", all_points)
        csv("pareto_feasible.csv", pareto(x[feasible], y[feasible]))
        if tracker is not None:
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
        else:
            csv("hypervolume.csv", pd.DataFrame({"hypervolume": hypervolumes if hypervolumes is not None else []}))
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
