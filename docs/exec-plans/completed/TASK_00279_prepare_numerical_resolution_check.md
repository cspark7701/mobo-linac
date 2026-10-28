# Task Completion Summary: Task 00279

## Summary
Prepare consolidated round2 task C2-12, the numerical-resolution check of the reported settings, which the author authorized on 2026-10-28 to run when the Sobol arm (C2-14) finishes. This task adds the run driver, the analysis script and their tests; the runs themselves follow.

## Key Changes
- **Source reconstruction.** The production source `pal_photo2.ini` was reproduced with ASTRA's `generator`:
  - quasi-random mode, 2D Gaussian transverse distribution with σ = 1.118 mm cut at 1.0 mm;
  - 2.553 ps Gaussian emission time cut at 4σ, reference clock −0.6383 ps;
  - isotropic 0.6 eV emission, 1 nC, probe particles.
  - The time, radius and momentum marginals agree with the file to print precision; only the pairing of coordinates differs.
- **Driver (`scripts/evaluate_revision_convergence.py`).**
  - Ten settings: the MOGA-derived nominal, TDR candidates A and B, the closest TDR-campaign observation (C2-13), and the six selected representatives.
  - 15 levels per setting: the production level, a regenerated quasi-random 10k source, five pseudo-random 10k sources, 20k and 40k particles, 48 and 64 grid cells per dimension, H/2 and H/4, and the medium (20k, 48, H/2) and fine (40k, 64, H/4) combinations.
  - Levels are applied as per-run namelist overrides of the production template, through the production evaluator; no production output is modified.
  - The fine runs are submitted first, and the per-run timeout is raised to 24 h.
  - The generator's random mode is clock-seeded, so each source file's SHA-256 is recorded, and the driver refuses to run if the pseudo-random sources are not distinct.
- **Analysis (`scripts/analyze_revision_convergence.py`).**
  - Per setting and quantity: the change to the fine and medium levels, the largest single-factor change and the spread over regenerated sources.
  - Production, NAPAC and TDR membership and signed TDR margins at each level, with changes flagged.
  - A check of the production-level rerun against the archived value.
- **Simulation driver:** new stage `convergence` in `scripts/run_revision_round2_simulations.sh`, with 16 workers by default and not part of `all`. The file was replaced by rename because the Sobol stage was running from it.
- **Task list:** C2-12 is marked authorized, with ten settings, 150 runs and an estimated 4–8 h wall clock.

## Validation Results
- A mock-evaluator rehearsal produced all 135 tasks of the nine-setting version in the expected order, with distinct source files.
- A real ASTRA plumbing test of the fine level over the first 0.3 m confirmed that the source, step and grid overrides reach `astra.in`. It ran in scratch space only.
- `tests/test_revision_convergence.py` (4 tests) and `tests/test_revision_reference_settings.py` passed; `ruff check` passed; `bash -n` passed for the driver.

## Status
Completed and committed locally. No push performed. The convergence stage starts automatically when the Sobol stage finishes.
