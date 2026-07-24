# Task 01 Summary: Consolidate the Production Execution Path

## Canonical Entry Points & CLI Integration
- Implemented subcommands in `mobo_linac.cli`:
  - `mobo-linac run-unconstrained --config configs/publication.yaml` (Phase 2 MOBO)
  - `mobo-linac run-constrained --config configs/publication.yaml` (Phase 3 Constrained MOBO)
  - `mobo-linac run-scalarized --config configs/publication.yaml` (Scalarized BO)
  - `mobo-linac run-validation --config configs/publication.yaml` (Validation Campaign)
  - `mobo-linac resume --run-dir results/<run_id>` (Resume from checkpoint)
  - `mobo-linac analyze --run-dir results/<run_id>` (Plotting & diagnostics analysis)
- Created `configs/publication.yaml` as the canonical publication configuration file.

## Script Refactoring & Legacy Migration
- Refactored production scripts in `scripts/`:
  - `scripts/run_mobo.py` -> Thin wrapper invoking `mobo_linac.cli.run_unconstrained`.
  - `scripts/run_constrained_mobo.py` -> Thin wrapper invoking `mobo_linac.cli.run_constrained`.
  - `scripts/run_scalarized.py` -> Thin wrapper invoking `mobo_linac.cli.run_scalarized`.
  - `scripts/run_validation_campaign.py` -> Clean package wrapper without `sys.path` manipulation.
  - `scripts/run_comparison_and_verification.py` -> Clean package wrapper without `sys.path` manipulation.
- Moved superseded root-level legacy files into `legacy/`:
  - `run_astra.py`, `mobo_utils.py`, `file_io.py`, `plot_utils.py`, `utils.py`
  - `get_data.ipynb`, `get_data-postprocessing.ipynb`, `mobo.ipynb`, `scalarized_bo.ipynb`

## Verification & Parity Results
- 0 legacy root imports remaining in `src/`, `scripts/`, or `tests/`.
- 0 `sys.path` manipulations remaining in production scripts.
- Pytest suite executed successfully: 42/42 unit tests passed.
- CLI smoke tests for all canonical subcommands verified.

## Acceptance Criteria Status
- [x] No publication entry point imports legacy root modules.
- [x] No production script modifies `sys.path`.
- [x] Every ASTRA evaluation uses an isolated directory.
- [x] CLI and notebook calls use the same package implementation.
- [x] Resume does not duplicate completed evaluations.
- [x] Existing unit and integration tests pass.
