"""Read recorded campaigns without inventing identities, feasibility, or conventions."""
from dataclasses import dataclass
import warnings
import json
from pathlib import Path

import numpy as np
import pandas as pd
from botorch.utils.multi_objective.pareto import is_non_dominated

from mobo_linac.io.artifacts import validate_run_completion
from mobo_linac.config import load_config
from mobo_linac.io.results import load_evaluation_results, results_to_dataframe
from mobo_linac.conventions import reporting_metadata, validate_campaign_compatibility
from mobo_linac.result_schema import ResultSchema
from mobo_linac.utils.logger import get_logger

logger = get_logger(__name__)

HISTORY_NAMES = ("candidate_history.json", "candidate_history.csv", "evaluations.csv")
PARETO_NAMES = ("pareto.csv", "pareto_all.csv", "pareto_feasible.csv")


def discover_candidate_source(source=None, root="results"):
    """Explicit paths fail clearly; omitted input selects the newest measured history (with a warning)."""
    if source is not None:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Candidate input not found: {path}")
        if path.is_file():
            return path
        for name in HISTORY_NAMES:
            if (path / name).is_file():
                return path / name
        candidates = [p for name in HISTORY_NAMES for p in path.rglob(name)]
        if not candidates:
            raise FileNotFoundError(f"Measured candidate history not found in {path}")
    else:
        candidates = [p for name in HISTORY_NAMES for p in Path(root).rglob(name)]
    if not candidates:
        return None
    # Choose the latest run, then use the same authoritative history preference as
    # an explicit directory. CSV exports are usually written just after JSON.
    directories = {p.parent for p in candidates}
    directory = max(directories, key=lambda directory: (
        max(p.stat().st_mtime_ns for p in candidates if p.parent == directory), str(directory)))
    selected = next(directory / name for name in HISTORY_NAMES if (directory / name).is_file())
    if source is None or len(directories) > 1:
        # Never silent: an implicit choice in a shared results tree is announced.
        message = f"No explicit candidate run given; using the most recent measured history: {selected}"
        warnings.warn(message, UserWarning, stacklevel=2)
        logger.warning(message)
    return selected


def load_candidates(source, config, root="results"):
    """Join explicit Pareto rows to sibling history; bare legacy CSV statuses stay unknown."""
    path = discover_candidate_source(source, root)
    if path is None:
        return []
    if path.name not in PARETO_NAMES:
        return load_evaluation_results(path, config=config)
    rows = load_evaluation_results(path, config=config)
    history = next((path.parent / name for name in HISTORY_NAMES if (path.parent / name).is_file()), None)
    if history is None:
        return rows
    recorded = load_evaluation_results(history, config=config)
    identified = "evaluation_id" in pd.read_csv(path, nrows=0).columns
    if identified:
        def key(result):
            return result.run_id, result.evaluation_id
    else:
        # Archived Pareto exports lack identities; fall back to exact recorded values.
        def key(result):
            return tuple(result.x_physical), tuple(result.objectives_physical or [])
    wanted = {key(row) for row in rows}
    matched = [result for result in recorded if key(result) in wanted]
    if {key(result) for result in matched} != wanted:
        raise ValueError("Pareto rows do not match recorded candidate history.")
    if identified:
        by_key = {key(result): result for result in matched}
        if any(by_key[key(row)].x_physical != row.x_physical for row in rows):
            raise ValueError("Pareto rows do not match recorded candidate history.")
    if path.name == "pareto_feasible.csv" and any(
        result.simulation_valid is not True or result.physically_feasible is not True for result in matched
    ):
        raise ValueError("Feasible Pareto export conflicts with candidate history.")
    return matched


@dataclass
class RunData:
    directory: Path
    config: object
    results: list
    metadata: dict
    hypervolume: pd.DataFrame

    def valid_results(self, feasible=False):
        schema = ResultSchema.from_config(self.config)
        records = []
        for result in self.results:
            values = schema.extract(result.objectives_physical)
            if (result.simulation_valid is True and len(result.x_physical) == len(schema.design_columns)
                    and np.isfinite(result.x_physical).all() and values is not None and np.isfinite(values).all()
                    and (not feasible or result.physically_feasible is True)):
                records.append(result)
        return records

    def pareto(self, feasible=False):
        records = self.valid_results(feasible)
        frame = results_to_dataframe(records, self.config)
        if records:
            schema = ResultSchema.from_config(self.config)
            values = schema.transform([r.objectives_physical for r in records])
            frame = frame.loc[is_non_dominated(values).numpy()]
        return frame.reset_index(drop=True)


def read_run_data(directory, config=None, legacy_reporting_metadata=None):
    """Require measured history and explicit reporting metadata for scientific reports.

    Legacy callers may supply a complete convention explicitly; no reference or
    feasibility is inferred from filenames, magnitudes, or train_X/train_Y rows.
    """
    directory = Path(directory)
    if (directory / "run_complete.json").exists():
        if not validate_run_completion(directory):
            raise ValueError("Run completion marker conflicts with recorded artifacts.")
    if config is None:
        path = next((directory / name for name in ("config.json", "config.yaml") if (directory / name).is_file()), None)
        if path is None:
            raise FileNotFoundError(f"Run configuration not found in {directory}")
        config = load_config(path)
    config.validate()
    path = directory / "reporting_metadata.json"
    metadata = json.loads(path.read_text()) if path.is_file() else legacy_reporting_metadata
    if metadata is None:
        raise ValueError(f"Explicit reporting metadata required for {directory}")
    validate_campaign_compatibility(metadata, metadata)
    expected = reporting_metadata(config, metadata["reporting_ref_point"], metadata.get("reference_policy", "explicit"))
    validate_campaign_compatibility(metadata, expected)
    history = next((directory / name for name in HISTORY_NAMES if (directory / name).is_file()), None)
    if history is None:
        raise FileNotFoundError(f"Measured candidate history not found in {directory}")
    results = load_evaluation_results(history, config=config)
    identities = [(r.run_id, r.evaluation_id) for r in results]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate candidate identity in run history.")
    hypervolume = pd.read_csv(directory / "hypervolume.csv")
    required = {"iteration", "num_valid_points", "num_feasible_points", "all_point_hypervolume", "feasible_hypervolume"}
    if not required.issubset(hypervolume.columns):
        raise ValueError("Hypervolume export lacks the explicit reporting columns.")
    if len(hypervolume) and not np.isfinite(hypervolume[list(required)].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite recorded hypervolume or observation counts.")
    for column, expected_reference in (
        ("reporting_ref_point_model", metadata["reporting_ref_point"]),
        ("reporting_ref_point_physical", ResultSchema.from_config(config).transform(metadata["reporting_ref_point"]).tolist()),
    ):
        if column in hypervolume:
            import ast
            for value in hypervolume[column]:
                try:
                    reference = ast.literal_eval(value) if isinstance(value, str) else value
                except (SyntaxError, ValueError) as error:
                    raise ValueError("Malformed hypervolume reporting reference.") from error
                if reference != expected_reference:
                    raise ValueError("Hypervolume reference disagrees with reporting metadata.")
    if len(hypervolume):
        counts = hypervolume[["num_valid_points", "num_feasible_points"]].to_numpy(dtype=float)
        if ((counts < 0).any() or (counts != np.floor(counts)).any()
                or (counts[:, 1] > counts[:, 0]).any() or (np.diff(counts, axis=0) < 0).any()
                or (hypervolume[["all_point_hypervolume", "feasible_hypervolume"]] < 0).any().any()):
            raise ValueError("Invalid recorded hypervolume or observation counts.")
    run = RunData(directory, config, results, metadata, hypervolume)
    if len(hypervolume):
        final = hypervolume.iloc[-1]
        if final.num_valid_points != len(run.valid_results()) or final.num_feasible_points != len(run.valid_results(True)):
            raise ValueError("Hypervolume observation counts disagree with candidate history.")
    return run


def read_comparable_runs(directories):
    runs = [directory if isinstance(directory, RunData) else read_run_data(directory) for directory in directories]
    for run in runs:
        validate_campaign_compatibility(run.metadata, reporting_metadata(run.config, run.metadata["reporting_ref_point"]))
    for run in runs[1:]:
        validate_campaign_compatibility(runs[0].metadata, run.metadata)
    return runs
