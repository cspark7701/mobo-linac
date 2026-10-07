"""
Result I/O, Serialization, DataFrame Conversions, and Checkpoint Management.
"""

import json
import os
import random
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import torch

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.result_schema import ResultSchema
from mobo_linac.diagnostics import DIAGNOSTIC_CHANNELS, diagnostic_observations, finite_measurement, normalize_diagnostics

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


def results_to_dataframe(
    results: List[EvaluationResult],
    config: Optional[Any] = None,
) -> pd.DataFrame:
    """
    Converts a list of EvaluationResult objects into a structured Pandas DataFrame.
    Dynamically binds column headers from config if provided, falling back to canonical linac defaults.
    """
    schema = ResultSchema.from_config(config)
    design_var_cols = list(schema.design_columns)
    physical_obj_cols = list(schema.physical_columns)
    model_obj_cols = list(schema.model_columns)

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
            "attempt_id": res.attempt_id, "manifest_path": res.manifest_path,
            "attempt_history": json.dumps(res.attempt_history),
        }

        # Add design variables
        for idx, col in enumerate(design_var_cols):
            if res.x_physical and idx < len(res.x_physical):
                row[col] = float(res.x_physical[idx])
            else:
                row[col] = np.nan

        # Add physical objectives
        for idx, col in enumerate(physical_obj_cols):
            if res.objectives_physical and idx < len(res.objectives_physical):
                row[col] = float(res.objectives_physical[idx])
            else:
                row[col] = np.nan

        # Add model-space objectives
        for idx, col in enumerate(model_obj_cols):
            if res.objectives_model and idx < len(res.objectives_model):
                row[col] = float(res.objectives_model[idx])
            else:
                row[col] = np.nan

        # Add diagnostics if available
        diags = normalize_diagnostics(res.diagnostics)
        sigma_energy_val = diags.get("sigma_energy_eV", diags.get("sigma_energy", np.nan))
        if pd.isna(sigma_energy_val) and "sigma_energy_eV" in row:
            sigma_energy_val = row["sigma_energy_eV"]

        row["sigma_x_m"] = diags.get("sigma_x_m", np.nan)
        row["sigma_y_m"] = diags.get("sigma_y_m", np.nan)
        row["sigma_xp_rad"] = diags.get("sigma_xp_rad", np.nan)
        row["sigma_yp_rad"] = diags.get("sigma_yp_rad", np.nan)
        row["sigma_z_m"] = diags.get("sigma_z_m", np.nan)
        row["mean_kinetic_energy_eV"] = diags.get("mean_kinetic_energy_eV", np.nan)
        row.setdefault("sigma_energy_eV", sigma_energy_val)
        row["n_particles_initial"] = diags.get("n_particles_initial", np.nan)
        row["n_particles_final"] = diags.get("n_particles_final", np.nan)
        row["transmission_fraction"] = diags.get("transmission_fraction", np.nan)

        rows.append(row)

    columns = list(dict.fromkeys(["evaluation_id", "run_id", "simulation_valid", "physically_feasible", "failure_category", "failure_reason", "runtime_s", "work_dir", "attempt_id", "manifest_path", "attempt_history"] + design_var_cols + physical_obj_cols + model_obj_cols + ["sigma_x_m", "sigma_y_m", "sigma_xp_rad", "sigma_yp_rad", "sigma_z_m", "mean_kinetic_energy_eV", "sigma_energy_eV", "n_particles_initial", "n_particles_final", "transmission_fraction"]))
    return pd.DataFrame(rows, columns=columns)


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
    config=None,
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
    config=None,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Return finite objective observations; constrained callers use the shared selector."""
    observed = get_training_observations(results, exclude_invalid, config=config)
    return observed.train_X, observed.train_Y, observed.feasible


def get_constraint_tensors(
    results: List[EvaluationResult],
    exclude_invalid: bool = True,
    config=None,
) -> torch.Tensor:
    """Return complete measured diagnostics in canonical order, without imputation.

    Use get_training_observations(require_diagnostics=True) to obtain identically
    selected design/objective rows and their stable evaluation identities.
    """
    return get_training_observations(results, exclude_invalid, require_diagnostics=True, config=config).constraints



def save_evaluation_results(
    results: List[EvaluationResult],
    run_dir: Union[str, Path],
    hypervolumes: Optional[List[float]] = None,
    config: Optional[Any] = None,
) -> Dict[str, Path]:
    """
    Saves candidate history JSON, CSV, Pareto front, and hypervolume history into run directory.
    """
    from mobo_linac.io.artifacts import RunArtifactWriter
    return RunArtifactWriter(run_dir, config).write(results, hypervolumes=hypervolumes)


def load_evaluation_results(
    history_path: Union[str, Path],
    config: Optional[Any] = None,
) -> List[EvaluationResult]:
    """
    Loads list of EvaluationResult objects from a JSON or CSV file.
    Dynamically binds variable and objective schemas if config is provided.
    """
    path = Path(history_path)
    if not path.exists():
        raise FileNotFoundError(f"Result file not found: {path}")

    schema = ResultSchema.from_config(config)
    design_var_cols = list(schema.design_columns)
    physical_obj_cols = list(schema.physical_columns)
    model_obj_cols = list(schema.model_columns)

    n_vars = len(design_var_cols)
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
        for row_index, row in df.iterrows():
            x_phys = [float(row.get(col, np.nan)) for col in design_var_cols]
            objs_phys = schema.extract(row.to_dict())
            # Earlier config-bound exports used model_{name}_neg for canonical objectives.
            model_keys = [col if col in row else f"model_{names[0]}_neg" if sign == -1 else col
                          for col, names, sign in zip(model_obj_cols, schema.objective_aliases, schema.signs)]
            objs_model = [float(row[col]) for col in model_keys] if all(col in row for col in model_keys) else None
            if objs_model is None and objs_phys is not None:
                objs_model = schema.transform(objs_phys).tolist()
            if objs_phys is None and objs_model is not None:
                objs_phys = schema.transform(objs_model).tolist()

            diags = {}
            for diag_col in [
                "sigma_x_m",
                "sigma_y_m",
                "sigma_xp_rad",
                "sigma_yp_rad",
                "sigma_z_m",
                "mean_kinetic_energy_eV",
                "transmission_fraction",
            ]:
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
                x_physical=x_phys if len(x_phys) == n_vars else x_phys,
                objectives_physical=objs_phys if objs_phys is not None and len(objs_phys) == n_objs else None,
                objectives_model=objs_model if objs_model is not None and len(objs_model) == n_objs else None,
                diagnostics=diags,
                simulation_valid=sim_valid,
                physically_feasible=phys_feas,
                failure_category=str(
                    row.get("failure_category", "NONE" if (sim_valid and phys_feas) else "UNHANDLED_EXCEPTION")
                ),
                failure_reason=str(row.get("failure_reason", "")) if not pd.isna(row.get("failure_reason")) else None,
                runtime_s=float(row.get("runtime_s", 0.0)),
                work_dir=str(row.get("work_dir", "")),
                attempt_id=None if pd.isna(row.get("attempt_id")) else str(row["attempt_id"]),
                manifest_path=None if pd.isna(row.get("manifest_path")) else str(row["manifest_path"]),
                attempt_history=json.loads(row["attempt_history"]) if isinstance(row.get("attempt_history"), str) else [],
            )
            results.append(res)

        return results
    else:
        raise ValueError(f"Unsupported file extension: {path.suffix}")


@dataclass
class CheckpointState:
    """
    Typed, schema-validated checkpoint state for Bayesian optimization campaigns.
    Preserves evaluation history, acquisition mode, hypervolume progression, RNG states,
    and runtime configuration with explicit legacy-version decoding.
    """
    iteration: int
    results: List[EvaluationResult]
    hypervolumes: List[float] = field(default_factory=list)
    acquisition_mode: str = "qLogNEHVI"
    reporting_ref_point: Optional[List[float]] = None
    seed: Optional[int] = None
    batch_size: Optional[int] = None
    constrained: bool = False
    torch_rng_state: Optional[torch.Tensor] = None
    numpy_rng_state: Optional[Tuple[Any, ...]] = None
    config: Optional[Dict[str, Any]] = None
    run_id: Optional[str] = None
    optimization_mode: Optional[str] = None
    scalar_weights: Optional[List[float]] = None
    num_initial_samples: Optional[int] = None
    initial_design: Optional[List[List[float]]] = None
    sobol_state: Optional[Dict[str, Any]] = None
    evaluation_batches: Optional[List[int]] = None
    metric_history: Optional[List[Dict[str, Any]]] = None
    reporting_scales: Optional[List[float]] = None
    planned_num_batches: Optional[int] = None
    num_workers: Optional[int] = None
    total_eval_budget: Optional[int] = None
    device: Optional[str] = None
    cuda_rng_states: Optional[List[torch.Tensor]] = None
    python_rng_state: Optional[Tuple[Any, ...]] = None
    pending_proposal: Optional[Dict[str, Any]] = None
    elapsed_wall_time_s: Optional[float] = None
    evaluation_elapsed_s: Optional[List[Optional[float]]] = None
    migration_notes: List[str] = field(default_factory=list)
    version: str = "2.0"
    checkpoint_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serializes checkpoint state into a dictionary for torch.save."""
        data = {
            f.name: getattr(self, f.name)
            for f in fields(self) if f.name not in ("results", "checkpoint_file")
        }
        data["iteration"] = int(self.iteration)
        data["results_serialized"] = [res.to_dict() for res in self.results]
        data["hypervolumes"] = [float(hv) for hv in self.hypervolumes]
        data["config"] = asdict(self.config) if is_dataclass(self.config) else self.config
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], checkpoint_file: Optional[str] = None) -> "CheckpointState":
        """Reconstructs and validates a CheckpointState from raw loaded checkpoint dictionary."""
        if not isinstance(data, dict):
            raise ValueError(f"Checkpoint data must be a dictionary, got {type(data).__name__}")
        if "iteration" not in data:
            raise ValueError("Checkpoint data missing required 'iteration' field")

        serialized = data.get("results_serialized")
        if serialized is None and "results" in data:
            raw_results = data["results"]
            results = [
                r if isinstance(r, EvaluationResult) else EvaluationResult.from_dict(r)
                for r in raw_results
            ]
        elif serialized is not None:
            results = [EvaluationResult.from_dict(d) for d in serialized]
        else:
            results = []

        raw_hv = data.get("hypervolumes", [])
        if isinstance(raw_hv, torch.Tensor):
            raw_hv = raw_hv.tolist()
        elif isinstance(raw_hv, np.ndarray):
            raw_hv = raw_hv.tolist()
        hypervolumes = [float(h) for h in raw_hv]

        version = str(data.get("version", "1.0"))
        if version not in ("1.0", "2.0"):
            raise ValueError(f"Unsupported checkpoint version: {version}")
        extra_names = (
            "run_id", "optimization_mode", "scalar_weights", "num_initial_samples",
            "initial_design", "sobol_state", "evaluation_batches", "metric_history",
            "reporting_scales", "planned_num_batches", "num_workers", "total_eval_budget", "device",
            "cuda_rng_states", "python_rng_state", "pending_proposal", "elapsed_wall_time_s", "evaluation_elapsed_s",
        )
        config = data.get("config")
        state = cls(
            iteration=int(data["iteration"]),
            results=results,
            hypervolumes=hypervolumes,
            acquisition_mode=str(data.get("acquisition_mode", "qLogNEHVI")),
            reporting_ref_point=data.get("reporting_ref_point"),
            seed=data.get("seed"),
            batch_size=data.get("batch_size"),
            constrained=bool(data.get("constrained", False)),
            torch_rng_state=data.get("torch_rng_state"),
            numpy_rng_state=data.get("numpy_rng_state"),
            config=asdict(config) if is_dataclass(config) else config,
            version=version,
            checkpoint_file=checkpoint_file,
            migration_notes=list(data.get("migration_notes", [])),
            **{name: data.get(name) for name in extra_names},
        )
        if version == "1.0":
            state.optimization_mode = (
                "scalarized_bo" if state.acquisition_mode == "scalarized_qLogNEI"
                else "constrained_mobo" if state.constrained else "unconstrained_mobo"
            )
            if state.batch_size and state.batch_size > 0:
                initial_count = len(results) - state.iteration * state.batch_size
                if initial_count > 0:
                    state.num_initial_samples = initial_count
                    state.initial_design = [r.x_physical for r in results[:initial_count]]
                    state.evaluation_batches = [0] * initial_count + [
                        it for it in range(1, state.iteration + 1) for _ in range(state.batch_size)
                    ]
            if results and len({r.run_id for r in results}) == 1:
                state.run_id = results[0].run_id
            state.migration_notes.append(
                "Legacy v1 state: batch membership inferred for a fixed-size completed campaign; "
                "exact prior acquisition fallback state and CUDA RNG states were not recorded."
            )
        return state

    # Dict-like access for backward compatibility
    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        if key == "results_serialized":
            return [res.to_dict() for res in self.results]
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or key == "results_serialized"

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            val = getattr(self, key)
            return val if val is not None else default
        if key == "results_serialized":
            return [res.to_dict() for res in self.results]
        return default


def _atomic_torch_save(data: Any, target_path: Path) -> None:
    """
    Saves torch data to a temporary file first, then atomically replaces the target file.
    Prevents corrupt or half-written checkpoint files during unexpected interruptions.
    """
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(f"{target_path.name}.tmp.{os.getpid()}")
    try:
        with tmp_path.open("wb") as stream:
            torch.save(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, target_path)
        directory_fd = os.open(target_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def save_run_checkpoint(
    iteration: int,
    results: List[EvaluationResult],
    hypervolumes: List[float],
    checkpoint_path: Union[str, Path] = "results/checkpoints/checkpoint.pt",
    acquisition_mode: str = "qLogNEHVI",
    config: Any = None,
    reporting_ref_point: Optional[Union[torch.Tensor, List[float]]] = None,
    seed: Optional[int] = None,
    batch_size: Optional[int] = None,
    constrained: Optional[bool] = None,
    torch_rng_state: Optional[torch.Tensor] = None,
    numpy_rng_state: Optional[Tuple[Any, ...]] = None,
    campaign_state: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Saves stateful checkpoint containing structured EvaluationResult records using atomic file write.
    """
    path = Path(checkpoint_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    ref_point_list = (
        reporting_ref_point.tolist()
        if isinstance(reporting_ref_point, torch.Tensor)
        else reporting_ref_point
    )
    config_dict = asdict(config) if is_dataclass(config) else (config.to_dict() if hasattr(config, "to_dict") else config)

    t_state = torch_rng_state if torch_rng_state is not None else torch.get_rng_state()
    n_state = numpy_rng_state if numpy_rng_state is not None else np.random.get_state()

    state = CheckpointState(
        iteration=iteration,
        results=results,
        hypervolumes=hypervolumes,
        acquisition_mode=acquisition_mode,
        reporting_ref_point=ref_point_list,
        seed=seed,
        batch_size=batch_size,
        constrained=bool(constrained) if constrained is not None else False,
        torch_rng_state=t_state,
        numpy_rng_state=n_state,
        config=config_dict,
        checkpoint_file=str(path),
        python_rng_state=random.getstate(),
        **(campaign_state or {}),
    )

    checkpoint_data = state.to_dict()
    _atomic_torch_save(checkpoint_data, path)

    # If saving an iteration checkpoint, also update latest checkpoint link/copy
    if path.name.startswith("checkpoint_iter_"):
        latest_path = path.parent / "checkpoint.pt"
        _atomic_torch_save(checkpoint_data, latest_path)

    return path


def load_run_checkpoint(checkpoint_path: Union[str, Path]) -> Optional[CheckpointState]:
    """
    Loads stateful checkpoint, validates schema, and returns a CheckpointState.
    Auto-detects directory vs file input.
    """
    path = Path(checkpoint_path)
    target_file: Optional[Path] = None

    if path.is_dir():
        candidates = [
            path / "checkpoints" / "checkpoint.pt",
            path / "gp_checkpoint" / "checkpoint.pt",
            path / "checkpoint.pt",
        ]
        for c in candidates:
            if c.exists():
                target_file = c
                break
        if target_file is None:
            # Check for latest iteration checkpoint in checkpoints/
            ckpt_dir = path / "checkpoints"
            if ckpt_dir.exists():
                iter_files = sorted(ckpt_dir.glob("checkpoint_iter_*.pt"))
                if iter_files:
                    target_file = iter_files[-1]
        if target_file is None and (path / "checkpoints" / "pending_batch.pt").exists():
            target_file = path / "checkpoints" / "pending_batch.pt"
    elif path.exists():
        target_file = path

    if target_file is None or not target_file.exists():
        return None

    try:
        checkpoint_data = torch.load(target_file, weights_only=False, map_location="cpu")
    except Exception as e:
        raise ValueError(f"Corrupted or unreadable checkpoint file at {target_file}: {e}")

    if not isinstance(checkpoint_data, dict) or "iteration" not in checkpoint_data:
        raise ValueError(f"Invalid checkpoint structure at {target_file}")

    return CheckpointState.from_dict(checkpoint_data, checkpoint_file=str(target_file))


def append_streaming_evaluation(
    output_dir: Union[str, Path],
    result: EvaluationResult,
    batch_idx: Optional[int] = None,
    candidate_idx: Optional[int] = None,
    config=None,
) -> Path:
    """Durably append JSONL first, then derive the CSV view; write errors propagate."""
    from mobo_linac.io.journal import append_record
    return append_record(output_dir, result, batch_idx, candidate_idx, config=config)


def load_streaming_evaluations(output_dir: Union[str, Path]) -> List[EvaluationResult]:
    """Load exact typed JSONL records, including legacy batch metadata, without CSV fallback."""
    from mobo_linac.io.journal import load_streaming_records
    return [record.result for record in load_streaming_records(output_dir)]
