# Task Completion Summary: Task 179

## Summary
Restored `setup.sh`, the shell environment loader removed in `8dd7de9` (TASK_164), as the author requested. It keeps its purpose and exports: source it to activate the conda environment, put `./bin` on `PATH`, and export `PROJECT_ROOT`, `ASTRA_BIN` and `GENERATOR_BIN`. The three defects for which TASK_164 removed it are fixed. `install.sh` remains the installer.

## Key Changes
- **`setup.sh`** (restored and fixed):
  - The usage line names the right file. The original said `source env_setup.sh`.
  - It no longer prepends `src/` to `PYTHONPATH`; the package comes from the editable install. It warns when an older version's `src/` entry is still on `PYTHONPATH`. That entry made pip treat a source checkout as installed during the wheel check of TASK_171.
  - `conda activate` runs only when conda is available and the environment exists. The environment is `linac-opt` by default, or `$MOBO_LINAC_ENV`. A missing environment produces a warning instead of an error.
  - New: it refuses to run unless sourced, does not duplicate `PATH` when sourced again, and warns when `bin/astra` or `bin/generator` is missing or not executable.
- **`tests/test_package_layout.py`**: the assertion that `setup.sh` does not exist is replaced by `test_setup_script_is_sourced_and_leaves_pythonpath_alone`. The new test checks that:
  - the script never assigns `PYTHONPATH`;
  - execution is refused;
  - sourcing twice leaves `PYTHONPATH` unchanged, sets `ASTRA_BIN` and adds `bin/` to `PATH` once.
- **`INSTALL.md`**: describes `source setup.sh` and how to clear a stale `PYTHONPATH`.

## Validation Results
- Executing `bash setup.sh` exits 1 with the "must be sourced" message.
- Sourcing it twice in a shell without `PYTHONPATH`:
  - activates `linac-opt` and adds a single `bin/` entry to `PATH`;
  - `mobo_linac` imports from the checkout through the editable install.
- The missing-environment and stale-`PYTHONPATH` warnings appear as intended.
- `tests/test_package_layout.py` and `tests/test_docs_links.py`: 18 passed. Ruff passes.

## Status
Completed.
