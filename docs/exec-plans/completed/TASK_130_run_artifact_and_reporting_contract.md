# Task Completion Summary: Task 130

## Summary
Implemented Task 06 from `docs/05_refactor_tasks/`: unified iteration and final run exports, recorded explicit scientific reporting conventions, separated measured campaign wall time from worker-runtime sums, and published checksum-backed completion markers only after required artifacts succeed.

## Key Changes
- **`src/mobo_linac/io/artifacts.py`**: Added `RunArtifactWriter` for candidate history, evaluation tables, training matrices, objective tables, diagnostic/failure tables, Pareto sets, hypervolume history, normalized metrics, and reporting metadata. All CSVs have ordinary named headers; empty writes clear previous rows. `pareto.csv` consistently aliases all-valid `pareto_all.csv`; `pareto_feasible.csv` is explicitly feasible-only. Extra CSV columns preserve scalarized case labels without changing typed JSON evaluation payloads.
- **Completion contract**: Atomic `run_complete.json` records evaluation count, final measured elapsed time, and SHA-256 artifact checksums. Writes invalidate the preceding marker. Campaign completion requires configuration, checkpoint, datasets, and requested figures. Validation detects missing/changed files. Benchmark and scalarized aggregation reject incomplete or changed artifacts.
- **Reporting metadata and compatibility**: Recorded schema version, ordered objective names/units/signs/scales, raw and normalized model-space references, constraint profile, design columns, hypervolume spaces, reference origin, and timing scope. Comparison requires complete matching conventions, without invented defaults or a micrometre-scale absolute tolerance. Raw iteration hypervolume and dimensionless per-evaluation hypervolume use the same recorded reference.
- **Campaigns, checkpoints, and timing**: Added an optional explicit model-space reporting reference while retaining ordinary initial-design reference selection. Resume validates the saved reference and reporting metadata. Monotonic elapsed time and logical evaluation completion observations are saved in checkpoints; worker durations remain a separate sum. Legacy/aggregate unknown wall time remains unknown. Export and figure failures cannot publish a final completed marker.
- **Benchmark and scalarized integration**: Benchmarks pass the existing configured signed/scaled reference to the campaign and consume the resulting metrics rather than overwriting them with a separate convention. Alternate record-returning runners receive explicit metadata and artifact markers. New scalarized suites reuse the first case's reporting reference across subsequent cases. Aggregation verifies conventions before writing outputs, uses the shared writer, and retains case labels. Removed the hard-coded reference from generated table captions.
- **Documentation**: README and simulation guide describe filenames, metadata, compatibility, timing, and completion. AGENTS.md now distinguishes ordinary campaign references from benchmark references and corrects the benchmark emittance reference units to micrometre-radian. Local ignored task/index documents record completion.

## Acceptance Criteria
- [x] Pareto semantics and named CSV headers are consistent through iteration and finalization.
- [x] Compared runs share an explicit recorded reference, scales, objective order/units/signs, and constraint profile, or comparison is rejected.
- [x] A deterministic parallel-batch timing fixture records six seconds elapsed versus twenty seconds summed worker runtime.
- [x] Empty and all-invalid observations retain configured dataset headers and clear stale rows.
- [x] Failed CSV/figure exports do not publish completion; changed persisted artifacts invalidate marker verification.

## Validation Results
Used `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python`, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1`, and an explicit source-tree `PYTHONPATH` for subprocesses.

- Final broader regression command: `PYTHONPATH=/home/cspark/Work/projects/mobo-linac/src python -m pytest tests/test_result_serialization.py tests/test_reporting_metrics.py tests/test_hypervolume.py tests/test_checkpoint_resume.py tests/test_scalarized_suite.py tests/test_benchmark.py tests/test_benchmark_campaign.py tests/test_cli.py tests/test_objectives.py tests/test_evaluation_result.py tests/test_config.py tests/test_paper_outputs.py -q --tb=short` — **239 passed, 1 skipped**, 102.48 seconds.
- Artifact/reporting/aggregation-focused check — **152 passed, 1 skipped**, 33.34 seconds.
- Reference-equivalence focused check — **6 passed**, 1.19 seconds.
- Publication subprocess check with source-tree imports — **2 passed**, 10.07 seconds. An earlier broader run loaded a stale installed package in these subprocesses; explicit `PYTHONPATH` resolved that environment mismatch without changing archived data.
- CUDA continuation was skipped because CUDA is unavailable. Campaign evaluations were mocked, timing evidence was deterministic, and publication figures/tables were written into temporary directories. Existing publication datasets were read only.
- `git diff --check` passed. No production ASTRA run, git push, or remote workflow query was performed. This is affected regression coverage, not a claim that the entire repository suite passed.

## Scope and Limitations
- Beam physics, configured engineering scales and thresholds, objective units/signs, seeds, acquisition-reference adaptation, and archived outputs are preserved. New reporting consistency does not rewrite historical hypervolumes.
- The explicit scientific decision retains ordinary campaigns' initial-observation reference, benchmarks' configured reference, and the standalone normalized helper's legacy default. New scalarized suites share their first case's actual reference rather than choosing a new pooled reference. Different recorded conventions cannot be silently aggregated.
- Metadata and verified completion are required by new aggregation paths. Legacy artifacts lacking this evidence remain readable by existing publication readers but require an explicitly established reporting convention before new aggregation; they are not silently migrated.
- Wall time covers observed active sessions and excludes downtime. Uncheckpointed time lost on interruption cannot be reconstructed. Legacy checkpoints without timing evidence identify their observed resume session. Aggregate suite wall time is unknown rather than a sum of worker or case runtimes.
- Metrics history records elapsed time at its export snapshot; the final marker records time through finalization. Completion markers certify their listed artifacts, and hashes are checked before completed-run consumption. Optimization recovery still uses durable proposals, checkpoints, and the JSONL journal.
- Typed candidate-history JSON and journal formats are unchanged. The low-level result-saving compatibility helper delegates exports but does not certify campaign completion by itself.
- `docs/05_refactor_tasks/` remains ignored by `.gitignore`; local task-status edits are absent from the ordinary commit file list.

## Status
Completed.
