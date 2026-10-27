# Task Completion Summary: Task 164

## Summary
Implemented TASK_38 from `docs/05_refactor_tasks/`. The package now has one version source, pinned Git dependencies, a single publication pin list that matches the recorded environment, one installer that never edits `PYTHONPATH`, and a wheel that runs a mock campaign outside the source tree.

## Key Changes
- **Version**: single-sourced in `mobo_linac.__version__` (`pyproject.toml` uses `dynamic = ["version"]`). CI compares against the distribution metadata.
- **Git dependencies**: `distgen` and `lume-astra` are pinned to the commits installed in the reference environment (d856bc1, 0af6c84).
- **Publication environment**:
  - `requirements-publication.txt` is the one exact pin list (torch 2.5.0, botorch 0.11.3, gpytorch 1.12, numpy 1.26.4, scipy 1.17.1, pandas 3.0.3, matplotlib 3.10.9, lume-base 0.5.0, the pinned Git revisions, and the package itself). It matches `docs/environment/package_versions.txt` (test).
  - `environment-lock.yml` only wraps it with Python 3.11.10.
  - The numpy pin replaces the former lume-astra patch, which only removed lume-astra's unpinned numpy requirement. The patch and its install guide were deleted.
- **Installer**: `install.sh` is the only setup script (`--publication`, `--create-env NAME`, `--no-tests`). It never edits `PYTHONPATH` and activates only an environment it created. `setup.sh` (wrong usage name, `PYTHONPATH` prepend, unconditional `conda activate`) was removed.
- **Bundled configurations**: the wheel installs them under `share/mobo-linac/configs`, and the default configuration search covers them. With TASK_31's `simulation:` section, an installed wheel runs mock campaigns, and real campaigns when an executable is configured or on `PATH`.
- **Python floor**: `>=3.10`, aligned with the code, CI matrix, README and INSTALL (from TASK_37).
- **CI wheel smoke job**: runs a full mock campaign from the bundled configuration outside the source tree.
- **Docs**: INSTALL and REPRODUCIBILITY describe the one-command install and the actual recorded versions. The previous list in REPRODUCIBILITY did not match the recorded environment.

## Acceptance Criteria
- [x] `pip install` of the built wheel yields a working `mobo-linac --help` and a mock campaign outside the source tree. Verified locally in a fresh virtual environment: the run completed with `run_complete.json` using the bundled `publication_200MeV.yaml`. CI runs the same smoke test.
- [x] The publication environment is recreated by one command (`./install.sh --create-env NAME --publication`) and its pins match `docs/environment/package_versions.txt` (test).
- [x] The version string exists in one place (test).

## Validation Results
Relevant tests pass: package layout (14), config, docs sync and production launcher. The wheel was built and smoke-tested locally. No push or remote query was performed.

## Scope and Limitations
- The publication pins reproduce the recorded environment. The refactored suite is exercised in the current development environment (botorch 0.17), and CI tests the unpinned ranges.
- The recorded `openpmd-beamphysics=0.0.0` (a development build) cannot be pinned, so that package stays unpinned.
- The reference conda environment also holds an older non-editable `mobo_linac` install in its site-packages. Tests import the source tree through the pytest `pythonpath` setting; running `./install.sh` replaces that copy with the editable install.

## Status
Completed.
