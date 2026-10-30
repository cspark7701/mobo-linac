# Consolidated revision tasks — round5

**Reviewers:** Reviewer 1 and Reviewer 2

**Recommendations:**
- Reviewer 1: **accept on scientific grounds** for the stated nominal-model study. No required tasks; two optional editorial suggestions (E1, E2).
- Reviewer 2: **accept**. One sentence should be corrected before acceptance, which the editor can verify (U1). The rest is editorial or optional.

Both reviewed the manuscript at `c1e9d21`. Neither requires new simulations, GP refits, optimization arms or another review round. The remaining work is wording in about six places, one table entry, one supplement note, an optional calculation on existing data, and the responses.

**Purpose:** A single working queue that merges the two round5 task lists. Overlapping requests are merged, each reviewer's specific concerns are kept, and conflicts are resolved explicitly. The individual reviewer documents remain the source records. This document does not authorize simulations, manuscript edits or publication actions.

**Excluded at the author's direction:** funding and acknowledgments, `\finaltrue` and any Zenodo deposition. Nothing about the withdrawn route (b) enters the manuscript. None of these are tracked here.

## Status (2026-10-30)

| ID | Status | Commit(s) | Remaining |
|---|---|---|---|
| C5-01 | Done | TASK_00326 | — |
| C5-02 | Done | TASK_00327 | — |
| C5-03 | Not started | — | — |
| C5-04 | Not started | — | — |
| C5-05 | Not started | — | — |
| C5-06 | Not started | — | — |
| C5-07 | Not started (optional) | — | — |
| C5-08 | Not started (optional) | — | — |
| C5-09 | Not started | — | — |

## Sources

- [Reviewer 1 round5 report](../reviews/reviewer1_round5_report.md) and [its revision tasks](reviewer1_round5_revision_tasks.md) (E1, E2; R5-01 to R5-03).
- [Reviewer 2 round5 report](../reviews/reviewer2_round5_report.md) and [its revision tasks](reviewer2_round5_revision_tasks.md) (comments 1–7; U1–U8).
- Background:
  - [consolidated round4 tasks](consolidated_round4_revision_tasks.md);
  - [round4 revision overview](round4_revision_overview.md);
  - the round4 responses in `../reviews/`.

## Ground rules carried into round5

- **Production data stay unchanged.** The production campaigns, the round2 revision runs and the `r3_*` and `r4_*` evidence files are not rewritten. Any new analysis goes in a new derived-evidence file, labelled post hoc.
- **Scope.** The paper is a comparison of the specified pipelines on the nominal numerical model. No task may add a physically resolved ranking, a validated machine setting, an engineering-acceptance claim or the efficacy of a corrected constraint method.
- **Scenarios are not bounds.** Any added sensitivity check is worded as a scenario.
- **Abstract.** No round5 item touches it. It stays at 262 words, with no numbers.
- **Layout.** The one-column review layout, scatter-only Pareto projections, grid lines and shaded constraint regions stay.
- **No public deposition.** No public repository, deposit, upload or push is implied by any task.
- **Not acceptance.** A completed checklist is not reviewer agreement or journal acceptance.

## Overlaps and how they are resolved

| Issue | Reviewer 1 | Reviewer 2 | Consolidated treatment |
|---|---|---|---|
| "Two further post-hoc scenarios give the same result" (Sec. V B) | E2 (optional): "scenarios" confuses two constructions with the many shifts inside them; prefer "sensitivity checks". | Comment 7 (optional): "give the same result" is loose, because the differential means are smaller; say that every paired difference stays positive in all ten groups. | **Compatible; merged into C5-06.** One sentence takes both: "Two further post-hoc sensitivity checks leave every paired difference positive in all ten groups." Both reviewers mark it optional. It is promoted to P2 because it is a single edit that settles two comments. |
| Archived `r3_resolution_bounds_*` names and notes | Acceptable as they are, because the manuscript corrects the interpretation and the evidence stays traceable. | Comment 5: keep the files, but add a README note that "bounds" there means the manuscript's scenarios. | **Compatible.** C5-05 adds the note only. No archived file changes, which is consistent with Reviewer 1. |
| Jitter tolerance of the TDR candidates (Sec. V I) | Judges C2 (amplitude) resolved; raises no concern about the adjacent sentence. | Comment 1 (requested before acceptance): only candidate A is fragile under the stated 0.8 threshold. | **No conflict.** C5-01 follows Reviewer 2. A per-candidate statement is consistent with Reviewer 1's acceptance of the conditional wording. |
| Kim et al. comparison (Sec. VI A) | Judges the round4 qualification resolved. | Comment 2 (editorial): base the emittance argument on the setting dependence of the refinement change and the source difference; the energy-spread definitions are not established to match. | **No conflict.** C5-02 follows Reviewer 2 as a precision edit. |
| Emittance quotation (Conclusions) | E1 (optional): "should not be quoted without a converged calculation" conflicts with the qualified nominal values the paper itself quotes. | — | C5-07, optional. |
| Upward scale beyond ×1.012 | — | Comment 6 (optional): ×1.17, the largest single-level increase, with a reviewer check; correct the 13 % figure of the round4 response to Reviewer 1. | C5-08 (optional analysis). The response correction is **not** optional and goes in C5-09. |

## Consolidated work queue

Priority: **P1** is requested before acceptance by at least one reviewer; **P2** is editorial; **P3** is optional.

| ID | Priority | Workstream | Reviewer items | New simulations? |
|---|---|---|---|---|
| C5-01 | P1 | Jitter tolerance stated per TDR candidate | R2 comment 1 (U1) | No |
| C5-02 | P2 | Kim et al. comparison: argument and energy-spread definition | R2 comment 2 (U2) | No |
| C5-03 | P2 | Contribution 3: "refinement and source level" | R2 comment 3 (U3) | No |
| C5-04 | P2 | Table I: mean-energy source spread below the recording step | R2 comment 4 (U4) | No |
| C5-05 | P2 | S1 README interpretation note for the round3 scenario files | R2 comment 5 (U5); consistent with R1's C1 closure | No |
| C5-06 | P2 | Sec. V B: name and state the two further checks exactly | R1 E2 (R5-02); R2 comment 7 (U7) | No |
| C5-07 | P3 | Conclusions: emittance-quotation sentence | R1 E1 (R5-01) | No |
| C5-08 | P3 | Common upward scale ×1.17 from existing data | R2 comment 6 (U6) | No |
| C5-09 | P2 | Responses and validation | R1 R5-03; R2 U8 | No |

---

### C5-01. State jitter tolerance per TDR candidate

**Sources:** Reviewer 2 comment 1 (U1).

- [x] Sec. V I, last sentence of the TDR-candidate paragraph: replace "these marginal settings already do not provide jitter-tolerant TDR operation" with a per-candidate statement under the archived threshold of 0.8, or define the term:
  - candidate A is fragile (36/50, interval 0.58–0.84);
  - candidate B passes the threshold (44/50), but its interval (0.76–0.95) does not exclude values below it;
  - neither retains TDR acceptance in every trial.
- [x] Check the Discussion, Sec. VI B and the Conclusions for the same unqualified claim.

**Done when:** every jitter statement about candidates A and B follows from the stated threshold and counts.

**Done:** Sec. V I now states the outcome per candidate under the lattice-only model and the archived 0.8 threshold: candidate A is fragile; candidate B passes the threshold, but its interval does not exclude values below it; neither retains TDR acceptance in every trial. The undefined "jitter-tolerant TDR operation" is gone. No other passage (Discussion, Sec. VI B, Conclusions, abstract, contribution 3) makes a jitter claim about the candidates.

### C5-02. Kim et al. comparison

**Sources:** Reviewer 2 comment 2 (U2).

- [x] **(a)** Sec. VI A: base "not resolved numerically" on the setting dependence of the refinement change (12–34 % in ε_x and 17–43 % in ε_y across the ten settings) and on the different sources, not on the size of the change. A common offset at the same nominal resolution would largely cancel.
- [x] **(b)** Qualify "The energy-spread difference is larger than its refinement change". The present σ_E is the projected RMS spread including chirp (Sec. II B); say that the definition of the published 0.165 % is not established to be the same, or restrict the sentence to the numerical point.

**Done when:** the paragraph makes no emittance or energy-spread comparison stronger than the evidence supports.

**Done:** Sec. VI A now says that the emittance differences (about 10–25 %) are not resolved numerically because the refinement change depends on the setting (12–34 % in ε_x and 17–43 % in ε_y across the ten re-tracked settings; Table I) and the two sources differ; a common refinement offset at the shared nominal resolution would largely cancel. The energy-spread sentence now says that the difference exceeds its refinement change, but that the published value is not established to be the projected RMS spread including chirp used here, so it is not compared quantitatively.

### C5-03. Contribution 3 precision

**Sources:** Reviewer 2 comment 3 (U3).

- [ ] "one candidate passes at every refinement level and the other fails at some" → "at every refinement and source level". Candidate A also fails with two of the five regenerated sources.

### C5-04. Mean-energy source spread in Table I

**Sources:** Reviewer 2 comment 4 (U4).

- [ ] Replace "≤ 0.005" in the source-spread cell of the mean-energy row with "< 0.01" or a note that it is below the recording step. The caption already says that mean energy is recorded to 0.01 MeV.
- [ ] Keep all other values unchanged.

### C5-05. Interpretation note for the round3 scenario files

**Sources:** Reviewer 2 comment 5 (U5). Reviewer 1 accepts the retained names and metadata, so a note is enough.

- [ ] Add one sentence to `docs/paper/supplement/README.md` (S1.13 or the reproduction notes). It should say that "bounds" in the names and notes of `r3_resolution_bounds_*` and in the docstring of `scripts/analyze_revision_resolution_bounds.py` is to be read as the common-shift scenarios of the manuscript (round4 interpretation correction).
- [ ] Do not edit the archived evidence files, their metadata or the script.

### C5-06. Name and state the two further checks exactly (Sec. V B)

**Sources:** Reviewer 1 E2 (R5-02); Reviewer 2 comment 7 (U7).

- [ ] Replace "Two further post-hoc scenarios give the same result" with, for example, "Two further post-hoc sensitivity checks leave every paired difference positive in all ten groups".
- [ ] Keep the upward family, the differential calculation, the reported values and the statement that none of these is an error bound.

**Done when:** the text distinguishes the two constructions from the shifts inside them and states exactly what they show.

### C5-07. Optional: the emittance-quotation sentence (Conclusions)

**Sources:** Reviewer 1 E1 (R5-01).

- [ ] Replace "absolute emittances should not be quoted without a converged calculation" with wording that separates reporting nominal-model values from treating them as converged physical predictions. For example: "absolute emittances should not be interpreted as numerically converged physical predictions".
- [ ] Keep every reported value, the nonconvergence finding and the nominal-model scope.

**Done when:** either the sentence is changed, or its non-adoption is recorded in the response.

### C5-08. Optional: common upward scale ×1.17

**Sources:** Reviewer 2 comment 6 (U6).

- [ ] If done, extend `scripts/analyze_revision_shift_scenarios.py` (with a test) or add a small script for a common upward scale of ×1.17. That is the largest single-level increase of a size or divergence in `r2_convergence_values.csv`: σ_y of the crowding-distance setting with one random source, +16.2 %.
- [ ] Write the result to a new evidence file without overwriting `r4_*`. Map it in S1.13 and the inventory, and rebuild the manifest.
- [ ] Add a half-sentence in Sec. V B, worded as a scenario, next to the C5-06 sentence. Reviewer 2's check gives, at ×1.17:
  - differences of 0.276 and 0.300 at nominal bunch length and energy;
  - 0.242–0.292 and 0.267–0.317 over the nine shifts;
  - smallest lower interval limits of 0.20 and 0.24, and all ten groups positive.

**Done when:** either the sentence and the evidence are added with scenario wording, or the task is recorded as not done with a reason.

### C5-09. Responses and validation

**Sources:** Reviewer 1 R5-03; Reviewer 2 U8.

- [ ] Write `docs/paper/reviews/reviewer1_round5_response.md` (E1, E2) and `reviewer2_round5_response.md` (comments 1–7). Record each optional item as adopted or not.
- [ ] In the Reviewer 1 response, correct the round4 response (C1, item 4). The largest size increase in the refinement records is 16.2 %, with a regenerated source; 13 % is the 64-cell-grid maximum. Mention it in the Reviewer 2 response (comment 6) as well.
- [ ] Package the manuscript diff (and the code diff, if C5-08 is done) against `c1e9d21`, a changed-file inventory and a round5 overview, as in round4.
- [ ] Validate:
  - `ruff`, the documentation-sync check and the documentation-link test;
  - the full test suite with 100 % coverage, only if code changes (C5-08);
  - the supplement manifest check and the regeneration check;
  - both PDF builds, inspecting Table I and the changed passages; the abstract stays at 262 words with no numbers.
- [ ] Do not equate task closure with reviewer agreement or journal acceptance.

**Done when:** every comment of both reviewers has a traceable disposition, and the validation status is reported honestly.

---

## Suggested order of work
1. **C5-01**, the only item requested before acceptance.
2. **Editorial pass:** C5-02, C5-03, C5-04, C5-06 and, if adopted, C5-07.
3. **C5-05**, the supplement note.
4. **C5-08**, only if the author wants it.
5. **C5-09**, last.
