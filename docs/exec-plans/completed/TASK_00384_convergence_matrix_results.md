# Task Completion Summary: Task 00384

## Summary
Ran and analyzed step 2 of the emittance-convergence follow-up: the grid × particle convergence matrix frozen in Task 00383. All 165 attempts are valid, and the reproduction gate passed. No half-step point is 1 %-adequate. The half → quarter step change, a median of 3–3.5 % lower in both emittances at 40k and at 640k particles, is the largest remaining effect. The manuscript and supplement are unchanged, as the author instructed.

## Key Changes
- **Physical run:** `scripts/evaluate_convergence_matrix.py run` at commit `2d1a5d5`.
  - Ran from 2026-11-12 18:43 to 2026-11-13 11:39 KST, using 360 CPU-h on 22 workers.
  - Outputs are under `results/convergence_matrix/` (untracked, 47 GB): journal SHA-256 `4ffd5b59…2dd7`, plus the completion record.
- **Gate:** all 15 `quarter_g64_n40k` reruns reproduced the round 6 combined-fine records (rtol 1e-9, atol 1e-12).
- **Predeclared analysis:** `scripts/analyze_convergence_matrix.py`, unchanged since the freeze. It wrote the following to `docs/paper/revisions/convergence_followup/`:
  - `rm_changes.csv`, `rm_refinements.csv` and `rm_adequacy.csv`;
  - `rm_particle_extrapolation.csv` and `rm_rank_agreement.csv`;
  - `rm_analysis_receipt.json`.
- **`convergence_followup/README.md`:** step 2 results and reading, under the interpretation rules fixed at the freeze.

## Results (15 settings, descriptive)
- **Primary endpoint:** no adequate point.
  - The best point is `half_g64_n160k`, where 11 of 15 settings stay within 1 % for 160k → 640k; the rule needs 12.
  - `half_g64_n640k` is terminal, and its step check was not met (0 of 15 within 1 %).
- **Step, half → quarter at 64 cells:**
  - median ε_x / ε_y change: −2.9 / −3.6 % at 40k and −3.5 / −3.5 % at 640k;
  - 29 of 30 settings × levels lower both emittances.
- **Particles:**
  - 40k → 160k: median ε_y −1.0 to −1.2 %.
  - 160k → 640k: median at most 0.1 %, with 60–73 % of settings within 1 %.
  - Per-setting changes of up to ±16 %, in both directions.
- **Grid:**
  - 32 → 48: median ε_x −1.6 to −3.6 %.
  - 48 → 64: median −0.5 to −1.0 %.
- **Other quantities:**
  - The median σ_E change is at most 0.6 %.
  - No setting changes feasibility class.
  - Spearman correlation with `half_g64_n640k` is 0.96–1.00 at every level.
- **Conclusion:** within this matrix, absolute emittance convergence is unresolved, and no levels were added after the outcomes were seen. A quarter-step or finer study would need a new protocol and separate authorization.

## Validation Results
- `tests/test_convergence_matrix.py`, `tests/test_rank_stability.py` and the documentation/supplement-map tests passed (see the commit's check run).
- The analysis receipt matches the journal and the frozen specification hash (`cb96300a…`).

## Status
Committed locally. No push performed. The manuscript and supplement are unchanged.
