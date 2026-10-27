# Task 05 — Structured Evaluation Results and Failure Semantics

## Summary

Task 05 defined a structured `EvaluationResult` data schema to cleanly separate simulation validity, beam physics feasibility, and objective values, preventing corrupted GP training datasets.

## Accomplishments

1. **Typed Result Dataclass**: Created `EvaluationResult` and `create_evaluation_result` in `src/mobo_linac/evaluation.py`.
2. **Failure Categorization**: Created `FailureCategory` enum distinguishing `SUCCESS`, `INFEASIBLE_BEAM`, `ASTRA_TIMEOUT`, `NONZERO_RETURN`, `MISSING_OUTPUT`, `EMPTY_OUTPUT`, `NAN_INF_DIAGNOSTICS`, `INVALID_TRANSMISSION`, and `UNHANDLED_EXCEPTION`.
3. **Data Serialization Utilities**: Implemented CSV and JSON serialization routines in `src/mobo_linac/io/results.py` saving `evaluations.csv`, `objectives_physical.csv`, `objectives_model.csv`, `constraints.csv`, `pareto_all.csv`, and `pareto_feasible.csv`.
4. **GP Training Filter**: Implemented `get_train_tensors` to filter out invalid/unconverged simulations while retaining feasible/infeasible valid samples for constraint-aware acquisition.

## Status

**Completed**. Validated by `tests/test_evaluation_result.py` and `tests/test_result_serialization.py`.
