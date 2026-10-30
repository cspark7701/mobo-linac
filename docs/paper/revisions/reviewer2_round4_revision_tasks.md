# Revision tasks for Reviewer 2 — round4

**Source report:** [reviewer2_round4_report.md](../reviews/reviewer2_round4_report.md)
**Previous round:** [reviewer2_round3_revision_tasks.md](reviewer2_round3_revision_tasks.md), [consolidated_round3_revision_tasks.md](consolidated_round3_revision_tasks.md)
**Reviewed manuscript revision:** `887673c`
**Recommendation:** Accept after minor revision. No new simulations are required, and no further review round is needed once T1–T4 are done.

Each task lists the review item it answers, the work involved, and what counts as done.
- **Priority:** **P0** required for acceptance, **P1** recommended, **P2** editorial.
- **Ground rules:** archived production results must not be rewritten. New analyses go in separate derived-evidence files under `docs/paper/revisions/evidence/`, labelled post hoc. Nothing about the withdrawn route (b) enters the manuscript.

---

## P0 — Required for acceptance

### T1. Correct the refined TDR membership in contribution 3 (comment 1)
- [ ] Contribution 3 says that TDR-feasible observations change membership under refinement. Replace this with a statement true for both candidates. Candidate B meets the TDR inequalities at all fifteen levels, and candidate A fails on the 64-cell grid and with two of five sources. For example: "membership near the limits is not resolved numerically".
- [ ] Check the abstract and Sec. VI B for the same generalization.
- **Done when:** contribution 3, Sec. VI B and the Conclusions make the same statement about refined TDR membership.

### T2. Align the regeneration claim of the Conclusions with Appendix A (comment 2)
- [ ] Replace "support regeneration of all reported values". Say that Supplement S1 identifies the inputs of every reported value, and that representative ledger-only analyses were regenerated from the minimal input set.
- [ ] Do not imply that levels 2b and 3, or the proposals, were replayed.
- **Done when:** the Conclusions, Appendix A and the supplement README make the same reproducibility claim.

### T3. Correct the population statement in the response to Reviewer 1 (comment 3)
- [ ] Either add to the Limitations that the ten re-tracked settings are feasible and mostly from constraint-aware searches, or correct item 3 of the M1 response in `reviewer1_round3_response.md`, so that it names only the sections that make the statement.
- [ ] Re-read both round-3 responses against the current manuscript for other claims that do not match the text.
- **Done when:** every location named in the responses contains the statement attributed to it.

### T4. Condition the Pareto-set size in the Discussion (comment 4)
- [ ] First sentence of the Discussion: attach the nominal-resolution condition to "a larger feasible Pareto set", or move the set size to the front-quality sentence, which is already conditioned.
- [ ] Check the Conclusions and the abstract for set-size claims without that condition.
- **Done when:** no objective-space quantity (front indicators or Pareto cardinality) is stated without the nominal-model condition.

---

## P1 — Recommended (existing data only)

### T5. Report the upward and differential bounds (comment 5)
- [ ] Extend `scripts/analyze_revision_resolution_bounds.py`, with a test, or add a small script. It should add:
  - **(a)** the measured upward scale of sizes and divergences (×1.012, from the step-only column of Table I) to the size scales;
  - **(b)** a differential worst case per matched group: the lowest constraint-aware post-initialization fraction over all shifts, minus each baseline's highest. Report the mean, the smallest group difference and the number of positive groups.
- [ ] Write the results to new evidence files (`r4_*`), add them to Supplement S1 and the input inventory, and rebuild the manifest. Do not overwrite the `r3_*` files.
- [ ] Add one sentence to the bounds paragraph of Sec. V B. The reviewer's computation gives, for the differential worst case, means of 0.166 and 0.211, smallest group differences of 0.062 and 0.132, and all ten groups positive. With ×1.012 the differences are 0.279 and 0.311.
- **Done when:** the manuscript states that the feasible-sampling advantage persists under the upward shift and under the differential worst case, with the evidence mapped in S1.

### T6. Qualify the comparison with Kim et al. (comment 6)
- [ ] Sec. VI A: add that the difference between the present ideal-distance point and the tracked example of Ref. [Kim2024] is not resolved numerically. Both are at nominal resolution, and the difference is of the order of the refinement shifts and the source spread.
- **Done when:** no absolute-emittance comparison in the manuscript is presented without the nominal-resolution qualification.

---

## P2 — Editorial

### T7. Reconcile the fallback wording (comment 7)
- [ ] Appendix D: say that the offline refits apply the production fallback rule, which no saved production fit triggered (Appendix A).

### T8. Length (comment 8, optional)
- [ ] Consider moving the paragraph that reclassifies the primary evaluations under the NAPAC, JKPS and JINST limits (end of Sec. II B) to an appendix.
- [ ] Consider moving the detailed published values of Sec. VI A to an appendix.
- [ ] Rebuild both layouts and update the page counts quoted in the round-4 response.

### T9. Abstract precision (comment 9)
- [ ] Replace "under the measured refinement shifts" with "under bounding shifts taken from the refinement check". Keep the abstract free of numbers and no longer than 262 words.

---

## Closing

### T10. Response and validation
- [ ] Write `docs/paper/reviews/reviewer2_round4_response.md`, mapping comments 1–9 to the changes.
- [ ] Run `ruff`, the documentation-sync check, the full test suite with 100 % coverage, the supplement manifest check and the regeneration check. Build both PDF layouts without errors, undefined references or overfull boxes.
- **Done when:** every comment has a traceable disposition, and the validation status is reported.

## Suggested order
1. T1–T4 (text and the response correction; one pass).
2. T5 (analysis, evidence and one sentence), then T6.
3. T7–T9 (editorial).
4. T10.
