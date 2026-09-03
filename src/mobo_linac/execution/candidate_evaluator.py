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


@dataclass
class EvaluationTask:
    """Specification of an individual candidate evaluation or rerun task."""

    task_id: str
    role: str
    parameters: List[float]
    nominal_result: Optional[EvaluationResult] = None
    namelist_overrides: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationOutcome:
    """Outcome of an evaluated task along with metric deltas relative to nominal."""

    task: EvaluationTask
    evaluated_result: EvaluationResult
    metric_deltas: Dict[str, float] = field(default_factory=dict)


def compute_metric_deltas(
    nominal_result: Optional[EvaluationResult],
    evaluated_result: EvaluationResult,
) -> Dict[str, float]:
    """
    Computes relative percentage differences between nominal and evaluated results.

    Returns:
        Dict containing diff_emit_x_pct, diff_emit_y_pct, diff_sigma_energy_pct,
        diff_transmission_pct, and max_diff_pct.
    """
    if nominal_result is None or not nominal_result.objectives_physical or not evaluated_result.objectives_physical:
        return {
            "diff_emit_x_pct": float("nan"),
            "diff_emit_y_pct": float("nan"),
            "diff_sigma_energy_pct": float("nan"),
            "diff_transmission_pct": float("nan"),
            "max_diff_pct": float("nan"),
        }

    nom_objs = nominal_result.objectives_physical
    eval_objs = evaluated_result.objectives_physical

    diff_ex = abs(eval_objs[0] - nom_objs[0]) / nom_objs[0] * 100.0 if nom_objs[0] > 0 else 0.0
    diff_ey = abs(eval_objs[1] - nom_objs[1]) / nom_objs[1] * 100.0 if nom_objs[1] > 0 else 0.0
    diff_se = abs(eval_objs[2] - nom_objs[2]) / nom_objs[2] * 100.0 if nom_objs[2] > 0 else 0.0

    nom_diags = nominal_result.diagnostics or {}
    eval_diags = evaluated_result.diagnostics or {}

    nom_trans = nom_diags.get("transmission_fraction", nom_diags.get("transmission", 1.0))
    eval_trans = eval_diags.get("transmission_fraction", eval_diags.get("transmission", 1.0))
    diff_trans = abs(eval_trans - nom_trans) / nom_trans * 100.0 if nom_trans > 0 else 0.0

    max_diff = max(diff_ex, diff_ey, diff_se, diff_trans)

    return {
        "diff_emit_x_pct": diff_ex,
        "diff_emit_y_pct": diff_ey,
        "diff_sigma_energy_pct": diff_se,
        "diff_transmission_pct": diff_trans,
        "max_diff_pct": max_diff,
    }


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
    ):
        self.config = config or load_config()
        self.base_output_dir = Path(base_output_dir)
        self.num_workers = int(num_workers)
        self.timeout = int(timeout)

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
        return compute_metric_deltas(nominal_result, evaluated_result)

    def evaluate_plan_parallel(
        self,
        tasks: List[EvaluationTask],
        custom_evaluator: Optional[Any] = None,
        on_task_complete: Optional[Callable[[EvaluationOutcome], None]] = None,
    ) -> List[EvaluationOutcome]:
        """
        Executes evaluation tasks in parallel, mapping outputs to EvaluationOutcome records.
        """
        if not tasks:
            return []

        outcomes: List[EvaluationOutcome] = []

        if custom_evaluator is not None:
            for task in tasks:
                raw_res = custom_evaluator(
                    task.parameters,
                    run_id=task.task_id,
                    eval_id=task.role,
                )
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
                )
                outcomes.append(outcome)
                if on_task_complete is not None:
                    on_task_complete(outcome)
            return outcomes

        evaluator = BatchEvaluator(
            base_results_dir=self.base_output_dir,
            template_dir=".",
            max_workers=self.num_workers,
            timeout=self.timeout,
            config=self.config,
        )

        cand_params = [t.parameters for t in tasks]
        eval_ids = [t.task_id for t in tasks]

        raw_results = evaluator.evaluate_batch(
            candidates=cand_params,
            run_id="candidate_eval",
            eval_ids=eval_ids,
        )

        for task, raw_r in zip(tasks, raw_results):
            eval_res = create_evaluation_result(raw_r, self.config)
            deltas = self.compute_relative_metric_deltas(task.nominal_result, eval_res)
            outcome = EvaluationOutcome(
                task=task,
                evaluated_result=eval_res,
                metric_deltas=deltas,
            )
            outcomes.append(outcome)
            if on_task_complete is not None:
                on_task_complete(outcome)

        return outcomes
