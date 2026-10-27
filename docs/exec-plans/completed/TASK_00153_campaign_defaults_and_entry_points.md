# Task Completion Summary: Task 148

## Summary
Implemented TASK_22 from `docs/05_refactor_tasks/`. Campaign defaults now have one source: the configuration. `run-validation` now runs in its own run directory from an installed package. `analyze` exports the figures it reports, and the run scripts are thin wrappers around the CLI.

## Key Changes
- **One default source**: `CampaignSettings` (`campaign:` section: num_initial_samples 16, num_batches 20, batch_size 8, seed 42, acquisition qLogNEHVI) is added to the configuration, schema and the three configuration files. `resolve_campaign_options` fills omitted options from it and takes the worker count from `execution.max_workers`.
- **CLI options**: `--n-iterations`, `--batch-size`, `--num-initial-samples`, `--num-workers`, `--seed` and `--acquisition` default to `None` (meaning the configured default). The robustness and benchmark `--num-workers` options no longer override the configuration with 4. `MoboCampaignRunner` uses the same configured defaults, replacing its hidden 16/6/4/42. The previous defaults (300, 20 or 6 iterations depending on entry point) are gone.
- **One run handler**: `resolve_plan` validates everything before side effects, and `run_campaign_command` serves unconstrained, constrained and scalarized campaigns. Dry runs print the resolved plan.
- **Validation**: `mobo_linac.campaigns.validation.run_validation_campaign` creates `<base>/validation_<timestamp>/`, where it previously used the base directory itself as the run. The installed CLI no longer imports `scripts/`.
- **`analyze`**: reads the run through `read_run_data` and exports hypervolume, Pareto, objective-evolution and constraint figures.
- **Removed**: the unreachable fallback dispatch table in `cli.main`, and the validation script's private plots and unused imports.
- **Scripts**: `run_constrained_mobo.py`, `run_unconstrained_mobo.py`, `run_scalarized_bo.py`, `run_scalarized_suite.py` and `run_validation_campaign.py` call `mobo_linac.cli.main`. `parse_args` uses the CLI parser, so options and defaults are identical; the scripts' differing default configuration files are gone.

## Acceptance Criteria
- [x] `run-validation` from an import path without the repository root creates `results/validation_<timestamp>/` and writes no run artifacts into the base directory (tested in a subprocess).
- [x] CLI and scripts resolve identical plans (parity test).
- [x] Omitting `--num-workers` uses `execution.max_workers`.

## Validation Results
Relevant modules pass: CLI (43), scalarized BO, scalarized suite, config, production launcher, checkpoint/resume, benchmark campaign, docs sync and candidate evaluator. No ASTRA campaign, push or remote query was performed.

## Scope and Limitations
The default iteration count of entry points that previously used 300 is now the configured 20. Production launches pass explicit values, so published settings are unchanged. Scalarized campaigns default to qLogNEI explicitly.

## Status
Completed.
