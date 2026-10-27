# Reviewer 1 report — round2

**Manuscript:** Multi-objective Bayesian optimization of a 200 MeV electron injector linac for the Korea Light Source

**Date:** 27 October 2026

**Review type:** Internal scientific pre-submission assessment in the Reviewer 1 role; not an external journal decision

**Reviewed revision:** `9077875be22358b68c9a090994f7a3718484720a`

**Version:** Generic article, 30-page PDF with keywords and contents

**Materials:** Manuscript, included tables and selected rendered figures, round1 report/response, C01–C16 supporting reports, selected derived CSV records and paired-analysis implementation.

## Recommendation to the editor

**Major revision; not acceptable in its present form.** The manuscript is substantially improved and has a potentially publishable application-focused contribution: a paired, budget-matched comparison of three specified optimization implementations on a fixed injector model. It now supports a descriptive feasible-sampling advantage under its production profile, and a more qualified comparison of empirical Pareto-set quality. I do not recommend rejection solely because the study uses simulations, because there is no new MOGA campaign, or because it does not prove global Pareto optimality.

The remaining concerns are substantive: physical acceptance and numerical resolution must be connected more directly to the conclusions; the unit-sensitive constrained acquisition must be treated as the actual tested method throughout; and the statistical interpretation of quality indicators sharing a data-derived reference needs further care. Documentation of a limitation is valuable but does not itself validate the affected scientific claim. Conversely, an administrative decision to close a revision task does not imply reviewer acceptance of the missing evidence.

A defensible revision can retain the current campaigns and focus the article on an empirical computational benchmark. No blanket production rerun, MOGA comparison, new algorithm arm or expanded error campaign is requested here. Stronger claims about engineering-ready settings, numerically resolved improvements or the performance of a corrected acquisition would require additional evidence. Acceptance after narrowing the scope remains an editorial judgment, not something guaranteed by completing a task list.

## Progress since round1

| Round1 issue | Round2 assessment |
|---|---|
| M1: Pareto quality and initialization | Substantially addressed: per-run epsilon, IGD+, directional coverage, histories, attainment and an initialization-separated feasible fraction are supplied. The empirical reference is properly distinguished from the unknown true front. Remaining inferential qualifications are in M4 below. |
| M2: Physical acceptance and domain | Source identification and transparency improved substantially through the official TDR comparison and explicit absolute phase intervals. Engineering relevance and small acceptance margins still need focused treatment; see M1/M2. No calibrated-crest claim is now made. |
| M3: Acquisition and noise | The implementation is much more accurately documented, including eight sampled inequality weights, effective noise floors and baseline handling. Offline unit sensitivity confirms the concern rather than removing it; see M3. |
| M4: Novelty and baselines | Adequately addressed for a comparison of the three recorded configurations. The NAPAC work is cited, and the MOGA, unequal-budget survey and missing constrained-scalarized/Sobol comparisons are appropriately bounded. I do not request these new arms for the narrowed study. |
| M5: Numerical fidelity and surrogates | Chronological prediction checks are a meaningful improvement. A traceable tracking-refinement bound remains absent. These are separate issues; see M2 and M5. |
| M6: Settings and interpretation | Six distinct control vectors, objective values, source moments and a cautious transport interpretation are now supplied. Avoid calling ideal-point proximity a demonstrated knee; see minor comments. |
| M7: Robustness | Adequately addressed within the explicit lattice-only scope: design-specific binomial bounds, correlated cavity errors, common random numbers and component statistics replace an opaque score ranking. No broader reliability or comparative robustness claim is supported. |
| M8: Inference and reproduction | Pairing, elapsed-cost accounting and actual execution details are much improved. The paper still needs a reader-resolvable supporting-package identity; see M4/M6. |

The feasible-only survey tables, independent weighting histories and accepted-region insets also resolve important presentation defects. Scatter-only Pareto projections remain appropriate.

## Major comments

### M1. Make the scientific target and acceptance population consistent throughout

**Locations:** Abstract; sections 2.2, 5.2, 6 and 7; Table 2 and Figure 4. **Action:** R2-01.

The manuscript now explicitly states that the production thresholds are not justified replacements for the TDR requirements. That is scientifically preferable to retroactive relabeling. However, the title, abstract and conclusions still foreground optimization of the KLS injector, while the demonstrated comparison primarily concerns a broader computational acceptance region. The positive abstract should identify this as a fixed reference-model comparison under a specified study acceptance profile, without adding numbers or a limitations paragraph. The conclusions should state what engineering conclusion can actually be drawn from the TDR check.

The archived primary totals are 648, 251 and 200 production-feasible observations, but only two constrained observations pass the checked TDR optimization inequalities; neither baseline has one. These two observations occur in two different matched runs. This is observed coverage, not evidence that two versus zero establishes a statistically demonstrated method advantage under the TDR profile. It also does not establish full acceptance, and the separately chosen lattice-jitter representatives must not be confused with these two candidates.

Provide a compact primary-results table or appendix entry identifying the two candidates with objectives and signed physical margins, and make it available from the article. The existing C01 CSV is sufficient for this reporting step. Specify that the counts concern the 4,800 **primary** evaluations: the current phrase “all archived observations” is too broad because the study also contains survey and jitter records. A new optimization campaign under TDR constraints is not required for the restricted computational claim.

### M2. Resolve the status of numerical accuracy at the scientifically relevant margins

**Locations:** Section 2.1, section 6.2, TDR reclassification and selected settings. **Action:** R2-02.

The revision correctly separates deterministic reproducibility, GP regularization and tracking-discretization uncertainty. It also correctly states that the cited JINST resolution settings do not supply a traceable refinement bound or establish the complete solver transition. These admissions resolve the reporting discrepancy but leave the physical validation question open.

This matters concretely. From the retained TDR-candidate diagnostics, the two horizontal-size margins are approximately 2.47 and 8.93 micrometres; the bunch-length margins are 8.16 and 7.96 micrometres; the lower-energy margins are 0.31 and 0.14 MeV. These are distances to thresholds, **not estimated numerical errors**. Without a suitable error estimate, their classification stability cannot be assessed. Likewise, the digits printed for representative objective values do not establish that differences at those digits are physically resolved.

First locate and report the existing convergence evidence the author says was completed, including compatible source, particle/mesh/integration settings and a quantitative residual estimate. Compare it with relevant margins and objective differences. Repeating all production calculations is not requested. If that evidence cannot be recovered, explicitly retain nominal-resolution classification as the result and remove any implication of engineering validation or numerically resolved optimal settings. This narrower route may support a benchmark paper, but the numerical-validation concern remains unresolved for a stronger injector-design claim. Merely citing the previous paper or marking C09 complete is insufficient. Any new tracking validation would need separate author authorization and a defined scope.

### M3. Treat the raw-residual acquisition as the tested implementation, not a validated general formulation

**Locations:** Section 3.2, section 5.5, Discussion, abstract/conclusions. **Action:** R2-03.

The improved specification is unusually useful: it reveals that a nominal smoothing value corresponds to 1 mm for a size residual, 1 mrad for a divergence residual and 0.001 eV for energy. At a zero beam size the size feasibility weight is only about 0.809 for the stated 1 mm limit. This is a strong, dimension-dependent softening, not merely a cosmetic choice of output units.

The offline analysis confirms changed ranks after a unit conversion. However, it evaluates only 32 single-point candidates at three snapshots from one prescribed run, without pruning, while production optimized eight-point batches with pruning. The unchanged best probe candidate does not establish invariance of the production optimizer, and the rank correlations do not quantify the impact on its physical trajectory. The current subsection acknowledges this correctly; the main claims must carry the same scope.

Retain the historical results as a comparison of the explicitly specified raw-residual constrained implementation against the two recorded baselines. State that this is not a new unit-invariant acquisition algorithm and that the dimensionless probe does not validate a corrected campaign. A concise synthesis should distinguish what the three-arm comparison demonstrates from what the offline diagnostic establishes. I accept the author's decision not to run the corrected arm for this restricted paper; it precludes claims about its performance. Further frozen-model batch probes are optional, not a substitute for physical campaign evidence and not a mandatory new task.

### M4. Distinguish exact enumeration from validated inference with a shared estimated reference

**Locations:** Section 4.2; paired results in section 5.2; Appendix A; C03/C04 analysis. **Action:** R2-04.

The paired sampling unit, initialization treatment, zero/tie handling and explicit twelve-test Holm family are improvements. The feasible-fraction differences do not depend on a pooled objective reference, and the retained records show that constraint-aware feasibility is larger in all ten matched groups for each baseline comparison. That result should be distinguished from the objective-quality tests.

Epsilon and IGD+ share a reference front estimated from all tested runs. The post-hoc HV reference is also constructed from those outcomes. Consequently, the transformed group differences share a fitted quantity. Treating the numerical reference as fixed in a bootstrap does not automatically establish the independent, sign-symmetric null model required by the signed-rank enumeration after data-dependent construction. Holm correction cannot repair unestablished individual-test calibration or post-hoc endpoint selection. Leaving a group out for one IGD+ summary checks self-inclusion sensitivity, but does not by itself validate all of the reported quality-test probabilities.

Do not describe the computed probabilities as exact evidence for a general optimization advantage merely because all sign assignments were enumerated. Either justify a suitable inferential construction and demonstrate its assumptions, or retain quality metrics, paired effects and reference sensitivities descriptively and identify the quality-test values as assumption-dependent exploratory calculations. No automatic replacement by an evaluation-level test, arbitrary permutation or a newly selected favorable endpoint is acceptable. If a nested run-level analysis is chosen, rebuild data-derived references inside the resampling procedure and state precisely what uncertainty it addresses; this is an optional offline route, not a guarantee of valid significance. Keep the distinction between mean-effect intervals and signed-rank hypotheses explicit.

### M5. Interpret predictive errors where optimization decisions are made

**Locations:** Section 5.6 and Table 7. **Action:** R2-05.

The unseen-next-batch check is stronger than in-sample fit diagnostics and appropriately discloses the physical-unit variance-accessor floor. Nominal 95% interval coverages around 79% for the two constrained emittance channels establish substantial undercoverage on the observed trajectories. The reported whole-trajectory emittance RMSEs, approximately 7.88 and 13.73 micrometre radian, also exceed many displayed feasible-front emittances. This does not invalidate the directly simulated objective values, but it needs interpretation before readers regard the surrogate as an accurate local beam model.

Explain that these aggregate errors mix early/late stages, infeasible regions and different selected inputs. If the authors wish to claim improved late-stage or near-front predictive accuracy, show stage-resolved and feasible/near-front summaries from the existing prediction records, with counts and run-level variability; otherwise explicitly refrain from that claim. Observed-value boundary conditioning is descriptive and does not constitute prospective safety calibration. The constant transmission channel supplies no evidence of loss discrimination. No model refitting, common-test-set ASTRA campaign or new architecture comparison is required to explain the current evidence.

### M6. Make the scientific supplement identifiable from the manuscript itself

**Locations:** References to “supporting data” and “supporting reproduction manifest” throughout Methods/Results; Appendices C/D. **Action:** R2-06.

A repository-aware reader can find detailed records, but a reader receiving only the PDF cannot resolve the repeated generic pointers. The manuscript does not identify the actual supporting package or code snapshot through a concrete citation, supplement identifier or URL. This weakens the otherwise strong reproducibility work.

Supply one concise, reader-resolvable software/supplement reference and a map to the run-level metrics, candidate diagnostics, C01 reclassification, prediction summaries and actual production settings. Distinguish the production startup revision from the revision-analysis code and note that sampler base draws were not archived. For peer review an accompanying versioned local supplement can suffice; public deposition can follow the author's publication workflow. A Data availability section is not required, and this comment does not authorize a remote upload or push. Preserve immutable simulations and identify any inputs not distributed with the supplement.

## Minor comments

1. **“Knee” terminology:** Section 4.3 and the prior-study discussion call the nearest normalized ideal-point solution a knee, while Appendix D correctly calls it an ideal-distance point. Ideal-point distance is not by itself a knee/curvature criterion. Use one accurate name consistently; no new selection run is needed.
2. **GP wording:** Section 3.1 says fixed noise keeps matrices conditioned “without smoothing the data.” A nonzero effective likelihood variance can change interpolation and posterior predictions. Replace this absolute phrase with a statement about numerical regularization and its effective scale.
3. **Budget matching:** “Differ only in their acquisition strategy” is too narrow: the arms have different target constructions, model counts, constraint information and MC sample counts. Call them specified optimization pipelines sharing the physical model, initial designs and simulation budget. Equal evaluation budgets are valid here but do not imply equal computation.
4. **Scientific labels:** Use consistent weighting names between section 4.4 and Table 6; prefer “emittance emphasis” to an operational “high brightness” label without a specified brightness metric. A centroid-distance representative need not be a physically balanced operating point.
5. **Conclusions:** Prioritize the paired feasible-sampling finding, empirical trade-offs and the engineering acceptance boundary over repeating pooled cardinalities. State the robustness result as conditional on the simulated lattice-only error model; do not use success in all samples as a reliability guarantee.
6. **Presentation and submission finish:** The generic article format, keywords, contents, scatter plots and grid lines are suitable for internal review. Complete funding/acknowledgments before submission, as already deferred to the author. Remove revision-integration comments from the eventual submission source, and supply PDF title/author/keyword metadata. The abstract can remain qualitative and without numbers. No return to JINST formatting is requested by this review.
7. **Length:** The paper is now 30 pages. Move implementation-audit detail to an identified supplement where it interrupts the physical argument, while retaining the unit-smoothing issue and acceptance definitions in the main text. Do not cut necessary scientific limitations merely to shorten the paper.

## Conditions for reconsideration and simulation implications

The minimum next revision should clarify the computational/engineering target, state a defensible numerical-evidence disposition, align all method claims with the executed acquisition, qualify reference-dependent inference, interpret surrogate errors and identify the supporting package. Most work is manuscript revision or offline analysis of existing records. The existing-data route remains available; it does not establish the missing numerical validation by definition.

New MOGA runs, constrained-scalarized/Sobol arms, a corrected MOBO campaign, RF crest scans and expanded source/alignment jitter campaigns are **not mandatory requests for the narrowed paper**. Their absence limits the claims that can be accepted. If the authors instead retain stronger claims requiring those studies, the evidentiary requirement changes; no such run is authorized by this review report. Funding text is an author action, not a simulation requirement.

## Evidence boundary and targeted checks

This is an independent assessment of the supplied revision, not a rerun of its simulations or a certification of all provenance. I recomputed terminal medians and totals from the 30 derived run histories and cross-checked the production totals against C01. I recomputed all twelve mean paired differences from those histories and checked agreement with the C04 table. I calculated the physical TDR margins above from the two stored candidate rows. These checks support internal consistency of derived reporting, not independent verification of raw ASTRA outputs or resolution convergence.

I inspected the current 30-page PDF text and representative rendered results/constraint-space pages, the included tables, and the C04 code's use of a fixed common reference. I did not execute ASTRA, refit GPs, re-audit all original manifests, independently rederive the authors' full posterior prediction set or reverify the external TDR/JINST/JKPS texts in this round. Statements about those sources are assessed against the manuscript and retained round1 evidence, not presented as new external verification.

### Review snapshot

| File | SHA-256 |
|---|---|
| `docs/paper/main.tex` | `63b6c3967ec4bd674da1f4f3a732cc17b925947bf7591bb2452c4a8b09a58317` |
| `docs/paper/main.pdf` | `57070caeec9a7f72e39343b9e3de31afd6e4cd4cba01cd3f24e5cb166fc5299c` |
| `docs/paper/revisions/evidence/c03_run_histories.csv` | `e099add6477d4e7463ae9e703a76eecbda61febcc88d8be0e2d4731156a85dd7` |
| `docs/paper/revisions/evidence/c04_paired_effects.csv` | `bd5dec66a633f35480dc3729dc1deca01031cfd699f79b78d6808f30329e3f54` |
| `docs/paper/revisions/evidence/c01_tdr_candidates.csv` | `e94945e22e6931f61226de6ca08222108cb6987e2250a2ca2f3caae9499f1370` |

The actionable plan is [Reviewer 1 round2 revision tasks](../revisions/reviewer1_round2_revision_tasks.md). The round1 report and response remain unchanged.
