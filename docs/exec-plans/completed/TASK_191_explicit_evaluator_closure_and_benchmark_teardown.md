# Task Completion Summary: Task 191

## Summary
Addressed the multiprocessing exit deadlock in multi-campaign benchmark runs (`03_screening.sh` and `04_primary.sh`) by adding explicit evaluator teardown in `CampaignLoop.run()`, `scheduler.run_campaign_job()`, and `CandidateEvaluatorBase.evaluate_plan_parallel()`. This ensures nested `ProcessPoolEvaluator` worker processes shut down cleanly before campaign controller processes attempt to exit and be joined by their parent executor.

## Key Changes
- `src/mobo_linac/campaigns/runner.py`: Wrapped `CampaignLoop.run()` execution in a `try...finally` block that invokes `self.evaluator.close()` for runner-instantiated evaluators, cleanly joining evaluator worker processes.
- `src/mobo_linac/campaigns/scheduler.py`: Wrapped `run_campaign_job()` in a `try...finally` block that guarantees any job evaluator with a `close()` method is cleanly closed upon task completion.
- `src/mobo_linac/execution/candidate_evaluator.py`: Closed locally created default evaluators in `evaluate_plan_parallel()` inside a `try...finally` block.
- `scripts/production/03_screening.sh` & `scripts/production/04_primary.sh`: Documented explicit evaluator lifecycle management on worker teardown.
- `tests/test_benchmark_scheduler.py`: Added `test_campaign_loop_explicitly_closes_default_evaluator` verifying that `CampaignLoop.run()` invokes `close()` on the default `ProcessPoolEvaluator` upon campaign completion.

## Validation Results
- `pytest tests/test_benchmark_scheduler.py`: 12 passed in 64.51s.
- `pytest tests/test_production_scripts.py`: 16 passed in 0.40s.
- Verified all 9 completed screening campaigns (360 total evaluations) in `results/paper_production/03_screening/benchmark/per_seed/` remain completely intact and valid.
- Zero commits or pushes performed autonomously.

## Status
Completed.
