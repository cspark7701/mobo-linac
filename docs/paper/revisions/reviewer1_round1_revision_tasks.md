# Revision tasks for Reviewer 1 — round1

**Source report:** [reviewer1_round1_report.md](../reviews/reviewer1_round1_report.md)

**Reviewed manuscript revision:** `fe459f2c08ef5c1a992d65a0a26288c5926ae104`

**Recommendation:** Major revision; not acceptable in its current form.

**Task status:** All revision tasks are open. This file proposes work; the review has not implemented manuscript revisions or launched simulations.

## Priorities and execution boundaries

P0 tasks address scientific issues blocking reconsideration. P1 tasks supply the evidence and reporting needed to interpret the comparison. P2 covers presentation and submission preparation. These priorities express this reviewer's judgment, not a guarantee of acceptance after completion.

Start with analysis of existing evidence. Preserve every completed campaign, its original feasibility labels, reference point, precision, seeds, budgets, provenance and physical validation. New requirement profiles, methods or validation calculations must have separate labels and outputs. Record any additional simulation cost separately from the historical campaign budgets. Do not remove failed observations, reduce validation or change physics to make an acceptance gate pass.

Keep the author's existing presentation choices: a qualitative abstract without numbers, limitations in Discussion, two-dimensional scatter-only Pareto plots, no explicit seed values or absolute runtimes in the main text, and no reinstatement of the removed Data availability or nominal-rerun verification sections. Reproducibility information and internal validation artifacts can remain in Methods, an appendix or the repository.

## P0 — scientific issues

### R1. Establish KLS requirements and justify the search domain

**Maps to:** M2.

**Work:** Author/engineering input and existing-data analysis.

**Dependency:** Complete before interpreting any newly filtered fronts as KLS-accepted solutions.

- [ ] Identify the reference lattice revision and an authoritative basis for every diagnostic limit in Table 2.
- [ ] Distinguish the study's acceptance definition from the earlier JKPS and NAPAC definitions. Explain whether those requirements are superseded, deliberately relaxed for exploration or applicable to a different lattice/source.
- [ ] Reclassify existing observations under the published requirements in a separate derived report. Include relevant energy-spread limits and report empty accepted sets honestly. Preserve the original labels and tables as historical results.
- [ ] Explain the relation of exit-plane limits to downstream transport/booster acceptance, and distinguish local beam-quality optimization from demonstrated injection performance.
- [ ] Report the phase intervals in degrees, explain the chosen nominal phase convention and pair coupling, and justify the domain without relying on percentages of an arbitrary absolute phase.

**Acceptance evidence:** A cited requirements/conventions table, a source-linked reclassification report, and a clear statement of which physical acceptance claim the paper makes. No historical bounds or physics settings silently change. Further tracking is needed only if the adopted engineering claim requires new evidence.

### R2. Quantify feasible Pareto-set quality and convergence

**Maps to:** M1.

**Work:** Existing histories and measured objective values.

**Dependency:** R1 fixes the interpretation; define the metric/scaling protocol before comparing outcomes.

- [ ] Select complementary reference-point-independent measures, such as directional set coverage and normalized additive epsilon indicators.
- [ ] Document fixed objective scales, direction conventions, duplicate handling, feasibility filtering and treatment of missing/empty feasible sets.
- [ ] Compute per-run quality versus evaluation budget, with separate treatment of the common initialization and subsequent search.
- [ ] If using a distance to an empirical attainment set, describe its observed, finite nature and evaluate sensitivity to pooling/self-inclusion. Do not call it a known global front.
- [ ] Present paired run-level effects and uncertainty. Retain pooled scatter views as coverage summaries rather than the sole comparative evidence.
- [ ] Label the new analyses as exploratory revision analyses. Preserve the historical zero-hypervolume endpoint and its concise disclosure without restoring its uninformative panels.

**Acceptance evidence:** Reproducible metric definitions/code, per-run and aggregate tables/curves, and conclusions that distinguish feasible sampling, diversity and objective quality. More nondominated points alone are not sufficient.

### R4. Reconcile mathematical methods with the executed implementation

**Maps to:** M3 and M8.

**Work:** Code/configuration/checkpoint audit; no ASTRA needed.

- [ ] Correct the batch qLogNEHVI expression or identify it explicitly as schematic. Explain candidate-wise feasibility, baseline treatment and the implemented logarithmic approximations.
- [ ] Document the actual BoTorch/GPyTorch versions, MC sampler/sample count, feasibility temperature, hypervolume smoothing settings, baseline pruning and reference-update convention.
- [ ] Audit the outcome transform for small-variance/constant channels and the effective likelihood noise, including the inspected transmission-channel variance discrepancy.
- [ ] Report effective noise safeguards and GP fitting recovery, rather than only requested settings. Do not describe every channel as unit-variance standardized if it is mean-centered only.
- [ ] Verify whether all inspected late-stage settings are representative of the campaign history; distinguish confirmed settings from defaults inferred from the environment.

**Acceptance evidence:** A methods-to-configuration/checkpoint audit and a mathematically consistent manuscript description. The requested variance and effective variance are distinguishable, and no old campaign is relabelled as having used revised settings.

### R5. Assess dimensional constraint-smoothing sensitivity

**Maps to:** M3.

**Work:** Saved-surrogate analysis first; new tracking conditional.

**Dependency:** R4 establishes the exact recorded method.

- [ ] Express each residual and smoothing width in physical units and show the consequences of representing the same quantity in different units.
- [ ] Define a justified dimensionless or channel-scaled alternative if changing the method. Preserve the original SI-residual implementation as its own recorded variant.
- [ ] Compare acquisition behavior/proposals using saved representative surrogates under controlled random sampling and unchanged precision/optimization settings.
- [ ] Decide whether the paper will characterize the original implementation or evaluate a revised method. Report this choice transparently.
- [ ] If drawing physical performance conclusions for a revised method, plan and execute separately identified, appropriately matched campaigns. Offline proposal changes cannot establish new feasible yield or front quality.

**Acceptance evidence:** A reproducible sensitivity assessment and a defensible statement of what the results demonstrate. Any revised-method performance claim has actual tracking evidence; existing outcomes are not reused as evidence for an algorithm that was not run.

### R6. Establish source characterization and numerical fidelity

**Maps to:** M5.

**Work:** Existing source/trajectory analysis plus bounded new validation tracking.

**Dependency:** R1 defines physically relevant margins; select the validation set and tolerances before examining convergence outcomes.

- [ ] Describe source spatial/temporal distributions, charge, intrinsic emittance/momentum assumptions and the generation/diagnostic conventions needed to reproduce the model.
- [ ] Choose representative settings spanning a compromise, objective extremes and near-boundary feasibility; include a nominal reference if available.
- [ ] Define a bounded particle-number and relevant mesh/resolution study that preserves the physical source properties and field model.
- [ ] State accuracy tolerances for objective changes and constraint margins, then quantify whether observed trade-offs and feasibility classifications are stable.
- [ ] Save these validation calculations separately, retaining the original production records and accounting for additional evaluations explicitly.

**Acceptance evidence:** A numerical-convergence table/figure and a justified accuracy statement. Identical-input rerun agreement alone does not satisfy this task. A wholesale repetition of the production benchmark is not automatically required.

### R7. Establish novelty and a fair baseline scope

**Maps to:** M4.

**Work:** Literature/claim audit first; new controls conditional.

- [ ] Cite and discuss the separate NAPAC2025 WECN03 BO/MOGA publication, DOI `10.18429/JACoW-NAPAC2025-WECN03`. Do not describe it as an ICABU proceeding.
- [ ] Explain the added contribution and distinguish changes in controls, objectives, constraints and protocol from methodological advances.
- [ ] Either restrict the primary scalarized comparison to the specified balanced weighting or design an equal-total-budget multiweight scalarized baseline. Do not use the unequal-budget survey as a matched baseline.
- [ ] Evaluate whether a matched space-filling control is needed to substantiate adaptive-search efficiency. If used, predefine the design, budget and physical validation to match the comparison.
- [ ] Add a matched MOGA campaign only if claiming MOGA superiority or speedup; contextual literature comparison alone does not require it.

**Acceptance evidence:** A precise novelty statement, an honest baseline definition and any new control evidence required by the resulting claims. An application contribution is acceptable in principle; a new acquisition algorithm need not be invented.

## P1 — supporting analysis and scientific reporting

### R3. Use paired run-level inference and explain initialization

**Maps to:** M1 and M8.

**Work:** Existing data.

**Dependency:** R2 supplies the quality indicators.

- [ ] Compute paired effects for feasible sampling and any front-quality indicators, preserving complete method triplets when resampling initializations.
- [ ] Avoid treating adaptive evaluations or pooled observations as independent statistical replicates.
- [ ] Explain that five paired initial designs already contain a feasible point and distinguish initialization-driven first-feasible outcomes from acquisition-driven ones.
- [ ] Report uncertainty appropriate to the claims. A significance test is optional; unsupported significance language is not.

**Acceptance evidence:** Paired effect estimates/intervals, an explicit initialization account and consistency between the statistical analysis and abstract/conclusions.

### R8. Report physically interpretable optimized operating points

**Maps to:** M6.

**Work:** Existing evaluations/provenance, with additional tracking only if essential reference evidence is absent.

- [ ] Export stable identities, complete magnetic/RF parameter vectors, objectives and constraint margins for a useful compromise and representative extremes.
- [ ] Compare with the nominal reference setting under the same conventions when a valid reference evaluation exists.
- [ ] Use stored beam evolution or other diagnostics to support explanations of focusing/phasing changes and trade-offs. Distinguish observed association from demonstrated mechanism.
- [ ] Separate per-coordinate best values from one simultaneously achievable operating point.

**Acceptance evidence:** A compact reproducible operating-point table and a physical interpretation supported by measured simulation outputs. This is not a request to restore the removed verification tables or rerun-comparison figure.

### R9. Interpret robustness probabilistically and review the score

**Maps to:** M7.

**Work:** Existing perturbation records and summaries.

- [ ] Give design-specific binomial uncertainty for the reported success fractions, with the assumptions stated. Do not pool different operating points into one universal reliability estimate.
- [ ] Specify the physical perturbation channels, phase-pair correlations, distributions and candidate-selection rule.
- [ ] Define the signed margin normalization for every bound, including the two-sided energy window, and assess the interpretation of the minimum across differently normalized channels.
- [ ] Justify or remove the ad hoc composite score. If retained, explain values above one and how mean objective ratios can conceal changes in individual objectives.
- [ ] Report interpretable per-objective means/spreads or quantiles and limiting margins already available in the saved summaries.
- [ ] Keep the existing lattice-jitter scope unless broader claims are accompanied by broader testing. Test baseline representatives only if claiming comparative robustness superiority.

**Acceptance evidence:** Uncertainty-aware robustness reporting and an interpretable score or replacement, without silently changing historical scores or overstating reliability.

### R10. Assess surrogate adequacy from saved models

**Maps to:** M5.

**Work:** Existing observations/checkpoints; no new tracking initially.

- [ ] Calculate predictive diagnostics using an appropriate validation/leave-one-out approach for objectives and constraint channels.
- [ ] Examine behavior near relevant feasibility boundaries, not only global fit errors.
- [ ] Report the treatment of constant channels and cases where classification discrimination cannot be estimated from the observations.
- [ ] Relate fitting recovery and uncertainty/calibration limitations to the scope of the optimization conclusions.

**Acceptance evidence:** A concise model-diagnostics summary and reproducible analysis that supports, rather than assumes, surrogate adequacy.

### R11. Supply minimal reproduction details and relative computational cost

**Maps to:** M8.

**Work:** Existing configurations, environment records and timing metadata.

- [ ] Identify the code revision and input/executable identities, model/proposal settings and effective worker/concurrency policy.
- [ ] Provide a stable mapping to original campaign records and seed manifests without printing seed numbers in the main manuscript.
- [ ] Report relative cost ratios under the same computational conditions and explain modelling/acquisition versus tracking overhead. Absolute runtimes need not be added.
- [ ] Ensure the reproduction instructions regenerate the actual included tables and figures and distinguish current code defaults from executed campaign settings.

**Acceptance evidence:** A self-contained methods/appendix/repository reproduction path and a substantiated relative-speed statement. No new Data availability section or public upload is mandated by this checklist.

## P2 — presentation and submission preparation

### R12. Complete the tables, figures and editorial checks

**Maps to:** Minor comments 1–7.

- [ ] Use clearly feasible extrema in the main scalarization-case comparison, or label all-valid extrema unambiguously and move them to supporting material as appropriate.
- [ ] Replace Phase 1/2/3 development labels and unsupported operational-mode names with scientific algorithm/weighting labels.
- [ ] Improve visibility of the accepted region in the dense constraint plots, retaining the full distributions and shaded acceptance explanation.
- [ ] Replace software parameter strings in Table 6's caption with physical language and check the table at final print size.
- [ ] Verify the JINST numerical comparison against the full article's tracked results and stated conditions.
- [ ] Complete bibliographic metadata and funding/acknowledgments using author-verified information.
- [ ] Remove repeated explanations and keep paragraphs organized around physical or methodological arguments. Retain the qualitative abstract and the requested two-dimensional scatter plots.
- [ ] Build the JINST PDF, inspect all references/tables/figures and run focused manuscript/output consistency checks after artifact generation has finished.

**Acceptance evidence:** A complete submission draft with no placeholders, resolved references, legible graphics and claims supported by the revised analysis.

## Suggested work order and response document

1. Resolve R1, R4 and R7, and record the intended claim scope and any revised analysis protocols.
2. Complete existing-data work in R2/R3 and R8–R11; use it to define the smallest scientifically justified additions.
3. Complete the R5 sensitivity work and R6 numerical validation; execute new comparison campaigns only where the selected claim scope requires them.
4. Integrate the scientific results, complete R12 and prepare a response mapping every M/minor comment to a change, an artifact or a justified non-adoption.

For each task, retain the reviewed baseline, list affected files/results, state whether additional simulations were required and explain the effect on the paper's conclusions. Revision readiness means that the scientific concerns have evidence-based responses, not merely that all boxes have been checked.
