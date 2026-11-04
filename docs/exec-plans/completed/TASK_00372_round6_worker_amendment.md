# Task Completion Summary: Task 00372

## Summary
Recorded the author's authorization to restart round6 (step 0) and raised the worker ceiling from two to 22 by a dated amendment (step 0a), leaving the frozen protocol and specification files unchanged. A direct check at 22 busy workers reproduced 22 completed runs exactly. No refined outcome was produced or used.

## Key Changes
- **Amendment.** `r6_protocol_amendment_01.md` and `r6_execution_amendment_01.json` supersede only `workers_total`. The JSON is tied to the frozen specification by its SHA-256. Sample, levels, seeds, budgets, tolerances, timeouts, zero retries, endpoints, serial order and GPU policy are unchanged.
- **Drivers.** `execution_workers()` in `scripts/prepare_revision_round6.py` supplies the ceiling to `evaluate_revision_round6_resolution.py` and `evaluate_revision_round6_scaling.py`, and refuses an amendment for another specification. `study_config` and `result_value` were extracted from `execute` for reuse; behavior is otherwise unchanged. The chain's comment was updated.
- **Worker check.** `scripts/check_revision_round6_workers.py` re-tracks an evenly spaced subset of completed production settings with all workers busy, in `results/revision_round6/worker_check/`, outside the study budget.
- **Supplement.** S1.15 map rows, the input inventory and the README cover the new records.

## Validation Results
- **Worker check (22 settings, 22 workers):** 22/22 valid; agreement with the historical ledgers and the two-worker journal; largest relative difference 0.0; median run time 1.04× that of two workers (mean 244.7 s vs 239.8 s). Finer levels were not measured.
- **Code path:** completions are returned in request order (`evaluate_requests`), so campaign training order does not depend on the worker count.
- **Tests:** `tests/test_revision_round6.py` and the new `tests/test_revision_round6_workers.py` pass; the worker-ceiling assertion now expects 22.
- `ruff check scripts tests`, `scripts/verify_docs_sync.py` and `scripts/build_supplement_manifest.py` passed.
- **Full test suite: not run in this step.** The chain's stable-source validation gate runs it before the remaining physical stages, and the earlier receipt no longer matches the changed code.

## Status
Completed and committed locally. No push performed. The pause marker remains until the recovery step.
