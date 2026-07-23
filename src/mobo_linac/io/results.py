"""
Result I/O, Serialization, DataFrame Conversions, and Checkpoint Management.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import torch
from botorch.utils.multi_objective.pareto import is_non_dominated

from mobo_linac.evaluation import EvaluationResult

DESIGN_VAR_COLUMNS = [
    "solenoid_field_T",
    "quad_1_gradient_T_m",
    "quad_2_gradient_T_m",
    "gun_phase_deg",
    "acc1_acc2_phase_deg",
    "acc3_acc4_phase_deg",
]

PHYSICAL_OBJ_COLUMNS = [
    "norm_emit_x_m_rad",
    "norm_emit_y_m_rad",
    "sigma_energy_eV",
]

MODEL_OBJ_COLUMNS = [
    "model_emit_x_neg",
    "model_emit_y_neg",
    "model_sigma_energy_neg",
]


def results_to_dataframe(results: List[EvaluationResult]) -> pd.DataFrame:
    """
    Converts a list of EvaluationResult objects into a structured Pandas DataFrame.
    """
    rows = []
    for res in results:
        row: Dict[str, Any] = {
            "evaluation_id": res.evaluation_id,
            "run_id": res.run_id,
            "simulation_valid": res.simulation_valid,
            "physically_feasible": res.physically_feasible,
            "failure_category": res.failure_category,
            "failure_reason": res.failure_reason or "",
            "runtime_s": res.runtime_s,
            "work_dir": res.work_dir,
        }

        # Add design variables
        for idx, col in enumerate(DESIGN_VAR_COLUMNS):
            if res.x_physical and idx < len(res.x_physical):
                row[col] = float(res.x_physical[idx])
            else:
                row[col] = np.nan

        # Add physical objectives
        for idx, col in enumerate(PHYSICAL_OBJ_COLUMNS):
            if res.objectives_physical and idx < len(res.objectives_physical):
                row[col] = float(res.objectives_physical[idx])
            else:
                row[col] = np.nan

        # Add model-space objectives
        for idx, col in enumerate(MODEL_OBJ_COLUMNS):
            if res.objectives_model and idx < len(res.objectives_model):
                row[col] = float(res.objectives_model[idx])
            else:
                row[col] = np.nan

        # Add diagnostics if available
        diags = res.diagnostics or {}
        row["sigma_x_m"] = diags.get("sigma_x", diags.get("sigma_x_m", np.nan))
        row["sigma_y_m"] = diags.get("sigma_y", diags.get("sigma_y_m", np.nan))
        row["sigma_xp_rad"] = diags.get("sigma_xp", diags.get("sigma_xp_rad", np.nan))
        row["sigma_yp_rad"] = diags.get("sigma_yp", diags.get("sigma_yp_rad", np.nan))
        row["sigma_z_m"] = diags.get("sigma_z", diags.get("sigma_z_m", np.nan))
        row["mean_kinetic_energy_eV"] = diags.get("mean_kinetic_energy", diags.get("mean_kinetic_energy_eV", np.nan))

        rows.append(row)

    return pd.DataFrame(rows)


def get_train_tensors(
    results: List[EvaluationResult],
    exclude_invalid: bool = True,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Generates (train_X, train_Y, train_feas_mask) double tensors for GP model fitting.

    Args:
        results: List of EvaluationResult records.
        exclude_invalid: If True, excludes invalid simulations (preventing sentinel values in GP training).

    Returns:
        Tuple of (train_X, train_Y, train_feas_mask) tensors.
    """
    train_x_list = []
    train_y_list = []
    feas_list = []

    for res in results:
        if exclude_invalid and not res.simulation_valid:
            continue
        if res.x_physical is None or res.objectives_model is None:
            continue

        train_x_list.append(res.x_physical)
        train_y_list.append(res.objectives_model)
        feas_list.append(res.physically_feasible)

    if len(train_x_list) == 0:
        train_X = torch.empty((0, 6), dtype=torch.double)
        train_Y = torch.empty((0, 3), dtype=torch.double)
        train_feas_mask = torch.empty((0,), dtype=torch.bool)
    else:
        train_X = torch.tensor(train_x_list, dtype=torch.double)
        train_Y = torch.tensor(train_y_list, dtype=torch.double)
        train_feas_mask = torch.tensor(feas_list, dtype=torch.bool)

    return train_X, train_Y, train_feas_mask


def save_evaluation_results(
    results: List[EvaluationResult],
    run_dir: Union[str, Path],
    hypervolumes: Optional[List[float]] = None,
) -> Dict[str, Path]:
    """
    Saves candidate history JSON, CSV, Pareto front, and hypervolume history into run directory.
    """
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)

    # 1. Save candidate_history.json
    json_path = run_path / "candidate_history.json"
    dict_list = [res.to_dict() for res in results]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dict_list, f, indent=2)

    # 2. Save candidate_history.csv
    df = results_to_dataframe(results)
    csv_path = run_path / "candidate_history.csv"
    df.to_csv(csv_path, index=False)

    # 3. Save train_X.csv & train_Y.csv
    train_X, train_Y, train_feas_mask = get_train_tensors(results, exclude_invalid=True)
    if train_X.shape[0] > 0:
        np.savetxt(run_path / "train_X.csv", train_X.numpy(), delimiter=",", header=",".join(DESIGN_VAR_COLUMNS))
        np.savetxt(run_path / "train_Y.csv", train_Y.numpy(), delimiter=",", header=",".join(MODEL_OBJ_COLUMNS))

        # Save pareto.csv if feasible valid samples exist
        feasible_mask = train_feas_mask
        if feasible_mask.sum().item() > 0:
            feas_X = train_X[feasible_mask]
            feas_Y = train_Y[feasible_mask]
            pareto_mask = is_non_dominated(feas_Y)
            pareto_X = feas_X[pareto_mask]
            pareto_Y_model = feas_Y[pareto_mask]
            pareto_Y_phys = -pareto_Y_model  # restore physical values for minimization

            pareto_data = np.hstack([pareto_X.numpy(), pareto_Y_phys.numpy()])
            pareto_headers = DESIGN_VAR_COLUMNS + PHYSICAL_OBJ_COLUMNS
            np.savetxt(run_path / "pareto.csv", pareto_data, delimiter=",", header=",".join(pareto_headers))

    # 4. Save hypervolume.csv if provided
    if hypervolumes is not None:
        np.savetxt(run_path / "hypervolume.csv", np.array(hypervolumes), delimiter=",", header="hypervolume")

    return {
        "json": json_path,
        "csv": csv_path,
    }


def load_evaluation_results(history_path: Union[str, Path]) -> List[EvaluationResult]:
    """
    Loads list of EvaluationResult objects from a JSON or CSV file.
    """
    path = Path(history_path)
    if not path.exists():
        raise FileNotFoundError(f"Result file not found: {path}")

    if path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [EvaluationResult.from_dict(d) for d in data]
    elif path.suffix == ".csv":
        df = pd.read_csv(path)
        results = []
        for _, row in df.iterrows():
            x_phys = [row[col] for col in DESIGN_VAR_COLUMNS if col in row and not pd.isna(row[col])]
            objs_phys = [row[col] for col in PHYSICAL_OBJ_COLUMNS if col in row and not pd.isna(row[col])]
            objs_model = [row[col] for col in MODEL_OBJ_COLUMNS if col in row and not pd.isna(row[col])]

            diags = {}
            for diag_col in ["sigma_x_m", "sigma_y_m", "sigma_xp_rad", "sigma_yp_rad", "sigma_z_m", "mean_kinetic_energy_eV"]:
                if diag_col in row and not pd.isna(row[diag_col]):
                    diags[diag_col] = float(row[diag_col])

            res = EvaluationResult(
                evaluation_id=str(row.get("evaluation_id", "eval_000000")),
                run_id=str(row.get("run_id", "default_run")),
                x_physical=x_phys,
                objectives_physical=objs_phys if len(objs_phys) == 3 else None,
                objectives_model=objs_model if len(objs_model) == 3 else None,
                diagnostics=diags,
                simulation_valid=bool(row.get("simulation_valid", False)),
                physically_feasible=bool(row.get("physically_feasible", False)),
                failure_category=str(row.get("failure_category", "UNHANDLED_EXCEPTION")),
                failure_reason=str(row.get("failure_reason", "")) if not pd.isna(row.get("failure_reason")) else None,
                runtime_s=float(row.get("runtime_s", 0.0)),
                work_dir=str(row.get("work_dir", "")),
            )
            results.append(res)
        return results
    else:
        raise ValueError(f"Unsupported file extension: {path.suffix}")


def save_run_checkpoint(
    iteration: int,
    results: List[EvaluationResult],
    hypervolumes: List[float],
    checkpoint_path: Union[str, Path] = "mobo_results/mobo_checkpoint.pt",
    acquisition_mode: str = "qLogNEHVI",
    config: Any = None,
) -> Path:
    """
    Saves stateful checkpoint containing structured EvaluationResult records.
    """
    path = Path(checkpoint_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    checkpoint_data = {
        "iteration": iteration,
        "results_serialized": [res.to_dict() for res in results],
        "hypervolumes": hypervolumes,
        "acquisition_mode": acquisition_mode,
        "config": config,
    }
    torch.save(checkpoint_data, path)
    return path


def load_run_checkpoint(checkpoint_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Loads stateful checkpoint and reconstructs EvaluationResult records.
    """
    path = Path(checkpoint_path)
    if not path.exists():
        return None

    checkpoint_data = torch.load(path, weights_only=False)
    serialized = checkpoint_data.get("results_serialized", [])
    checkpoint_data["results"] = [EvaluationResult.from_dict(d) for d in serialized]
    return checkpoint_data
