# Task Completion Summary: Task 162

## Summary
Implemented TASK_36 from `docs/05_refactor_tasks/`. One factory constructs every fresh campaign runner, the scripts are thin wrappers of CLI subcommands, comparison and manuscript logic live in a package `reporting` module, and the notebooks are configuration-driven clients that execute against mock runs.

## Key Changes
- **Runner factory**: `campaigns.runner.campaign_runner(config, options, ...)` constructs every fresh runner, from the CLI run modes, the scalarized suite, validation and benchmarks. Only resume, which restores a checkpointed runner, constructs one directly.
- **Acquisition**:
  - `-a/--acquisition` choices come from the `Acquisition` enum, including `qLogNEI`.
  - Scalarized BO now requires `qLogNEI`; the `qLogNEHVI` stand-in was removed.
- **One input option**: `--input` for robustness and verification. `--history-path` and `--pareto-csv` are hidden deprecated aliases that warn.
- **Reporting package** (layer 4):
  - `reporting.comparison`: `run_phase_comparison`, `verify_pareto_candidates`, `load_phase_results`.
  - `reporting.paper`: `generate_paper_artifacts`, `check_manuscript_consistency` and the required-file lists.
  - New subcommands: `mobo-linac compare` and `mobo-linac paper-figures`. `main` returns the subcommand exit code, and `python -m mobo_linac.cli` exits with it.
- **Thin scripts**: every `scripts/run_*.py`, `run_comparison_and_verification.py` and `generate_paper_figures.py` is a wrapper of its subcommand with no argparse. The unused `run_campaign_variant` and target-constant imports are gone. The production launcher passes `--input` to robustness.
- **Notebooks**: the five notebooks were regenerated as thin clients (outputs stripped).
  - They are parameterized by environment variables (`MOBO_PHASE{1,2,3}_DIR`, `MOBO_PHASE_DIRS`, `MOBO_ANALYSIS_DIR`, ...).
  - They optionally start campaigns through the CLI.
  - They read recorded runs and configuration, and call package functions only (summaries, plotting, verification table).
  - They contain no objective names, weights, scales, binary paths or stale module imports.

## Acceptance Criteria
- [x] One function constructs runners for all CLI run modes (source test).
- [x] Script wrappers contain no argparse definitions (source test). `scripts/sync_site.py` is a site-maintenance tool, not a campaign wrapper.
- [x] Notebooks contain no hard-coded objective names, weights or scales and have no stored outputs (test). All five execute against mock suite, phase, comparison and verification runs via `nbclient` (`tests/test_notebooks.py`).

## Validation Results
Relevant modules pass:
- notebooks (10), CLI (46), LaTeX reporting, paper outputs (51), comparison
- candidate evaluator, verification, scalarized BO and suite, benchmark campaign
- production launcher, config, package layout, docs sync

No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
- Subcommand names and documented flags are unchanged; deprecated input aliases warn.
- Notebook execution needs `nbclient`, `nbformat` and `ipykernel`; the test skips if they are absent.

## Status
Completed.
