"""
Execution management module for mobo_linac.
Provides process-safe parallel evaluation of ASTRA simulation batches and
candidate evaluation base abstractions for robustness and verification.
"""

from mobo_linac.execution.candidate_evaluator import (
    CandidateEvaluatorBase,
    EvaluationOutcome,
    EvaluationTask,
    compute_metric_deltas,
)
from mobo_linac.execution.parallel import (
    BatchEvaluator,
    evaluate_candidates_parallel,
)

__all__ = [
    "BatchEvaluator",
    "evaluate_candidates_parallel",
    "CandidateEvaluatorBase",
    "EvaluationTask",
    "EvaluationOutcome",
    "compute_metric_deltas",
]
