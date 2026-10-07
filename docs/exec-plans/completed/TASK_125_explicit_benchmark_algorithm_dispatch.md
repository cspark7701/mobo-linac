# Task Completion Summary: Task 125

## Summary
Implemented Task 01 from `docs/05_refactor_tasks/`: made benchmark algorithm dispatch explicit, fixed reporting argument binding and worker forwarding, enforced exact evaluation budgets, and replaced CSV-existence completion checks with persisted experiment state and validated evaluation counts.

## Key Changes
- **`src/mobo_linac/benchmark_algorithms.py`**: Added a simulator-independent registry defining optimization mode, acquisition, constraint policy, and executor availability. Four implemented algorithms are supported; NSGA-II, Sobol-only, and unknown executors are rejected before output creation.
- **`src/mobo_linac/config.py`**: Bound benchmark defaults and validation to the registry. Added validation for non-empty unique algorithms/seeds, positive initial count, and valid normalized physical reporting reference values.
- **`src/mobo_linac/campaigns/benchmark.py`**: Passed explicit runner settings and keyword reporting arguments; honored configured constraint profiles and reporting references; persisted atomic benchmark state with experiment signature, evaluation kind, budgets, and counts. Completion requires unique candidate IDs and full evaluation/metric histories. Analysis discovers custom algorithm/seed pairs from the saved manifest and rejects mixed reporting settings or mock/ASTRA kinds.
- **`src/mobo_linac/campaigns/runner.py`**: Added optional `total_eval_budget` support. Proposal paths use a smaller final batch where necessary; default non-benchmark execution remains unchanged.
- **`src/mobo_linac/cli/commands/benchmark.py`**: Forwarded `--num-workers` and clarified supported algorithms.
- **Tests**: Added recording-runner dispatch checks, CLI propagation/rejection checks, exact-budget and seed-pairing mock campaigns, partial-batch coverage in every BO proposal path, custom reporting/analysis checks, interrupted-state preservation, missing-artifact rejection, and mock/production completion isolation. Updated older runnable benchmark fixtures to use implemented algorithms; external Sobol data used in reporting/plot fixtures remain supported.
- **Documentation**: Updated README and benchmark protocol with implemented algorithms, budget semantics, reporting conventions, completion validation, and interruption limitations. Updated the ignored local Task 01 document and task index to reflect completion.

## Acceptance Criteria
- [x] Recording runner confirms optimization mode, acquisition, constraints, and worker count for all four advertised runnable algorithms.
- [x] Tiny mock campaigns reach evaluation, checkpoint, metrics, aggregation, and figure exports.
- [x] Algorithms receive identical seed-paired initial designs and exact requested budgets, including failed evaluations and final partial batches.
- [x] Candidate-history existence alone cannot classify an interrupted run as completed.
- [x] Completed compatible runs are skipped; incomplete/incompatible outputs are preserved and rejected for automatic reuse.
- [x] Production runs cannot silently reuse completed mock benchmarks.
- [x] Existing configuration, CLI, checkpoint resume, and scalarized execution regressions pass.

## Validation Results
Used the existing `linac-opt` Python environment at `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python`.

- Broader affected regression run: `python -m pytest tests/test_benchmark_campaign.py tests/test_benchmark.py tests/test_cli.py tests/test_config.py tests/test_checkpoint_resume.py tests/test_scalarized_bo.py -q` — **64 passed**, 321.26 seconds.
- Final benchmark/configuration regression run after completion/provenance guards: `python -m pytest tests/test_benchmark_campaign.py tests/test_benchmark.py tests/test_config.py -q` — **53 passed**, 8.13 seconds.
- Python syntax compilation succeeded for changed source modules. Existing invalid-escape warnings in configuration documentation strings were observed and are outside this task.
- `git diff --check` passed; repository status contains only the intended source, test, documentation, and completion-summary changes.
- Mock evaluators and temporary test outputs were used; no production ASTRA campaigns or remote GitHub workflow queries were needed.

## Scope and Limitations
- Nominal beam physics, physical thresholds, objective units, field maps, source distributions, and archived production/publication outputs were preserved.
- Benchmark normalized hypervolume explicitly uses the existing `BenchmarkConfig.reporting_ref_point` (default physical normalized `[1.5, 1.5, 1.5]`) and engineering scales `[1e-6, 1e-6, 1e6]`. Runner acquisition references and existing reporting helper defaults are unchanged.
- Budgets count candidate evaluations, including failures; ASTRA retry attempts do not consume separate candidate budget entries.
- NSGA-II and Sobol-only benchmark implementations remain future work. Scalarized benchmarking uses the existing equal-weight runner default, rather than launching a weight sweep.
- Automatic recovery of interrupted or legacy unmarked benchmark directories is deferred to Tasks 02–03. This task preserves such artifacts and requires a new output directory rather than overwriting or silently skipping them.
- `docs/05_refactor_tasks/` is ignored by the existing `.gitignore`; its local task-status edits do not appear in the ordinary commit file list.

## Status
Completed.
