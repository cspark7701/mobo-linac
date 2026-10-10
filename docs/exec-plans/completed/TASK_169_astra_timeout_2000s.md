# Task Completion Summary: Task 169

## Summary
Raised the per-attempt ASTRA time limit (`execution.timeout_sec`) from 30 s to 2000 s. This resolves the open item recorded in TASK_168: a single real ASTRA run takes about 280 s on the reference host (281.4 s measured with two parallel workers; 322–337 s with four concurrent runs), so the old 30 s limit would have timed out every evaluation of a physical campaign.

## Key Changes
- `configs/mobo_200MeV.yaml` and `configs/publication_200MeV.yaml`: `execution.timeout_sec: 2000`.
- `src/mobo_linac/config.py`: the `ExecutionConfig.timeout_sec` default is 2000, so configurations that omit the field get the same limit.
- No beam physics, campaign settings or reporting conventions changed. Archived `release/` artifacts were left untouched.

## Notes
- The publication configuration's SHA-256 changes. Launch records (`logs/launch_*.json`) capture the new hash, and the configuration should be frozen with this value before the Stage 1 pilot.
- A timed-out attempt is reported as `TIMEOUT` (TASK_168). It is retried only if `TIMEOUT` is in `execution.retry_statuses`, within `execution.retries`, which is 0 in both configurations.

## Validation Results
Config (96), docs sync, Pareto verification (19), production launcher (9) and package layout (15) tests pass.

## Status
Completed.
