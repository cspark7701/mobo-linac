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

from mobo_linac.config import MoboConfig, load_config
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.execution.parallel import BatchEvaluator
from mobo_linac.execution.requests import EvaluationRequest
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
    config: Optional[MoboConfig] = None,
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
        config: Optional[MoboConfig] = None,
        base_output_dir: Union[str, Path] = "results",
        num_workers: int = 1,
        timeout: int = 30,
        template_dir: Union[str, Path] = ".",
        template_in: str = "astra.in",
    ):
        self.config = config or load_config()
        self.base_output_dir = Path(base_output_dir)
        self.num_workers = int(num_workers)
        self.timeout = int(timeout)
        self.template_dir = Path(template_dir)
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

    def evaluate_plan_parallel(
        self,
        tasks: List[EvaluationTask],
        custom_evaluator: Optional[Any] = None,
        on_task_complete: Optional[Callable[[EvaluationOutcome], None]] = None,
        request_evaluator: Optional[Any] = None,
        run_id: str = "candidate_eval",
    ) -> List[EvaluationOutcome]:
        """
        Executes evaluation tasks in parallel, mapping outputs to EvaluationOutcome records.
        """
        if not tasks:
            return []

        outcomes: List[EvaluationOutcome] = []

        if custom_evaluator is not None and request_evaluator is not None:
            raise ValueError("Choose a legacy evaluator or a complete-request evaluator")
        if custom_evaluator is not None and any(task.namelist_overrides for task in tasks):
            raise ValueError("Namelist overrides require a complete-request evaluator")
        if custom_evaluator is not None or request_evaluator is not None:
            for task in tasks:
                if request_evaluator is not None:
                    raw_res = request_evaluator(task.to_request(), config=self.config)
                else:
                    raw_res = custom_evaluator(task.parameters, run_id=task.task_id, eval_id=task.role)
                eval_res = (
                    raw_res
                    if isinstance(raw_res, EvaluationResult)
                    else create_evaluation_result(raw_res, self.config)
                )
                deltas = self.compute_relative_metric_deltas(task.nominal_result, eval_res)
                outcome = EvaluationOutcome(
                    task=task,
                    evaluated_result=eval_res,
                    metric_deltas=deltas,
                    execution_details=raw_res if isinstance(raw_res, dict) else {},
                )
                outcomes.append(outcome)
                if on_task_complete is not None:
                    on_task_complete(outcome)
            return outcomes

        evaluator = BatchEvaluator(
            base_results_dir=self.base_output_dir,
            template_dir=self.template_dir,
            template_in=self.template_in,
            max_workers=self.num_workers,
            timeout=self.timeout,
            config=self.config,
            retries=self.config.execution.retries,
            clean_on_success=self.config.execution.clean_on_success,
        )

        raw_results = evaluator.evaluate_requests(
            requests=[task.to_request() for task in tasks],
            run_id=run_id,
        )

        if len(raw_results) != len(tasks):
            raise ValueError("Backend returned an incomplete candidate batch")
        for task, raw_r in zip(tasks, raw_results):
            eval_res = create_evaluation_result(raw_r, self.config)
            deltas = self.compute_relative_metric_deltas(task.nominal_result, eval_res)
            outcome = EvaluationOutcome(
                task=task,
                evaluated_result=eval_res,
                metric_deltas=deltas,
                execution_details=raw_r,
            )
            outcomes.append(outcome)
            if on_task_complete is not None:
                on_task_complete(outcome)

        return outcomes
