# Consolidated revision tasks — round1

**Reviewers:** Reviewer 1 and Reviewer 2

**Recommendation shared by both:** Major revision; the reviewed manuscript is not acceptable in its present form.

**Purpose:** One execution and response plan that merges overlapping requests, preserves reviewer-specific concerns and incorporates later author clarifications. Use this document as the working revision queue; the individual reviewer documents remain source records. This document does not implement revisions or authorize new simulation campaigns.

## Sources and current status

- [Reviewer 1 report](../reviews/reviewer1_round1_report.md) and [revision tasks](reviewer1_round1_revision_tasks.md).
- [Reviewer 2 revised report](../reviews/reviewer2_round1_report.md) and [revision tasks](reviewer2_round1_revision_tasks.md).
- [Task 220: convergence comment withdrawn](../../exec-plans/completed/TASK_00226_withdraw_convergence_review_comment.md) and [Task 221: convergence study already completed](../../exec-plans/completed/TASK_00227_record_completed_convergence_study.md).
- [Task 222: current Reviewer 2 filenames](../../exec-plans/completed/TASK_00229_match_reviewer2_document_names.md).

The reviewer documents assess manuscript revision `fe459f2`; this consolidation uses their current round1 versions, including Reviewer 2's later corrections. Reviewer 1's older request for a new numerical-convergence study is superseded by the author clarification recorded in Tasks 220–221. The author reports prior convergence work, but C09 closes with resolution correspondence and an explicit absence of a traceable numerical-error bound. Neither review's recommendation is thereby automatically resolved.

Task status is recorded within each section; unchecked items remain open. P0 identifies central scientific revisions, P1 supporting scientific analysis/documentation, and P2 presentation or response preparation. Work categories distinguish analysis of existing records, manuscript changes and conditional new tracking.

## Author-defined scope: MOBO, with published MOGA context

The author has confirmed that the MOGA simulation study has already been completed and published. This paper focuses on MOBO, with constraint-aware and unconstrained multi-objective BO compared against scalarized BO. **No new MOGA/NSGA-II optimization campaigns, larger-budget MOGA baselines or new ASTRA reevaluations of published MOGA settings are included in this revision plan.** Published MOGA results and any compatible evidence already available may be discussed as literature context; they do not form a new matched benchmark.

C12 requires an explicit statement of this scope in the manuscript Introduction. The response letters must explain why the reviewers' requests for new MOGA simulations are not adopted, without claiming that the requested simulations were performed or that reviewers have already accepted the scope decision. Other BO, space-filling and robustness calculations remain proposed tasks, not runs authorized by this document.

## Preserve the evidence and resolve conflicting requests explicitly

Keep the original campaign outputs, physical validation, seeds, budgets, precision, provenance, feasibility labels and reporting reference immutable. New classifications and post-hoc metrics belong in separate derived outputs; changed methods, domains or error models require separately identified runs. Do not replace historical results with outcomes from a method that was not actually run, discard awkward Pareto points, reduce physical validation or change physics merely to pass a gate.

| Issue | Source requests | Consolidated treatment |
|---|---|---|
| Numerical convergence | Reviewer 1 originally requested new resolution calculations; Reviewer 2 withdrew that request after author clarification. | Author-closed under C09: document published resolution correspondence and the missing numerical-error bound; no new campaign adopted. |
| Hypervolume | Reviewer 1 emphasizes reference-point-independent set comparisons; Reviewer 2 also requests post-hoc HV and sensitivity. | C03 retains both analysis requests, with new metadata and clear post-hoc labels. Preserve the original endpoint. Do not automatically restore the repetitive zero-HV panels removed by the author; decide main-text versus supporting placement from the usefulness of the new analysis. |
| Corrected acquisition and new baselines | Reviewer 2 explicitly requests reruns/new arms; Reviewer 1 permits narrower claims in some cases. | C06–C07 retain the BO and space-filling baseline requests. New MOGA/NSGA-II simulations are excluded by the author-defined scope, and that non-adoption must be explained in the response. New performance claims for changed BO methods still require new evidence. |
| MOGA comparison | Reviewer 2 requests new NSGA-II/MOGA benchmarks and reevaluation of a published MOGA setting. | The MOGA study is already published. Cite and discuss those results only; do not schedule new MOGA-related tracking. State the MOBO focus in the manuscript and explain this scope decision to the reviewers. |
| Robustness scope | Reviewer 2 requests broader errors; Reviewer 1 accepts a restricted claim with explicit limits. | C10 separates improvements possible from current records from the proposed expanded tests. Broader tests remain an unresolved request unless completed or addressed by a reasoned response. |
| Numbers in the abstract | Reviewer 2 requests jitter amplitudes/sample counts; the author explicitly wants no numbers in the abstract. | Keep the abstract qualitative and place quantitative conditions in Methods/Results/captions. Qualify or remove unsupported abstract claims. Explain this response rather than silently ignoring the request. |
| Absolute runtime and seed values | Reviewer 2 requests explicit values; the author excludes them from the main text. | C13 uses relative cost ratios and overhead analysis. Stable run identities and seed mappings remain in the reproducibility manifest. |
| Data availability and ICABU citation | Reviewer 2 requests an availability statement/DOI and an ICABU citation; the author removed that section and confirmed presentation-only ICABU work. | Supply reproducibility information without restoring the removed section or inventing a DOI/proceeding. A verified presentation reference is possible; the separate published NAPAC paper must be distinguished. |
| Figure numbering | Some Reviewer 2 references use older figure numbers. | Address the scientific content through current figure labels/files, not obsolete numbers. Existing Pareto Figures 2 and 5 remain scatter-only; the removed nominal-verification figure is not to be restored. |

These are proposed response dispositions consistent with the author's instructions, not assertions that either reviewer has accepted a departure from their request.

## Consolidated work queue

| ID | Priority | Workstream | Work category | Main dependencies |
|---|---|---|---|---|
| C01 | P0 | KLS acceptance requirements and objective definition | Author/source clarification; existing-data analysis | None |
| C02 | P0 | Physical RF-phase domain and phase convention | Existing evidence; conditional targeted tracking/reruns | C01 |
| C03 | P0 | Pareto quality and sample-efficiency metrics | Existing histories | C01; metric protocol fixed first |
| C04 | P1 | Paired statistical inference and initialization | Existing histories | C03 |
| C05 | P0 | Acquisition equation, effective noise and reference audit | Code/configuration/checkpoint analysis | None |
| C06 | P0 | Constraint-smoothing sensitivity and revised-method evidence | Offline analysis; conditional new campaigns | C05; C01–C02 for any new domain |
| C07 | P0 | Fair BO and space-filling baselines | Protocol decision; conditional new BO/control campaigns | C01–C02, C05–C06 |
| C08 | P1 | Optimized settings, source description and beam physics | Existing diagnostics; conditional targeted studies | C01–C02 |
| C09 | P1 | Cite and report completed numerical convergence | Documentation; underlying study already done | Existing study/source supplied |
| C10 | P0 | Robustness uncertainty, score and proposed error extensions | Existing records; conditional expanded tracking | C01, C08; protocol before new tests |
| C11 | P1 | Surrogate validation and constant-channel handling | Existing models and observations | C05 |
| C12 | P0 | MOBO scope and published MOGA context | Manuscript and literature/available-record analysis only | C01–C02, C08 |
| C13 | P1 | Reproducibility and relative computational cost | Existing metadata and timings | C05, C07 |
| C14 | P2 | Scientific tables and units | Presentation/generator changes | C01, C03, C10 |
| C15 | P2 | Consistent figures and survey placement | Presentation/generator changes | C03, C08, C10 |
| C16 | P2 | Prose, abstract and submission front matter | Editorial/author input | Scientific tasks complete |
| C17 | P2 | Validation and point-by-point response | Documentation and focused checks | All adopted revisions |

### C01. Establish the accepted KLS-reference problem

**Status:** Completed for the explicitly bounded production-model comparison. The official October 2025 KLS TDR supplies the engineering reference; [C01 evidence](evidence/c01_acceptance.md) compares its requirements and reclassifies archived data. The production profile is not TDR-equivalent, and full machine acceptance is not claimed.

**Sources:** Reviewer 1 M2/R1; Reviewer 2 M4/R6 and minor 12/R14.

- [x] Identify the lattice/design revision and the current engineering basis for each size, divergence, bunch-length, mean-energy and transmission limit.
- [x] Define the energy-spread objective precisely: total RMS, correlated/chirp-containing or uncorrelated/slice quantity; justify its relevance to booster/transport acceptance.
- [x] State the eight inequalities explicitly, including the two sides of the mean-energy interval.
- [x] Compare the present requirements with the cited JKPS/NAPAC requirements, including any energy-spread cutoff, and explain whether differences are deliberate, superseded or design-specific.
- [x] Reclassify existing observations under relevant published profiles in separate derived outputs, using consistent geometric/normalized-emittance and energy-spread conventions. Preserve original labels and report empty accepted sets honestly.

**Done when:** A cited requirements/conventions table and reclassification summary support a clearly bounded physical acceptance claim. Mathematical feasibility is not equated automatically with demonstrated KLS injection performance.

### C02. Justify phase windows in physical units

**Status:** Closed by author scope decision (2026-10-26), with limitations retained. The author closes C02 with the historical absolute-phase domain retained. No calibrated crest, engineering tolerance or alternative-domain ranking is claimed. This is a reasoned non-adoption of the remaining validation request, not evidence that the missing validation has been performed.

**Sources:** Reviewer 1 M2/R1; Reviewer 2 M2/R3.

- [ ] **Not adopted in this revision:** Establish the crest or other chosen physical phase reference for the gun and structure pairs from existing evidence or a separately planned scan.
- [ ] **Not adopted in this revision:** Report nominal and representative phases relative to that reference and justify each interval in degrees, including why phases are coupled within each pair.
- [x] Assess the effect of the broad ACC3/4 domain. A restricted-data reanalysis can describe sampled coverage but cannot, by itself, demonstrate how an adaptive algorithm would behave when rerun in a different domain.
- [ ] **Not adopted in this revision:** If a revised domain is adopted, define the matched rerun protocol before execution. Keep historical bounds and campaigns available under their original definitions.

**Original scientific completion criterion (not claimed satisfied):** The intervals have a physical interpretation independent of an arbitrary phase origin, and any domain-sensitivity claim is supported by the appropriate analysis or new tracking.

### C03. Measure feasible-front quality and convergence

**Status:** Completed. [C03 report](evidence/c03_report.md) and reproducible per-run summaries cover epsilon, IGD+, directional coverage, reference sensitivity and attainment. Main text and supporting appendix identify the exploratory scope and empirical-reference bias.

**Sources:** Reviewer 1 M1/R2; Reviewer 2 M1/R1 and minor 5/R12.

- [x] Fix objective scales, minimization conventions, duplicate policy, empty-set handling and evaluation checkpoints before producing comparative summaries.
- [x] Add complementary set-quality indicators, such as directional coverage and normalized additive epsilon, with per-run histories rather than pooled cardinality alone.
- [x] Address Reviewer 2's post-hoc feasible-HV request using separate metadata and several justified reference choices. A pooled-nadir reference is data-derived, not automatically an engineering requirement; example bounds suggested by a reviewer are not approved machine limits.
- [x] If using IGD+, document its empirical reference set, finite coverage and possible self-inclusion bias. IGD+ avoids an HV reference point but is not reference-free: it still requires a reference set.
- [x] Add empirical attainment summaries and sample-efficiency curves, preserving all feasible nondominated observations even when some do not contribute to a selected indicator.
- [x] Label new analyses as post hoc/exploratory. Preserve the original reference and concise zero-endpoint disclosure; place useful new results in the main text or supporting material without resurrecting redundant historical plots.

**Done when:** Reproducible per-run metrics, histories and sensitivity results distinguish feasible sampling, objective quality and diversity. Counts and visual density do not substitute for quality.

### C04. Use the paired design and interpret initialization correctly

**Status:** Completed. [C04 report](evidence/c04_report.md) gives paired effects, pointwise bootstrap intervals, exact signed-rank tests and a twelve-comparison Holm family. Initialization is separated and manuscript claims reflect endpoint-dependent evidence.

**Sources:** Reviewer 1 M1/M8, R2/R3; Reviewer 2 M3c/M5, R4/R7.

- [x] Compute paired method effects with run-level uncertainty, resampling matched groups rather than individual adaptive evaluations.
- [x] Resolve Reviewer 2's request for paired tests and multiplicity correction. State the comparison family, handle ties/zero differences correctly, and avoid unsupported significance claims; do not manufacture a test for an all-zero endpoint.
- [x] Explain that five common initial designs already contain a feasible point. Remove or qualify the first-feasible row and distinguish initialization from post-initialization search without treating a conditional subgroup as an unbiased new benchmark.
- [x] Align abstract/conclusion statements with the supported comparisons and distinguish pooled coverage from a typical run.

**Done when:** Comparative effects have appropriate paired evidence and the first-feasible metric is not credited to acquisition when it arose during shared initialization.

### C05. Reconcile the acquisition and GP description with execution

**Status:** Completed. [C05 audit](evidence/c05_report.md) verifies all saved model/proposal artifacts and distinguishes directly recorded evidence from reconstructed library defaults. Manuscript Methods corrected; unsaved sampler draws/pruned subsets are disclosed.

**Sources:** Reviewer 1 M3/M8, R4; Reviewer 2 M3a, minor 8, R2/R10 and part of R15.

- [x] Correct the batch acquisition equation or label it schematic, explaining candidate-wise constraints, baseline feasibility and logarithmic relaxations.
- [x] Audit executed sampler/sample counts, pruning, smoothing parameters, precision, fitting recovery and effective noise against saved configurations/artifacts.
- [x] Report mean-only handling of constant/small-variance channels and distinguish requested training variance from effective likelihood floors, including the inspected transmission example.
- [x] Explain the acquisition reference's observation basis, inclusion of infeasible observations, negated/model-space calculation and update rule. Keep it distinct from reporting references.
- [x] Calculate transition behavior using the actual archived feasibility function. Reviewer 2's illustrative ordinary-logistic values must not be assumed exact for BoTorch's fat-tailed indicator.
- [x] Count models and inequalities correctly: independent objective and diagnostic outputs are not one GP per inequality; the shared energy channel supplies two bounds.

**Done when:** A traceable methods/settings audit reproduces what was executed and distinguishes implementation facts from inferred defaults or reviewer illustrations.

### C06. Assess scaling and obtain evidence for any corrected method

**Status:** Completed for author-approved offline sensitivity and narrower historical-method claims. [C06 report](evidence/c06_report.md) quantifies unit-dependent ranks and verifies dimensionless unit invariance. The requested corrected primary arm is explicitly not adopted and has no measured physical-performance claim.

**Sources:** Reviewer 1 M3/R5; Reviewer 2 M3a/R2.

- [x] Quantify original per-channel smoothing widths in physical units and test equivalent unit representations using saved representative surrogates.
- [x] Define a justified dimensionless residual or channel-specific scale/temperature if revising the acquisition. Keep the original behavior reproducible as a separate variant.
- [x] Separate offline acquisition/proposal sensitivity from measured physical performance.
- [x] Address Reviewer 2's explicit request for a corrected constraint-aware primary arm. If undertaken, match initial designs, budgets, precision and physical validation, and disclose original versus corrected results.
- [x] If retaining the original method with narrower claims instead, provide a reasoned response and quantified sensitivity; do not mark the requested rerun satisfied by wording alone.

**Done when:** Scaling and interpretation are defensible, and every performance claim about a revised method has corresponding new evaluation evidence. Do not relabel historical outcomes as corrected-method results.

### C07. Define and evaluate the necessary BO and space-filling baselines

**Status:** Closed by explicit author choice to retain existing simulations. [C07 report](evidence/c07_report.md) and comparison matrix distinguish measured arms from unrun controls. New constrained-scalarized, Sobol and MOGA arms are not adopted; their physical performance is not claimed.

**Sources:** Reviewer 1 M4/R7; Reviewer 2 M3b/R4.

- [x] Specify a comparison matrix separating constraint awareness from multi-objective acquisition and fixing domain, initial design, total budget, batch size, fidelity and evaluation accounting.
- [x] Address the requested constrained scalarized qLogNEI baseline and matched Sobol/random-search control.
- [x] Limit the balanced scalarized baseline to that specified weighting, or add an equal-total-budget multiweight allocation. The five-times-larger survey is not the matched control.
- [x] Record the author decision excluding new MOGA/NSGA-II runs, including low-budget and larger-budget benchmark arms. Remove unsupported claims of a newly demonstrated MOGA speedup or superiority and explain the non-adoption in the reviewer responses.
- [x] Decide which historical arms remain comparable after any domain, model or physics changes. Do not pair results from incompatible problem definitions merely because their seed labels match.

**Scope disposition:** The BO comparison and any adopted space-filling controls have appropriate matched evidence, and the response explains the exclusion of MOGA simulations. No matched MOGA performance claim is made from a literature-only comparison. Any new BO/control campaigns are separately planned; this document launches none.

### C08. Explain the accelerator settings and trade-off mechanisms

**Status:** Completed within existing-evidence scope; [C08 report](evidence/c08_report.md) supplies source moments, full representative settings, geometry, trajectories and constraint activity. Generator provenance and isolated causal mechanisms are explicitly unestablished.

**Sources:** Reviewer 1 M2/M5/M6, R1/R6/R8; Reviewer 2 M4/R6 and minor 14/R14.

- [x] Describe source spatial/temporal distributions, charge, intrinsic-emittance/momentum assumptions and distribution-generation/diagnostic conventions.
- [x] Give complete parameter vectors, objectives and margins for reproducibly identified compromises and extremes; compare with an evaluated nominal reference where available.
- [x] Explain horizontal/vertical emittance asymmetry and phasing effects using existing trajectories, source checks and sensitivity evidence. GP ARD lengths are surrogate diagnostics, not causal proof by themselves.
- [x] Check actual quadrupole positions before adopting Reviewer 2's conditional downstream-of-linac explanation. Add geometry in the schematic or an appendix instead of restoring the sentence the author removed.
- [x] Plan isolated diagnostic counterfactuals only where existing evidence is insufficient. Changes such as quadrupoles off or altered solver transition are labelled mechanism studies, not replacements for production physics or a new mandatory resolution study.
- [x] State which constraints were inactive in the observed sample, without asserting they are inactive throughout the whole design domain, and clarify representative uniqueness and selection.

**Done when:** The optimized settings have an engineering interpretation supported by simulation evidence, not only an objective-space label. Nominal-rerun verification tables/figures need not be restored.

### C09. Document the completed numerical-convergence study

**Sources:** Reviewer 1 M5/R6, superseded in part; Reviewer 2 minor 16/R15; Tasks 220–221.

**Status:** Closed by author scope decision (2026-10-26), with limitations retained. The author closes C09 with the cited JINST resolution correspondence and an explicit absence of a traceable numerical-error bound. No repeat convergence campaign or full solver-equivalence claim is adopted. This is a reasoned non-adoption of the remaining validation request, not evidence that the missing validation has been performed.

- [ ] **Not adopted in this revision:** Locate and cite the previous injector study and the specific convergence evidence.
- [ ] **Not adopted in this revision:** Document equivalence of the present macroparticle, space-charge-grid, transition and image-charge settings to those validated previously.
- [ ] **Not adopted in this revision:** Quote the existing residual objective uncertainty and compare it with reported method differences and feasibility margins. If values cannot yet be located, obtain the source information rather than inventing an uncertainty estimate.
- [x] Revise the numerical-resolution discussion consistently and explain the relation of deterministic fixed-noise regularization to residual numerical uncertainty, keeping effective library floors separate under C05.

**Original scientific completion criterion (not claimed satisfied):** Readers can locate the prior validation and judge the accuracy relevant to this study. The older Reviewer 1 request is answered with the later clarification and evidence, not another convergence campaign. Source characterization and surrogate validation remain separate open tasks.

### C10. Make robustness results interpretable and resolve the expanded-error request

**Status:** Completed for the explicitly retained lattice-only scope. [C10 report](evidence/c10_report.md) independently audits both assessments, reports per-design intervals and component statistics, and records non-adoption of broader error-model/scan requests without claiming them performed.

**Sources:** Reviewer 1 M7/R9; Reviewer 2 M6/R5 and minor 11/14.

- [x] Report design-specific binomial uncertainty, objective degradation/spreads and limiting margins from existing records; do not pool heterogeneous settings into one universal reliability estimate.
- [x] Define margin normalization, especially the two-sided energy band, and audit the composite score at full precision. Identical rounded scores are not proof of a bug; verify calculation, clipping and rounding before changing anything.
- [x] Justify the score or replace its presentation with interpretable components. Preserve historical scores and explain any new convention separately.
- [x] Identify selected runs through stable identities/manifest mappings, state phase-pair correlations and clarify the six-times-fifty accounting and distinct parameter vectors.
- [x] Address Reviewer 2's explicit RF-amplitude/JKPS-error-model and alignment requests. If added, validate parameter mappings and use isolated outputs with the full physical checks. Source jitter requires a physically valid source-generation model.
- [x] Resolve the tolerance-scan ambiguity: Reviewer 2's report and task list express amplitudes differently. Fix a table of physical standard deviations and corresponding multipliers before any new run; do not infer the intended levels silently.
- [x] Decide whether larger samples or baseline-representative tests are needed for the chosen reliability/comparative claims. If keeping the narrower existing scope, justify the departure from Reviewer 2's request explicitly.

**Done when:** Reliability, score meaning and tested error coverage are clear. Wider robustness claims have wider-model evidence, and numeric conditions remain in Methods/Results rather than the abstract.

### C11. Validate the surrogate models

**Status:** Completed. [C11 report](evidence/c11_report.md) validates unseen next batches from all saved models, reports undercoverage and boundary errors, and distinguishes constant transmission from validated loss discrimination.

**Sources:** Reviewer 1 M5/R10.

- [x] Use saved observations/models for suitable leave-one-out or predictive validation and uncertainty checks for objectives and diagnostics.
- [x] Examine performance near relevant constraint boundaries and report fitting recovery.
- [x] Treat constant transmission explicitly; discrimination cannot be estimated from a channel with no observed failures.

**Done when:** A reproducible diagnostics summary supports the surrogate interpretation and identifies unassessed calibration. This is model validation, not a request to repeat the completed ASTRA convergence study.

### C12. State the MOBO scope and use published MOGA results as context

**Sources:** Reviewer 1 M4/R7 and minor 5; Reviewer 2 M7/R8 and minor 9; subsequent author decision excluding MOGA simulations.

**Scope decision:** The earlier MOGA simulation study is complete and published. No new MOGA/NSGA-II campaigns or MOGA-setting reevaluation runs are required or scheduled. Manuscript and literature work completed; see [C12 evidence](evidence/c12_prior_work.md) and the C12 portions of both reviewer response drafts.

- [x] State explicitly in the Introduction that the present study focuses on MOBO, comparing its constraint-aware and unconstrained variants with scalarized BO, building on the previously published MOGA injector study.
- [x] Cite the JINST MOGA optimization and JKPS error-analysis papers, and retain the separate published NAPAC2025 WECN03 BO/MOGA work when positioning the BO contribution. Do not confuse the NAPAC paper with the ICABU presentations.
- [x] Verify the previously published values and comparison conditions from the literature or existing records, including controls, source model, objective definitions and acceptance limits. Do not perform fresh ASTRA tracking for this MOGA comparison.
- [x] Interpret cross-paper differences as contextual trade-offs, with explicit differences in conditions. Do not claim matched-budget MOGA superiority, speedup or new reproduction of the published optimum.
- [x] Explain the exclusion of the requested new MOGA benchmarks and published-setting reevaluation in both response letters. Preserve the original reviewer requests as records; mark their simulation branches not adopted under the author-defined paper scope.

Suggested manuscript wording for the revision:

> The injector-linac design has previously been optimized using MOGA, and its error sensitivity has been examined in a separate published study. The present work focuses on multi-objective Bayesian optimization, comparing constraint-aware and unconstrained multi-objective BO with scalarized BO. The published MOGA results provide design context for interpreting the observed trade-offs.

Add the appropriate existing JINST and JKPS citations to this passage when editing the manuscript.

**Done when:** The manuscript clearly states the MOBO focus, accurately cites the completed MOGA work and limits the MOGA comparison to published or already available evidence. The revision queue contains no new MOGA-related simulation work, and the responses give the reasoned non-adoption.

### C13. Substantiate reproducibility and relative cost

**Status:** Completed. [C13 report](evidence/c13_report.md) records actual execution settings, code/input identities, paired relative duration and overlap-aware evaluation intervals. Unmeasured fitting/acquisition components remain combined.

**Sources:** Reviewer 1 M8/R11; Reviewer 2 minor 7/9, R9 and part of R16.

- [x] Record code/input/executable identities and actual model, proposal, device and worker/concurrency settings, reconciling CLI overrides with saved configurations.
- [x] Keep raw seed mappings in a reproducibility manifest and provide stable references to the campaigns and representative settings.
- [x] Quantify relative computational-cost ratios and modelling/acquisition versus tracking overhead where supported by timing records. Do not treat sums of overlapping ASTRA worker runtimes as elapsed fractions.
- [x] Remove or qualify speed claims if the available timings do not support the comparison. Keep absolute runtimes out of the main text as instructed by the author.
- [x] Provide sufficient reproduction information through Methods, an appendix or repository instructions without restoring the removed Data availability section or inventing a public archive identifier.

**Done when:** The reported configuration and relative-speed conclusions are reproducible from retained evidence.

### C14. Make the tables scientific and consistent

**Status:** Completed. [C14 report](evidence/c14_report.md) documents feasible-only extrema, method/weighting names, consistent units and readable table layouts.

**Sources:** Reviewer 1 minor 1/2/4/6, R12; Reviewer 2 minor 1/2/13/15, R11/R14/R16.

- [x] Use feasible extrema consistently in the main comparison, or explicitly separate all-valid extrema. Keep raw observations unchanged.
- [x] Replace Phase 1/2/3 labels and unsupported operational-archetype/FEL-mode names with method and weighting names.
- [x] Remove stale reference-point wording where it no longer describes a reported metric.
- [x] Use consistent emittance/energy units and human-readable physical descriptions in captions.
- [x] Improve print-size legibility with suitable table layout rather than excessive resizing, and include the revised robustness quantities from C10.

**Done when:** Every table clearly identifies its population, units and physical interpretation.

### C15. Improve figures and the survey presentation

**Status:** Completed. [C15 report](evidence/c15_report.md) documents independent survey curves, consistent vector figures, acceptance zooms, explicit constant-transmission coverage and appendix survey placement.

**Sources:** Reviewer 1 minor 3/7, R12; Reviewer 2 minor 3–6, R12/R13 and parts of R1/R6.

- [x] Fix the survey feasibility plot so independent weighting campaigns do not appear to be one sequential 880-evaluation run; use separate curves or an appropriately defined summary.
- [x] Keep method colors/markers consistent, remove embedded manuscript titles and use vector output where practical.
- [x] Add accepted-region zooms or density views to crowded constraint panels while retaining the complete distributions and shaded-limit explanation.
- [x] Address the constant-transmission panel without silently removing coverage of a required diagnostic. A compact annotation/supporting view can retain that information; an energy-spread-versus-energy panel must not invent an energy-spread constraint absent from the selected requirements.
- [x] Add the attainment/representative information justified by C03/C08 and use suitable shared axes. Keep Pareto views two-dimensional and scatter-only, without smooth front curves.
- [x] Shorten the descriptive unequal-budget survey or move detail to an appendix/supporting material, retaining all-case artifacts and the budget qualification.

**Done when:** Figures communicate constraint status and trade-offs without misleading continuity, density or algorithm identity, and every original case remains available.

### C16. Consolidate prose and finish front matter

**Status:** Editing completed; [C16 report](evidence/c16_report.md) records scientific prose and verified presentation/statistical citations. Funding/acknowledgments are deferred explicitly to the author; finalfalse remains set and submission readiness is not claimed.

**Sources:** Reviewer 1 minor 6/7, R12; Reviewer 2 minor 9–16, R13/R14/R16 and abstract requests in R5/R9.

- [x] Keep the abstract qualitative, without numerical values or spelled-out counts, and remove or qualify claims not supported by the revised study.
- [x] State limitations coherently in Discussion; place most plotting conventions in captions and avoid repetitive audit/provenance language or padding paragraphs merely to increase length.
- [x] Center the motivation on storage-ring injection and the accepted KLS-reference problem rather than implying demonstrated FEL/UED operation.
- [x] Add only a verified ICABU presentation reference if available; do not invent a proceeding. Complete verified bibliography metadata; funding/acknowledgments remain explicitly author-deferred.
- [ ] **Author-deferred:** Resolve funding/acknowledgment placeholder before submission. Set the final-build switch only when appropriate. Assess the harmless upstream hyperref warning without unnecessarily modifying publisher-owned style files.

**Done when:** The manuscript is complete, coherent and consistent with the author's presentation instructions. Conflicting reviewer requests receive explicit responses rather than being silently marked complete.

### C17. Validate the revision and prepare both response letters

**Status:** Completed for the adopted revision scope. See [final overview](round1_revision_overview.md); scientific limitations and author-deferred funding remain explicit.

**Sources:** Both reports; Reviewer 1 R12; Reviewer 2 R17.

- [x] Prepare `reviewer1_round1_response.md` and `reviewer2_round1_response.md` under `docs/paper/reviews/`, mapping every major/minor comment to C tasks, manuscript changes, evidence or a reasoned non-adoption.
- [x] Include the completed-convergence clarification in the response to the older Reviewer 1 request. Explain the author decision not to adopt Reviewer 2's new MOGA/NSGA-II benchmarks and MOGA-setting reevaluation because the current paper focuses on MOBO and the MOGA work is already published. Do not imply reviewer withdrawal or agreement; other BO/broader-robustness requests have explicit author-directed non-adoption dispositions.
- [x] Produce the requested revision diff against the reviewed manuscript baseline, separating new code/results from narrative edits.
- [x] Regenerate affected assets, build JINST, inspect the PDF and run focused checks after artifact generation finishes. Verify preserved historical evidence and traceability of new derived outputs and simulation variants.

**Done when:** Both reviewers' comments are accounted for, the manuscript/figures are consistent and the remaining disagreements are visible to the author/editor. Completing a checklist is not a guarantee of journal acceptance.

## Coverage of the original task lists

The mappings below retain every original task group. A mapping records where a request is handled; it does not mean that the request is already fulfilled.

| Reviewer 1 task | Consolidated tasks |
|---|---|
| R1 | C01, C02, C08 |
| R2 | C03, C04 |
| R3 | C04 |
| R4 | C05 |
| R5 | C06 |
| R6 | C08, C09; new convergence campaign superseded by Tasks 220–221 |
| R7 | C07, C12 |
| R8 | C08 |
| R9 | C10 |
| R10 | C11 |
| R11 | C13 |
| R12 | C14, C15, C16, C17 |

| Reviewer 2 task | Consolidated tasks |
|---|---|
| R1 | C03, C04, C15 |
| R2 | C05, C06 |
| R3 | C02 |
| R4 | C04, C07; MOGA/NSGA-II simulation branch not adopted |
| R5 | C10, C16 |
| R6 | C01, C08, C15 |
| R7 | C04 |
| R8 | C12; new MOGA-setting reevaluation not adopted |
| R9 | C13, C16 |
| R10 | C05 |
| R11 | C14 |
| R12 | C15 |
| R13 | C15, C16 |
| R14 | C01, C08, C14, C16 |
| R15 | C05, C09; author-closed with numerical-error-bound limitation |
| R16 | C13, C14, C16 |
| R17 | C17 |

## Suggested sequence

1. Establish the physical definitions, recorded-method audit and prior-work context: C01, C02, C05, C09, C12.
2. Complete analysis possible from existing histories/models: C03, C04, C08, C10's statistical/score audit, C11 and C13. Freeze any new metric/experiment protocols before interpreting comparative results.
3. Resolve the remaining BO/validation scope decisions and undertake only justified, separately planned additions under C02, C06, C07, C08 or C10. Do not run new MOGA/NSGA-II simulations or published-MOGA-setting reevaluations, and do not rerun the completed convergence study. C12 is manuscript/literature work only.
4. Integrate the results, revise tables/figures/prose under C14–C16 and finish both point-by-point responses under C17.
