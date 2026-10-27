# Task Completion Summary: Task 195

## Summary
Stopped the running CPU primary experiment at the user's request, preserved one late-stage surrogate for a full CPU/GPU proposal comparison, and changed production stages 04 onward to a CUDA device policy.

## Key Changes
- Terminated process group 415430, covering the stage-04 shell, benchmark scheduler, campaign controllers, and worker pools. Confirmed that the group had no remaining processes.
- Preserved the unconstrained seed-42 iteration-18 GP artifact (152 training observations), configuration, observed history, proposal history, completion evidence, scheduler state, launch records, and original primary logs under `results/paper_production/device_benchmark_20261016/input/`.
- Added `tools/benchmark_saved_proposal.py` to restore the fitted model without refitting, benchmark full float64 qLogNEHVI proposals on CPU and CUDA, record timings/candidates/failures, and compare results. Each uses eight candidates, ten restarts, 1,024 raw samples, a 200-iteration cap, the default 128 MC samples, and one PyTorch CPU thread. Both devices use restart batch limit one; the archived CPU run used five. This preserves the total acquisition budget while using the same restart chunking on both devices.
- Added an optional, explicitly selected post-benchmark cleanup: only after both workers succeed and their workload metadata match, remove the old `04_primary/` directory, its stage logs, and status markers. Preserved benchmark evidence and stages 01–03 are outside that deletion. A restarted benchmark or symlink prevents cleanup.
- Set the default device for stages 04–07 to `cuda:0`. Stages 04/05 validate CUDA availability and an actual float64 allocation before optimization. Stages 06/07 have no acquisition optimizer and retain their existing CPU ASTRA audits/report generation, recording `optimization=none`.
- Preserved all physical validation, constraints, seeds, evaluation budgets, precision, batches, and simulation settings. Updated production guidance to distinguish ASTRA-only forecasts from proposal costs and recommend one GPU campaign initially.

## Validation Results
All 23 production-script, benchmark-worker, and cleanup-coordinator tests passed. These include unavailable-CUDA rejection, exact proposal-budget forwarding, successful cleanup, and preservation of primary outputs after a failed device benchmark. Shell syntax and whitespace checks passed. Tests caught a result-field serialization mismatch before the long benchmark finished; it was corrected, and the two initial timing workers were stopped so the final comparison could restart with corrected reporting.

## Status
Completed: both full-budget device benchmarks succeeded and the old primary outputs were removed. Production was not restarted. Git publication was explicitly approved; its outcome is recorded in `results/paper_production/device_benchmark_20261016/publication_status.json`.

## Progress at 2026-10-16 13:45 KST
The GPU benchmark completed successfully in 368.11 seconds (6 min 8 s), with 4.20 seconds for acquisition construction and 363.16 seconds for optimization. Peak allocated GPU memory was 2,083,850,752 bytes (approximately 1.94 GiB). The CPU benchmark remained active at approximately 14 minutes elapsed with one CPU core occupied. No restart or optimizer-iteration progress counter is available, so its remaining duration cannot be reliably inferred. Historical final-batch CPU wall time was about 10.3 hours, including fitting and simulation and with different restart chunking; it is context rather than an equivalent proposal-only timing. Cleanup remains pending until CPU completion.

## Authorized Git Publication
The user explicitly approved `git add`, `git commit`, and `git push` for this task after the running benchmark finishes, overriding the repository's usual no-push rule for this publication only. Automatic approval review nevertheless rejected a combined background commit/push action because the authorization did not explicitly name the payload and destination for private-repository egress. A precise approval request was presented for the 12 reviewed code/test/documentation files to `https://github.com/cspark7701/mobo-linac`, branch `main`, excluding simulation data and model files.

The unaffected local work uses a detached local-commit watcher: after successful comparison and primary cleanup it verifies the reviewed file contents and branch, records the final benchmark result in this task summary, then stages only the task's files and commits using the repository's required message format. This watcher performs no remote operation. It records its outcome and commit ID in `results/paper_production/device_benchmark_20261016/publication_status.json` and stops on failed benchmark/cleanup or unexpected repository changes. Remote push remains pending the precise approval. No remote workflow status is queried.

## Benchmark Completion
Status: completed.

Same saved 152-observation surrogate, float64, qLogNEHVI, eight candidates, ten restarts,
1,024 raw samples, up to 200 optimizer iterations, and 128 MC samples.
Both devices use restart batch limit one; the archived CPU proposal used five.
This changes restart chunking, not the search budget. No GP refit or ASTRA evaluation was run.
The CPU and GPU workers ran concurrently with one PyTorch CPU thread each;
these are workload timings, not a claim of bitwise equal candidates or an end-to-end production speedup.

- cpu: completed; elapsed 35212.94 s.
  Acquisition construction 5.55 s; optimization 35207.05 s.
- cuda_0: completed; elapsed 368.11 s.
  Acquisition construction 4.20 s; optimization 363.16 s.

Measured acquisition construction + proposal speedup: 95.85×.

Old primary output removed: True.
Physical constraints, validation counts, seeds, budgets, and ASTRA settings in the scripts are unchanged.
Production was not restarted. Raw per-device results and logs are retained in this directory.
