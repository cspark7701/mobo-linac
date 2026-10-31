# Reviewer 1 revision tasks — round6

**Source:** [Reviewer 1 round6 report](../reviews/reviewer1_round6_report.md), formalizing [Task 00340](../../exec-plans/completed/TASK_00340_manuscript_acceptance_assessment.md).

**Recommendation:** Major revision under this internal assessment. R6-01 and R6-02 are the two substantive requests before this assessor recommends acceptance. Reviewer 2's different recommendation is preserved in the [consolidated queue](consolidated_round6_revision_tasks.md).

**Status:** All tasks are unstarted. A request to create this list is not a request to run simulations. The author can adopt or decline work with a documented reason; non-adoption is not completion of the requested validation or a change in the recommendation.

## R6-01. Representative numerical validation

**Priority:** P1. **Report:** R6-01. **Consolidated:** C6-05 disposition and C6-06. **Detail:** A6-01–A6-03 in the [additional validation plan](round6_additional_validation_plan.md).

- [ ] Freeze the sample-selection protocol, seed, strata, inclusion probabilities, numerical levels, tolerances, stopping rules and resource budget before new outcomes.
- [ ] Include all three methods and matched groups, both feasibility states, near-boundary observations and random interior controls. Do not substitute the ten already selected feasible settings for this sample.
- [ ] Reproduce nominal observations and re-track identical controls at the planned levels in new directories, separating source changes from fixed-source refinement.
- [ ] Analyze shifts, margins, classification flips and failures by stratum. Use sampling-aware uncertainty for any population estimate; do not assume unsampled settings are unchanged.
- [ ] State whether the evidence supports, weakens or leaves the feasible-sampling comparison unresolved, and whether the achieved resolution is converged for the claimed quantities.

**Deliverables:** a frozen protocol/manifest, provenance-complete re-tracking records and `r6_resolution_*` analyses.

**Done when:** adopted evaluations and analyses are fully accounted for, with the sampling/numerical limits reported. An inconclusive result is a completed analysis but may leave the scientific request unresolved. If declined, record that disposition in the response without marking the validation done.

## R6-02. Matched constraint-scaling comparison

**Priority:** P1. **Report:** R6-02. **Consolidated:** C6-05 disposition and C6-07. **Detail:** common protocol A6-01 and A6-04–A6-06 in the [additional plan](round6_additional_validation_plan.md).

- [ ] Freeze residual scales, dimensionless temperatures, physical widths, random streams, shared initial designs, matched budgets and endpoints before campaign outcomes.
- [ ] Implement and test an explicit normalized-residual mode while preserving the raw default, physical feasibility, diagnostic GP observations and archived reproducibility.
- [ ] Verify unit consistency, inequality signs, q=8/pruning behavior and checkpoint/resume. Disclose the physical-width changes introduced by a common dimensionless temperature.
- [ ] Run contemporaneous matched arms only after adoption and readiness checks; account for all failed attempts, fallback behavior and computation time.
- [ ] Report paired feasible-fraction effects and uncertainty, without assuming normalization improves outcomes. Keep nominal-resolution scaling experiments distinct from tracking convergence.

**Deliverables:** protocol, implementation/tests, campaign manifests, raw ledgers and `r6_scaling_*` outcome analyses.

**Done when:** the declared experiment is executed and analyzed honestly, or non-adoption is recorded separately. A negative or inconclusive result must remain visible and is not automatic acceptance.

## R6-03. Front-quality scope and endpoint consistency

**Priority:** P2. **Report:** R6-03. **Consolidated:** C6-05 and C6-09.

- [ ] Retain the original failed hypervolume endpoint and the exploratory labels on historical replacement indicators.
- [ ] Distinguish feasible-sampling evidence from front quality in any new result or conclusion.
- [ ] If secondary front-quality outcomes are planned for new campaigns, freeze their reference rule before outcomes; otherwise keep them explicitly exploratory.

**Done when:** existing and new indicators have accurate endpoint/reference status and no general superiority claim is inferred. This does not require a new standalone analysis if the existing scope remains unchanged.

## R6-04. Optional constrained-scalarized comparator

**Priority:** P3. **Report:** R6-04. **Consolidated:** C6-08. **Detail:** A6-07 in the [additional plan](round6_additional_validation_plan.md).

- [ ] Record adoption or non-adoption independently of R6-01/R6-02.
- [ ] If adopted, define and test a genuine constrained scalarized acquisition with frozen weights, scales, seeds, budgets and comparison rules before runs.
- [ ] If omitted, preserve the missing-comparator limitation and avoid attributing a unique benefit to vector-valued acquisition over constraint-aware scalarization.

**Done when:** the optional decision and any adopted comparison are documented. Omitting this arm does not leave a third mandatory scientific request open.

## R6-05. Response and validation

**Priority:** P1 for closing the disposition. **Report:** R6-05. **Consolidated:** C6-09.

- [ ] Write `docs/paper/reviews/reviewer1_round6_response.md`, mapping R6-01–R6-05 to evidence, changes, reasoned non-adoption or unresolved limitations. Do not imply that retaining the nominal-model route has already changed this recommendation.
- [ ] Retain both reviewers' recommendations and earlier response history; do not count Task 00340 and its formalized report as independent reviews.
- [ ] Map any new evidence to exact inputs/checksums, preserve archives, and run the relevant checks for adopted code/manuscript changes. Do not claim tests, builds, simulations or regeneration that were not performed.
- [ ] Package the round6 changes and response, use the next available five-digit task summary and required local commit format, and do not push or upload.

**Done when:** every item has a traceable disposition and validation record, with scientific uncertainty and reviewer disagreement accurately stated. Checklist closure is not journal acceptance.

## Suggested order

1. Record the C6-05 scope/adoption disposition.
2. If adopted, follow the A6 numerical and scaling dependencies for R6-01/R6-02. Decide R6-04 separately.
3. Preserve R6-03 throughout analysis and integration.
4. Close R6-05 alongside Reviewer 2's V6 using the consolidated queue.
