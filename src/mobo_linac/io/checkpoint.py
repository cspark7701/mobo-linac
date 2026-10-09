"""Typed, versioned campaign checkpoints (schema v3) with explicit legacy migration.

A checkpoint groups its state into nested records:

- ``campaign`` (:class:`CampaignSpec`): run identity and plan (mode, acquisition, seed,
  weights, sizes, budget, device, workers)
- ``rng`` (:class:`RngState`): torch, NumPy, Python and CUDA generator states
- ``progress`` (:class:`ProgressState`): initial design, Sobol position, batch membership, timing
- ``metrics`` (:class:`MetricState`): fixed reporting reference, scales, metric history
- ``proposals`` (:class:`ProposalState`): proposal history and the durable pending batch

Every record field is required at construction (no defaults), so a forgotten field fails
when the snapshot is built rather than being saved as ``None``. Archived v1/v2 files are
mapped by :func:`migrate_to_v3`; v3 files with unknown keys are rejected. Values that a
legacy file cannot provide are explicit ``None`` and are rejected by resume validation
(``campaigns.state``) unless a legacy migration supplies them.
"""

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.utils.durable import atomic_torch_save, safe_torch_load

SCHEMA_VERSION = "3.0"
SUPPORTED_VERSIONS = ("1.0", "2.0", SCHEMA_VERSION)


@dataclass
class CampaignSpec:
    run_id: Optional[str]
    optimization_mode: Optional[str]
    acquisition_mode: str
    constrained: bool
    seed: Optional[int]
    scalar_weights: Optional[List[float]]
    num_initial_samples: Optional[int]
    batch_size: Optional[int]
    planned_num_batches: Optional[int]
    num_workers: Optional[int]
    total_eval_budget: Optional[int]
    device: Optional[str]


@dataclass
class RngState:
    torch_rng_state: Optional[torch.Tensor]
    numpy_rng_state: Optional[Tuple[Any, ...]]
    python_rng_state: Optional[Tuple[Any, ...]]
    cuda_rng_states: Optional[List[torch.Tensor]]

    @classmethod
    def capture(cls, device: Union[str, torch.device] = "cpu") -> "RngState":
        """Snapshot every generator the campaign draws from."""
        cuda = torch.cuda.get_rng_state_all() if torch.device(device).type == "cuda" else []
        return cls(torch.get_rng_state(), np.random.get_state(), random.getstate(), cuda)

    def validate(self) -> None:
        """Check payloads on temporary generators before touching global random state."""
        try:
            torch.Generator().set_state(self.torch_rng_state.cpu())
            np.random.RandomState().set_state(self.numpy_rng_state)
            if self.python_rng_state is not None:
                random.Random().setstate(self.python_rng_state)
            for cuda_state in self.cuda_rng_states or []:
                if cuda_state.dtype != torch.uint8 or cuda_state.ndim != 1 or cuda_state.numel() == 0:
                    raise ValueError("Invalid CUDA RNG state tensor.")
        except (TypeError, ValueError, RuntimeError, AttributeError) as error:
            raise ValueError(f"Invalid checkpoint RNG state: {error}") from error

    def restore(self) -> None:
        torch.set_rng_state(self.torch_rng_state.cpu())
        np.random.set_state(self.numpy_rng_state)
        if self.python_rng_state is not None:
            random.setstate(self.python_rng_state)
        if self.cuda_rng_states:
            torch.cuda.set_rng_state_all([rng.cpu() for rng in self.cuda_rng_states])


@dataclass
class ProgressState:
    initial_design: Optional[List[List[float]]]
    sobol_state: Optional[Dict[str, Any]]
    evaluation_batches: Optional[List[int]]
    elapsed_wall_time_s: Optional[float]
    evaluation_elapsed_s: Optional[List[Optional[float]]]


@dataclass
class MetricState:
    reporting_ref_point: Optional[List[float]]
    reporting_scales: Optional[List[float]]
    metric_history: Optional[List[Dict[str, Any]]]
    hypervolumes: List[float]


@dataclass
class ProposalState:
    proposal_history: Optional[List[Dict[str, Any]]]
    pending_proposal: Optional[Dict[str, Any]]


_GROUPS = {"campaign": CampaignSpec, "rng": RngState, "progress": ProgressState,
           "metrics": MetricState, "proposals": ProposalState}


@dataclass
class CheckpointState:
    """One durable campaign snapshot. ``checkpoint_file`` and ``migrated_from`` are runtime-only."""

    iteration: int
    results: List[EvaluationResult]
    config: Optional[Dict[str, Any]]
    campaign: CampaignSpec
    rng: RngState
    progress: ProgressState
    metrics: MetricState
    proposals: ProposalState
    model_artifact: Optional[Dict[str, Any]] = None
    migration_notes: List[str] = field(default_factory=list)
    version: str = SCHEMA_VERSION
    checkpoint_file: Optional[str] = None
    migrated_from: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """The v3 on-disk payload (results stored as dictionaries)."""
        data = {name: {item.name: getattr(getattr(self, name), item.name) for item in fields(cls)}
                for name, cls in _GROUPS.items()}
        data["metrics"]["hypervolumes"] = [float(value) for value in self.metrics.hypervolumes]
        return {"version": SCHEMA_VERSION, "iteration": int(self.iteration),
                "results_serialized": [result.to_dict() for result in self.results],
                "config": asdict(self.config) if is_dataclass(self.config) else self.config,
                **data, "model_artifact": self.model_artifact, "migration_notes": list(self.migration_notes)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any], checkpoint_file: Optional[str] = None) -> "CheckpointState":
        """Decode a v3 payload, migrating v1/v2 payloads first; unknown v3 keys are rejected."""
        if not isinstance(data, dict):
            raise ValueError(f"Checkpoint data must be a dictionary, got {type(data).__name__}")
        if "iteration" not in data:
            raise ValueError("Checkpoint data missing required 'iteration' field")
        source = str(data.get("version", "1.0"))
        payload = migrate_to_v3(data)
        unknown = set(payload) - {"version", "iteration", "results_serialized", "config", "model_artifact",
                                  "migration_notes", *_GROUPS}
        if unknown:
            raise ValueError(f"Unknown checkpoint fields: {sorted(unknown)}.")
        groups = {}
        for name, group in _GROUPS.items():
            values = payload.get(name)
            if not isinstance(values, dict) or set(values) != {item.name for item in fields(group)}:
                raise ValueError(f"Checkpoint section '{name}' does not match the v3 schema.")
            groups[name] = group(**values)
        groups["metrics"].hypervolumes = [float(value) for value in groups["metrics"].hypervolumes]
        return cls(iteration=int(payload["iteration"]),
                   results=[EvaluationResult.from_dict(item) for item in payload.get("results_serialized") or []],
                   config=payload.get("config"), model_artifact=payload.get("model_artifact"),
                   migration_notes=list(payload.get("migration_notes") or []), checkpoint_file=checkpoint_file,
                   migrated_from=None if source == SCHEMA_VERSION else source, **groups)


def _plain_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if data.get("results_serialized") is not None:
        return list(data["results_serialized"])
    return [item.to_dict() if isinstance(item, EvaluationResult) else item for item in data.get("results") or []]


def _float_list(values) -> List[float]:
    if isinstance(values, (torch.Tensor, np.ndarray)):
        values = values.tolist()
    return [float(value) for value in values or []]


def migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """v1 stored no campaign plan: infer mode, batch membership and run identity where unambiguous."""
    data = dict(data, version="2.0", results_serialized=_plain_results(data))
    data.pop("results", None)
    results = data["results_serialized"]
    data["optimization_mode"] = ("scalarized_bo" if data.get("acquisition_mode") == "scalarized_qLogNEI"
                                 else "constrained_mobo" if data.get("constrained") else "unconstrained_mobo")
    iteration, batch_size = int(data["iteration"]), data.get("batch_size")
    if batch_size and batch_size > 0:
        initial_count = len(results) - iteration * batch_size
        if initial_count > 0:
            data["num_initial_samples"] = initial_count
            data["initial_design"] = [item.get("x_physical") for item in results[:initial_count]]
            data["evaluation_batches"] = [0] * initial_count + [
                batch for batch in range(1, iteration + 1) for _ in range(batch_size)]
    run_ids = {item.get("run_id") for item in results}
    if results and len(run_ids) == 1:
        data["run_id"] = run_ids.pop()
    data["migration_notes"] = list(data.get("migration_notes") or []) + [
        "Legacy v1 state: batch membership inferred for a fixed-size completed campaign; "
        "exact prior acquisition fallback state and CUDA RNG states were not recorded."]
    return data


def migrate_v2_to_v3(data: Dict[str, Any]) -> Dict[str, Any]:
    """Group the flat v2 fields; fields a legacy file never recorded become explicit ``None``."""
    flat = dict(data)
    grouped = {name: {item.name: flat.pop(item.name, None) for item in fields(group)} for name, group in _GROUPS.items()}
    grouped["campaign"]["acquisition_mode"] = str(grouped["campaign"]["acquisition_mode"] or "qLogNEHVI")
    grouped["campaign"]["constrained"] = bool(grouped["campaign"]["constrained"])
    grouped["metrics"]["hypervolumes"] = _float_list(grouped["metrics"]["hypervolumes"])
    payload = {"version": SCHEMA_VERSION, "iteration": int(flat.pop("iteration")),
               "results_serialized": _plain_results(flat), "config": flat.pop("config", None),
               "model_artifact": flat.pop("model_artifact", None),
               "migration_notes": list(flat.pop("migration_notes", None) or []), **grouped}
    flat.pop("results_serialized", None)
    flat.pop("results", None)
    flat.pop("version", None)
    if flat:
        raise ValueError(f"Unknown legacy checkpoint fields: {sorted(flat)}.")
    config = payload["config"]
    payload["config"] = asdict(config) if is_dataclass(config) else config
    return payload


def migrate_to_v3(data: Dict[str, Any]) -> Dict[str, Any]:
    version = str(data.get("version", "1.0"))
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"Unsupported checkpoint version: {version}")
    if version == "1.0":
        data = migrate_v1_to_v2(data)
        version = "2.0"
    return migrate_v2_to_v3(data) if version == "2.0" else dict(data)


def save_run_checkpoint(path: Union[str, Path], state: CheckpointState) -> Path:
    """Atomically write a typed snapshot; an iteration checkpoint also refreshes ``checkpoint.pt``."""
    if not isinstance(state, CheckpointState):
        raise TypeError("save_run_checkpoint requires a CheckpointState.")
    path = Path(path)
    payload = state.to_dict()
    atomic_torch_save(payload, path)
    if path.name.startswith("checkpoint_iter_"):
        atomic_torch_save(payload, path.parent / "checkpoint.pt")
    return path


def run_directory(target: Union[str, Path]) -> Path:
    """Run directory of a run path or of a checkpoint file inside ``checkpoints``/``gp_checkpoint``."""
    path = Path(target)
    if path.is_file() or path.suffix == ".pt":
        return path.parent.parent if path.parent.name in ("checkpoints", "gp_checkpoint") else path.parent
    return path


def find_checkpoint(target: Union[str, Path]) -> Optional[Path]:
    """Locate the checkpoint file for a file or run-directory target.

    Search order for a directory: ``checkpoints/checkpoint.pt``, ``gp_checkpoint/checkpoint.pt``
    (archived layout), ``checkpoint.pt``, the latest ``checkpoints/checkpoint_iter_*.pt``, and
    finally ``checkpoints/pending_batch.pt`` (a campaign interrupted before its first commit).
    """
    path = Path(target)
    if not path.is_dir():
        return path if path.exists() else None
    for candidate in (path / "checkpoints" / "checkpoint.pt", path / "gp_checkpoint" / "checkpoint.pt",
                      path / "checkpoint.pt"):
        if candidate.exists():
            return candidate
    iterations = sorted((path / "checkpoints").glob("checkpoint_iter_*.pt"))
    if iterations:
        return iterations[-1]
    pending = path / "checkpoints" / "pending_batch.pt"
    return pending if pending.exists() else None


def load_run_checkpoint(checkpoint_path: Union[str, Path], allow_unsafe_pickle: bool = False) -> Optional[CheckpointState]:
    """Load (and migrate) the checkpoint found by :func:`find_checkpoint`; ``None`` when absent.

    Loading uses ``weights_only=True`` with only the NumPy array allow-list;
    ``allow_unsafe_pickle`` is an explicit opt-in for trusted archived checkpoints that
    stored arbitrary Python objects.
    """
    target_file = find_checkpoint(checkpoint_path)
    if target_file is None:
        return None
    try:
        checkpoint_data = safe_torch_load(target_file, allow_unsafe_pickle=allow_unsafe_pickle)
    except Exception as e:
        raise ValueError(f"Corrupted, unreadable or unsafe checkpoint file at {target_file}: {e}") from e
    if not isinstance(checkpoint_data, dict) or "iteration" not in checkpoint_data:
        raise ValueError(f"Invalid checkpoint structure at {target_file}")
    return CheckpointState.from_dict(checkpoint_data, checkpoint_file=str(target_file))
