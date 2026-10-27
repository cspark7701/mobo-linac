# Reviewer 1 revision tasks — round2

**Source:** [Reviewer 1 round2 report](../reviews/reviewer1_round2_report.md)

**Reviewed revision:** `9077875be22358b68c9a090994f7a3718484720a`

**Recommendation:** Major revision; not acceptable in its present form.

**Status:** Proposed tasks only. This document does not authorize executing revisions or additional simulations.

## Scope and execution order

Retain existing production simulations and their provenance. Do not treat a closed round1 task as newly verified scientific evidence. No MOGA campaign, new BO/control arm, expanded jitter study or crest scan is required for the narrowed computational comparison. Never replace the historical acquisition or feasibility labels retrospectively.

Suggested order: **R2-01 → R2-02 → R2-03 → R2-04 → R2-05 → R2-06 → R2-07 → R2-08**. Scope/numerical-evidence decisions come first because they determine the claims that later editing can retain. R2-04–R2-06 can be investigated independently after those decisions.

| ID | Priority | Deliverable | New simulations? |
|---|---|---|---|
| R2-01 | P1 | Consistent computational target and explicit TDR candidate/margin summary | No; existing C01 and primary records |
| R2-02 | P1 | Traceable numerical-error evidence or explicit claim restriction | Existing evidence first; new validation only conditionally and with separate approval |
| R2-03 | P1 | Claims tied consistently to the executed raw-residual acquisition | No; corrected-arm efficacy remains unmeasured |
| R2-04 | P1 | Defensible treatment of shared-reference statistical inference | No; prose or optional offline reanalysis |
| R2-05 | P2 | Interpretation of predictive errors and optional stage-resolved summaries | No; saved prediction records |
| R2-06 | P1 | Reader-resolvable scientific supplement and version mapping | No; packaging/documentation |
| R2-07 | P2 | Terminology, concise synthesis and author submission items | No; funding remains an author dependency |
| R2-08 | P2 | Round2 response and final consistency validation | No; focused checks and PDF build |

## R2-01 — Align the target and acceptance interpretation

**Covers:** Major M1; minor 5.

- [ ] Define the positive contribution in the abstract as a matched fixed-model study under a specified computational acceptance profile, retaining the author's no-numbers preference.
- [ ] Distinguish primary production feasibility, the checked TDR optimization subset and full machine acceptance throughout results and conclusions.
- [ ] Replace “all archived observations” with the actual primary evaluation population where the 648/251/200 and two/zero/zero counts are reported.
- [ ] Provide the two TDR-candidate objectives and signed physical margins in a compact table or identifiable supplement; use stable candidate IDs without raw seed numbers in manuscript prose.
- [ ] State that the two candidates are not automatically the six independently selected jitter representatives and that two versus zero is not an established TDR-profile algorithm ranking.

**Done when:** Every feasibility and robustness claim identifies its population/profile, and a reader can inspect the TDR candidates and margins. No production relabeling or new tracking.

## R2-02 — Resolve the numerical-evidence disposition

**Covers:** Major M2.

- [ ] Locate the previously completed convergence record, if available; identify particle, mesh, integration, source and solver-transition correspondence.
- [ ] If a quantitative bound is available, compare it with objective differences and candidate margins, including approximately 2.47/8.93 micrometre horizontal-size and 8.16/7.96 micrometre bunch-length margins.
- [ ] If unavailable, state explicitly that acceptance classifications are nominal-resolution results and avoid claims of numerically validated engineering settings; preserve the unresolved scientific limitation in the response.
- [ ] Do not substitute deterministic repeats, GP likelihood variance, physical jitter spread or quoted output precision for tracking-discretization error.
- [ ] Record whether the paper follows the restricted benchmark route or retains a stronger claim needing evidence. Obtain separate authorization before any new validation calculation.

**Done when:** Numerical accuracy is either supported by traceable evidence or its absence is consistently reflected in the retained claims. The restricted route does not count as completed physical validation or guarantee acceptance.

## R2-03 — Identify the actual constrained method in all claims

**Covers:** Major M3; minor 3.

- [ ] Describe the comparison as three specified pipelines, not algorithms differing only by an acquisition formula.
- [ ] Retain the raw residual units, effective smoothing scales, unequal posterior sample counts and baseline handling in the method specification.
- [ ] Add a concise interpretation distinguishing empirical pipeline performance from the frozen-model unit-sensitivity result.
- [ ] Keep q=1/unpruned/one-run probe limitations visible wherever their results are interpreted; unchanged probe argmax is not production q=8 invariance.
- [ ] Do not attribute historical outcomes to normalized residuals or imply measured efficacy for a corrected method.

**Done when:** Abstract, methods, results and conclusion identify the same executed implementation and make no unsupported corrected-method/general-algorithm claim. Additional frozen-model probes are optional, not required.

## R2-04 — Qualify reference-dependent inference

**Covers:** Major M4.

- [ ] Separate feasible-fraction inference from epsilon/IGD+/HV calculations using a reference estimated from the tested outcomes.
- [ ] Explain why exact sign enumeration alone does not establish calibration after a shared data-derived transformation; retain the signed-rank assumptions and post-hoc scope.
- [ ] Choose and document one defensible route: descriptive quality effects/sensitivities with clearly assumption-dependent exploratory probabilities, or a justified offline inference procedure addressing reference construction.
- [ ] If resampling data-derived reference uncertainty, rebuild references within the appropriate run-level procedure and report the estimand and remaining assumptions. Do not present this as automatically validating a p-value.
- [ ] Distinguish unadjusted paired mean-effect intervals from signed-rank hypotheses and Holm-adjusted probabilities; do not change endpoints to obtain a favorable ranking.

**Done when:** The paper makes no stronger quality-significance claim than the inferential construction supports. All original tables remain preserved as historical evidence; no new ASTRA runs.

## R2-05 — Explain the surrogate accuracy relevant to the search

**Covers:** Major M5.

- [ ] Explain the whole-trajectory RMSE and undercoverage without suggesting that surrogate errors invalidate directly tracked observations.
- [ ] State that aggregate RMSE mixes optimization stages and feasible/infeasible regions; observed-boundary conditioning is descriptive.
- [ ] Either refrain from claims of accurate local/late-stage surrogate prediction, or calculate stage/feasible-region summaries from existing C11 records with counts and run-level variation.
- [ ] Keep API-floored versus covariance-derived interval conventions distinct and do not claim calibrated machine reliability or transmission loss discrimination.

**Done when:** Predictive limitations and any retained local-accuracy claim are supported at the corresponding scope. Optional additional summaries use saved predictions, without refitting or new tracking.

## R2-06 — Make the supporting evidence accessible to a reader

**Covers:** Major M6.

- [ ] Add a specific supplement/software reference or accompanying package identifier in Methods or an appendix; no new Data availability section is required.
- [ ] Map reported results to run-level quality/paired summaries, TDR candidate diagnostics, full representative diagnostics, prediction summaries and actual execution settings.
- [ ] Distinguish production startup code from analysis revision and identify configuration/CLI overrides and nondistributed inputs.
- [ ] State the limit from unsaved sampler base draws; do not promise bitwise campaign replay from incomplete acquisition artifacts.
- [ ] Validate local package links and completeness. Publication/deposition is a separate action; this task does not authorize upload or git push.

**Done when:** A reader with the article and accompanying package can locate the evidence without knowledge of internal task numbers.

## R2-07 — Finish terminology, synthesis and author items

**Covers:** Minor 1–7, in coordination with R2-01/R2-03.

- [ ] Use “ideal-distance point” consistently instead of an unsupported knee designation; explain centroid-distance naming.
- [ ] Replace “without smoothing the data” with an accurate effective fixed-noise regularization description.
- [ ] Harmonize survey weighting labels and remove any unmeasured brightness/operational implication.
- [ ] Center the conclusions on supported comparisons and acceptance scope; reduce repeated pooled counts and move excessive implementation detail to the identified supplement.
- [ ] Preserve scatter-only projections, grid lines, generic article format, keywords and contents. Add PDF metadata and remove stale revision-integration comments when preparing the submission source.
- [ ] **Author-dependent:** supply funding and acknowledgment text before submission. Do not invent it or mark this item complete while deferred.

**Done when:** Terminology and conclusions are consistent and the remaining author dependency is explicit. Format changes alone do not resolve the major scientific comments.

## R2-08 — Respond and validate

- [ ] Create `docs/paper/reviews/reviewer1_round2_response.md`, mapping each major/minor comment to a change, evidence or reasoned non-adoption.
- [ ] Clearly distinguish narrowed claims from newly supplied validation; do not assert reviewer agreement or journal acceptance.
- [ ] Check affected data/table consistency and Markdown/LaTeX links. Run only focused tests justified by any changed analysis code.
- [ ] Build the full manuscript and inspect affected figures, tables, contents and references; retain the qualitative abstract and separate affiliations.
- [ ] Summarize unresolved evidence/funding requirements and prepare a local change inventory; follow repository task-summary/commit rules without pushing.

**Done when:** Every comment has a traceable disposition, validation is reported honestly and unresolved issues remain visible for editorial reconsideration.
