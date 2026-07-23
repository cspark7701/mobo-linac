"""
Execution management module for mobo_linac.
Provides process-safe parallel evaluation of ASTRA simulation batches.
"""

from mobo_linac.execution.parallel import (
    BatchEvaluator,
    evaluate_candidates_parallel,
)

__all__ = [
    "BatchEvaluator",
    "evaluate_candidates_parallel",
]
