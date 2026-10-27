# Task Completion Summary: Task 175

## Summary
Raised the NumPy pin in `requirements-publication.txt` from 1.26.4 to 2.4.6. While checking the change with a fresh install, I found that the publication pin set had not been installable at all:
- The pinned distgen revision (`d856bc1`) requires `numpy>=2`, so `numpy==1.26.4` could not be installed alongside it.
- `botorch==0.11.3` requires `numpy<2.0`, so raising NumPy alone is also unresolvable (pip `ResolutionImpossible`).

BoTorch and GPyTorch were therefore raised to the versions of the `linac-opt` environment, in which this repository's tests and real-ASTRA runs have been executed. Physics and the configuration are unchanged.

## Key Changes
- `requirements-publication.txt`: `numpy==2.4.6`, `botorch==0.17.2` (requires `torch>=2.2`, so `torch==2.5.0` is kept), `gpytorch==1.15.2` (required by BoTorch 0.17.2).
- `docs/environment/package_versions.txt`: the same three versions, so the pins still match the recorded environment (`tests/test_package_layout.py`).
- `REPRODUCIBILITY.md`: the version list, with the reason for each change.

## Validation Results
- Fresh Python 3.11.10 venv, `pip install -r requirements-publication.txt` (CPU torch wheel):
  - resolved numpy 2.4.6, botorch 0.17.2, gpytorch 1.15.2, linear_operator 0.6.1, torch 2.5.0+cpu, scipy 1.17.1, pandas 3.0.3, matplotlib 3.10.9, distgen 2.3.2 and lume-astra 0.6.1 at `0af6c84`;
  - `pip check`: no broken requirements.
- Unit suite in that environment: 750 passed, 49 skipped, 0 failed.
  - The 12 skips beyond CI's 37 are tests that need `jsonschema` or `nbclient`, which are not installed there (they are not runtime dependencies).
- `tests/test_package_layout.py`, `tests/test_docs_links.py` and `scripts/verify_docs_sync.py` pass.

## Notes
`docs/environment/package_versions.txt` still lists pandas 3.0.3 and matplotlib 3.10.9. The `linac-opt` environment currently has pandas 3.0.5 and matplotlib 3.11.1; those pins were left unchanged because they resolve and pass.

## Status
Completed.
