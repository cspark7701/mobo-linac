"""
Result I/O, Serialization, DataFrame Conversions, and Checkpoint Management.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import torch

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.result_schema import ResultSchema
from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS, DIAGNOSTIC_NAMES, diagnostic_observations, finite_measurement, normalize_diagnostics

METADATA_COLUMNS = ["evaluation_id", "run_id", "simulation_valid", "physically_feasible", "failure_category",
                    "failure_reason", "runtime_s", "work_dir", "attempt_id", "manifest_path", "attempt_history"]
TELEMETRY_COLUMNS = ["n_particles_initial", "n_particles_final"]


def result_row(res: EvaluationResult, schema: ResultSchema) -> Dict[str, Any]:
    """One flat record (CSV row) for an evaluation; absent values are NaN."""
    row: Dict[str, Any] = {
        "evaluation_id": res.evaluation_id,
        "run_id": res.run_id,
        "simulation_valid": res.simulation_valid,
        "physically_feasible": res.physically_feasible,
        "failure_category": res.failure_category,
        "failure_reason": res.failure_reason or "",
        "runtime_s": res.runtime_s,
        "work_dir": res.work_dir,
        "attempt_id": res.attempt_id, "manifest_path": res.manifest_path,
        "attempt_history": json.dumps(res.attempt_history),
    }
    for values, columns in ((res.x_physical, schema.design_columns),
                            (res.objectives_physical, schema.physical_columns),
                            (res.objectives_model, schema.model_columns)):
        for idx, col in enumerate(columns):
            row[col] = float(values[idx]) if values and idx < len(values) else np.nan
    # Canonical diagnostic channels and particle-count telemetry; absent values stay NaN.
    diags = normalize_diagnostics(res.diagnostics)
    for name in DIAGNOSTIC_NAMES:
        row.setdefault(name, diags.get(name, np.nan))
    for name in TELEMETRY_COLUMNS:  # archived results stored counts with diagnostics
        row.setdefault(name, res.telemetry.get(name, diags.get(name, np.nan)))
    return row


def rows_to_dataframe(rows: List[Dict[str, Any]], schema: ResultSchema) -> pd.DataFrame:
    columns = list(dict.fromkeys(METADATA_COLUMNS + list(schema.design_columns) + list(schema.physical_columns)
                                 + list(schema.model_columns) + list(DIAGNOSTIC_NAMES) + TELEMETRY_COLUMNS))
    return pd.DataFrame(rows, columns=columns)


def results_to_dataframe(
    results: List[EvaluationResult],
    config: Any,
) -> pd.DataFrame:
    """
    Converts a list of EvaluationResult objects into a structured Pandas DataFrame.
    Column headers come from the configuration (or an explicit ResultSchema).
    """
    schema = ResultSchema.from_config(config)
    return rows_to_dataframe([result_row(res, schema) for res in results], schema)


@dataclass(frozen=True)
class TrainingObservations:
    """One identity-ordered selection shared by design, objectives and diagnostics."""

    evaluation_ids: Tuple[Tuple[str, str], ...]
    train_X: torch.Tensor
    train_Y: torch.Tensor
    feasible: torch.Tensor
    constraints: Optional[torch.Tensor] = None


def get_training_observations(
    results: List[EvaluationResult],
    exclude_invalid: bool = True,
    require_diagnostics: bool = False,
    *,
    config,
) -> TrainingObservations:
    """Select observed finite rows without fabricating missing diagnostic values.

    Constrained training uses a complete-case policy across the seven diagnostic
    channels. Objective-only training retains finite archived objective records.
    Selection preserves evaluation order and identifies rows by run/evaluation ID.
    """
    schema = ResultSchema.from_config(config)
    selected = []
    diagnostic_rows = []
    identities = set()
    for result in results:
        if exclude_invalid and not result.simulation_valid:
            continue
        if not result.x_physical or not result.objectives_model:
            continue
        if not all(finite_measurement(value) for value in result.x_physical + result.objectives_model):
            continue
        if len(result.x_physical) != len(schema.design_columns) or len(result.objectives_model) != len(schema.signs):
            raise ValueError("Training observation width does not match result schema.")
        observed = diagnostic_observations(result.diagnostics) if require_diagnostics else None
        if require_diagnostics and observed is None:
            continue
        identity = (result.run_id, result.evaluation_id)
        if identity in identities:
            raise ValueError("Duplicate evaluation identity in training observations.")
        identities.add(identity)
        selected.append(result)
        if require_diagnostics:
            diagnostic_rows.append(observed)
    train_X = torch.tensor([r.x_physical for r in selected], dtype=torch.double) if selected else torch.empty((0, len(schema.design_columns)), dtype=torch.double)
    train_Y = torch.tensor([r.objectives_model for r in selected], dtype=torch.double) if selected else torch.empty((0, len(schema.signs)), dtype=torch.double)
    feasible = torch.tensor([r.physically_feasible is True for r in selected], dtype=torch.bool)
    constraints = None
    if require_diagnostics:
        constraints = (torch.tensor(diagnostic_rows, dtype=torch.double) if selected
                       else torch.empty((0, len(DIAGNOSTIC_CHANNELS)), dtype=torch.double))
    return TrainingObservations(tuple((r.run_id, r.evaluation_id) for r in selected),
                                train_X, train_Y, feasible, constraints)


def get_train_tensors(
    results: List[EvaluationResult],
    exclude_invalid: bool = True,
    *,
    config,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Return finite objective observations; constrained callers use the shared selector."""
    observed = get_training_observations(results, exclude_invalid, config=config)
    return observed.train_X, observed.train_Y, observed.feasible


def get_constraint_tensors(
    results: List[EvaluationResult],
    exclude_invalid: bool = True,
    *,
    config,
) -> torch.Tensor:
    """Return complete measured diagnostics in canonical order, without imputation.

    Use get_training_observations(require_diagnostics=True) to obtain identically
    selected design/objective rows and their stable evaluation identities.
    """
    return get_training_observations(results, exclude_invalid, require_diagnostics=True, config=config).constraints



def load_evaluation_results(
    history_path: Union[str, Path],
    config: Any,
) -> List[EvaluationResult]:
    """
    Loads list of EvaluationResult objects from a JSON or CSV file.
    CSV columns are bound through the configured (or explicit legacy) ResultSchema.
    """
    path = Path(history_path)
    if not path.exists():
        raise FileNotFoundError(f"Result file not found: {path}")

    schema = ResultSchema.from_config(config)
    design_var_cols = list(schema.design_columns)
    physical_obj_cols = list(schema.physical_columns)
    model_obj_cols = list(schema.model_columns)

    n_objs = len(physical_obj_cols)

    if path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [EvaluationResult.from_dict(d) for d in data]
    elif path.suffix == ".csv":
        with path.open(encoding="utf-8") as stream:
            legacy_header = stream.readline().startswith("# ")
        df = pd.read_csv(path, float_precision="round_trip")
        if legacy_header:
            df.rename(columns={df.columns[0]: df.columns[0][2:]}, inplace=True)
        if not set(design_var_cols).issubset(df.columns):
            raise ValueError("CSV lacks named design columns required by the result schema.")
        results = []
        # Plain row dictionaries avoid constructing one pandas Series per record.
        for row_index, row in enumerate(df.to_dict("records")):
            x_phys = [float(row.get(col, np.nan)) for col in design_var_cols]
            objs_phys = schema.extract(row)
            # Earlier config-bound exports used model_{name}_neg for canonical objectives.
            model_keys = [col if col in row else f"model_{names[0]}_neg" if sign == -1 else col
                          for col, names, sign in zip(model_obj_cols, schema.objective_aliases, schema.signs)]
            objs_model = [float(row[col]) for col in model_keys] if all(col in row for col in model_keys) else None
            if objs_model is None and objs_phys is not None:
                objs_model = schema.transform(objs_phys).tolist()
            if objs_phys is None and objs_model is not None:
                objs_phys = schema.transform(objs_model).tolist()

            diags = {}
            for diag_col in DIAGNOSTIC_NAMES:
                if diag_col in row and not pd.isna(row[diag_col]):
                    diags[diag_col] = float(row[diag_col])

            def observed_bool(name):
                value = row.get(name)
                if value is None or pd.isna(value):
                    return None
                if isinstance(value, (bool, np.bool_)):
                    return bool(value)
                if isinstance(value, str) and value.lower() in ("true", "false"):
                    return value.lower() == "true"
                raise ValueError(f"Invalid CSV boolean status: {name}")
            sim_valid = observed_bool("simulation_valid")
            phys_feas = observed_bool("physically_feasible")

            res = EvaluationResult(
                evaluation_id=str(row.get("evaluation_id", f"legacy_row_{row_index:06d}")),
                run_id=str(row.get("run_id", "default_run")),
                x_physical=x_phys,
                objectives_physical=objs_phys if objs_phys is not None and len(objs_phys) == n_objs else None,
                objectives_model=objs_model if objs_model is not None and len(objs_model) == n_objs else None,
                diagnostics=diags,
                simulation_valid=sim_valid,
                physically_feasible=phys_feas,
                failure_category=str(
                    row.get("failure_category", "SUCCESS" if (sim_valid and phys_feas) else "UNHANDLED_EXCEPTION")
                ),
                failure_reason=str(row.get("failure_reason", "")) if not pd.isna(row.get("failure_reason")) else None,
                runtime_s=float(row.get("runtime_s", 0.0)),
                work_dir=str(row.get("work_dir", "")),
                attempt_id=None if pd.isna(row.get("attempt_id")) else str(row["attempt_id"]),
                manifest_path=None if pd.isna(row.get("manifest_path")) else str(row["manifest_path"]),
                attempt_history=json.loads(row["attempt_history"]) if isinstance(row.get("attempt_history"), str) else [],
                telemetry={name: float(row[name]) for name in TELEMETRY_COLUMNS
                           if name in row and not pd.isna(row[name])},
            )
            results.append(res)

        return results
    else:
        raise ValueError(f"Unsupported file extension: {path.suffix}")
