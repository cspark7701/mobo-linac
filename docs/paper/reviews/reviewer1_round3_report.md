# Reviewer 1 report — round3

**Manuscript:** Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design

**Date:** 29 October 2026

**Review type:** Internal scientific pre-submission assessment as Reviewer 1, not an external journal decision.

**Target/version:** Physical Review Accelerators and Beams; 51-page, one-column REVTeX review copy.

**Reviewed revision:** `00190d83b2026b1764af01b1a51bbb0eb10e95d1`.

## Recommendation

**Major revision. I cannot recommend acceptance in the current form.** The revision is substantially more informative and transparent than round2. It now contains a useful space-filling control, measured numerical-resolution sensitivity, a re-evaluated reference setting, TDR-candidate perturbations, and a much better separation of computational feasibility from engineering acceptance. Several earlier objections are resolved and should not be reopened merely because the article is being reviewed again.

The decisive new issue is that the numerical study finds large, setting-dependent emittance changes and changed TDR classifications, rather than establishing convergence. This is a scientifically valuable result, but it changes how the optimization comparison can be interpreted. The retained evidence establishes behavior of the specified pipelines on the nominal numerical model. It does not establish that the physical Pareto ranking or comparative feasibility advantage survives a sufficiently resolved beam-dynamics calculation. Several current passages still extrapolate beyond that boundary, particularly the claims about the edge of the control domain and the effect of omitted amplitude errors. A new statistical defect also appears in the pooled Sobol uncertainty interval.

I recommend revision rather than rejection because the matched comparison, retained evidence and candid negative findings can support a useful paper. The authors should choose clearly between a numerical-model benchmark with a central resolution-sensitivity result and a physically validated injector-optimization comparison. The latter requires evidence not yet supplied. This review does not demand a new MOGA campaign, a new constrained-scalarized arm or a wholesale repetition of production as a prerequisite to considering the narrower paper. Completing the previous task list does not itself establish acceptance.

## Assessment of the round2 response

| Round2 concern | Round3 disposition |
|---|---|
| Computational profile versus TDR requirements | Substantially addressed through the revised title/abstract, explicit relaxed-profile rationale and candidate-margin table. Claims about the location/reach of the TDR region still overinterpret sparse observations. |
| Missing numerical-error evidence | The authors appropriately withdrew the earlier convergence assurance and performed a 150-run sensitivity study. The reporting gap is resolved; the study demonstrates unresolved numerical accuracy, not successful convergence. See M1. |
| Actual constrained implementation | Addressed for the historical raw-residual pipeline: units, smoothing, sample counts and offline-probe limitations are clear. No corrected-method efficacy is claimed. I do not require a corrected arm for the restricted benchmark. |
| Shared-reference inference | Largely addressed. Quality-test probabilities are explicitly exploratory and the rebuilt-reference bootstrap is a useful sensitivity analysis. Neither is treated here as a proof of population-level significance. A separate new Sobol issue remains. |
| Predictive errors | Meaningfully addressed with stage/region summaries and offline noise refits. Undercoverage remains disclosed. Some explanations are hypotheses rather than established causes. |
| Identifiable supplement | The numbered S1 map and production-code identities are improvements. The claim that ledgers alone regenerate every evidence file is contradicted by the scripts' dependencies; see M5. |
| Terminology, figures and presentation | Ideal-distance naming, separate pipeline definitions, scatter-only Pareto plots and acceptance-region insets are appropriate. A one-column review copy is acceptable; its page count alone is not an objection. |

## Strengths and checked findings

The primary comparison retains shared initial conditions, equal evaluation budgets and run-level pairing. The Sobol addition addresses a genuine prior gap without being misrepresented as a MOGA benchmark. Its 41 feasible observations among 1,440 post-initialization evaluations and the positive feasibility differences for all three BO pipelines in each of the ten matched groups are reproducible from the supplied summary records. The new nominal-reference comparison appropriately reveals that no primary feasible setting dominates the re-evaluated reference in all three objectives; this is useful context, not evidence that the searches found no useful trade-offs.

The resolution files contain ten settings at fifteen levels, or 150 setting-level combinations. I independently checked the reported fine-versus-production changes: horizontal emittance decreases by 11.66–33.55% and vertical emittance by 17.10–43.10%. All 150 checks remain production-feasible, while TDR membership varies. These checks concern the selected settings, not all evaluations or every method's feasible front. The candor about this distinction, the unsaved acquisition samples and the limited jitter model is welcome.

## Major comments

### M1. Propagate the measured numerical sensitivity into the central scientific claim

**Locations:** Beamline and simulation; primary comparison; Limitations; Conclusions. **Task:** R3-01.

The result is no longer simply an unknown error bar. The nominal resolution produces material, nonuniform changes in the objectives being optimized; the medium-to-fine change remains as large as approximately 9%, and the ordering of tested emittances is not fully preserved. A common numerical setup across algorithms controls one experimental factor, but does not make its discrepancy cancel when different algorithms select different parts of the domain.

The ten-setting check consists of six representatives from a constrained run, two constrained primary TDR candidates, one constrained TDR-campaign setting and the MOGA-derived nominal. It contains no matched selection of unconstrained/scalarized/Sobol front or rejected-boundary observations. Consequently, “all ten remain production-feasible” cannot validate the primary feasible fractions or front rankings at a refined resolution. In particular, checking already feasible representatives does not measure how many nominally rejected baseline observations would change classification. Nor does refining nominal settings validate every jittered neighbor.

The current Limitations acknowledge that a converged comparison has not been performed, but the conclusion's unqualified statement that production classifications are stable is broader than the evidence. Add a compact numerical-resolution table/plot and explicitly attach the tested population to every stability statement. Treat medium/fine differences as observed sensitivity, not a rigorous error bound. Distinguish fixed-source mesh/step changes from particle/source changes: reproducing source marginals does not prove identical multidimensional source distributions, although the fixed-source step-only effects already establish a numerical problem.

For the existing-data route, make the main contribution explicitly the comparative behavior of these pipelines on a nominal numerical model, together with evidence of that model's resolution limitation. Quantitative physical emittance rankings and engineering-ready Pareto settings cannot be conclusions of that route. If a physically resolved comparison is retained, define a tolerance-based, method-balanced validation plan, including boundary/rejected observations, and demonstrate sufficient tracking stability before asserting it. A finite sample can diagnose stability but cannot automatically certify all trajectories or prove that unchanged optimization would have selected the same candidates. Further tracking requires separate author approval; this report does not prescribe or launch a blanket campaign rerun.

### M2. Correct the uncertainty model for the Sobol arm

**Location:** Sources of the feasible-sampling difference; `analyze_revision_space_filling.py` and associated evidence. **Task:** R3-02.

The observed Sobol fraction, 41/1,440, is correctly reported. The claimed “exact 95% interval” of 2.1–3.8% is not justified by an independent-binomial model: points within a scrambled Sobol sequence are deliberately dependent. The independent randomizations are the ten run-level scrambles, not the 1,440 individual points. The same script also computes pooled binomial intervals for the adaptive BO observations in its initialization-reference output, where independent identically distributed Bernoulli sampling is likewise not established.

Use the ten independent run-level estimates for uncertainty, report their dispersion, or retain the pooled fraction as descriptive without an exact-binomial interval. Preserve pairing when estimating BO-minus-Sobol effects; the existing paired group bootstrap follows that principle and need not be discarded merely because the pooled interval is wrong. Document the small number of independent replicates and the fact that the continued 144-point segments are the fixed-budget comparison actually executed. Do not alter their point sets to repair the analysis.

SciPy's official QMC documentation distinguishes independent Monte Carlo draws from QMC point sets and describes uncertainty assessment using independent randomized replications: [QMC tutorial](https://docs.scipy.org/doc/scipy/tutorial/stats/quasi_monte_carlo.html), [QMC integration](https://scipy.github.io/devdocs/reference/generated/scipy.integrate.qmc_quad.html). This is an analysis correction using existing data, not a reason to rerun ASTRA. The design-specific binomial intervals for genuinely independent jitter draws are a separate construction and are not invalidated by this comment.

### M3. Do not infer domain geometry or a causal mechanism from outcome categories

**Locations:** Abstract; Sources of the feasible-sampling difference; Reach of the TDR acceptance region; Conclusions. **Task:** R3-03.

The manuscript repeatedly places the TDR region “at the edge of the explored domain,” concluding that the controls reach it only there and that additional controls are probably needed. The evidence establishes rare sampled TDR feasibility and closeness to diagnostic thresholds, not the location or topology of a feasible region in six-dimensional control space. In unit-cube coordinates, candidate A spans approximately 0.479–0.860 across its controls; its solenoid/quadrupole coordinates are close to 0.5. Candidate B has a gun phase near 0.962 but most other coordinates are interior. A near-threshold beam diagnostic is not the same as a near-boundary design variable. Three finite-budget, unit-sensitive constrained campaigns cannot establish that a region is inaccessible or identify additional controls as necessary.

Replace the geometric assertion with the directly observed result: sparse nominal-resolution coverage, small diagnostic margins and changing membership under refinement. If “edge” means the diagnostic acceptance boundary, say so explicitly. Additional RF/matching controls may be motivated as future design options, not a demonstrated remedy.

Similarly, the exclusive violation categories exactly decompose an observed feasibility-fraction gap, but do not identify causal effects of individual acquisition terms. Conditioning on energy-acceptable outcomes compares different method-selected populations. The manuscript can report that the gap is numerically concentrated in transverse-violation categories; it should not claim that this establishes why the acquisition worked or isolates an energy-independent mechanism. This qualification is particularly important because energy-related categories account for 63% of the gap to scalarized BO, whereas transverse-only categories dominate the comparison with unconstrained MOBO. The abstract/conclusion should not merge these into a comparator-independent “mainly transverse” mechanism.

### M4. Restrict the RF-amplitude argument to what the calculation estimates

**Location:** Robustness to lattice jitter, RF-amplitude paragraph. **Task:** R3-04.

The first-order calculation estimates RMS mean-energy variation from energy gains at one nominal setting under two assumed correlation structures. It is not a bound on the full beam response or on the complete feasibility event. The manuscript compares 0.40 MeV RMS with a 3.11 MeV lower-energy headroom and then suggests that amplitude jitter would not change production-profile classification for the representatives. However, the same text identifies bunch length or upper energy as limiting other representatives, and amplitude changes can modify phase slippage, focusing, chirp and the transverse diagnostics. A large lower-energy margin alone cannot establish those other margins.

Describe 0.28/0.40 MeV as conditional linearized estimates, not an error bound, and identify the nominal setting used. Remove the all-constraint classification implication. Likewise, scaling the projected energy spread by the same fraction requires an additional approximation and does not follow automatically from scaling the mean gain. The directly simulated lattice-only results can stand without this extrapolation. No additional amplitude or alignment simulation is required if the claims are restricted accordingly.

### M5. Correct the supplement's regeneration claim

**Locations:** Appendix A Supporting package; Supplement S1 “What is and is not distributed.” **Task:** R3-05.

Both state that approximately 10 MB of evaluation ledgers suffice to regenerate every evidence file. This is demonstrably too broad. `analyze_revision_predictions.py` loads hashed GP checkpoint files through `torch.load`; the frozen-model scaling analysis also restores checkpoints. The RF estimate reads a retained `astra.Zemit.001`; the convergence analysis reads `convergence_results.jsonl`, its completion record and a plan describing levels/sources. The specified `evaluations.csv`, `config.json`, `run_complete.json` set alone does not contain all of these inputs.

Distinguish (i) reproducing plots/tables from distributed derived evidence, (ii) regenerating analysis evidence from the appropriate raw ledgers/checkpoints/tracking outputs, and (iii) replaying simulations or proposals. Provide an item-level input inventory and an exact snapshot identifier. State which required inputs accompany the local review package and which must be obtained separately. A manifest checker passing only demonstrates its implemented file/label/checksum checks; it does not demonstrate successful regeneration from the proposed minimal package. This correction needs no public deposition, new simulations or remote action.

## Focused minor comments

1. **Dominance wording:** “No pipeline exceeded [the nominal reference]” and “do not demonstrate an improvement on it” are too broad following explicit improvements in individual objectives. State “no primary feasible observation Pareto-dominated it at the nominal resolution.” The reference is not itself established as the true optimum.
2. **Surrogate explanations:** The offline inferred-noise refit supports sensitivity to regularization. It does not isolate kernel misspecification and adaptive selection as the causes of the remaining undercoverage. Label them hypotheses; do not interpret the retained 88 initial-parameter fallbacks as successful equivalent fits. Report whether the coverage comparison changes when distinguishing fallback cases, if a causal explanation is retained; otherwise use descriptive wording.
3. **Precision and figures:** Label key objective/acceptance tables and Pareto captions as nominal-resolution results. Preserve full precision in evidence, but avoid implying that four-decimal emittance differences have physical accuracy. Include the new refinement results in a compact display rather than relying entirely on prose; the main scientific qualification should be visible beside the optimized fronts.
4. **Review readability:** The expanded manuscript now has several strong results competing for attention. Lead with the specified-pipeline comparison and measured numerical limitations, then use the supplemental analyses to support those claims. Keep the requested one-column review layout, scatter points, grid lines and shaded constraint regions; no cosmetic format reversal is needed.

## What would permit reconsideration

The revised scope should make clear which result remains supported after the refinement finding. Correct the Sobol uncertainty, unsupported domain/causal interpretation, amplitude extrapolation and supplement dependencies. Address the minor wording issues without promoting any observational sensitivity into a validated error bound or algorithmic mechanism. These corrections are predominantly offline or textual. New numerical validation is conditional on retaining a physically resolved optimization claim; no new study is authorized by this report.

I would reassess a sharply framed numerical-model comparison favorably after those issues are resolved, but I cannot certify in advance that it meets PRAB's significance threshold. If the paper instead remains a claim about physically reliable injector Pareto settings, numerical validation is a scientific acceptance requirement, not an optional presentation item. The recommendation is based on scientific evidence, not administrative publication items excluded by the author.

## Review trace and evidence boundary

I read the current manuscript's revised methods/results/discussion and round2 response/overview, inspected the PDF text and rendered Pareto/constraint pages, and examined the cited local analysis code and supplement map. I checked the 150 setting-level rows, emittance-change ranges, production classifications, Sobol counts and all three paired feasible-fraction signs/means from the derived evidence. The paired BO-minus-Sobol mean differences are approximately 0.41806, 0.14236 and 0.10694 for constrained, unconstrained and scalarized BO. I also checked the two original TDR candidates' normalized control coordinates against their actual run configurations. The supplement manifest checker completed successfully; the dependency concern above is not a claim that it failed.

No ASTRA run, GP refit, simulation mutation or full raw-output provenance audit was performed. The resolution aggregates were checked against the stored analysis files, not independently rederived from every tracking output. External checking in this round was limited to primary QMC documentation; prior engineering-source comparisons were assessed through the manuscript and retained evidence rather than independently reverified.

| Reviewed file | SHA-256 |
|---|---|
| `docs/paper/main.tex` | `3eb87c5c38df195e015bfe996a1aadd95d487bf63603f804be6a0f4311f9e82a` |
| `docs/paper/main.pdf` | `38b7d4de0d088b4c4af155f5c5e45a86eedf3e11b285bf3798d88abd161d46fd` |
| `docs/paper/revisions/evidence/r2_convergence_values.csv` | `3b9738783706b136133c80caa3d42544562c8d423abf49db0cc8de2a174f5030` |
| `docs/paper/revisions/evidence/r2_convergence_classification.csv` | `f70c05893f17a1118313649446a144d48fab3c98666b4afad20634513d8334a6` |
| `docs/paper/revisions/evidence/r2_sobol_arm_runs.csv` | `805f5455d8ba890efd0c08e61a376179a3ffa1a0061373f08966b5fa72d39036` |

The proposed actions are in [Reviewer 1 round3 revision tasks](../revisions/reviewer1_round3_revision_tasks.md). Earlier reports and responses remain unchanged.
