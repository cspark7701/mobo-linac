# Task Completion Summary: Task 00371

## Summary
Fixed the CPU-only coverage gap in `src/mobo_linac/campaigns/strategies.py` by adding portable tests for CUDA random-stream handling. Production code and coverage thresholds remain unchanged.

## Key Changes
- The existing local coverage data identified two missed statements, lines 100–101: entering the CUDA device context and seeding its generator in `proposal_random_stream`.
- Added four parameterized cases covering explicit CUDA device selection and implicit current-device selection, each with successful and failing proposal bodies.
- Retained the real `torch.random.fork_rng` context and CPU RNG. Simulated only CUDA device/state operations with CPU generators, so these cases run on GitHub's CPU-only runners.
- Verified deterministic seeded CPU and simulated CUDA draws, selection of the correct generator, restoration of all saved RNG states, and cleanup after exceptions. These are control-flow/state-isolation checks, not GPU numerical validation.

## Validation Results
- With `CUDA_VISIBLE_DEVICES=''`, the focused strategy-related run reports **34 passed, 3 GPU-only tests skipped**.
- Coverage measured with `--cov=src/mobo_linac/campaigns`, then restricted using `coverage report --include='*/campaigns/strategies.py' --fail-under=100 -m`: **105 statements, 0 missed, 100%**.
- Focused test selection: `tests/test_model_edge_cases.py`, `tests/test_normalized_constraints.py`, `tests/test_gp_and_acquisition.py::test_campaign_checkpoint_links_reloadable_model`, and `tests/test_benchmark_campaign.py::test_partial_final_batch_reaches_acquisition_proposal`.
- The four new cases also pass independently. During development, their initial assertion incorrectly expected the CUDA seeding context to remain active throughout the proposal; corrected it to verify device selection during seeding and restoration before the proposal body. The final focused run is clean.
- Ruff for the changed test file and `strategies.py`, and `git diff --check`, passed.

## Scope and Limitations
Only the strategy-focused test additions and this completion record changed. No application behavior, simulation data, workflow, coverage exclusion or threshold changed. Coverage was written under `/tmp`, preserving the existing package coverage database. No remote GitHub Actions query, simulation, push or full-package coverage claim is part of this task.

## Status
Completed and committed locally. The requested module reaches 100% line coverage without requiring CUDA hardware.
