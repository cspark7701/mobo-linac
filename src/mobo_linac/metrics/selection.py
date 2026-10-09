"""Single selection service for representative feasible-Pareto candidates.

Robustness analysis, rerun verification and publication summaries all consume the
same :class:`RepresentativeSet`, so a role such as ``knee_point`` always names the
same evaluation for a given history.

Knee policy (``ideal_distance``): in direction-aware cost space (minimized
objectives as-is, maximized objectives negated), each objective is min-max
normalized over the feasible Pareto set; the knee is the point closest to the
ideal (all-zero) corner in Euclidean distance. The policy is scale invariant and is
recorded with every selection.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple, Union

import numpy as np
import torch
from botorch.utils.multi_objective.pareto import is_non_dominated

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.result_schema import ResultSchema, legacy_objective_alias

KNEE_POLICY = "ideal_distance"
SUPPORTED_POLICIES = (KNEE_POLICY,)


def compute_crowding_distances(objs) -> np.ndarray:
    """NSGA-II crowding distances for an (N, M) objective matrix; extremes are infinite."""
    values = np.asarray(objs, dtype=np.float64)
    if values.ndim == 1:
        values = values[:, np.newaxis]
    if values.size == 0:
        return np.zeros(0, dtype=np.float64)
    n, m = values.shape
    if n <= 2:
        return np.full(n, np.inf, dtype=np.float64)
    distances = np.zeros(n, dtype=np.float64)
    for column in range(m):
        order = np.argsort(values[:, column], kind="stable")
        span = values[order[-1], column] - values[order[0], column]
        distances[order[[0, -1]]] = np.inf
        if abs(span) <= 1e-12:
            continue
        gaps = (values[order[2:], column] - values[order[:-2], column]) / span
        interior = order[1:-1]
        finite = ~np.isinf(distances[interior])
        distances[interior[finite]] += gaps[finite]
    return distances


def objective_role(objective) -> str:
    """Role name for an objective extreme, e.g. ``min_emit_x`` for archived names."""
    prefix = "min" if objective.physical_direction == "minimize" else "max"
    return f"{prefix}_{legacy_objective_alias(objective.name) or objective.name}"


def _identity(result: EvaluationResult) -> Tuple[str, str]:
    return (result.run_id, result.evaluation_id)


@dataclass(frozen=True)
class RepresentativeSet:
    """Selected roles plus the policy and data needed to audit the selection."""

    roles: Dict[str, EvaluationResult]
    policy: str
    objective_columns: Tuple[str, ...]
    feasible_pareto_identities: Tuple[Tuple[str, str], ...]
    normalized_costs: Dict[Tuple[str, str], List[float]] = field(default_factory=dict)

    def identities(self) -> Dict[str, Tuple[str, str]]:
        return {role: _identity(result) for role, result in self.roles.items()}

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "policy": self.policy,
            "objective_columns": list(self.objective_columns),
            "roles": {role: {"run_id": run_id, "evaluation_id": evaluation_id}
                      for role, (run_id, evaluation_id) in self.identities().items()},
            "feasible_pareto": [{"run_id": run_id, "evaluation_id": evaluation_id}
                                for run_id, evaluation_id in self.feasible_pareto_identities],
        }

    def write(self, path: Union[str, Path]) -> Path:
        from mobo_linac.io.artifacts import atomic_json
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(path, self.to_dict())
        return path


def valid_measured(results: Sequence[EvaluationResult], schema: ResultSchema, feasible: bool):
    """Measured records with complete finite designs and objectives; inputs are never modified."""
    selected, values = [], []
    for result in results:
        objectives = schema.extract(result.objectives_physical)
        if (result.simulation_valid is True and (not feasible or result.physically_feasible is True)
                and result.x_physical and len(result.x_physical) == len(schema.design_columns)
                and np.isfinite(result.x_physical).all()
                and objectives is not None and np.isfinite(objectives).all()):
            selected.append(result)
            values.append(objectives)
    return selected, np.asarray(values, dtype=np.float64).reshape(len(selected), len(schema.signs))


def pareto_subset(results: Sequence[EvaluationResult], config, feasible: bool) -> List[EvaluationResult]:
    """Non-dominated subset of valid (optionally feasible) measured records, in input order."""
    schema = ResultSchema.from_config(config)
    records, values = valid_measured(results, schema, feasible)
    if not records:
        return []
    mask = is_non_dominated(schema.transform(torch.as_tensor(values))).tolist()
    return [record for record, keep in zip(records, mask) if keep]


def select_representatives(results: Sequence[EvaluationResult], config, policy: str = KNEE_POLICY) -> RepresentativeSet:
    """Select objective extremes, knee, balanced and maximum-crowding feasible Pareto candidates.

    Raises ValueError when no measured feasible candidate exists; infeasible points
    are never substituted.
    """
    if policy not in SUPPORTED_POLICIES:
        raise ValueError(f"Unsupported representative selection policy: {policy}")
    schema = ResultSchema.from_config(config)
    objectives = getattr(config, "objectives", None)
    if objectives is None:
        raise TypeError("Representative roles require the campaign MoboConfig.")
    front = pareto_subset(results, config, feasible=True)
    if not front:
        raise ValueError("No measured valid, feasible candidates available for representative selection.")
    values = np.asarray([schema.extract(r.objectives_physical) for r in front], dtype=np.float64)
    costs = values * -np.asarray(schema.signs, dtype=np.float64)
    span = costs.max(axis=0) - costs.min(axis=0)
    normalized = (costs - costs.min(axis=0)) / np.where(span > 0, span, 1.0)

    roles: Dict[str, EvaluationResult] = {}
    for index, objective in enumerate(objectives):
        roles[objective_role(objective)] = front[int(np.argmin(costs[:, index]))]
    knee_index = int(np.argmin(np.linalg.norm(normalized, axis=1)))
    roles["knee_point"] = front[knee_index]
    roles["balanced"] = front[int(np.argmin(np.linalg.norm(normalized - normalized.mean(axis=0), axis=1)))]
    crowding = compute_crowding_distances(normalized)
    finite = np.isfinite(crowding)
    roles["crowding_distance_max"] = front[int(np.argmax(np.where(finite, crowding, -1.0)))] if finite.any() else front[knee_index]
    return RepresentativeSet(
        roles=roles, policy=policy, objective_columns=tuple(schema.physical_columns),
        feasible_pareto_identities=tuple(_identity(r) for r in front),
        normalized_costs={_identity(r): row.tolist() for r, row in zip(front, normalized)},
    )


def read_representatives(path: Union[str, Path]) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
