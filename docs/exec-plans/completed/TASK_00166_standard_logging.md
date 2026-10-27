# Task Completion Summary: Task 161

## Summary
Implemented TASK_35 from `docs/05_refactor_tasks/`. The custom logger is replaced by standard-library logging, library code no longer prints, every campaign writes a `run.log`, and `--quiet` silences every workflow.

## Key Changes
- **`utils/logger.py`**: built on `logging`.
  - `get_logger(name)` returns a standard `logging.Logger` under `mobo_linac`, configured with defaults on first use.
  - `configure_logging(level, log_file, quiet, verbose, debug)`: one console handler (errors to stderr, other records to stdout) plus an optional file handler formatted as `time [LEVEL] [module] message`.
  - `--verbose` now means INFO with timestamps (previously the same as `--debug`), and `--debug` means DEBUG.
  - `run_log(run_dir)` adds a per-run file handler.
  - `MoboLogger`, `LogLevel`, `success()` and `section()` were removed.
- **Per-run log**: every campaign writes `<run_dir>/run.log` (timestamps, levels, module names). It is opened only after resume validation, so a rejected resume creates no directory.
- **No library prints**: the robustness workflow's dry-run plan and summary are logged; CLI status lines (analysis summary, exported figures, verification and benchmark results, schema/docs exports) are logged. `print` remains only for user-requested CLI output (dry-run plans, the validate-config report).
- **Progress lines**: campaign progress lines no longer embed layout newlines.
- **Verbosity flags**: every subcommand (run, resume, benchmark, analyze, robustness, verification, validate-config) accepts `--quiet/--verbose/--debug` through the shared `add_verbosity_args`.
- **Warnings policy**: data-quality conditions callers may assert (truncated journal tail, best-effort legacy resume, implicit run selection) are raised with `warnings.warn`; operational events are logged. Documented in the README.

## Acceptance Criteria
- [x] `print(` appears only in CLI presentation code (source-scan test).
- [x] Every campaign directory contains `run.log` with timestamps, levels and module names (tested).
- [x] `--quiet` suppresses all non-warning output, including the robustness and verification workflows (CLI test).

## Validation Results
Relevant modules pass: logger (9, rewritten for standard logging), CLI (44), config, benchmark, checkpoint/resume, device policy, package layout, robustness, run data, scalarized suite and benchmark campaign. No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- Scientific outputs are unchanged.
- `run.log` is not part of the completion checksum set, because it keeps growing across resumed sessions.

## Status
Completed.
