# Task Completion Summary: Task 126

## Summary
Implemented Task 02 from `docs/05_refactor_tasks/`: versioned and completed the campaign checkpoint contract, restored campaign settings and proposal streams on resume, preserved metrics across failed evaluations, and validated compatibility before writing existing run artifacts.

## Key Changes
- **`src/mobo_linac/io/results.py`**: Added version 2 checkpoint fields for run identity, optimization mode, normalized scalar weights, initial design, actual Sobol position, raw evaluation batch membership, full metric records, reporting scales, iteration plan, workers, budget, device, and CUDA/Python RNG states. Configuration dataclasses serialize as dictionaries. Loading maps tensors to CPU and explicitly rejects unsupported versions; legacy version 1 decoding records migration assumptions.
- **`src/mobo_linac/campaigns/state.py`**: Added independent configuration/state validation, legacy migration, and RNG restoration. Checks parameter order/bounds/mapping, objectives/signs, constraints, model/execution settings, reporting conventions, record identities, initial design, batch membership, metrics, and RNG payloads before resume writes.
- **`src/mobo_linac/campaigns/runner.py`**: Consolidated checkpoint persistence. Resume restores saved settings, raw batch boundaries, complete tracker history, Sobol position, and random state. Configuration and environment metadata are preserved. Batch-size overrides affect future proposals only; saved fixed budgets determine remaining batch counts and final partial batches. Resume requires the original run identity and compatible compute device.
- **`src/mobo_linac/acquisition/mobo.py`**: Final numerical fallback uses the campaign-owned Sobol stream, so its actual consumption is checkpointed. Standalone acquisition callers retain their existing optional-stream behavior.
- **`src/mobo_linac/config.py` and CLI resume**: Configuration reconstruction uses the existing validators without needing local configuration files. CLI defaults restore the saved plan, mode, weights, initial count, workers, and device. Legacy scalarized checkpoints require explicit original weights via `--legacy-scalar-weights`.
- **Tests**: Added interrupted/uninterrupted comparisons across all three optimization modes with failed evaluations, forced production acquisition fallback, low-data Sobol proposals, batch-size/budget overrides, incompatible configs and corrupt states, legacy migration, directory/device rejection, and CLI execution outside the project directory. Focused proposal stubs consume Torch, NumPy, and Python RNG through the real campaign/checkpoint flow; production GP/acquisition regressions remain separate.
- **Documentation**: Updated README and simulation guide with checkpoint continuation and migration rules; updated the ignored local Task 02 document and index.

## Acceptance Criteria
- [x] CLI resume preserves nondefault initial counts, scalarized weights, optimization mode, worker count, seed, and saved iteration plan.
- [x] Interrupted and uninterrupted CPU mock campaigns agree in candidates and metric histories, including failures and forced Sobol fallback.
- [x] Conditional CUDA RNG continuation coverage is present; the test skips when CUDA is unavailable.
- [x] Incompatible same-dimension configurations and invalid checkpoint state fail before existing metadata/artifacts are overwritten.
- [x] Completed batch membership survives future batch-size changes, including campaigns with a saved exact evaluation budget.
- [x] Legacy migration exposes missing settings and records its reproducibility limitations.

## Validation Results
Used the existing `linac-opt` Python environment at `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python`.

- Affected checkpoint, serialization, CLI, benchmark, and configuration regression run: **83 passed, 1 skipped** before final validation refinements.
- Follow-up checkpoint/CLI regression run: **40 passed, 1 skipped**, 75.29 seconds.
- Final broader affected regression run: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m pytest tests/test_checkpoint_resume.py tests/test_result_serialization.py tests/test_cli.py tests/test_benchmark_campaign.py tests/test_config.py tests/test_benchmark.py tests/test_scalarized_bo.py tests/test_gp_and_acquisition.py -k 'not test_tune_full_optimization_pipeline' -q` — **113 passed, 1 skipped, 1 deselected**, 80.89 seconds. This includes the final device-change and outside-project configuration checks.
- Two earlier broader attempts were stopped during the unrelated full surrogate/acquisition tuning grid after 112 and 113 passing tests respectively. The final successful run explicitly deselects that grid; it is not a claim that the full repository suite passed.
- `git diff --check` passed. Mock evaluators and temporary test outputs were used; no production ASTRA runs or remote GitHub workflow queries were needed.

## Scope and Limitations
- Nominal beam physics, configured thresholds, objective units, field maps, source distributions, and archived simulation/publication outputs are preserved.
- Version 2 reproducibility is validated on CPU with stochastic proposal stubs and production fallback logic. Exact numerical continuation assumes a compatible numerical environment and deterministic evaluation/proposal behavior. CUDA was unavailable in this environment, so its conditional test was skipped.
- Version 1 migration assumes fixed-size completed batches and infers Sobol consumption for the old low-data branch. Original scalar weights and planned iteration targets must be supplied. Missing historical acquisition fallback draws, Python/CUDA RNG states, and original device prevent a guarantee of exact legacy continuation.
- Resume covers completed checkpoint boundaries. Stream journal reconciliation, in-flight batch recovery, and automatic incomplete-benchmark recovery remain Task 03.
- `docs/05_refactor_tasks/` is ignored by the existing `.gitignore`; local task-status edits do not appear in the ordinary commit file list.

## Status
Completed.
