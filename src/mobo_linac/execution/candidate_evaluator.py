"""
Base Candidate Evaluator Abstraction for Verification and Robustness Studies.

Provides unified parallel execution scheduling, working directory isolation,
and relative metric delta computations across nominal and perturbed/rerun candidates.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
import numpy as np

from mobo_linac.config import MoboConfig
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution.parallel import ProcessPoolEvaluator
from mobo_linac.execution.requests import EvaluationRequest
from mobo_linac.execution.contracts import Evaluator, evaluate_requests, evaluation_identity
from mobo_linac.result_schema import ResultSchema
from mobo_linac.diagnostics import finite_measurement, normalize_diagnostics


@dataclass
class EvaluationTask:
    """Specification of an individual candidate evaluation or rerun task."""

    task_id: str
    role: str
    parameters: List[float]
    nominal_result: Optional[EvaluationResult] = None
    namelist_overrides: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_settings: Dict[str, float] = field(default_factory=dict)

    def to_request(self) -> EvaluationRequest:
        return EvaluationRequest(self.task_id, list(self.parameters), self.namelist_overrides,
                                 dict(self.source_settings), dict(self.metadata))


@dataclass
class EvaluationOutcome:
    """Outcome of an evaluated task along with metric deltas relative to nominal."""

    task: EvaluationTask
    evaluated_result: EvaluationResult
    metric_deltas: Dict[str, Any] = field(default_factory=dict)
    execution_details: Dict[str, Any] = field(default_factory=dict)


def compute_metric_deltas(
    nominal_result: Optional[EvaluationResult], evaluated_result: EvaluationResult,
    config: MoboConfig,
) -> Dict[str, Any]:
    """Compare configured physical objectives and measured transmission, without defaults.

    Undefined relative errors (including a zero nominal denominator) remain unknown.
    Compatibility scalar fields remain NaN when their configured objective is absent.
    """
    schema = ResultSchema.from_config(config)
    nominal = schema.extract(nominal_result.objectives_physical) if nominal_result else None
    rerun = schema.extract(evaluated_result.objectives_physical)
    issues = {}
    def relative(name, before, after):
        if before is None or after is None:
            issues[name] = "missing"
        elif not finite_measurement(before) or not finite_measurement(after):
            issues[name] = "nonfinite"
        elif before == 0:
            issues[name] = "zero_denominator"
        else:
            value = abs(after - before) / abs(before) * 100.0
            if np.isfinite(value):
                return float(value)
            issues[name] = "nonfinite_relative_error"
        return None
    objective_deltas = {name: relative(name, nominal[index] if nominal is not None else None,
                                      rerun[index] if rerun is not None else None)
                        for index, name in enumerate(schema.physical_columns)}
    original_diags = normalize_diagnostics(nominal_result.diagnostics) if nominal_result else {}
    rerun_diags = normalize_diagnostics(evaluated_result.diagnostics)
    transmission = relative("transmission_fraction", original_diags.get("transmission_fraction"),
                            rerun_diags.get("transmission_fraction"))
    values = list(objective_deltas.values()) + [transmission]
    result = {
        "objective_deltas_pct": objective_deltas, "comparison_issues": issues,
        "comparison_complete": not issues,
        "diff_transmission_pct": transmission if transmission is not None else float("nan"),
        "max_diff_pct": max(values) if not issues else float("nan"),
    }
    for name, column in [("diff_emit_x_pct", "norm_emit_x_m_rad"),
                         ("diff_emit_y_pct", "norm_emit_y_m_rad"),
                         ("diff_sigma_energy_pct", "sigma_energy_eV")]:
        value = objective_deltas.get(column)
        result[name] = value if value is not None else float("nan")
    return result


class CandidateEvaluatorBase(ABC):
    """
    Abstract base class managing parallel worker lifecycle, candidate directory isolation,
    and relative metric comparisons.
    """

    def __init__(
        self,
        config: MoboConfig,
        base_output_dir: Union[str, Path] = "results",
        num_workers: int = 1,
        timeout: int = 30,
        template_dir: Optional[Union[str, Path]] = None,
        template_in: str = "astra.in",
    ):
        from mobo_linac.astra.runner import resolve_template_dir
        if not isinstance(config, MoboConfig):
            raise TypeError("Candidate evaluation requires the campaign MoboConfig.")
        self.config = config
        self.config.validate()
        for name, value in (("timeout", timeout), ("num_workers", num_workers)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
        self.base_output_dir = Path(base_output_dir)
        self.num_workers = num_workers
        self.timeout = timeout
        self.template_dir = Path(template_dir).resolve() if template_dir is not None else resolve_template_dir(config)
        self.template_in = template_in

    @abstractmethod
    def generate_evaluation_plan(
        self,
        candidates: Sequence[EvaluationResult],
    ) -> List[EvaluationTask]:
        """Generates the list of evaluation tasks (reruns or perturbations) from candidates."""
        pass

    def compute_relative_metric_deltas(
        self,
        nominal_result: Optional[EvaluationResult],
        evaluated_result: EvaluationResult,
    ) -> Dict[str, float]:
        """Computes relative percentage deltas between nominal and evaluated result."""
        return compute_metric_deltas(nominal_result, evaluated_result, self.config)

    def default_evaluator(self) -> ProcessPoolEvaluator:
        """The production ASTRA backend for this study's settings."""
        return ProcessPoolEvaluator(self.config, base_results_dir=self.base_output_dir, template_dir=self.template_dir,
                                    template_in=self.template_in, max_workers=self.num_workers, timeout=self.timeout)

    def evaluate_plan_parallel(
        self,
        tasks: List[EvaluationTask],
        evaluator: Optional[Evaluator] = None,
        on_task_complete: Optional[Callable[[EvaluationOutcome], None]] = None,
        run_id: str = "candidate_eval",
    ) -> List[EvaluationOutcome]:
        """Evaluate the tasks with one evaluator (default: the process-pool ASTRA backend)."""
        for task in tasks:
            task.to_request().validate(self.config)
        if not tasks:
            return []
        by_id = {evaluation_identity(task.task_id): task for task in tasks}
        outcomes: Dict[str, EvaluationOutcome] = {}

        def complete(completion):
            task = by_id[completion.result.evaluation_id]
            outcome = EvaluationOutcome(
                task=task, evaluated_result=completion.result,
                metric_deltas=self.compute_relative_metric_deltas(task.nominal_result, completion.result),
                execution_details=completion.details,
            )
            outcomes[completion.result.evaluation_id] = outcome
            if on_task_complete is not None:
                on_task_complete(outcome)

        backend = evaluator if evaluator is not None else self.default_evaluator()
        completions = evaluate_requests(backend, [task.to_request() for task in tasks],
                                        run_id=run_id, config=self.config, on_complete=complete)
        return [outcomes[completion.result.evaluation_id] for completion in completions]
