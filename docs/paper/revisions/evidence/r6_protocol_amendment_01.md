# Round6 protocol amendment 01: worker ceiling

Date: 4 November 2026. Authorized by the author. `r6_protocol.md`, `r6_specification.json` and the sampling files stay frozen and unchanged; this record and `r6_execution_amendment_01.json` supersede only their two-worker ceiling.

## Change

The global ceiling rises from two to **22 CPU evaluation workers**, with one thread per process. The two re-runs of the interrupted attempts stay at two workers; the remaining numerical attempts and the scaling campaigns use the new ceiling. Campaigns still run one at a time with joint batches of eight, so scaling uses at most 16 workers for the initial design and eight afterwards.

**Reason:** run time only. The machine became available, and the remaining 4,704 attempts were estimated at about four weeks with two workers. The decision uses no scientific outcome. At this date 387 production and 44 combined-fine results exist; only their run times informed the estimate.

## Unchanged

The sample, numerical levels, seeds, budgets, tolerances, timeouts, zero retries, endpoints, analyses, serial order of the studies, shared worker lock and GPU policy.

## Why results should not depend on the worker count

ASTRA runs in separate processes with separate working directories and no shared state, and completions are returned to the campaign in request order (`mobo_linac.execution.contracts.evaluate_requests`), so training order does not follow completion order. To test this directly, `scripts/check_revision_round6_workers.py` re-tracks 22 completed production settings with all 22 workers busy and requires agreement with the historical ledgers and the two-worker journal at the frozen reproduction tolerances. The receipt is `r6_worker_check.json`: all 22 settings reproduced with a largest relative difference of exactly zero across the checked diagnostics and objectives, and the median run took 1.04 times as long as the same setting at two workers. These attempts are infrastructure checks in `results/revision_round6/worker_check/`, outside the study budget and all analyses.

## Expected effect on timing

The machine has 12 physical cores and 24 threads, so 22 busy workers share cores. The check above measured a 4 % slowdown at production resolution; finer levels were not measured. Elapsed times remain descriptive. The paired scaling arms run under the same worker policy, so their cost comparison is not affected by this amendment, but numerical levels run before and after it are not comparable in elapsed time.
