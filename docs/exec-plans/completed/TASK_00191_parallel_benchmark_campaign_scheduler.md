# Task Completion Summary: Task 186

## Summary
Implemented process-isolated scheduling of independent benchmark algorithm/seed campaigns with a global ASTRA-worker cap and coordinated reporting. Scientific budgets, batch sizes, seeds, physical simulation settings, validation gates, verification reruns, and robustness counts remain unchanged.

## Key Changes
- `campaigns/scheduler.py`: serializable campaign jobs, spawned campaign execution, configuration-source provenance restoration, controller thread limits, and exclusive POSIX benchmark locks.
- `campaigns/benchmark.py`: bounded concurrent submission, conservative worker allocation, completion validation in the parent, shared manifest ownership, PID/timing/error records in `scheduler.json`, and final aggregation only after successful completion. Stops submitting after a failure and drains active jobs; incomplete artifacts remain available for investigation. Sequential execution remains the default and supports existing custom evaluators.
- `cli/commands/benchmark.py`: added `--max-concurrent-campaigns`, `--total-workers`, and `--campaign-threads`. `--num-workers` caps each campaign; the global cap defaults to that value and is divided across campaign slots.
- Production steps 03/04: accept `MAX_CONCURRENT_CAMPAIGNS` and `CAMPAIGN_THREADS`; use `WORKERS` as the global ASTRA cap. Forecasts account for divided per-campaign worker allocations and unchanged evaluation/disk budgets.
- Benchmark aggregation now closes its saved comparison figures. Combined tests exposed an existing leak after repeated report generation.
- Added process-overlap, nested spawned evaluation-pool, resource-cap, seeded-history, exact-budget, completion-checksum, failure/crash, lock, serialization, valid-GP-artifact, CLI-forwarding, forecast and figure-lifecycle coverage.
- Updated README, production instructions, and strategic campaign plan. Documented custom evaluator serialization and the distinction between the ASTRA worker cap, controller CPU threads, and GPU memory.

## Validation Results
- Existing benchmark, production and CLI regressions: 59 passed before adding new coverage.
- Initial scheduler/package/CLI tests: 26 passed, including real spawned campaign overlap and nested process pools.
- Combined final regression suite: 91 passed without a warning summary. Includes successful constrained/unconstrained GP proposals, abrupt controller crashes, preserved failed outputs, exact short final batches, completed-run skipping and corruption rejection.
- The first combined run exposed three failures from open benchmark report figures (88 passed); closing owned figures resolved them, as confirmed by the subsequent successful run.
- Final controller-cleanup follow-up checks: 3 passed (ordinary failure, abrupt crash, and successful constrained/unconstrained GP campaigns).
- Ruff, `git diff --check`, and production shell syntax checks passed.
- No real ASTRA simulations, commits, pushes, or remote workflow queries were performed. No measured production speedup is claimed.

## Usage
After committing the tracked changes, start the primary stage with its usual predecessor gates:

```bash
WORKERS=8 MAX_CONCURRENT_CAMPAIGNS=2 CAMPAIGN_THREADS=1 scripts/production/04_primary.sh
```

This permits two independent campaigns with four ASTRA workers each. The same settings apply to step 03. Steps 02/05/06 retain their existing scheduling. All 30 primary algorithm/seed pairs and their 160-evaluation budgets remain in the plan.

## Status
Completed.
