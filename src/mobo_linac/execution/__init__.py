"""
Execution management module for mobo_linac.
Provides process-safe parallel evaluation of ASTRA simulation batches,
candidate evaluation base abstractions, and canonical mock evaluation infrastructure.
"""

from mobo_linac.execution.requests import EvaluationRequest, requests_for
from mobo_linac.execution.candidate_evaluator import (
    CandidateEvaluatorBase,
    EvaluationOutcome,
    EvaluationTask,
    compute_metric_deltas,
)
from mobo_linac.execution.contracts import Evaluator, evaluate_requests
from mobo_linac.execution.mock import FunctionEvaluator, MockEvaluator
from mobo_linac.execution.parallel import ProcessPoolEvaluator

__all__ = [
    "Evaluator",
    "evaluate_requests",
    "ProcessPoolEvaluator",
    "FunctionEvaluator",
    "CandidateEvaluatorBase",
    "EvaluationTask",
    "EvaluationRequest",
    "requests_for",
    "EvaluationOutcome",
    "compute_metric_deltas",
    "MockEvaluator",
]
