# Emittance-convergence follow-up (after round 6)

This folder holds a follow-up to round 6, made at the author's request on 2026-11-12. It is not part of the round 6 package or the supplement. On 2026-11-20 the author asked for steps 1–3a to be added to the manuscript; they appear in `main.tex` as Sec. V D (`sec:convergence_followup`, Table `tab:convergence_followup`) and in the appendix paragraph "Follow-up convergence study". The supplement is unchanged.

| File | Content |
|---|---|
| `rs_rank_stability.csv`, `rs_rank_summary.json` | Step 1: rank stability of the round 6 re-tracked objectives (from `scripts/analyze_rank_stability.py`) |
| `rm_protocol.md`, `rm_specification.json`, `rm_settings.csv` | Step 2: grid × particle matrix protocol and its frozen inputs (added at the freeze) |
| `rm_changes.csv`, `rm_refinements.csv`, `rm_adequacy.csv`, `rm_particle_extrapolation.csv`, `rm_rank_agreement.csv`, `rm_analysis_receipt.json` | Step 2 results (from `scripts/analyze_convergence_matrix.py`) |
| `rm_sensitivity_by_setting.csv`, `rm_sensitivity_correlations.csv`, `rm_sensitivity_strata.csv`, `rm_sensitivity_summary.json` | Post-hoc exploratory look at which settings drive the step 2 changes (from `scripts/explore_convergence_sensitivity.py`; not predeclared) |
| `rq_protocol.md`, `rq_specification.json` | Step 3a: step size versus space-charge update interval, at 64 cells and 160k (frozen 2026-11-13) |
| `rq_changes.csv`, `rq_pairs.csv`, `rq_adequacy.csv`, `rq_mechanism.csv`, `rq_mechanism_by_setting.csv`, `rq_order.csv`, `rq_noise_band.csv`, `rq_rank_agreement.csv`, `rq_cost.csv`, `rq_analysis_receipt.json` | Step 3a results (from `scripts/analyze_convergence_step_test.py`) |
| `particle_ladder_protocol_draft.md` | Superseded particle-only draft, not adopted |

## Step 1 — rank stability from the existing round 6 runs

**Data.** 387 settings at five levels (`results/revision_round6/resolution`), checked against the journal checksums and the completion record. No simulation was run. The summaries are unweighted descriptions of the sample, with 95 % cluster-bootstrap intervals over the ten matched groups (2,000 resamples).

| Levels | Quantity | Spearman [95 %] | Pairs in same order | Same order, pairs >5 % apart | Same order, same campaign | Median shift |
|---|---|---|---|---|---|---|
| fixed medium → fixed fine | ε_x | 0.993 [0.990, 0.995] | 97.0 % | 98.1 % | 97.3 % | −5.5 % |
| | ε_y | 0.989 [0.985, 0.992] | 96.2 % | 97.6 % | 96.5 % | −7.4 % |
| production → combined fine | ε_x | 0.979 [0.969, 0.985] | 94.1 % | 95.6 % | 94.7 % | −22.9 % |
| | ε_y | 0.962 [0.950, 0.972] | 92.0 % | 93.6 % | 92.4 % | −30.6 % |
| | σ_E | 1.000 [1.000, 1.000] | 99.5 % | 100 % | 99.4 % | −0.9 % |
| fixed fine → combined fine (10k → 40k) | ε_x | 0.999 | 98.9 % | 99.7 % | 99.1 % | −2.0 % |
| | ε_y | 0.999 | 98.7 % | 99.8 % | 98.8 % | −2.3 % |

The per-method correlations for production → combined fine are close to one another: Spearman 0.973–0.978 for ε_x and 0.954–0.964 for ε_y.

**Reading.**
- **Settings mostly keep their order.** The production emittances are 23–31 % higher than at the finest level, but the shift mostly preserves the order of settings.
- **Some pairs still swap.** Between production and the finest level, 6–8 % of all setting pairs, and 4–6 % of pairs more than 5 % apart, change order (ε_y more than ε_x). The correlation also varies by setting, so the shift is not a single common factor.
- **Energy spread** is effectively resolution-independent.
- **What this supports:** an argument that the optimizer's ordering, and hence the method comparison, depends only weakly on resolution. It does not support converged absolute emittances, and it says nothing about Pareto fronts beyond the sampled settings.

## Step 2 — grid × particle convergence matrix

**Run.** The run used the frozen protocol in [rm_protocol.md](rm_protocol.md). It started on 2026-11-12 at 18:43 KST and finished on 2026-11-13 at 11:39 KST, using 360 CPU-h on 22 workers.
- **Records:** all 165 attempts are valid, and the completion record was written (journal SHA-256 `4ffd5b59…2dd7`).
- **Gate:** passed. All 15 `quarter_g64_n40k` reruns reproduced the round 6 combined-fine records within rtol 1e-9.
- **Disk:** 47 GB under `results/convergence_matrix/`, against a planning estimate of 15 GB.
- **Scope:** the summaries below describe the 15 settings only.

**Primary endpoint.** No half-step point is 1 %-adequate.

| Point (half step) | Refinements checked | Lowest share within 1 % | Status |
|---|---|---|---|
| g32 × 40k / 160k / 640k | particles, grid | 0.20 / 0.07 / 0.07 | not adequate |
| g48 × 40k / 160k / 640k | particles, grid | 0.20 / 0.27 / 0.20 | not adequate |
| g64 × 40k | particles, step | 0.00 | not adequate |
| g64 × 160k | particles | 0.73 (11 of 15) | not adequate (needs 12) |
| g64 × 640k | step | 0.00 | terminal, step check not met |

**Changes per refinement.** Each cell gives the median signed change for ε_x / ε_y, then the share of settings with both emittances within 1 %.

| Refinement | at 40k | at 160k | at 640k |
|---|---|---|---|
| grid 32 → 48 | −3.6 / −0.4 %, 20 % | −1.6 / +0.3 %, 7 % | −1.6 / −0.1 %, 7 % |
| grid 48 → 64 | −0.8 / −0.5 %, 47 % | −0.7 / −0.7 %, 27 % | −1.0 / −0.8 %, 20 % |
| step half → quarter, g64 | −2.9 / −3.6 %, 0 % | — | −3.5 / −3.5 %, 0 % |

| Refinement (×4 particles) | g32 | g48 | g64 |
|---|---|---|---|
| 40k → 160k | −0.0 / −1.0 %, 27 % | −0.1 / −1.2 %, 20 % | −0.3 / −1.2 %, 27 % |
| 160k → 640k | +0.1 / +0.0 %, 60 % | −0.0 / −0.1 %, 67 % | +0.0 / −0.1 %, 73 % |

- **Energy spread:** the median σ_E change is at most 0.6 % in every refinement.
- **Feasibility:** no setting changes feasibility class in any refinement.
- **Diagnostics:** settings within the round 6 diagnostic tolerances:
  - 60 % for the step refinements;
  - 67 % for grid 32 → 48;
  - 93–100 % for every other refinement.

**Reading** (under the interpretation rules fixed at the freeze):
- **Not converged.** Absolute emittance convergence is not reached within this matrix, so no candidate resolution follows.
- **Step size dominates what remains.**
  - Halving the step from half to quarter at 64 cells lowers both emittances for every setting but one (ε_x +0.1 % for that one). The median drop is 3–3.5 %, and the change does not shrink from 40k to 640k particles.
  - Half step is therefore not adequate at 64 cells. The round 2 estimate of about 1 %, made at 10k particles on the production grid, does not carry over to the 64-cell grid.
- **Particles have converged in the median, not per setting.**
  - From 160k to 640k, the median emittance change is at most 0.1 %, and 60–73 % of settings change by at most 1 %.
  - Individual settings still move by up to ±5–16 %, in both directions.
  - Those per-setting changes behave like sampling scatter more than a systematic trend: the ×4 changes take both signs, and a geometric extrapolation applies to only 5–8 of the 15 settings per grid.
- **Grid 48 → 64** still lowers the median by about 0.5–1 % at every particle count, with per-setting changes up to about 16–18 %.
- **Ranking is stable.** Spearman correlation with `half_g64_n640k` is 0.96–1.00 for every level, including both quarter-step levels (0.96–0.97). This is consistent with step 1.
- **Not tested here:** whether a quarter-step grid/particle point, or a finer step than quarter, is 1 %-adequate. A follow-up on that would need a new frozen protocol and separate authorization.

### Exploratory follow-up — which settings drive the changes (post hoc)

This analysis was not predeclared. It uses only the completed step 2 journal (`scripts/explore_convergence_sensitivity.py`). With 15 settings and several measures, the p-values are unadjusted and the results only generate hypotheses.

- **Sensitivity is a property of the setting.**
  - The settings that change most with particles also change most with grid and with step: Spearman 0.65–0.81 among the largest particle, 160k → 640k, grid 48 → 64 and step changes.
  - Large changes are concentrated but not confined to a few settings. Changes above 10 % appear in 29 of the 210 setting × refinement comparisons, spread over 9 of the 15 settings. Changes above 5 % appear in at least 5 of the 14 refinements for 7 settings, and in none for 3.
- **Infeasible settings are more sensitive.**
  - The six settings that are infeasible at `half_g64_n640k` all have a transverse rms size above 1 mm, and feasibility is the same at every level.
  - Their median absolute change over all refinements is 4.9 %, against 1.4 % for the nine feasible settings (Mann–Whitney p = 0.012).
  - The most sensitive single setting is feasible, however (σ_y′ 0.67 mrad).
- **Exit-plane associations.**
  - Sensitivity rises with the larger transverse size (ρ = 0.56) and with size × divergence (ρ = 0.61).
  - It does not depend on the x/y aspect ratio (ρ ≈ 0) or on the emittance itself.
  - Transmission is 1 for every setting, so aperture losses play no part.
- **The step change is not driven by the outliers.**
  - The nine feasible settings still drop by a median 2.1–2.4 % (ε_x) and 3.0–3.2 % (ε_y) from half to quarter step, with 0 of 9 within 1 %.
  - For particles, the feasible settings are much closer to converged: 160k → 640k at 64 cells keeps 8 of 9 within 1 %.
- **Next step.** Step 3a ([rq_protocol.md](rq_protocol.md)) tests whether the step change comes from the space-charge update interval (`Max_count=10`, `Max_scale=0.01` in the template) or from the integration step. It also estimates the order of step convergence.

## Step 3a — step size versus space-charge update interval

**Run.** The run used the frozen protocol in [rq_protocol.md](rq_protocol.md), at commit `690aff8`.
- **Time:** from 2026-11-13 17:07 to 2026-11-14 05:35 KST, using 254 CPU-h on 22 workers. Disk use is 35 GB under `results/convergence_step_test/`.
- **Records:** all 120 attempts are valid, and the completion record was written (journal SHA-256 `caf4b91a…96c2`).
- **Gate:** passed. All 15 `half_mc10` reruns reproduced step 2's `half_g64_n160k` within rtol 1e-9.
- **Scope:** the summaries describe the 15 settings at 64 cells and 160k particles only.

**Paired changes.** Each cell gives the median ε_x / ε_y change with its 95 % bootstrap interval, and the share of settings within the limit.

| Pair | Median ε_x [95 %] | Median ε_y [95 %] | Within 1 % | Within max(1 %, noise band) |
|---|---|---|---|---|
| half → quarter (Max_count 10) | −2.7 % [−3.3, −1.3] | −3.1 % [−5.7, −2.7] | 0 % | 13 % |
| quarter → eighth (Max_count 10) | −0.9 % [−1.9, −0.5] | −1.1 % [−3.4, −0.9] | 20 % | 33 % |
| half: Max_count 10 → 1 | −0.7 % [−1.8, +0.9] | −1.7 % [−2.2, +1.0] | 7 % | 7 % |
| half → quarter (Max_count 1) | −3.1 % [−4.4, −1.6] | −3.4 % [−5.1, −1.3] | 7 % | 7 % |

**Primary 1, mechanism: mixed.**
- The median ratio R is 0.32 (ε_x) and 0.42 (ε_y), between the 0.3 and 0.7 thresholds.
- Per setting, R ranges from −7.9 to +8.4. The update-interval change takes both signs (10 of 15 settings lower), whereas halving the step lowers ε in 14–15 of 15 settings.
- Halving the step changes ε by −3.1 / −3.4 % even when space charge is recomputed every step.
- So the update interval accounts for part of the half → quarter change but does not remove the step dependence.
- The infeasible stratum alone classifies as step dominated.

**Primary 2, order and adequacy.**
- **Observed order** from the medians: 1.56 (ε_x) and 1.47 (ε_y); the per-setting medians are 1.69 / 1.59. The feasible stratum gives 2.4 / 1.6.
- **Richardson remainders** (median over settings): quarter step +1.4 % (ε_x) and +1.8 % (ε_y) above the extrapolated limit; eighth step +0.5 % and +0.6 %.
- **Adequacy:** neither half nor quarter is 1 %-adequate. Neither the systematic rule (the 95 % interval goes beyond ±2 %) nor the per-setting rule (33 % against the required 80 %) is met for quarter → eighth.
- **Eighth step:** it has no finer level, so it is assessed only through the extrapolated remainder of about 0.5 %.

**Secondary.**
- **Noise band:** twice the replicate SD from the four half-step sources has a median of 0.5 % (ε_x) and 0.6 % (ε_y). It exceeds 1 % in about a quarter of the settings, up to 11–13 % in the most sensitive one.
- **Ranking:** Spearman correlation with `eighth_mc10` is 0.99–1.00 for both quarter levels and 0.94–0.97 for the half levels.
- **Other quantities:** no setting changes feasibility class. σ_E changes by at most 0.6 % (median). Settings within the round 6 diagnostic tolerances: 60 % for half → quarter and 80 % for quarter → eighth.
- **Cost per run:**
  - eighth step 3.9 h and quarter 2.1 h;
  - half 1.1–1.3 h under full load (the gate's 0.94 h ran on 15 workers);
  - `Max_count=1` costs about 1.9× at both steps. The 3 cm probe's +24 % did not carry over to the full beamline.

**Reading** (under the interpretation rules fixed at the freeze):
- **Unresolved.** The mechanism is mixed and no step is 1 %-adequate, so absolute emittance convergence stays unresolved at this resolution, and no levels are added.
- **Descriptive picture:**
  - The emittance falls with step size at an observed order of about 1.5.
  - The quarter step sits about 1.5 % and the eighth step about 0.5 % above the extrapolated limit, in the median.
  - Recomputing space charge every step costs about 2× and does not remove the step dependence.
  - The ordering of settings is already stable at the quarter step.
- **Not assessed here:** grid convergence beyond 64 cells at the quarter or eighth step. A study of it would need a new protocol and authorization.
