# Task Completion Summary: Task 00387

## Summary
Ran and analyzed step 3a of the emittance-convergence follow-up, frozen in Task 00386. The author authorized it on 2026-11-13 with the instruction: "launch step 3a. If it finishes or stops, commit it and push." All 120 attempts are valid and the gate passed.

The predeclared outcome:
- **Mechanism:** mixed. The space-charge update interval explains roughly a third of the half → quarter change, and the step dependence remains when space charge is recomputed every step.
- **Adequacy:** neither half nor quarter step is 1 %-adequate.
- **Conclusion:** absolute emittance convergence stays unresolved under the frozen rules.

The manuscript and supplement are unchanged.

## Key Changes
- **Physical run:** `scripts/evaluate_convergence_step_test.py run` at commit `690aff8`.
  - Ran from 2026-11-13 17:07 to 2026-11-14 05:35 KST, using 254 CPU-h on 22 workers.
  - Outputs are under `results/convergence_step_test/` (untracked, 35 GB): journal SHA-256 `caf4b91a…96c2`, plus the completion record.
- **Gate:** all 15 `half_mc10` reruns reproduced step 2's `half_g64_n160k` (rtol 1e-9, atol 1e-12).
- **Predeclared analysis:** `scripts/analyze_convergence_step_test.py`, unchanged since the freeze. It wrote the following to `docs/paper/revisions/convergence_followup/`:
  - `rq_changes.csv`, `rq_pairs.csv` and `rq_adequacy.csv`;
  - `rq_mechanism.csv`, `rq_mechanism_by_setting.csv` and `rq_order.csv`;
  - `rq_noise_band.csv`, `rq_rank_agreement.csv` and `rq_cost.csv`;
  - `rq_analysis_receipt.json`.
- **`convergence_followup/README.md`:** step 3a results and reading, and the file list.

## Results (15 settings, 64 cells, 160k; descriptive)
- **Paired median changes, ε_x / ε_y:**

  | Pair | Change | Within 1 % (noise-aware) |
  |---|---|---|
  | half → quarter | −2.7 / −3.1 % | 0 % (13 %) |
  | quarter → eighth | −0.9 / −1.1 % | 20 % (33 %) |
  | half, Max_count 10 → 1 | −0.7 / −1.7 % | both signs across settings |
  | half → quarter at Max_count 1 | −3.1 / −3.4 % | — |
- **Mechanism:** median R is 0.32 / 0.42, which is mixed. The per-setting R ranges from −7.9 to +8.4.
- **Order:** about 1.5 from the medians (1.6–1.7 per setting). The Richardson remainder is about 1.4–1.8 % at quarter step and 0.5–0.6 % at eighth step.
- **Noise band** (twice the replicate SD): median 0.5–0.6 %, up to 11–13 %.
- **Ranking:** Spearman correlation with eighth is 0.99–1.00 for the quarter levels and 0.94–0.97 for the half levels.
- **Feasibility and σ_E:** no setting changes feasibility class, and the median σ_E change is at most 0.6 %.
- **Cost per run:** eighth 3.9 h, quarter 2.1 h and half about 1.2 h. `Max_count=1` costs about 1.9×.

## Validation Results
- The analysis receipt matches the journal and the frozen specification (`58ef9214…`).
- Every record is valid and every replicate is valid.
- The convergence-follow-up, documentation-link, documentation-sync and supplement-map tests were rerun before the commit.

## Status
Committed and pushed to `origin/main` per the author's instruction. The manuscript and supplement are unchanged.
