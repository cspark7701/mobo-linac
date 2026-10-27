# Task Completion Summary: Task 174

## Summary
Added `ninja` to the package dependencies. Newer BoTorch releases (0.18) compile a fused C++ extension for the qLogEHVI acquisition when `ninja` and a C++ compiler are available. Without `ninja`, BoTorch warns and uses its slower pure-Python implementation. This was the last warning in the Python 3.12 test run (TASK_173). Optimization results and beam physics are unchanged.

## Key Changes
- `pyproject.toml`: adds `ninja>=1.11` to `[project] dependencies`, because BoTorch needs it at run time, not only in development.
- `INSTALL.md`: lists a C++ compiler (`g++` or `clang++`) as an optional, recommended prerequisite. The extension builds once (about 30 s) and is then cached.
- `requirements-publication.txt` is unchanged. Its pins record the reference environment (BoTorch 0.11.3, which has no fused extension), and its `-e .` line installs `ninja` through the package.

## Validation Results
- Python 3.12 environment (BoTorch 0.18.1, torch 2.14.1+cpu): with `ninja` 1.13.2 installed, `_try_load_fused_kernel()` compiled and loaded the extension with `UserWarning` treated as an error.
- Python 3.12 full unit suite at the current `main` plus this change: 762 passed, 37 skipped, no warnings. Before TASK_173 it reported 22 warnings.
- Python 3.11: `tests/test_gp_and_acquisition.py` and `tests/test_package_layout.py` pass (41 passed, 2 CUDA skips).

## Status
Completed.
