"""
Execution management module for mobo_linac.
Provides process-safe parallel evaluation of ASTRA simulation batches,
candidate evaluation base abstractions, and canonical mock evaluation infrastructure.
"""

from mobo_linac.execution.candidate_evaluator import (
    CandidateEvaluatorBase,
    EvaluationOutcome,
    EvaluationTask,
    compute_metric_deltas,
)
from mobo_linac.execution.mock import (
    CliMockEvaluator,
    MockBatchEvaluator,
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
    "MockBatchEvaluator",
    "CliMockEvaluator",
]
