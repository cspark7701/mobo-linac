# Task Completion Summary: Task 00352

## Summary
Add an explicit normalized-residual acquisition convention.

## Key Changes
Implement raw-compatible residual mode, temperature and physical-width metadata, explicit posterior sample count and matched per-iteration random streams. Physical diagnostics, feasibility tests and GP targets stay unchanged. Validate q=8 acquisition gradients on CPU/CUDA, unit consistency and checkpoint restoration: 159 focused tests passed, followed by 117 sampling/restart tests. Lint and documentation sync pass; the full coverage suite is running before physical scaling campaigns are launched.

## Validation Results
Reviewed the scoped diff and checked whitespace before committing. Additional task-specific checks are recorded in the description above.

## Status
Completed locally. The user authorized a push after the round6 revision work is complete; no push at this step.
