# Task Completion Summary: Task 183

## Summary
Addressed the reported pytest standardization and Cholesky warnings while preserving scientific data, GP transforms, and existing numerical warning visibility.

## Key Changes
- `src/mobo_linac/models/gp.py`: explicitly retain BoTorch Standardize's existing `1e-8` threshold. For measured output deviations below that threshold, suppress only the expected constructor notice about missing unit variance. Mean-only scaling is intentional for those small/constant outputs and is recorded at DEBUG level; input-scaling and numerical warnings remain visible.
- `tests/test_gp_models.py`: add CPU/CUDA checks that constant, small, and ordinary outcomes retain the same targets, means, and scales as default Standardize. Assert unrelated input-scaling warnings remain visible.
- `tests/test_gp_and_acquisition.py`: seed the acquisition-construction fixture and evaluate a distinct midpoint query. Querying an already observed noisy-baseline point created a singular joint MC posterior and triggered the reported Cholesky jitter warning.
- No global warning filter was added. Beam physics, GP scaling, observation noise, and production Cholesky settings remain unchanged.

## Validation Results
- New warning-policy and acquisition-construction regressions: 9 passed on CPU/CUDA.
- Affected GP, acquisition, surrogate, scalarized campaign, configuration-boundary and CLI workflow tests: 85 passed, without a warning summary.
- Notebook tests using a temporary kernel tied to the installed project interpreter: 10 passed, without a warning summary.
- Reported InputDataWarning and Cholesky jitter notices were promoted to errors in those successful runs; existing noise-floor warning filters remained active.
- An initial overly broad numerical-warning error filter also promoted the repository's expected fixed-noise-floor notices to errors (26 failures, 59 passes). Replaced that verification filter with the specific reported Cholesky message and reran successfully; no production fix was made for expected noise-floor notices.
- Ruff and `git diff --check` passed.
- No real ASTRA runs, Git pushes, or remote workflow queries were performed. The entire test suite was not rerun.

## Status
Completed.
