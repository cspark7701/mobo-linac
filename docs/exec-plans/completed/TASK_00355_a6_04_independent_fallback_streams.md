# Task Completion Summary: Task 00355

## Summary
Isolate experiment fallback randomness and pin campaign code.

## Key Changes
Ensure optimizer-fallback and low-data Sobol proposals use the matched per-iteration proposal seed rather than consuming the initial-design stream. Preserve default campaign behavior. Record scientific code hashes and pause matched campaigns if code changes. Nine focused normalized-mode tests pass, including saved initial-stream position; lint passes.

## Validation Results
Reviewed the scoped diff and checked whitespace before committing. Additional task-specific checks are recorded in the description above.

## Status
Completed locally. The user authorized a push after the round6 revision work is complete; no push at this step.
