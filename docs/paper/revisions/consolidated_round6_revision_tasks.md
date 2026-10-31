# Consolidated revision tasks: round 6

## Sources, scope and status

- [Reviewer 2 report](../reviews/reviewer2_round6_report.md) and [tasks V1–V6](reviewer2_round6_revision_tasks.md): **accept**, with V1 requested before acceptance, V2–V3 editorial, V4–V5 optional and V6 closing checks. No new simulations are required by this reviewer.
- [Task 00340](../../exec-plans/completed/TASK_00340_manuscript_acceptance_assessment.md): **major revision under a separate internal assessment**, requesting two new validation workstreams. Its constrained-scalarized suggestion is optional.
- [Review synthesis](../reviews/round6_review_synthesis.md): source mapping, author constraints and the unresolved difference between these recommendations. No separate Reviewer 1 round 6 report is present.

**All tasks are planned and unstarted.** No manuscript edits, code changes, simulations or uploads were executed in creating this queue. Prior [round 5 closure](round5_revision_overview.md) and reviewer recommendations are unchanged. Creating or completing this queue is not journal acceptance.

Priority: P1 addresses an explicit review requirement or a necessary disposition; P2 is editorial; P3 is optional. A P1 label on a conditional research item applies only if the author adopts that workstream in C6-05.

## Consolidated work queue

| ID | Priority | Task | Sources | New simulations? | Dependencies |
|---|---|---|---|---|---|
| C6-01 | P1 | Define the physical weighted-sum target precisely in prose | R2 V1 | No | None |
| C6-02 | P2 | Remove the remaining appendix kernel hypothesis | R2 V2; author removal instruction | No | None |
| C6-03 | P2 | Restore or explicitly confirm abstract scope wording | R2 V3 | No | None |
| C6-04 | P3 | Re-wrap the undercoverage paragraph | R2 V4 | No | After C6-02 if adopted |
| C6-05 | P1 | Record the disposition of the conflicting validation requests | R2 V5; internal I6-01–I6-04 | No | None |
| C6-06 | Conditional P1 | Representative numerical validation | Internal I6-01; R2 V5 optional advice | Yes, only if adopted | C6-05; frozen protocol |
| C6-07 | Conditional P1 | Matched raw/normalized acquisition campaigns | Internal I6-02 | Yes, only if adopted | C6-05; frozen protocol and tested implementation |
| C6-08 | P3 | Optional constraint-aware scalarized comparator | Internal I6-04 | Yes, only if separately adopted | C6-05; separate protocol |
| C6-09 | P1 | Responses, evidence integration and final validation | R2 V6; all dispositions | No additional runs | Core items and recorded decisions on optional/conditional work |

## Ground rules

- Preserve the author's recent dispositions: no negated-cost explanation, no categorical kernel claim, and no broad humanization pass. Resolve each review comment with the smallest justified change.
- Preserve archived production runs, feasibility labels, round 1–5 evidence, prior reviews and their responses. New evidence, if commissioned, uses new directories and an `r6_` prefix.
- Keep the current PRAB format, qualitative number-free abstract convention, and distinctions between numerical validity, production feasibility, TDR acceptance and machine reliability. Funding/acknowledgments, data availability and `\finaltrue` remain author decisions.
- Do not confuse optional advice from Reviewer 2 with required experiments. Do not state that its acceptance recommendation settles the separate internal review's higher evidence requirement.
- New analyses may support, weaken or leave a claim unresolved. Never define completion as obtaining a favourable result, or use repeated runs until a desired outcome appears.
- No push or upload. Remote GitHub Actions queries require the specific approval described in AGENTS.md. Use local checks for this work.

## C6-01. Define the weighted-sum target precisely in prose

**Source:** Reviewer 2 comment 1, V1. This is the only correction that Reviewer 2 explicitly requests before acceptance.

- [ ] Define the scalarized cost as the weighted sum of the physical objective values divided by their stated reporting scales, and say that it is minimized. Keep the existing scales and equal weights.
- [ ] Use an exact one-line prose definition. Do not restore a negated-cost explanation or the removed displayed/inline scalar-cost formula unless the author later changes that instruction.
- [ ] Check that “weighted cost” in the channel-attribution section and “scalarized cost” in predictive checks refer to the same definition.
- [ ] Preserve every measured value, objective definition and acquisition choice.

**Deliverable:** a local methods edit and consistent downstream terminology.

**Done when:** the physical baseline target can be reconstructed unambiguously from the text, without adding implementation-sign commentary or changing the executed method.

## C6-02. Remove the remaining appendix kernel hypothesis

**Source:** Reviewer 2 comment 2, V2, reconciled with the author's instruction to remove the categorical kernel sentence.

- [ ] Remove “Kernel misspecification” from the appendix sentence that currently pairs it with adaptive test points as possible explanations for remaining undercoverage.
- [ ] Keep the adaptive-test-point hypothesis conditional, and retain the statement that this check does not test it. Make singular/plural references grammatically consistent.
- [ ] Do not reintroduce the deleted kernel claim in the main text, even as a softened assertion, under this task.
- [ ] Preserve the noise-refit experiment, coverage values and its stated limitations.

**Deliverable:** a minimal appendix correction.

**Done when:** the main text and appendix use a consistent set of hypotheses, while respecting the author's removal instruction.

## C6-03. Restore the abstract's scope signals or document deliberate retention

**Source:** Reviewer 2 comment 3, V3.

- [ ] Restore “specified” in the opening description of the Bayesian optimization pipelines, or record the author's deliberate decision to omit it.
- [ ] Prefer a closing statement about the scope of the present results, rather than wording that reads as a commitment to a future physically resolved optimization. Restore the earlier meaning, or explain deliberate retention in the response.
- [ ] Preserve “persists in the tested diagnostic-shift scenarios”, the distinction between nominal-model and engineering claims, and the abstract's lack of numerical values.
- [ ] Record the resulting word count; do not invent a requirement to return to exactly 262 words.

**Deliverable:** a local abstract edit or explicit non-adoption response.

**Done when:** the scope matches the stated executed-pipeline study, or the author's intended alternative is documented without broadening the claims.

## C6-04. Optional source wrapping

**Source:** Reviewer 2 comment 4, V4.

- [ ] Re-wrap the paragraph beginning “Several mechanisms could explain the undercoverage” to the surrounding source line length.
- [ ] Check equality after whitespace normalization. Do not change its meaning, hypotheses or rendered scientific content.

**Done when:** source formatting is consistent, or the optional item is recorded as not adopted.

## C6-05. Record the scientific-scope disposition

**Sources:** Reviewer 2 comment 5/V5 and internal I6-01–I6-04.

- [ ] Record whether the author retains the current nominal-model submission route or adopts additional validation before submission. Cite the earlier scope-based closure and both current recommendations accurately.
- [ ] If retaining the current route, respond to the additional requests with the existing numerical/smoothing limitations and a reasoned scope explanation. Mark C6-06 and C6-07 “not adopted for this revision”, rather than falsely completed. The separate internal major-revision recommendation remains on record unless explicitly reassessed.
- [ ] If adopting additional research, select each workstream explicitly, freeze its protocol and resource budget, and identify the stronger claim it is intended to test before collecting outcomes. Do not treat this task list as authorization to start ASTRA.
- [ ] Decide C6-08 separately. It is optional under both source records and is not a third mandatory scientific request.
- [ ] Keep historical front-quality indicators exploratory, regardless of the route. No historical endpoint or feasibility label may be rewritten.

**Deliverable:** a traceable disposition in the round 6 overview and response.

**Done when:** required editorial work, conditional research and unresolved reviewer disagreement are distinguished, with no invented consensus or acceptance claim.

## C6-06. Conditional representative numerical validation

**Adoption condition:** explicit selection in C6-05. **Detail:** A6-01 through A6-03 in the [additional validation plan](round6_additional_validation_plan.md).

- [ ] Freeze a stratified sample across methods, matched groups, feasibility states, boundary channels and search stages before new outcomes. Retain inclusion probabilities and a precision/cost basis for sample size.
- [ ] Re-track identical controls at declared levels in a fresh directory. Check nominal reproduction first and separate source changes from step/grid refinement.
- [ ] Analyze diagnostic shifts, physical margins, feasibility flips and failed attempts by stratum. Use sampling-aware uncertainty for any population estimate; do not assume unsampled observations remain unchanged.
- [ ] Separate a medium-level submission check suggested by Reviewer 2 from a demonstration of numerical convergence. A limited sample or unconverged refinement may leave the broader internal request unresolved.
- [ ] Report supportive, adverse or inconclusive findings with their limitations.

**Deliverables:** frozen manifest/protocol, new run records, `r6_resolution_*` evidence and an analysis report.

**Done when:** adopted work is fully accounted for and supports only the scope justified by its sampling and numerical precision; or non-adoption is recorded under C6-05. Completed tracking alone does not settle convergence or reviewer agreement.

## C6-07. Conditional matched residual-scaling comparison

**Adoption condition:** explicit selection in C6-05. **Detail:** common protocol A6-01 and A6-04 through A6-06 in the [additional validation plan](round6_additional_validation_plan.md).

- [ ] Freeze normalization scales, temperatures, their physical widths, endpoints, seeds, shared initial designs and budgets before looking at new optimization outcomes.
- [ ] Implement an explicit recorded mode with tests of residual signs, unit transformations, all inequality sides, physical feasibility invariance, q=8/pruning behavior and checkpoint/resume. Preserve raw defaults and archived behavior.
- [ ] Run contemporaneous matched raw-residual and normalized-residual arms only after the adopted protocol and readiness checks. Disclose that a common dimensionless temperature changes physical smoothing widths, so the experiment tests that convention rather than unit conversion alone.
- [ ] Analyze paired feasible fractions, channel-group violations, failures and cost. Keep secondary front-quality analyses prospective or explicitly exploratory according to their reference construction.
- [ ] Do not call normalized residuals a validated or superior method before results. Nominal-resolution scaling campaigns do not resolve tracking convergence.

**Deliverables:** implementation/test records, new per-group campaigns and `r6_scaling_*` effects/metadata.

**Done when:** the frozen comparison is executed and analyzed honestly, or non-adoption is recorded. A negative or inconclusive result is a completed analysis, not automatic acceptance or evidence of efficacy.

## C6-08. Optional constrained-scalarized comparator

**Source:** internal I6-04, distinct from the two main internal validation requests. **Detail:** A6-07 in the [additional validation plan](round6_additional_validation_plan.md).

- [ ] Record adoption/non-adoption separately from C6-06 and C6-07.
- [ ] If adopted, define and test a genuine constraint-aware scalarized acquisition; freeze its weights, scaling, initial designs, budgets and comparisons before runs.
- [ ] Separate the benefit of constraint information from the choice of vector-valued acquisition.
- [ ] If declined, retain the explicit missing-comparator limitation. Do not infer a unique MOBO benefit over constraint-aware scalarization.

**Done when:** the optional decision and any adopted experiment are documented. Omitting this comparator does not leave Reviewer 2's required correction open.

## C6-09. Responses and validation

**Source:** Reviewer 2 V6, plus all internal dispositions. Use A6-08/A6-09 of the [additional plan](round6_additional_validation_plan.md) only if new evidence is produced.

- [ ] Write `docs/paper/reviews/reviewer2_round6_response.md`, mapping comments 1–5 to exact changes or reasoned non-adoption. Write a separately attributed response/disposition for Task 00340; do not attribute it to Reviewer 1, for whom no round 6 report is present.
- [ ] Add `round6_revision_overview.md`, manuscript/code diffs against the declared baseline and a changed-file/hash inventory. Preserve earlier review packages.
- [ ] Update supplement evidence mappings, input inventory and checksums if new analyses are adopted. Do not extend regeneration claims beyond the inputs actually checked.
- [ ] For editorial-only work, build the two-column PRAB manuscript and check references, overfull boxes, changed passages and number-free abstract. Run the relevant manuscript, paper-output and documentation-link checks.
- [ ] Regenerate and compile the local upload folder with `python scripts/build_prab_submission.py --compile`; verify that its bibliography is current. No upload is implied.
- [ ] If code is changed, add meaningful tests and run the applicable local CI/coverage checks under the current resource constraints. State unrun checks accurately.
- [ ] Save the next available five-digit completion summary and commit only related changes using the repository format. Do not push.

**Done when:** every source comment has a disposition, all adopted work has evidence and validation receipts, non-adopted work is visible, and no task status is equated with journal acceptance.

## Suggested execution order

1. Complete the core C6-01–C6-03 editorial dispositions; C6-04 is optional.
2. Record C6-05 before any new scientific runs. Its disposition can be prepared alongside the editorial work.
3. Execute C6-06/C6-07 only if adopted; C6-08 is separately optional. Follow the A6 dependencies in the additional plan rather than treating this as a request for parallel agent work.
4. Close C6-09 with the actual results and route-specific validation.
