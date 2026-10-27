# Task Completion Summary: Task 192

## Summary
Resolved the failure in `tests/test_mock_evaluator.py::test_execution_code_has_no_capability_probing` caused by the capability check `hasattr(backend, "close")` introduced in `candidate_evaluator.py` during Task 191. The Evaluator protocol in `mobo_linac.execution` strictly defines only `evaluate(...)` and forbids capability-probing heuristics. Candidate evaluation in `CandidateEvaluatorBase` was restored to its standard protocol usage.

## Key Changes
- `src/mobo_linac/execution/candidate_evaluator.py`: Removed `hasattr(backend, "close")` and restored standard invocation of `evaluate_requests(backend, ...)`. Evaluator lifecycle management for benchmark and campaign processes remains cleanly and correctly handled at the campaign layer (`CampaignLoop.run()` and `scheduler.run_campaign_job()`).
- `tests/test_mock_evaluator.py`: Verified `test_execution_code_has_no_capability_probing` passes with 0 regex offenders.
- `tests/test_candidate_evaluator.py`: Verified all 11 candidate evaluation tests pass.

## Validation Results
- `pytest tests/test_mock_evaluator.py`: 11 passed in 0.40s.
- `pytest tests/test_candidate_evaluator.py`: 11 passed in 2.31s.
- `pytest tests/test_benchmark_scheduler.py`: 12 passed in 105.59s.
- `git diff --check` and clean execution architecture verified.

## Status
Completed.
