# Task Completion Summary: Task 00383

## Summary
Step 2 of the emittance-convergence follow-up, authorized by the author on 2026-11-12: froze a grid × particle convergence matrix on 15 of the round 6 settings, with its runner and predeclared analysis. This commit is the freeze. The physical run starts after it, and its results will be recorded in a later task. The manuscript and supplement are unchanged.

## Key Changes
- **Protocol:** `docs/paper/revisions/convergence_followup/rm_protocol.md`.
  - 11 levels per setting:
    - half step at grids 32/48/64 × 40k/160k/640k particles;
    - a quarter-step 64-cell 40k gate;
    - a quarter-step 64-cell 640k step check.
  - 165 attempts in total.
  - The primary endpoint is the 1 %-adequate half-step points: every refinement available from the point changes both emittances by at most 1 % for at least 12 of 15 settings.
- **Frozen inputs.**
  - `rm_specification.json`: levels, tolerances, seed, workers, and the hashes of the template, sources and round 6 inputs.
  - `rm_settings.csv`: 15 settings, one per method × feasibility × boundary cell plus one extra per method, selected with seed 20261112 and no refinement outcome.
- **Sources.**
  - The round 6 40k file is reused byte for byte.
  - 160k and 640k were generated with the identical deck, changing only the particle count and filename.
- **`scripts/evaluate_convergence_matrix.py`** (`prepare` and `run`). The run:
  - refuses to start unless the freeze is committed and the template hashes match;
  - runs the gate first, which must reproduce the round 6 combined-fine records (rtol 1e-9);
  - keeps an append-only checksummed journal, a pending list and a completion record.
- **`scripts/analyze_convergence_matrix.py`:** the predeclared analysis.
  - Changes per refinement, adequacy, round 6 diagnostic tolerances and feasibility changes.
  - Particle extrapolation, made only for monotone settings.
  - Rank agreement with the 64-cell 640k level.
- **`tests/test_convergence_matrix.py`** (9 tests): levels and the gate against round 6, deterministic selection, task ordering, the gate's tolerance, a mock prepare-run-resume-analyze cycle with tamper and interruption checks, the freeze requirement, the adequacy rule on synthetic grid/step/particle-limited data, invalid-run handling, and geometric extrapolation.
- The superseded particle-only draft now points to this protocol.

## Pre-freeze checks
- A 640k source and a 2 cm ASTRA run on the 64-cell grid confirmed that the binary accepts 640,000 particles, using 71 MB. No physics output was used.
- Over the same 2 cm, 640k cost about 2.7× per step relative to 40k. This bounds the runtime estimate at roughly 10–25 h on 22 workers.

## Validation Results
- New and related tests: 38 passed (matrix, rank stability, round 6, documentation links, supplement map).
- `tests/test_production_scripts.py` and `tests/test_cli.py`: 65 passed.
- `ruff check src scripts tests`: passed.
- Full suite not rerun; `mobo_linac` is unchanged.

## Status
Frozen and committed locally. The physical run is launched after this commit. No push performed.
