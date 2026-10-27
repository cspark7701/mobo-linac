# Task Completion Summary: Task 151

## Summary
Implemented TASK_25 from `docs/05_refactor_tasks/`. A single module, `mobo_linac.io.durable`, now performs every durable file operation in the package, and checkpoints load without unpickling arbitrary objects.

## Key Changes
- **`io/durable.py`** provides the following operations:
  - `atomic_write_bytes`, `atomic_write_text`, `atomic_json` and `atomic_csv`, which write through a hidden temporary file, flush, fsync, `os.replace` it over the target and fsync the directory.
  - `atomic_torch_save`.
  - `write_once_json`, using exclusive creation.
  - `append_line_durable`.
  - `truncate_durable`, `ensure_trailing_newline`, `unlink_durable`, `snapshot_file` and `fsync_dir`.
- **Safe loading**: `safe_torch_load` uses `weights_only=True` with an allow-list of only the NumPy array reconstruction globals (needed for the NumPy RNG state). `load_run_checkpoint(..., allow_unsafe_pickle=False)` makes full unpickling an explicit opt-in for trusted archives, and GP artifacts load through the same function.
- **Writers moved onto the module**:
  - Run artifact CSVs and `evaluation_history.json` (which records NaN explicitly).
  - Hypervolume history, journal CSV rebuild, append and tail repair.
  - Provenance snapshots and the workdir manifest.
  - Verification summary and the root "latest" views.
  - Robustness, scalarized suite and benchmark tables.
  - Configuration JSON/YAML/schema exports, environment info, `config_source.json` and LaTeX tables.
- **Removed duplicates**: `io.results._atomic_torch_save`, `io.artifacts.atomic_json` and `astra.workdir.write_once_json`. The workdir module re-exports `write_once_json` from the durable module for compatibility.

## Acceptance Criteria
- [x] `os.replace`, `os.fsync` and `NamedTemporaryFile` appear only in `io/durable.py`, enforced by a source-scan test.
- [x] Fault injection (a crash before rename) leaves the previous complete file and no temporary file, for text, JSON, CSV and torch payloads.
- [x] New checkpoints load with `weights_only=True`; arbitrary pickled objects are rejected unless the caller opts in explicitly.

## Validation Results
New `tests/test_durable_io.py` (7 tests). The affected modules pass: result serialization, checkpoint/resume, workdirs, verification, LaTeX, paper outputs, GP/acquisition, surrogate pipeline, parallel evaluation, scalarized suite, benchmark campaign, config, robustness, candidate evaluator, CLI and docs sync. No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- File formats and filenames are unchanged.
- Archived checkpoints that pickled non-tensor Python objects require `allow_unsafe_pickle=True`.
- Incremental (non-rebuild) artifact and journal writes follow in TASK_26.

## Status
Completed.
