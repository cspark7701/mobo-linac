# Task Completion Summary: Task 127

## Summary
Implemented Task 03 from `docs/05_refactor_tasks/`: introduced a versioned durable evaluation journal, persisted proposals before submitting initial and BO batches, reconciled streamed work against checkpoint history, and resumed only candidates without durable completions.

## Key Changes
- **`src/mobo_linac/io/journal.py`**: Added a version 1 envelope separating typed evaluation data from batch and candidate positions. Legacy flat JSONL records decode directly. Stable run/evaluation identities deduplicate identical completions and reject conflicts. Only incomplete unterminated trailing JSON is recoverable; malformed interior records and invalid schemas surface errors. JSONL is authoritative and flushed/synced before atomic CSV regeneration.
- **`src/mobo_linac/io/results.py` and I/O exports**: Routed streaming APIs through the journal, removed lossy CSV recovery fallback, exposed metadata-preserving journal reads, and added optional pending-proposal state to version 2 checkpoints. Atomic Torch saves now sync file contents and directory entries. Pending-only initial runs are discoverable without a completed checkpoint.
- **`src/mobo_linac/campaigns/state.py`**: Validated pending schema, batch sequence, candidate dimensions/bounds, stable IDs, initial design, and plan membership. An initial pending snapshot uses iteration `-1`, empty completed results/metrics, and a deferred reporting reference.
- **`src/mobo_linac/campaigns/recovery.py`**: Added read-only checkpoint/proposal/journal reconciliation before repairs, submissions, or artifact writes. Conflicting candidate data, identities, batches, base histories/metrics, or orphaned journal work fail explicitly. A checkpoint committed before pending-file cleanup covers the proposal and prevents repeated evaluations.
- **`src/mobo_linac/campaigns/runner.py`**: Saves `checkpoints/pending_batch.pt` with candidates, IDs, base history, and post-proposal RNG/Sobol state before evaluator submission. Recovery submits only missing IDs and restores proposal order. Pending batches retain their saved size; overrides apply to later proposals, with remaining fixed-budget batches recomputed accordingly. Checkpoint durability precedes pending-file removal. Existing journals/proposals require resume rather than a fresh campaign.
- **Evaluators**: Sequential, process-pool, and mock callbacks propagate persistence failures. Failed/crashed worker results retain candidate identity and parameters. The runner also detects custom evaluators that suppress callback errors.
- **Tests**: Added all-mode initial/BO interruption recovery with out-of-order successful and failed completions, repeated initial interruptions, interruption before/after checkpoint commits, forced Sobol fallback, pending-size budget overrides, CLI initial recovery, journal migration/corruption/deduplication, stale CSV recovery, conflicting state rejection before writes, and callback/CSV write failures.
- **Documentation**: Updated README, simulation guide, and benchmark protocol with durable artifacts, recovery rules, override semantics, compatibility, and benchmark-level limitations. Updated the ignored local Task 03 status and task index.

## Acceptance Criteria
- [x] Journal envelopes and legacy flat records with batch metadata round-trip without CSV fallback.
- [x] An interruption after an out-of-order completion submits only missing candidates on resume, preserving IDs and proposal order.
- [x] Repeated resume does not duplicate results and works before the first completed-batch checkpoint.
- [x] Fully journaled batches recover without resubmission across checkpoint commit/cleanup interruptions.
- [x] Callback persistence errors remain observable and cannot silently mark the campaign complete.
- [x] Corrupt or incompatible journal/proposal state fails before recovery writes or submissions.
- [x] Forced Sobol fallback resumes with matching subsequent candidates and metric histories.

## Validation Results
Used the existing `linac-opt` Python environment at `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python`, with CPU math threading bounded to one thread.

- Initial focused non-integration regression run: **68 passed, 1 skipped, 1 deselected**, 21.59 seconds.
- Broader affected regression run: **134 passed, 1 skipped, 1 deselected**, 71.13 seconds.
- Additional commit-boundary, forced-fallback, corruption, pending-file and CLI initial-recovery checks: **13 passed**, 5.76 seconds.
- Final focused checkpoint, journal serialization, and parallel evaluator run after tail-parser refinements: **79 passed, 1 skipped, 1 deselected**, 16.16 seconds.
- Final broader regression run: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m pytest tests/test_checkpoint_resume.py tests/test_result_serialization.py tests/test_parallel_evaluation.py tests/test_cli.py tests/test_benchmark_campaign.py tests/test_config.py tests/test_benchmark.py tests/test_scalarized_bo.py -m 'not integration' -q` — **146 passed, 1 skipped, 1 deselected**, 71.69 seconds. This verifies the final candidate-ID allocation and journal API exports.
- Final serialization run after adding exponent/Unicode truncation handling: `python -m pytest tests/test_result_serialization.py -q` — **21 passed**, 1.40 seconds.
- `git diff --check` passed. Tests used mock evaluators and temporary artifacts; no production ASTRA runs or remote GitHub workflow queries were needed. CUDA continuation was skipped because CUDA is unavailable; the real ASTRA integration test was excluded.

## Scope and Limitations
- Nominal beam physics, physical thresholds, objective units, field maps, source distributions, and archived simulation/publication outputs are preserved.
- Recovery reuses durably journaled completions, including failures. A solver result lost before journal persistence may require reevaluation. Existing retry/attempt-directory behavior remains outside this task and is addressed by the planned immutable-attempt refactor.
- The campaign parent is the single journal writer; concurrent campaigns writing the same directory are unsupported. CSV is a derived view and can be reconstructed after interruption.
- Evaluators without completion callbacks persist returned batches but cannot expose individual completed candidates before returning.
- Legacy flat JSONL is supported, but legacy work beyond a completed checkpoint without a saved proposal is rejected because the remaining candidates and post-proposal state cannot be recovered safely.
- Exact candidate-continuation checks use deterministic mock evaluations and stochastic proposal stubs through the real checkpoint/journal flow. GPU availability and numerical-environment limitations from Task 126 remain applicable.
- Benchmark dispatch does not automatically resume incomplete experiments or reconcile benchmark-level metrics/completion markers; campaign recovery is implemented independently of that orchestration.
- `docs/05_refactor_tasks/` remains ignored by the repository's existing `.gitignore`, so local task-status edits do not appear in the ordinary commit file list.

## Status
Completed.
