# Reviewer 1 report — round6

**Manuscript:** *Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design*

**Date:** 2026-10-31. **Source snapshot:** `fecab6c30d70a0fea21cbbfbf84813c1898470a0`, `docs/paper/main.tex`, SHA-256 `8d6814ab67e41aa2384af6e0bf95dabe9a90dc73ecf2bf7a8a9ee106e6244eb9`.

**Review status:** Internal scientific pre-submission assessment labelled Reviewer 1 at the author's request. This report formalizes [Task 00340](../../exec-plans/completed/TASK_00340_manuscript_acceptance_assessment.md); it is not another independent review, a new set of experiments, or a journal decision.

**Other records considered:** [Reviewer 2 round6](reviewer2_round6_report.md), [Reviewer 1 round5](reviewer1_round5_report.md), and the [round5 closure](../revisions/round5_revision_overview.md).

## Recommendation

**Major revision under this assessment.** The matched budgets, shared initial designs, ten paired runs, failure-inclusive accounting and transparent treatment of the failed hypervolume endpoint are strengths. The best-supported result is the higher feasible-sampling fraction of the recorded constraint-aware pipeline within the nominal numerical model.

Before recommending acceptance under the evidence standard of Task 00340, I request representative numerical validation and a matched constraint-scaling comparison. These are the two substantive requests, R6-01 and R6-02. They do not require full production campaigns to be repeated automatically, and they do not require a favourable result: adverse or inconclusive results must be reported and reflected in the claims.

## Relation to the earlier recommendation

The archived Reviewer 1 round5 report accepted the explicitly limited nominal-model study without new simulations. It remains unchanged. The present recommendation applies a stricter validation standard to the same acknowledged limitations; it is not evidence of a newly discovered scientific regression caused by the prose edits. The completed editorial fixes in Task 00339 did not produce new numerical evidence.

Reviewer 2 continues to accept the nominal-model route and requests no new simulations. I recognize that difference in assessment. The author may respond by retaining that route and explaining the scope, or adopt additional validation. A scope response is a legitimate disposition, but does not itself change this recommendation or establish agreement between reviewers.

## R6-01. Representative numerical validation of feasible sampling

**Priority:** P1 under this recommendation. **New ASTRA work:** yes if adopted.

The refinement check reports substantial emittance changes and includes only ten feasible selected settings, mostly from constraint-aware searches. It contains no rejected or baseline-method observation. Its stable production classifications therefore cannot establish stability across the populations used in the main method comparison. The common-shift scenarios are correctly described, but cannot test actual setting-dependent changes.

Request a frozen stratified sample across methods, matched groups, search stages and feasibility boundaries, including rejected observations and interior controls. Re-track the same physical settings at declared numerical levels, check nominal reproduction, and separate fixed-source step/grid effects from source changes. Report margins, diagnostic shifts, classification flips and failed evaluations. Use sampling probabilities and appropriate uncertainty for any extrapolation to original run-level feasible fractions; sampled labels alone are not refined classifications of all historical observations.

A modest medium-level check can add evidence without establishing convergence. State the achieved numerical precision and whether it supports the feasible-sampling comparison, weakens it or leaves it unresolved. Re-tracking fixed historical settings does not reproduce the trajectories of campaigns optimized at refined resolution.

## R6-02. Matched comparison of constraint-residual conventions

**Priority:** P1 under this recommendation. **New implementation/campaign work:** yes if adopted.

The recorded smoothing scale has very different physical widths across diagnostic channels. The frozen-surrogate probe establishes unit sensitivity but supplies no optimization outcomes under normalization.

Freeze a dimensionless residual convention, its temperatures and physical widths before observing new campaign outcomes. Verify signs, both energy inequalities, consistent unit transformations and unchanged physical feasibility classification. Then compare contemporaneous raw and normalized arms with common initial designs and matched seeds, simulation budgets, model settings and acquisition-optimization budgets.

A common dimensionless temperature changes relative physical smoothing widths, so describe the experiment as testing the declared normalization-and-temperature convention. It is not unit conversion alone. Use paired feasible-fraction effects as the main outcome, retain failures and costs, and state what the number of groups can resolve. No assumption that the normalized arm will perform better is warranted.

## R6-03. Preserve the exploratory status of objective-quality analyses

**Priority:** P2, principally a scope/consistency check. **New simulations:** no independent requirement.

The original fixed-reference hypervolume endpoint was uninformative; the replacement references were estimated from the outcomes. The manuscript already discloses this appropriately. Keep feasible sampling separate from front quality and retain the post-hoc labels. Any prospective secondary indicator for new campaigns needs a reference rule fixed before their outcomes. This item does not demand another retrospective quality analysis or a third scientific workstream.

## R6-04. Optional constraint-aware scalarized comparator

**Priority:** P3. **New simulations:** only if separately adopted.

A constraint-aware scalarized arm could help distinguish the use of constraint information from the choice of vector-valued acquisition. This would strengthen interpretation, but is not a third mandatory request. If omitted, retain the explicit missing-comparator limitation and do not claim a unique MOBO advantage over constraint-aware scalarization.

## R6-05. Response, evidence and validation

**Priority:** P1 for a complete disposition. **New simulations:** none beyond adopted requests.

Give each item an explicit adopted, not-adopted-with-reason, or unresolved status. Preserve original runs and prior reviews. Map new evidence to its exact sources and report negative/inconclusive outcomes. Keep Reviewer 2's editorial requests and the author's no-negated-cost/no-categorical-kernel instructions in view. Validate any changed code and manuscript, without presenting task closure as reviewer agreement or acceptance.

## Review trace and limits

- This report formalizes the assessment already recorded in Task 00340 against the same unchanged manuscript. It uses the earlier full-source reading and targeted checks; no new PDF inspection, literature audit, simulation, GP refit or independent recomputation is claimed here.
- Source concerns are in the numerical-resolution discussion, constraint-smoothing methods and appendix, primary comparison, and limitations/conclusions.
- The earlier Reviewer 1 acceptance and Reviewer 2's present acceptance are recorded explicitly rather than overwritten or treated as concurrence with this assessment.

The [Reviewer 1 round6 task list](../revisions/reviewer1_round6_revision_tasks.md) maps R6-01–R6-05 to deliverables. The [consolidated queue](../revisions/consolidated_round6_revision_tasks.md) includes both reviewers' items and distinguishes experimental adoption from whether a requested validation has been satisfied.
