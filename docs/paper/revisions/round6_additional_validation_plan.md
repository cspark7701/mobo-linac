# Additional validation plan for round 6

## Conditional scope

This is the detailed research track supporting C6-06 through C6-08 of the [consolidated round 6 queue](consolidated_round6_revision_tasks.md). It expands the numerical and constraint-scaling requests of [Task 00340](../../exec-plans/completed/TASK_00340_manuscript_acceptance_assessment.md), labelled I6-01 and I6-02 in the [review synthesis](../reviews/round6_review_synthesis.md).

**All A6 tasks are conditional and unstarted.** No new simulations are required by Reviewer 2's round 6 recommendation. C6-05 must record the author's disposition before this research track is adopted; creating a task list is not authorization to execute it. The two recommendations remain distinct. A negative or inconclusive finding is a valid completed analysis, but it does not automatically satisfy an acceptance condition.

Internal requests: I6-01 = representative numerical validation; I6-02 = matched residual-scaling campaigns; I6-03 = exploratory status of front-quality evidence; I6-04 = optional constraint-aware scalarization. Priority labels below apply only if this track is adopted. They do not override the core editorial queue or reopen round 5.

## Work queue

| ID | Priority | Task | Source | Dependencies | New ASTRA evaluations? |
|---|---|---|---|---|---|
| A6-01 | P1 | Freeze protocols, samples, outcomes and resource budgets | I6-01, I6-02, I6-03 | None | No |
| A6-02 | P1 | Implement and execute representative re-tracking | I6-01 | A6-01 | Yes |
| A6-03 | P1 | Analyze setting-dependent changes and feasible-sampling effects | I6-01 | A6-02 | No; any expansion follows the frozen rule |
| A6-04 | P1 | Implement and verify the normalized-residual arm | I6-02 | A6-01 | No; mock and analytic checks |
| A6-05 | P1 | Execute matched raw and normalized campaigns | I6-02 | A6-04 | Yes |
| A6-06 | P1 | Analyze the scaling comparison and qualify front-quality evidence | I6-02, I6-03 | A6-05 | No |
| A6-07 | P3 | Optional constraint-aware scalarized comparator | I6-04 | Separate adoption; protocol before its runs | Yes, if adopted |
| A6-08 | P2 | Integrate completed evidence into manuscript and supplement | I6-01 to I6-03 | Adopted A6-03/A6-06; A6-07 only if adopted | No |
| A6-09 | P1 | Close responses, provenance and validation | All dispositions | A6-08; A6-07 disposition | No |

## Constraints on all tasks

- Preserve the recorded production, survey and round 1–5 outputs, feasibility labels and evidence. New raw runs belong in new directories under `results/revision_round6/`; derived evidence uses a new `docs/paper/revisions/evidence/r6_` prefix.
- Give every new evaluation a stable identity and record original run/evaluation identity, physical controls, template and source hashes, executable, environment, numerical overrides, seed, elapsed time and attempt outcome. Keep invalid attempts in all applicable budgets and denominators.
- Refined re-tracking is a check of historical settings; it is not a replay of an optimization trajectory at a refined resolution. Normalized campaigns at nominal resolution are not a convergence study. Neither workstream can substitute for the other.
- Retain the fixed-lattice problem, objective definitions, actual source distribution, production acceptance profile and physical-unit feasibility tests. Do not silently introduce TDR constraints or claim that marginal TDR membership is numerically resolved.
- Keep the original failed hypervolume endpoint and post-hoc analyses traceable. No new result may be relabelled as predeclared in the historical campaigns.
- Preserve the current PRAB manuscript format and the author's qualitative, number-free abstract convention. Funding/acknowledgments, `\finaltrue`, public deposition and uploads are outside this queue.
- Do not add another general humanization pass. Manuscript changes in A6-08 must follow the new evidence and the author's stated dispositions.
- No push. Remote GitHub Actions queries remain subject to the specific approval policy in AGENTS.md; local checks are available.

## A6-01. Freeze the validation protocols and resource budgets

Apply protocol sections only to adopted workstreams; record the other sections as not adopted. A6-08 and A6-09 require only the adopted branches and documented dispositions for the others.

**Deliverables:** `evidence/r6_protocol.md`, `evidence/r6_sampling_manifest.csv`, and a machine-readable campaign/analysis specification. Save them before viewing new outcomes.

- [ ] Inventory the original three-method, ten-group primary comparison and the existing refinement records. Identify missing local input files before scheduling work.
- [ ] Define sampling strata across method, matched group, observed feasibility, signed diagnostic margin and search stage. Include baseline-method and rejected observations, near-boundary observations on both sides, and a random interior subset. Define signed margins and near-boundary bins explicitly.
- [ ] Freeze deterministic sample selection, seed, stratum population sizes, inclusion probabilities, numbers per stratum and all inclusion/exclusion rules. Mark empty strata. Existing ten selected settings can supply continuity but cannot replace this sample.
- [ ] Choose the sample size from the desired precision and available cost. Freeze the rule for expansion or stopping before new labels are available. Do not stop or expand according to whether the algorithm difference is positive.
- [ ] Declare numerical levels, source-file handling and convergence tolerances. Existing production/medium/fine levels are starting points, not evidence that a chosen fine level is converged. Separate fixed-source step/grid changes from particle-count or regenerated-source changes.
- [ ] Specify the target quantity: refined classifications of the sampled historical observations, and any sampling-weighted estimate for historical feasible fractions. Define uncertainty that accounts for both selection within strata and paired-group variation. Record when the design cannot support a population estimate.
- [ ] Freeze the normalized-residual scales, dimensionless temperature(s), physical smoothing widths, seed set, initial designs, model/optimizer settings and equal per-run budget. Use a convention selected before campaign outcomes; the previous offline probe is exploratory context, not confirmatory evidence.
- [ ] Plan contemporaneous raw and normalized control arms. Ten groups with two arms and 160 evaluations each would cost 3,200 ASTRA attempts, before pilots or extra comparators; this is a planning example, not an allocation. Freeze the actual group count and budget, and state the weaker inference if using fewer groups.
- [ ] Specify independent random streams for initialization, posterior sampling and candidate proposals. Reuse standardized streams across matched arms where appropriate, recording their identities without promising bitwise reproduction of historical proposals.
- [ ] Predeclare the feasible fraction as the main scaling endpoint, all-evaluation and post-initialization denominators, paired effect summaries and uncertainty. Predeclare any secondary indicators, reference construction, multiplicity treatment and limitations.
- [ ] Estimate tracking cost, disk use, worker count and wall time for both workstreams using measured costs. Record resource limits, valid resumption and failure accounting. Mark resource-unavailable work as not run.

**Done when:** input inventory, selected identities, exact budgets, analysis choices, numerical tolerances and stopping rules are versioned and hashed before new evaluations. The protocol distinguishes validation failures, insufficient precision and scientific outcomes.

## A6-02. Implement and execute representative re-tracking

**Starting points:** `scripts/evaluate_revision_convergence.py`, `scripts/analyze_revision_convergence.py`, and the `r2_convergence_*` evidence. The old driver hard-codes ten reported settings and output paths; do not run it unchanged and call its sample representative.

- [ ] Add a separate driver or a backward-compatible manifest input and output-directory option. Keep old defaults and archived results reproducible.
- [ ] Verify unique identities and exact control vectors against the original ledgers; fail on mismatched or missing source records.
- [ ] Use meaningful mock tests for manifest selection, source/template overrides, resumption, duplicate/conflicting records and failed attempts. Check that archived directories cannot be overwritten.
- [ ] Reproduce nominal-resolution observations first. Investigate discrepancies before attributing later changes to refinement.
- [ ] Execute the frozen refinement plan in a fresh directory. Hold the actual source file fixed for the declared step/grid contrasts; identify source changes in other contrasts explicitly.
- [ ] Preserve outputs, physical diagnostics, objective values, failures and checksums for every selected setting and level.

**Deliverables:** new run directory, immutable plan, attempt records, completion marker and source/provenance manifests; new `r6_resolution_*` evidence inputs.

**Done when:** all scheduled attempts are accounted for, nominal reproduction is checked, no archived output is changed, and every refined observation can be joined to its original identity. Unfinished or failed tracking is reported, not discarded.

## A6-03. Analyze numerical sensitivity across methods and boundaries

- [ ] Compute per-setting changes in all objectives and diagnostics between levels, signed physical margins, feasibility flips and failures. Separate discretization and source effects.
- [ ] Report results by method, matched group, original classification, boundary channel and search stage. Include unresolved or failed observations.
- [ ] Test the declared numerical tolerances; report where further refinement is needed. Stable classifications alone are not objective convergence.
- [ ] Summarize sampled flip rates without presenting them as full-campaign fractions. If estimating historical population fractions, use the frozen inclusion probabilities and appropriate sampling/paired-group uncertainty.
- [ ] Do not leave unobserved settings at their nominal labels and describe the resulting totals as measured refined totals. Do not infer actual refinement outcomes from a common multiplicative shift.
- [ ] Compare the feasible-sampling effects under the declared analysis. Report support, reversal, or inconclusive uncertainty for each comparison. Keep the distinction between reclassified historical samples and campaigns optimized at a refined resolution.

**Deliverables:** `r6_resolution_values.csv`, `r6_resolution_classification.csv`, stratified summaries, paired/weighted estimates where justified, metadata and a limitations report.

**Done when:** the analysis quantifies what was measured, how sampling affects extrapolation and which numerical claims remain unresolved, regardless of the sign of an effect.

## A6-04. Implement and test the normalized-residual arm

**Starting points:** `src/mobo_linac/constraints.py` and the residual definitions in `scripts/analyze_revision_scaling.py`. The latter is an offline q=1 probe without production pruning; it is not a campaign implementation.

- [ ] Make the comparison mode explicit and recorded. Preserve raw-residual defaults and saved-run compatibility. Keep physical diagnostic GP observations and observed feasibility unchanged; scale only the residuals and their declared smoothing temperatures.
- [ ] Use the protocol's dimensionless residuals, for example upper/lower distances divided by the size/divergence/length thresholds, energy half-band, and allowed transmission loss. Record both energy sides separately.
- [ ] State that a common dimensionless temperature changes relative physical widths. Report those widths. If isolating normalization from width changes is a target, include the protocol's width-preserving control; do not claim that this is the same contrast as changing to a common temperature.
- [ ] Test residual signs, all inequality sides, threshold values and equivalence under consistent unit transformations, including scales and temperatures. Use common posterior samples for acquisition-value comparisons.
- [ ] Check real production features: q=8 joint proposals, baseline pruning, dtype/device handling, checkpoint/resume and fallback metadata. A q=1 ranking check alone does not close this task.
- [ ] Verify with mock campaigns that mode, scales, temperatures, effective widths and randomness are exported and restored, without changing the scientific constraint definitions.

**Done when:** mode selection and restart behavior are reproducible, physical feasibility is identical for identical diagnostics, raw compatibility is preserved and unit-consistency tests pass. No efficacy claim follows from these tests.

## A6-05. Run the matched raw/normalized comparison

- [ ] Run the declared readiness checks and a separately labelled infrastructure pilot. If the protocol changes after a pilot, version the new protocol and keep pilot outcomes outside the confirmatory set.
- [ ] Start both arms from exactly the same initial controls in each group. Match simulation budget, source, numerical resolution, model family, fit settings, posterior sample count, optimizer budgets and hardware policy; vary only the declared residual/temperature convention.
- [ ] Do not substitute old raw campaigns for contemporaneous controls without establishing all relevant execution equivalences; historical observations remain contextual. To compare new outcomes with unconstrained/scalarized arms as a new matched experiment, specify and validate those controls in advance as well.
- [ ] Keep every invalid attempt in the budget, record all fallback and fitting outcomes, and retain elapsed cost. Do not select the best seed or temperature after seeing the results.
- [ ] Check completion and artifact hashes for every scheduled arm/group before analysis.

**Deliverables:** fresh per-group run directories, campaign manifest, complete ledgers, checkpoint/proposal histories and completion receipts.

**Done when:** every prespecified arm/group is accounted for under the frozen budget. Partial runs, restarts and unsuccessful proposals remain visible.

## A6-06. Analyze the scaling experiment

- [ ] Compute raw-versus-normalized paired differences in all-evaluation and post-initialization feasible fractions using the frozen denominators. Include uncertainty across matched groups and failed evaluations.
- [ ] Describe differences by violated channel group and search stage, plus computational cost. Do not infer a causal physical mechanism from violation counts alone.
- [ ] Keep any secondary front-quality analysis separate. Use references fixed before outcomes or an explicit external/training-only construction; keep outcome-derived sensitivity analyses labelled post hoc.
- [ ] State whether the result concerns the selected normalization-and-temperature convention, and whether the sample size supports a stable comparison. Do not label normalized residuals as calibrated machine reliability or assume that normalization improves performance.
- [ ] Preserve the original failed hypervolume endpoint and the exploratory status of historical quality indicators.

**Deliverables:** `r6_scaling_runs.csv`, paired-effect summaries, acquisition-convention metadata, uncertainty plots and a concise outcome report.

**Done when:** the protocol can be traced to every result, both favourable and unfavourable effects are reported, and the original pipeline comparison is distinguished from the new experiment.

## A6-07. Optional: constraint-aware scalarized comparator

- [ ] Record explicit adoption or non-adoption before any additional runs. Declining this task does not leave either main validation task incomplete.
- [ ] If adopted, specify a constrained scalarized acquisition and verify its behavior rather than changing the existing unconstrained scalarized arm by name alone.
- [ ] Freeze weights, scales, constraint convention, initial designs, seeds, simulation budgets and statistical comparisons. Plan any additional multiplicity treatment before outcomes.
- [ ] Compare it with the relevant contemporaneous arms under matched conditions. Distinguish constraint-information effects from objective-representation effects.

**Done when:** adoption is documented and, if adopted, the declared comparison is executed and analyzed; otherwise the manuscript retains the explicit missing-comparator limitation. This item must not silently become a condition of closing I6-01 or I6-02.

## A6-08. Integrate the evidence without broadening claims beyond it

- [ ] Add a concise methods description and result for each completed validation workstream, with tables/figures linked to new evidence. Explain any unresolved or adverse findings.
- [ ] Keep measured refined settings, weighted population estimates, common-shift scenarios and new optimization trajectories distinct.
- [ ] Update the conclusion's numerical and normalization scope only where evidence warrants it. Do not infer converged global Pareto fronts, machine reliability or TDR engineering acceptance.
- [ ] Keep historical quality indicators exploratory. Any new predeclared indicator belongs to its own prospective experiment, without retroactive endpoint replacement.
- [ ] Preserve the author's prior prose dispositions, qualitative abstract convention, existing equations/data unless a specific change is justified, and deferred acknowledgments. Do not rerun broad humanization.
- [ ] Map new evidence, generators, input classes and checksums in `docs/paper/supplement/README.md`, `input_inventory.csv` and the supplement manifest, following their actual reproducibility needs.

**Done when:** every changed scientific statement has a precise evidence source and scope, and the new evidence is reproducible from its declared inputs.

## A6-09. Close the internal response and validation package

- [ ] Write `docs/paper/reviews/round6_internal_response.md`, mapping I6-01 to I6-04 to tasks, evidence and dispositions. Do not create responses attributed to external reviewers who did not submit round 6 reports.
- [ ] Produce `round6_revision_overview.md`, manuscript/code diffs against the frozen round 6 baseline and a changed-file/hash inventory. Preserve earlier round packages.
- [ ] Run meaningful tests for new code and appropriate local CI checks, including the package's 100% line-coverage requirement where applicable. Follow current resource constraints; explicitly record unrun checks and leave incomplete validation visible.
- [ ] Check documentation links, configuration/docs sync, supplement manifest and relevant regeneration paths. Existing regeneration claims must not be silently extended to analyses requiring new tracking or checkpoint records.
- [ ] Compile the current PRAB manuscript and inspect changed pages, tables, figure references and citations. If a separate review layout is generated, keep it separate from the default source format.
- [ ] Record each completed executed task using the next available five-digit summary filename and the required local commit format. Do not push or upload.

**Done when:** all required dispositions and validation receipts are traceable, optional A6-07 has a recorded decision, and the queue states any residual scientific uncertainty. Closing tasks is not journal acceptance and does not require a favourable experimental outcome.

## Execution order

1. Freeze A6-01 before producing new outcomes.
2. Follow the numerical branch A6-02 → A6-03 and the scaling branch A6-04 → A6-05 → A6-06 as resources allow. These are workstream dependencies, not a request to spawn agents or run jobs concurrently.
3. Decide separately whether to adopt A6-07.
4. Integrate A6-08 and close A6-09 after the required evidence is available.

The raw/normalized campaign comparison does not by itself resolve tracking convergence. Representative refinement does not establish that a normalized acquisition has better outcomes. Any stronger combined claim would need an additional design that tests both changes together.
