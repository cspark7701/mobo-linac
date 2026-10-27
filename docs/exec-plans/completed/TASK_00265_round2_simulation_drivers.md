# Task Completion Summary: Task 00265

## Summary
Add the drivers for the round2 optional simulations authorized by the author on 2026-10-27: the MOGA-derived reference setting, the jitter assessments, three TDR-constrained campaigns and the budget-matched Sobol arm (consolidated tasks C2-01, C2-03, C2-07 and C2-08).

## Key Changes
- `configs/revision_tdr_200MeV.yaml`: the publication configuration with only the description and the constraints changed to the KLS TDR optimization requirements.
  - The TDR has no upper energy bound, so a 1 GeV ceiling is used.
  - `min_transmission: 0.99995` requires zero loss of the 9,999 counted particles, matching the TDR's strict T > 0.9999.
- `scripts/run_revision_reference_settings.py`:
  - re-evaluates the MOGA-derived nominal setting once, after checking that its deck matches `beam_tracking/astra.in`;
  - applies the archived lattice-jitter protocol (50 trials, common seed 42) to that setting under the production profile;
  - applies the same protocol to the two TDR-passing primary observations under the TDR profile.
- `scripts/run_revision_round2_simulations.sh`: runs the reference stage, then `run-benchmark` for constraint-aware qLogNEHVI under the TDR configuration (seeds 42–44, 160 evaluations), then the Sobol arm. Each stage records provenance and refuses to overwrite outputs.
- The Sobol arm is a 160-point initial design with zero acquisition iterations for each of seeds 42–51. Its first 16 points are the shared initial design of the matching primary seed.
- `tests/test_revision_reference_settings.py`: checks the configuration differences and the nominal vector, and rehearses the reference stage with the mock evaluator.

## Validation Results
- The TDR configuration loads and validates; a diff against the publication configuration shows only the description and constraint changes.
- Dry runs of the TDR benchmark and the Sobol campaign show the planned budgets.
- A mock Sobol campaign for seed 42 reproduces the 16 shared initial points exactly in `train_X.csv`. A direct 160-point Sobol draw matches seeds 42, 47 and 51 to the CSV precision.
- `ruff check` passed, `bash -n` passed and 3 new tests passed.

## Status
Completed and committed locally before launching the runs. No push performed.
