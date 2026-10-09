# Task Completion Summary: Task 157

## Summary
Implemented TASK_31 from `docs/05_refactor_tasks/`. ASTRA inputs and the executable are now configuration data, executables are resolved portably without modifying the environment, and attempt execution is split into explicit stages that return a record referencing the manifest.

## Key Changes
- **`simulation:` configuration section** (`SimulationConfig`): `template_dir`, `input_template`, `static_files` and `executable`.
  - `load_config` resolves relative paths against the configuration file and stores them as absolute paths.
  - Both YAML configurations declare the current lattice (`..`, `astra.in`, the four field/distribution files, `../bin/astra`).
  - `execution.template_dir` (added in TASK_29) migrates to `simulation.template_dir`.
  - When an archived checkpoint configuration lacks the section, resume takes code inputs (not scientific settings) from the default configuration.
- **Executable resolution**: `resolve_executable_path` (read-only) tries the configured path, then `$ASTRA_BIN`, then `PATH`, and raises a clear `FileNotFoundError`.
  - The author-specific candidate paths, the `parents[3]` project-root assumption and the silent invalid-path fallback were removed.
  - The executable is passed to lume-astra as `command=`, so `os.environ` is never written.
  - The `distgen` compatibility patch is an isolated, documented adapter.
- **Template directory**: `resolve_template_dir` requires `simulation.template_dir` and never falls back to the working directory.
- **Attempt stages**: `run_astra_eval` is now `prepare_attempt` (validation, executable resolution before reservation, attempt record), `apply_settings`, `execute`, `capture_provenance` and `build_manifest`, operating on an `_Attempt` record.
  - Only a `MoboConfig` is accepted; worker tasks convert the serialized configuration once per task.
  - Durations use `time.monotonic()`.
  - The returned record references `manifest_path` (plus status, measurements and timestamps) instead of embedding the manifest.
- **Generic infrastructure**:
  - The workdir manager has no hard-coded lattice files; static files come from configuration.
  - `apply_parameters_to_astra` takes only `MoboConfig`, so dictionary duck typing is gone.
  - `template_in` plumbing was removed from the evaluators, verifier and CLI.
- **Robustness and mock**: robustness evidence is read from the attempt manifest file, and the mock evaluator no longer reports a manifest path it never writes.
- **Docs**: README and AGENTS describe configuration-driven executable and template resolution.

## Acceptance Criteria
- [x] No user-specific paths, `parents[N]` repository assumptions or `os.environ[...]` writes remain in the ASTRA package (source-scan test).
- [x] Missing executables fail before any attempt directory is reserved (tested).
- [x] Importing and running mock campaigns leaves `os.environ` unchanged (existing subprocess test, plus a real-attempt test).
- [x] A second synthetic lattice (different template file, static files and executable) runs through the same code with only configuration changes (tested).

## Validation Results
Relevant modules pass:
- workdirs (19), parameter mapping, parser
- candidate evaluator, verification, robustness, mock evaluator
- checkpoint/resume, CLI, package layout, benchmark campaign
- scalarized BO and suite, visualizations, configuration boundaries
- config, comparison, docs sync

No real ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- Namelist values, field maps and physics are unchanged.
- The legacy single-directory cleanup branch is kept because a test confirms it preserves evidence from archived layouts.
- A wheel-install smoke test belongs to the CI and packaging tasks (TASK_37/TASK_38).

## Status
Completed.
