# Task 07 — Python Package Layout and Dependency Metadata

## Summary

Task 07 converted the codebase into a standard installable Python package (`mobo_linac`) using `pyproject.toml` and a clean `src/` layout.

## Accomplishments

1. **Standard `src/` Layout**: Structured package modules under `src/mobo_linac/` (`astra`, `execution`, `models`, `acquisition`, `metrics`, `io`, `plotting`).
2. **Metadata & Pyproject Setup**: Added `pyproject.toml` pinning tested dependencies (`torch`, `botorch`, `gpytorch`, `pandas`, `matplotlib`, `pyyaml`).
3. **CLI Console Entry Points**: Created `mobo-linac` command-line entry point in `src/mobo_linac/cli.py` supporting `mobo-linac run`, `mobo-linac resume`, and `mobo-linac analyze`.
4. **Editable Installation**: Confirmed `pip install -e .` enables clean module imports across scripts, notebooks, and tests without `sys.path` hacks.

## Status

**Completed**. Validated by `tests/test_package_layout.py`.
