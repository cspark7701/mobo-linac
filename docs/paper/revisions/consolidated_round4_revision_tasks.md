# Consolidated revision tasks — round4

**Reviewers:** Reviewer 1 and Reviewer 2

**Recommendations:**
- Reviewer 1: **minor revision**. Acceptable after C1–C3 for the nominal-numerical-model scope. This is up from major revision in round3.
- Reviewer 2: **accept after minor revision**. No further review round is needed once T1–T4 are done.

Both reviewed the manuscript at `887673c`. Neither requires new simulations, GP refits or optimization arms. Both accept the route (a) scope chosen in round3, a comparison of the specified pipelines on the nominal numerical model. The remaining work is wording, one table, one response correction and an optional analysis of existing data.

**Purpose:** A single working queue that merges the two round4 task lists. Overlapping requests are merged, each reviewer's specific concerns are kept, and conflicts are resolved explicitly. The individual reviewer documents remain the source records. This document does not authorize simulations, manuscript edits or publication actions.

**Excluded at the author's direction:** funding and acknowledgments, `\finaltrue` and any Zenodo deposition. Nothing about the withdrawn route (b), including its stage A results, enters the manuscript. None of these are tracked here.

## Status (2026-10-30)

| ID | Status | Commit(s) | Remaining |
|---|---|---|---|
| C4-01 | Done | TASK_00312 | — |
| C4-02 | Not started (optional) | — | — |
| C4-03 | Done | TASK_00313 | — |
| C4-04 | Not started | — | — |
| C4-05 | Not started | — | — |
| C4-06 | Not started | — | — |
| C4-07 | Not started | — | — |
| C4-08 | Not started | — | — |
| C4-09 | Not started | — | — |
| C4-10 | Not started | — | — |
| C4-11 | Not started | — | — |

## Sources

- [Reviewer 1 round4 report](../reviews/reviewer1_round4_report.md) and [its revision tasks](reviewer1_round4_revision_tasks.md) (C1–C3; R4-01 to R4-04).
- [Reviewer 2 round4 report](../reviews/reviewer2_round4_report.md) and [its revision tasks](reviewer2_round4_revision_tasks.md) (comments 1–9; T1–T10).
- Background:
  - [consolidated round3 tasks](consolidated_round3_revision_tasks.md);
  - [round3 revision overview](round3_revision_overview.md);
  - the round3 responses in `../reviews/`.

## Ground rules carried into round4

- **Production data stay unchanged.** The production campaigns, the round2 revision runs and the round3 evidence files (`r3_*`) are not rewritten. Any new analysis goes in new derived evidence files (`r4_*`), labelled post hoc.
- **Scope.** The paper is a comparison of the specified pipelines on the nominal numerical model. No task may add a physically resolved ranking, a validated machine setting, an engineering-acceptance claim or the efficacy of a corrected constraint method.
- **Common-shift scenarios are not bounds.** After C4-01, the 27 transformations are described as post-hoc common-shift sensitivity scenarios. Any optional extension (C4-02) is described the same way.
- **Abstract.** It stays qualitative and without numbers, and no longer than 262 words.
- **Layout.** The one-column review layout, scatter-only Pareto projections, grid lines and shaded constraint regions stay.
- **No public deposition.** No public repository, deposit, upload or push is implied by any task.
- **Not acceptance.** A completed checklist is not reviewer agreement or journal acceptance.

## Overlaps and how they are resolved

| Issue | Reviewer 1 | Reviewer 2 | Consolidated treatment |
|---|---|---|---|
| Meaning of the 27 transformations | C1 (required): they are common-shift scenarios, not a bound. Replace "to bound the effect" and "bounds that effect". Abstract: "persists in the tested diagnostic-shift scenarios". The grid excludes the small positive transverse changes of Table I. No extra scenarios are needed. | Comment 9 (editorial): "under bounding shifts taken from the refinement check". Comment 5 (recommended): add the upward shift (×1.012) and a differential worst case. | **Conflict on wording, resolved for Reviewer 1.** "Bounding shifts" would reintroduce the bound language that Reviewer 1 rejects, and "scenarios" is the more accurate description. C4-01 applies Reviewer 1's wording everywhere, which also satisfies Reviewer 2's request for precision. Reviewer 2's extra checks become the optional C4-02. If it is done, it is reported as additional scenarios, not as a bound. The exclusion of upward changes is stated in C4-01 in any case. |
| RF amplitude and the TDR margins | C2 (required): "indicates that amplitude jitter would cause further TDR failures" is too strong. Make it a conditional risk statement, based on a nominal-reference estimate. | Asked in round3 (minor 2) for the comparison itself; no round4 objection. | **Compatible.** C4-06 keeps the comparison, as Reviewer 2 requested, in the conditional form Reviewer 1 requires. Both point to a narrower claim. |
| TDR membership under refinement | Accepted the round3 TDR wording. | Comment 1 (required): contribution 3 says that membership "changes", but candidate B passes at every level. | C4-03 follows Reviewer 2; this agrees with Reviewer 1's emphasis on resolution-dependent membership. |
| Reproducibility claim | Judges the reproduction package substantially resolved, and confirms the regeneration check for three generators. | Comment 2 (required): the Conclusions still say "all reported values". | C4-04 follows Reviewer 2. Reviewer 1's own check confirms that only representative paths were tested. |
| Response accuracy | — | Comment 3 (required): the response to Reviewer 1 (M1, item 3) names the Limitations and the Conclusions for a population statement that only Sec. II A makes. | C4-10. Correct the round3 response, or add the half-sentence to the Limitations, and say which in the round4 responses. |
| Objective-space claims | Pareto-quality results are exploratory and conditional (no new request). | Comment 4 (required): "a larger feasible Pareto set" in the Discussion lacks the nominal-resolution condition. Comment 6 (recommended): the comparison with Kim et al. needs the same qualification. | C4-05 (required) and C4-08 (recommended). Both apply the condition that Reviewer 1 already attaches to Pareto quality. |
| Table I | C3 (required): percent headings conflict with the MeV energy row; define the fine-vs-medium denominator and whether entries are magnitudes. | — | C4-07. |
| Editorial | — | Comments 7 (fallback wording) and 8 (length, optional). | C4-09. |

## Consolidated work queue

Priority: **P0** is required by at least one reviewer; **P1** is recommended; **P2** is editorial or response work.

| ID | Priority | Workstream | Reviewer items | New simulations? |
|---|---|---|---|---|
| C4-01 | P0 | Describe the 27 transformations as common-shift scenarios | R1 C1 (R4-01); R2 comment 9 (T9), comment 5a text | No |
| C4-02 | P1, optional | Upward-shift and differential scenarios from existing data | R2 comment 5 (T5) | No |
| C4-03 | P0 | Refined TDR membership in contribution 3 | R2 comment 1 (T1) | No |
| C4-04 | P0 | Regeneration claim of the Conclusions | R2 comment 2 (T2) | No |
| C4-05 | P0 | Condition the Pareto-set size in the Discussion | R2 comment 4 (T4) | No |
| C4-06 | P0 | Conditional RF-amplitude implication for the TDR candidates | R1 C2 (R4-02) | No |
| C4-07 | P0 | Table I units and comparison convention | R1 C3 (R4-03) | No |
| C4-08 | P1 | Qualify the comparison with Kim et al. | R2 comment 6 (T6) | No |
| C4-09 | P2 | Fallback wording; optional length reduction | R2 comments 7–8 (T7, T8) | No |
| C4-10 | P0 | Correct the round3 response to Reviewer 1 | R2 comment 3 (T3) | No |
| C4-11 | P2 | Responses and validation | R1 R4-04; R2 T10 | No |

---

### C4-01. Describe the 27 transformations as common-shift sensitivity scenarios

**Sources:** Reviewer 1 C1 (R4-01); Reviewer 2 comment 9 (T9) and the text part of comment 5(a).

- [x] Replace every description of the analysis as a bound:
  - "To bound the effect of the numerical resolution" (Sec. V B);
  - "Sec. V B bounds that effect" (Sec. II A);
  - "bounding shifts" (Discussion, Limitations, Conclusions, contribution 5).

  Use "post-hoc common-shift sensitivity scenarios motivated by the ten-setting refinement check", or an equivalent concise phrase.
- [x] In the main result (Sec. V B), state that each scenario applies the same transverse factor, bunch-length factor and energy shift to every evaluation of every method.
- [x] State that stability in these 27 scenarios does not establish stability under setting- or channel-dependent changes or under converged tracking.
- [x] State that the grid does not enclose every measured change: it omits the small positive transverse changes of Table I (up to 1.2 %, step only).
- [x] Abstract: "persists in the tested diagnostic-shift scenarios" (Reviewer 1's wording; this also settles Reviewer 2's comment 9). Keep the abstract free of numbers and ≤ 262 words.
- [x] Keep the computed values, the 27 scenarios and the `r3_resolution_bounds_*` filenames. If the metadata note is updated, record it as an interpretation correction.

**Done when:** no reader can mistake the scenarios for re-tracking of the primary campaigns, a worst-case error bound or demonstrated convergence. Abstract, contribution 5, Secs. II A and V B, the Discussion, the Limitations and the Conclusions use the same wording.

**Done:** Every description of the 27 transformations as a bound is replaced by post-hoc common-shift sensitivity scenarios: abstract ("persists in the tested diagnostic-shift scenarios", still 262 words and no digits), contribution 5, Sec. II A, Sec. V B, the Discussion, the Limitations and the Conclusions. Sec. V B states that every scenario applies the same changes to every evaluation of every method, that the grid omits the measured increases of sizes and divergences (up to 1.2 % step only; larger for some single-factor and source levels at individual settings), and that stability in the scenarios does not establish stability under setting- or channel-dependent changes or converged tracking. Values, scenarios and the `r3_resolution_bounds_*` files are unchanged; their metadata note is not rewritten.

### C4-02. Optional: upward-shift and differential scenarios

**Sources:** Reviewer 2 comment 5 (T5). Reviewer 1 says no extra scenarios are required for C1, so this task is optional.

- [ ] If done, extend `scripts/analyze_revision_resolution_bounds.py` (with a test) or add a small script for two additions:
  - the upward transverse scale ×1.012;
  - a per-group differential case: the lowest constraint-aware post-initialization fraction over all scenarios, minus each baseline's highest.
- [ ] Write new evidence files (`r4_*`), add them to Supplement S1 and the input inventory, and rebuild the manifest.
- [ ] Add one sentence to Sec. V B, worded as additional scenarios, not a bound. Reviewer 2's computation gives:
  - ×1.012: differences 0.279 and 0.311;
  - differential case: means 0.166 and 0.211, smallest group differences 0.062 and 0.132, all ten groups positive.

**Done when:** either the sentence and the evidence are added with scenario wording, or the task is recorded as not done with a reason.

### C4-03. Refined TDR membership in contribution 3

**Sources:** Reviewer 2 comment 1 (T1).

- [x] Contribution 3: replace "their membership changes under numerical refinement" with a statement true for both candidates. Candidate B passes at all fifteen levels; candidate A fails on the 64-cell grid and with two of five sources. For example: "membership near the limits is not resolved numerically".
- [x] Check the abstract and Sec. VI B for the same generalization.

**Done when:** contribution 3, Sec. VI B and the Conclusions agree.

**Done:** Contribution 3 now says that TDR-feasible observations lie within micrometres of the diagnostic limits, "where membership is not resolved numerically: one candidate passes at every refinement level and the other fails at some". This matches Sec. VI B (candidate B passes at all fifteen levels; candidate A fails on the 64-cell grid and with two of five sources) and the Conclusions ("membership near the limits is not numerically resolved"). The abstract makes no membership claim.

### C4-04. Regeneration claim of the Conclusions

**Sources:** Reviewer 2 comment 2 (T2); consistent with Reviewer 1's evidence-boundary check.

- [ ] Replace "support regeneration of all reported values". Say that S1 identifies the inputs of every reported value, and that representative ledger-only analyses were regenerated from the minimal input set.
- [ ] Do not imply that levels 2b or 3, or the proposals, were replayed.

**Done when:** the Conclusions, Appendix A and the supplement README make the same claim.

### C4-05. Condition the Pareto-set size in the Discussion

**Sources:** Reviewer 2 comment 4 (T4).

- [ ] First sentence of the Discussion: attach the nominal-resolution condition to "a larger feasible Pareto set", or move the set size to the front-quality sentence, which is already conditioned.
- [ ] Check the abstract and the Conclusions for unconditioned set-size or front-quality claims.

**Done when:** no objective-space quantity is stated without the nominal-model condition.

### C4-06. Keep the RF-amplitude implication for the TDR candidates conditional

**Sources:** Reviewer 1 C2 (R4-02); Reviewer 2 round3 minor 2 (the comparison itself).

- [ ] Replace "indicates that amplitude jitter would cause further TDR failures" with a conditional statement. Because the scales are comparable, omitted amplitude errors could reduce TDR acceptance and merit a candidate-specific study.
- [ ] Say that the gain estimate comes from the MOGA-derived nominal reference, not from a tracked amplitude response of candidates A and B.
- [ ] Keep the measured lattice-only counts (36/50 and 44/50) and their intervals. Infer no failure count or probability.

**Done when:** the text distinguishes a scale-based risk indication from demonstrated amplitude-induced failures.

### C4-07. Table I units and comparison convention

**Sources:** Reviewer 1 C3 (R4-03).

- [ ] Remove the conflict between the percent column headings and the MeV row: state in the caption that all entries are percent except mean energy (MeV), or set the energy row apart.
- [ ] Define the denominator of the "fine vs medium" column (relative to the medium level, or as computed) and state that its entries are maximum magnitudes, whereas the first two columns are signed ranges.
- [ ] Verify the caption against `evidence/r2_convergence_summary.csv` or the generating formula. Keep all values unchanged.

**Done when:** every entry has one unambiguous unit and convention, in the source and in the rendered table.

### C4-08. Qualify the comparison with Kim et al.

**Sources:** Reviewer 2 comment 6 (T6).

- [ ] Sec. VI A: add that the difference between the present ideal-distance point and the tracked example of Ref. [Kim2024] (about 10–25 % in emittance) is of the order of the refinement changes and the source spread, so it is not resolved numerically.

**Done when:** no absolute-emittance comparison is presented without the nominal-resolution qualification.

### C4-09. Editorial: fallback wording and length

**Sources:** Reviewer 2 comments 7 and 8 (T7, T8).

- [ ] Appendix D: say that the offline refits apply the production fallback rule, which no saved production fit triggered (Appendix A).
- [ ] *Optional:* move the reclassification under the NAPAC, JKPS and JINST limits (end of Sec. II B) and the detailed published values of Sec. VI A to an appendix.
- [ ] Rebuild both layouts and record the page counts.

### C4-10. Correct the round3 response to Reviewer 1

**Sources:** Reviewer 2 comment 3 (T3).

- [ ] The round3 response (M1, item 3) says that "Sec. II A, the Limitations and the Conclusions" describe the ten settings as feasible and mostly from constraint-aware searches; only Sec. II A does. Prefer adding the half-sentence to the Limitations, which also makes the manuscript more explicit. Otherwise correct the response.
- [ ] Re-read both round3 responses against the current manuscript for other mismatches.
- [ ] Record the correction in the round4 responses rather than silently rewriting history.

**Done when:** every location named in the responses contains the statement attributed to it.

### C4-11. Responses and validation

**Sources:** Reviewer 1 R4-04; Reviewer 2 T10.

- [ ] Write `docs/paper/reviews/reviewer1_round4_response.md` (C1–C3) and `reviewer2_round4_response.md` (comments 1–9). In the Reviewer 2 response, explain why Reviewer 1's "scenario" wording was used instead of "bounding shifts" (comment 9).
- [ ] Confirm the narrower scope is intact: no physical Pareto-rank validation, machine acceptance or corrected-method efficacy.
- [ ] Package the manuscript diff and the code diff against `887673c`, a changed-file inventory and a round4 overview, as in round3.
- [ ] Validate:
  - `ruff`, the documentation-sync check and the full test suite with 100 % coverage;
  - the supplement manifest check and the regeneration check;
  - both PDF builds, inspecting Table I and the changed summary passages.
- [ ] Do not equate task closure with reviewer agreement or journal acceptance.

**Done when:** every comment of both reviewers has a traceable disposition and the validation status is reported honestly.

---

## Suggested order of work
1. **C4-01**, the scenario wording. It touches the abstract and most summary sections, so do it first.
2. **Summary text in one pass:** C4-03, C4-04, C4-05, C4-06, C4-08 and C4-10.
3. **C4-07** (Table I) and **C4-09** (editorial).
4. **C4-02**, only if the author wants it.
5. **C4-11**, last.
