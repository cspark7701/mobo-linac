# Revision tasks for Reviewer 2 — round5

**Source report:** [reviewer2_round5_report.md](../reviews/reviewer2_round5_report.md)
**Previous round:** [reviewer2_round4_revision_tasks.md](reviewer2_round4_revision_tasks.md), [consolidated_round4_revision_tasks.md](consolidated_round4_revision_tasks.md)
**Reviewed manuscript revision:** `c1e9d21`
**Recommendation:** Accept. U1 should be corrected before acceptance and can be checked by the editor. No new simulations and no further review round are needed.

Each task lists the review item it answers, the work involved, and what counts as done.
- **Priority:** **P1** requested before acceptance, **P2** editorial, **P3** optional.
- **Ground rules:** archived production results and the `r3_*` and `r4_*` evidence files are not rewritten. Any new analysis goes in a new derived-evidence file, labelled post hoc. Nothing about the withdrawn route (b) enters the manuscript.

---

## P1 — Requested before acceptance

### U1. State jitter tolerance per TDR candidate (comment 1)
- [ ] Sec. V I, last sentence of the TDR-candidate paragraph: replace "these marginal settings already do not provide jitter-tolerant TDR operation" with a per-candidate statement under the archived threshold of 0.8, or define "jitter-tolerant". For example:
  - candidate A is fragile (36/50, interval 0.58–0.84);
  - candidate B passes the threshold (44/50), but its interval (0.76–0.95) does not exclude values below it;
  - neither retains TDR acceptance in every trial.
- [ ] Check the Discussion, Sec. VI B and the Conclusions for the same unqualified claim.
- **Done when:** every jitter statement about candidates A and B follows from the stated threshold and counts.

---

## P2 — Editorial

### U2. Kim et al. comparison (comment 2)
- [ ] **(a)** Sec. VI A: base "not resolved numerically" on the setting dependence of the refinement change (12–34 % in ε_x, 17–43 % in ε_y across the ten settings) and on the different sources, not on the size of the refinement change. Both calculations are at the same nominal resolution, so a common offset would largely cancel.
- [ ] **(b)** Qualify "The energy-spread difference is larger than its refinement change". The present σ_E is the projected RMS spread including chirp (Sec. II B). The manuscript does not establish that the published 0.165 % uses the same definition. Say so, or restrict the sentence to the numerical point.

### U3. Contribution 3 precision (comment 3)
- [ ] "passes at every refinement level and the other fails at some" → "at every refinement and source level". Candidate A also fails with two of the five regenerated sources.

### U4. Mean-energy source spread in Table I (comment 4)
- [ ] Replace "≤ 0.005" in the source-spread column of the mean-energy row with "below the recording step" or "< 0.01". The caption says that mean energy is recorded to 0.01 MeV.

### U5. Interpretation note for the round-3 scenario files (comment 5)
- [ ] Add one sentence to `docs/paper/supplement/README.md` (S1.13 or the reproduction notes). It should say that "bounds" in the names and notes of `r3_resolution_bounds_*` and in the docstring of `scripts/analyze_revision_resolution_bounds.py` is to be read as the common-shift scenarios of the manuscript (round-4 interpretation correction).
- [ ] Do not edit the archived evidence files or their metadata.

---

## P3 — Optional (existing data only)

### U6. Larger common upward scales (comment 6)
- [ ] Optional: extend `scripts/analyze_revision_shift_scenarios.py` (with a test), or add a small script, with the common upward scale ×1.17. That is the largest single-level increase of a size or divergence in `r2_convergence_values.csv`: σ_y of the crowding-distance setting with one random source, +16.2 %.
- [ ] Write the result to a new evidence file (for example `r5_upward_max_*`) or as an added file of the `r4_` set, without overwriting existing files. Map it in S1.13 and the inventory, and rebuild the manifest.
- [ ] Add a half-sentence in Sec. V B, worded as a scenario. The reviewer's check gives, at ×1.17:
  - differences of 0.276 and 0.300 at nominal bunch length and energy;
  - 0.242–0.292 and 0.267–0.317 over the nine shifts;
  - smallest lower interval limits of 0.20 and 0.24, and all ten groups positive.
- [ ] In the round-5 response, whether or not this is done, correct the round-4 response to Reviewer 1 (C1, item 4). The largest increase in the records is 16.2 % with a regenerated source; 13 % is the 64-cell-grid maximum.

### U7. "Give the same result" (comment 7)
- [ ] Sec. V B: replace "Two further post-hoc scenarios give the same result" with a statement that they leave every paired difference positive in all ten groups. The differential means are smaller.

---

## Closing

### U8. Response and validation
- [ ] Write `docs/paper/reviews/reviewer2_round5_response.md`, mapping comments 1–7 to the changes or to reasoned non-adoption.
- [ ] Run `ruff`, the documentation-sync check, the full test suite with 100 % coverage (only if code changes), the supplement manifest check and the regeneration check. Build both PDF layouts without errors, undefined references or overfull boxes. Keep the abstract unchanged, at 262 words with no numbers.
- **Done when:** every comment has a traceable disposition and the validation status is reported. Closing the tasks does not establish journal acceptance.

## Suggested order
1. U1 (the only item requested before acceptance).
2. U2–U5 (one editorial pass).
3. U6–U7, if the author wants them.
4. U8.
