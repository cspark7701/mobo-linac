# Task Completion Summary: Task 00386

## Summary
Froze step 3a of the emittance-convergence follow-up, as the author instructed on 2026-11-13: "use the recommended options, run the probe, then freeze". The options are rotated quasi-random replicates, all 15 settings as the primary sample, and the eighth step kept. The study separates the space-charge update interval from the integration step at 64 cells and 160k particles. The pre-freeze probe was run. The 120-attempt run itself has not been launched and needs separate authorization. The manuscript and supplement are unchanged.

## Key Changes
- **`rq_protocol.md`** (renamed from `rq_protocol_draft.md`): status FROZEN, the author's decisions, the probe results, a revised rotation check, and an updated budget. The open-decisions section is removed.
- **`rq_specification.json`** (new) records:
  - 8 levels and the order after the gate;
  - the gate: `half_mc10` against step 2's `half_g64_n160k`, rtol 1e-9;
  - rotation angles 40°/80°/160° with their invariants;
  - feasibility strata fixed from step 2's `half_g64_n640k` (9 feasible);
  - every threshold and the bootstrap seed 20261113;
  - template hashes. `rm_settings.csv` is reused, checked by hash.
- **`scripts/evaluate_convergence_step_test.py`** (new), with `prepare` and `run`:
  - checks the step 2 completion record and template hashes;
  - writes the rotated sources;
  - runs the gate first, then the levels longest first;
  - keeps an append-only journal with pending and completion records.
- **`scripts/analyze_convergence_step_test.py`** (new, predeclared analysis):
  - paired changes and the sample-noise band;
  - bootstrap intervals of the median;
  - the mechanism ratio and its class;
  - the observed order with Richardson remainders;
  - adequacy of the half and quarter steps;
  - strata, rank agreement and cost.
- **`tests/test_convergence_step_test.py`** (new, 7 tests):
  - level construction, and the rotation invariants with tamper detection;
  - a mock prepare → run → resume → tamper → analyze cycle on a mock step 2;
  - gate reproduction;
  - mechanism classes, observed order (1 and 2) and adequacy on synthetic data;
  - the effect of the noise band, and invalid runs counting against adequacy.
- **`convergence_followup/README.md`:** file list and the link to step 3a.

## Pre-freeze probe (2026-11-13, scratch only; no physics output used)
- **Setup:** 3 cm, 64 cells, 160k, using the template's default settings.
  - `Max_count` 10 and 1 at half step, with the 2D solver and with the 3D solver (`z_trans=0.01`);
  - eighth step in 3D.
- **Parsing:** ASTRA's echoed input confirms `MAX_COUNT = 1` and `Z_TRANS = 0.01`.
- **Effect of `Max_count=1`:** it changed the emittances (by 0.005 % in 2D and 0.02 % in 3D) and cost +18 % (2D) and +24 % (3D) CPU, so no `Max_scale=0` fallback is needed.
- **Cost not taken from the probe:** emission control dominates the first 3 cm, and the eighth step ran faster than half there. Eighth-step cost is scaled from step 2.
- **Rotated sources:** the 160k source rotated at 40°, 80° and 160° passes the invariant checks (1e-9).
- **Deck check:** the runner's override path writes `max_count`, `h_max`/`h_min` and the rotated distribution into the namelists.

## Budget
About 220–270 CPU-h, or about 11–15 h on 22 workers, and up to about 35 GB of disk. 695 GB is free.

## Validation Results
- Convergence step-test, matrix, rank-stability, documentation-link, documentation-sync and supplement-map tests: 29 passed.
- `ruff check scripts tests`: passed.
- Full suite not rerun; `mobo_linac` is unchanged.

## Status
Frozen and committed locally. `results/convergence_step_test/` (template and sources, untracked) is prepared. The run is not launched. No push performed.
