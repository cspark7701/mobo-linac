# Reviewer 1 revision tasks — round4

**Source:** [Reviewer 1 round4 report](../reviews/reviewer1_round4_report.md)

**Reviewed revision:** `887673c99cb148ec97e045304374a86dbc022884`.

**Recommendation:** Minor revision; acceptable after the focused corrections for the nominal-numerical-model study. This is a reviewer recommendation, not an editorial decision.

**Status:** Proposed tasks only; not yet executed.

## Scope and sequence

Retain the nominal-model scope and all original simulation evidence. No new simulations, GP refits, optimization arms or public publication actions are required. Suggested order: **R4-01 → R4-02 → R4-03 → R4-04**. The first three are independent editorial corrections once the scientific scope remains fixed.

| ID | Priority | Deliverable | New simulations? |
|---|---|---|---|
| R4-01 | P1 | Correct the meaning of common-shift sensitivity results | No |
| R4-02 | P2 | Qualify the TDR amplitude-risk inference | No |
| R4-03 | P2 | Clarify Table I units and relative-change convention | No |
| R4-04 | P2 | Respond and validate the final limited revision | No |

## R4-01 — Describe common-shift scenarios accurately

**Covers:** Report C1.

- [ ] Replace claims that the analysis bounds numerical-resolution effects with “post-hoc common-shift sensitivity scenarios,” or equivalent accurate wording.
- [ ] In the main result, state that each scenario applies the same transverse factor, bunch-length factor and energy shift to every evaluated setting and method.
- [ ] Clarify that stable ordering in these 27 scenarios does not prove stability under arbitrary setting-dependent numerical errors or converged tracking.
- [ ] Do not describe the scenario grid as enclosing all observed changes: it excludes the small positive transverse changes shown in Table I and does not cover arbitrary channel-dependent transformations.
- [ ] Update abstract, contribution 5, section cross-references, Results, Discussion and Conclusions consistently; use “persists in the tested diagnostic-shift scenarios” in the abstract.
- [ ] Preserve the computed values, 27 scenarios, historical evidence filenames and production labels. If current explanatory metadata is updated, record it as an interpretation correction, not new physical evidence.

**Done when:** A reader cannot mistake the scenario analysis for primary-campaign re-tracking, a worst-case error bound or demonstrated numerical convergence. No expanded scenario study is required.

## R4-02 — Keep the amplitude implication conditional

**Covers:** Report C2.

- [ ] Replace “amplitude jitter would cause further TDR failures” with an explicitly conditional statement that it could threaten the small energy margins.
- [ ] Identify the limitation that the gain estimate comes from the nominal reference, not a tracked candidate-specific amplitude-response calculation.
- [ ] Preserve the measured lattice-only trial counts and uncertainty; infer no additional failure count or probability.

**Done when:** The text distinguishes a scale-based risk indication from demonstrated amplitude-induced failures. No new tracking.

## R4-03 — Clarify the resolution table

**Covers:** Report C3.

- [ ] Make clear that relative changes are in percent except for the mean-energy row, whose changes are in MeV; remove the conflict between row units and column headings.
- [ ] Specify the denominator used for fine-versus-medium relative changes and whether displayed maxima are absolute magnitudes.
- [ ] Keep signed fine/step changes and archived numerical values unchanged; verify the caption against the generating evidence or formula.

**Done when:** Every entry has one unambiguous unit and comparison convention in both the source and rendered table.

## R4-04 — Complete the response and final checks

- [ ] Create `docs/paper/reviews/reviewer1_round4_response.md` mapping C1–C3 to changes and manuscript locations.
- [ ] Confirm the accepted narrower scope remains intact: no physical Pareto-rank validation, machine acceptance or general corrected-method efficacy is claimed.
- [ ] Check the affected wording, table values, internal links and supplement consistency. Run focused computation checks only if calculations change.
- [ ] Build the manuscript and visually inspect Table I and affected summary passages; preserve the qualitative abstract and current review layout.
- [ ] Record the review baseline and validation in the next numbered task summary and commit related files locally using the repository format. Do not push.

**Done when:** All three scientific comments have verifiable dispositions and the manuscript is ready for the reviewer's final acceptance recommendation. Do not reopen resolved requests or equate the recommendation with a journal decision.
