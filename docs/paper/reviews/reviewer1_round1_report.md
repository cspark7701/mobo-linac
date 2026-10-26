# Reviewer 1 report — round1

**Manuscript:** Multi-objective Bayesian optimization of a 200 MeV electron injector linac for the Korea Light Source

**Review date:** 26 October 2026

**Review type:** Internal scientific pre-submission assessment in the Reviewer 1 role

**Reviewed revision:** `fe459f2c08ef5c1a992d65a0a26288c5926ae104`

**Material:** Current 20-page manuscript, included tables/figures, selected production records and relevant implementation details.

## Recommendation to the editor

**Major revision. The manuscript is not acceptable in its present form.** It is potentially suitable for JINST after substantive scientific revision, rather than editorial polishing alone. The useful result is a controlled simulation comparison that finds feasible injector settings and indicates greater feasible sampling efficiency for the particular constraint-aware implementation. The present evidence does not yet establish the quality or convergence of the reconstructed Pareto sets sufficiently to support a strong comparative optimization study. Physical acceptance requirements, numerical fidelity and details of the acquisition implementation also need a firmer basis.

The subject fits JINST's stated coverage of accelerator modelling, simulation and software methods. A simulation-only paper is appropriate; machine experiments are not a prerequisite for this recommendation. The missing evidence concerns the validity and interpretation of the simulation study itself. See the [JINST scope](https://jinst.sissa.it/jinst/help/helpLoader.jsp?pgType=about).

## Overall assessment and strengths

The study addresses a relevant injector problem with competing transverse and longitudinal objectives. It correctly separates numerical validity, physical feasibility and nondominance. The distinction between the three-objective Pareto set and its pairwise projections is stated clearly, and the shaded constraint plots avoid equating acceptance in one projection with satisfaction of all constraints. The treatment of unequal survey budgets and the disclosure of the uninformative original hypervolume endpoint are also appropriate.

The primary design is stronger than a single-run comparison: the methods share initial designs, evaluation budgets and physical simulation settings. My targeted check confirmed matching initial design vectors and initial feasibility flags for all ten paired primary runs. The diagnostic inventory agrees with the reported 4,800 primary observations, of which 1,099 are feasible, and 1,232 survey observations, of which 194 are feasible. These checks support internal consistency; they do not establish numerical convergence, optimality or transfer to the machine. The retained data are a valuable basis for revision, and much of the missing analysis can be performed without repeating the existing production campaigns.

## Major comments

### M1. Quantify Pareto-set quality, not only feasible sampling and point count

**Location:** Sections 4.2, 5.2–5.4 and 7; Table 3; Figures 2 and 5.

The central scientific question is which method finds useful feasible trade-offs efficiently. Feasible fractions and nondominated cardinalities do not answer that question by themselves. A set can contain more nondominated points because it is densely sampled in a small region, and a method can find many feasible points without improving beam quality. The pooled counts of 49, 27 and 17 therefore cannot substitute for a per-run comparison of front quality or convergence. The manuscript acknowledges this limitation but does not supply an alternative quantitative evaluation.

Add complementary, reference-point-independent comparisons from the existing histories: for example, directional set coverage and a normalized additive epsilon indicator. If an empirical attainment reference is used for a distance indicator, identify it as an observed approximation, document its construction and examine sensitivity to pooling or self-inclusion. Fix objective scales consistently across methods and evaluation counts. Show progress versus simulation budget and paired run-level differences with uncertainty, rather than treating individual evaluations as independent replicates. These should be identified as exploratory revision analyses, not retrospectively declared original primary endpoints. It is unnecessary to restore the zero-hypervolume panels or change their historical reference.

The first-feasible metric also needs context: in five of the ten paired initial designs, feasibility was already reached within the common initialization. Such outcomes do not measure acquisition performance. Explain this limitation and distinguish initialization from subsequent search when interpreting the metric.

### M2. Establish the physical meaning of the feasible set and the search domain

**Location:** Section 2; Tables 1 and 2; Section 6.1.

The current thresholds define a mathematical feasible set, but their adequacy for KLS injection is not demonstrated. The manuscript itself identifies differences from the earlier JKPS study: wider beam-size and bunch-length limits and no energy-spread feasibility cutoff. Thus a setting called feasible here is not automatically an accepted KLS injection solution. The robust-table emittance-extreme example has an energy spread of 1.6049 MeV; its feasibility under the present definition should not be read as satisfying the earlier 0.5 MeV requirement. This is a question of different requirements, not evidence of a failed simulation.

Provide the current engineering basis for each limit and identify the lattice/design revision to which it applies. Reclassify the existing observations under the cited published requirements as a separately labelled sensitivity analysis, retaining the original statuses. If those requirements are superseded, cite the replacement or supply the acceptance argument. State the source-distribution properties and explain the connection between the exit-plane diagnostics and downstream transport or booster acceptance.

The phase bounds need physical justification as well. A percentage of an absolute RF phase depends on the chosen phase origin and is not invariant under adding a full RF period. In Table 1 the phase intervals also have quite different angular widths. Report and justify the actual angular intervals and the coupling of structure pairs as a defined local search problem. Do not silently change historical bounds to address this concern; any alternative-domain study must be separate.

### M3. Resolve the acquisition specification and dimensional constraint smoothing

**Location:** Sections 3.1–3.3, especially the qLogNEHVI equation and the following paragraph.

The text acknowledges that the same numerical smoothing temperature is applied to residuals in different SI units. This is a substantial methodological issue. The numerical width of `1e-3` corresponds to a millimetre for a size residual, a milliradian for a divergence residual, and a millielectronvolt for an energy residual. Consequently, changing the unit representation can change the acquisition even though the physical problem is unchanged. An observed advantage should be attributed to the recorded implementation, not assumed to represent a unit-invariant constrained-BO formulation.

Audit the dimensional formulation and quantify sensitivity. A dimensionless residual definition or explicitly channel-scaled temperatures is a defensible alternative, but it would be a revised method. Separate offline sensitivity checks on saved surrogates from any new campaign evidence; proposal changes alone do not prove improvements in physical performance.

The displayed batch acquisition is also insufficiently specified as an exact expression. A single feasibility product does not explain how the candidate-wise indicators enter the batch hypervolume calculation or how baseline feasibility and logarithmic relaxations are handled. Either give a correct formulation for the actual implementation or label the equation schematic and document the implementation precisely. BoTorch exposes separate feasibility and hypervolume smoothing parameters, baseline pruning and sampling settings; these should be reported with the campaign library version. See the [official qLogNEHVI API](https://botorch.readthedocs.io/en/stable/acquisition.html#botorch.acquisition.multi_objective.logei.qLogNoisyExpectedHypervolumeImprovement).

A saved late-stage constrained GP provides a concrete additional reporting discrepancy: the constant transmission channel has requested training variance `1e-24`, outcome scale `1`, and stored likelihood variance `1e-6`. This is consistent with the installed double-precision fixed-noise floor, whereas the manuscript gives only the requested variance formula and says outputs are standardized. The code uses mean-only scaling for sufficiently small output variance. Report the effective safeguards and audit their occurrence. This observation alone does not show that the optimization results are wrong, or that other channels have an incorrect variance.

### M4. Position the novelty against the earlier published BO work and qualify the baseline

**Location:** Introduction, Sections 4.1/4.4 and 6.1.

A directly relevant prior publication is missing: C. S. Park, *Multi-objective Bayesian optimization of an electron injector linac for 4th generation light sources: A comparative study with MOGA*, NAPAC2025, WECN03, DOI `10.18429/JACoW-NAPAC2025-WECN03`. The paper describes scalarized BO and MOGA on the Korea-4GSR injector. Its design variables, objective convention and acceptance limits differ from the present study. Cite it and state exactly what the present work adds: explicit constraint modelling, true vector-valued acquisition, repeated paired comparisons or other demonstrable developments. This NAPAC proceeding is separate from the ICABU presentations and does not imply that an ICABU proceeding exists. [Conference paper](https://prebys.physics.ucdavis.edu/NAPAC-25/proceedings/pdf/WECN03.pdf).

The primary scalarized baseline uses one fixed weighting, while vector-valued acquisition seeks a set of compromises. This is a valid comparison of the specified configurations, but it is not a general test of the best attainable scalarized-BO front. Either limit the conclusion accordingly or include an equal-total-budget allocation across scalarization weights. The five-times-larger survey cannot serve as that matched baseline. A space-filling control would also clarify what adaptive BO adds beyond the common initialization. A new MOGA campaign is necessary only for a matched MOGA performance claim, not merely to provide literature context.

### M5. Demonstrate numerical fidelity and surrogate adequacy

**Location:** Sections 2.1 and 3.1; Discussion.

Using the same tracking settings for every algorithm is necessary but does not establish that those settings resolve the relevant trade-offs. The paper supplies a particle count and mesh sizes but no numerical convergence evidence. Numerical error near a feasibility boundary can alter both the classification and the Pareto set, even if repeated calculations with identical inputs agree perfectly.

Provide source-distribution characteristics and a bounded resolution study at representative points, including a compromise, objective extremes and a point close to a limiting constraint. Vary particle number and relevant mesh/resolution settings while preserving physical source properties, and report changes in objectives and margins against stated tolerances. These are additional validation calculations, not replacements for completed campaigns. Original inputs, budgets and evidence must remain intact.

The GP models also need evidence beyond successful fitting. Existing checkpoints can support leave-one-out predictive errors, uncertainty calibration and diagnostic-channel performance near the feasibility boundary. A constant transmission channel needs explicit treatment; predictive discrimination is not identifiable when the observed channel has no failures. The manuscript should explain which outcomes are learned accurately enough to support the acquisition and where surrogate uncertainty remains poorly assessed.

### M6. Present reproducible accelerator settings and physical interpretation

**Location:** Sections 5.2/5.3, Table 6 and Conclusions.

The paper reports objective extrema and representative roles, but does not give a compact set of optimized magnetic/RF settings together with their complete constraint diagnostics. A reader cannot readily reconstruct a useful operating point or understand why its trade-off differs from another. Coordinate-wise minima are correctly distinguished from a single setting, yet the scientific contribution would be stronger if the actual settings were interpreted in beam-dynamics terms.

Using existing records, provide representative parameter vectors, objectives and constraint margins for a balanced operating point and useful extremes. Compare them with the nominal reference setting under the same evaluation convention, if that setting has been evaluated. Explain the focusing and phasing changes, supported where possible by stored longitudinal beam evolution or other recorded diagnostics. Do not infer a causal mechanism from scatter plots alone. This request concerns the physical content of optimized solutions, not reinstatement of the removed nominal-rerun verification subsection or figure.

### M7. Give statistical meaning to robustness and justify the composite score

**Location:** Section 4.3, Section 5.5 and Table 6.

The result that all sampled perturbations remain feasible is useful, but the displayed value of `1.00` is an estimate rather than proof of unit feasibility probability. With 50 successes in 50 independent draws from the stated perturbation model, the exact one-sided 95% lower success bound is approximately 0.942; the corresponding two-sided lower bound is approximately 0.929. Report an interval or equivalent uncertainty statement per operating point. The 600 heterogeneous perturbations should not be pooled into a single reliability estimate for every design.

Define the normalization of the constraint margins and justify the robust score, or replace it with interpretable quantities already stored: probability, objective means/spreads and minimum margins. The implementation normalizes each margin by its threshold. For a narrow energy acceptance window around a much larger mean energy, this produces a different numerical margin scale from an upper size limit; taking the smallest value across channels can make the identity of the limiting channel depend on that convention. The score can also exceed one, and averaging objective ratios can conceal a larger degradation in one objective. These properties require explanation if the score is retained.

Clarify the correlations implied by perturbing common RF-phase controls and identify the runs and candidate-selection rule used for the assessment. Expanded source, gradient and alignment tests are optional if the claims remain explicitly limited to the existing lattice-jitter model; they become necessary if a broader robustness claim is made. Comparative robustness superiority would additionally require applying the same protocol to appropriately selected baseline solutions.

### M8. Make the comparative inference and reproducibility package self-contained

**Location:** Sections 3–5; Table 3; paper reproduction instructions.

The paired design should be used when reporting comparative uncertainty. Marginal confidence intervals for each method are not confidence intervals for their difference, and individual samples within an adaptive campaign are not independent experimental units. Report run-level paired effects for feasible sampling and any newly introduced quality indicator, or keep statements explicitly descriptive. Explain the role of initialization and the distinction between pooled and typical-run performance.

The methods should identify the code revision, effective GP/acquisition settings, actual worker/concurrency policy and a reproducible mapping to the saved campaign configurations. Software defaults and model-training recovery are part of the executed method. Relative computational-cost ratios and a short account of where the overhead arises would substantiate the speed comparison without requiring absolute runtimes in the manuscript. Raw seed numbers can remain in the reproducibility manifest rather than the main text. A dedicated Data availability section is not required to address this comment; the necessary information can be provided in Methods, an appendix or a linked reproducibility package.

## Minor comments

1. **Table 5:** Its minima use all-valid observations, including infeasible ones, unlike the feasible operating-point objective of the study. Prefer feasible minima in the main table, or make the distinction unmistakable in the column headings and present the all-valid extrema separately. Do not alter the underlying observations.
2. **Tables 4 and 5:** Replace development labels such as “Phase 1/2/3” and unexplained operational-archetype wording with algorithm and weighting names. “High-Brightness FEL Mode” should not imply demonstrated FEL performance in a KLS injector study.
3. **Figures 6 and 7:** The full distributions are valuable, but the accepted beam-size region is small and the overlaid markers are dense. Add a clearly identified zoom/inset or complementary case-level views for the accepted region while retaining the full data and consistent status encoding. Smooth Pareto lines are neither needed nor requested.
4. **Table 6:** Replace raw software parameter names in the caption with physical names. Improve the table's legibility and explain the robustness-score range if it is retained.
5. **Literature comparison:** Check the JINST summary values against the full article's actual tracked operating point and specify the comparison basis. Comparing separately reported extrema or different source/acceptance conventions must not be presented as dominance.
6. **Bibliography and submission finish:** Complete the unresolved Emmerich page metadata and the funding/acknowledgment placeholder. Check journal citation formatting and remove development-only language. The qualitative abstract can remain without numerical values; its statements must stay aligned with the revised evidence.
7. **Style:** Prefer concise physical interpretation to repeated explanations of file formats, marker rules and scope. Fuller paragraphs are useful when they develop an argument, but extra length alone does not improve a scientific paper.

## What is required before reconsideration

A satisfactory revision should establish the physical definition of an accepted KLS-reference solution, supply a quantitative per-run assessment of the observed feasible fronts, reconcile the acquisition/noise description with the executed implementation, address numerical fidelity, and position the contribution against the published earlier BO study. It should also make representative settings and uncertainty interpretable. Merely increasing the number of points, extending the prose or producing additional plots would not resolve these concerns.

I recommend major revision rather than rejection because the controlled campaign design and retained evidence provide a credible starting point. Several revisions are analysis and reporting tasks using existing data. New tracking should be limited to justified controls or validation studies, with their scope defined before execution; a wholesale repetition of all production runs is not automatically required. The final publication decision remains an editorial judgment after the revised scientific evidence is assessed.

## Evidence boundary and review trace

This was a targeted assessment, not a complete re-execution or provenance certification. I read the manuscript and included tables, checked aggregate diagnostic counts, compared initial design vectors/feasibility across all primary method pairs, inspected acquisition and robustness code, and examined one late-stage primary constrained GP artifact. I did not run ASTRA, refit surrogates, execute new optimization campaigns or infer that unavailable validation studies had failed.

Review snapshot hashes:

| File | SHA-256 |
|---|---|
| `docs/paper/main.tex` | `94545766637720bf9f0848540b6aa99df541d6c48fdafa49096d272d1e2daa1c` |
| `docs/paper/main.pdf` | `758ea12b4a87a4c60505f54077c8841e027985d82f4e96961613d74e558e2c90` |
| `docs/paper/primary_results.json` | `06fb9ee5831660dd1a30ec200e9ad66beb5a6a85cf879e632e00af00c8d7eb31` |

Supporting repository evidence includes `primary_results.json`, `primary_results_table.tex`, the campaign manifests/evaluation exports, `constraint_spaces_20261026/constraint_observations.csv`, `src/mobo_linac/acquisition/mobo.py`, `src/mobo_linac/models/gp.py`, `src/mobo_linac/robustness/evaluator.py`, and the predeclared primary constrained run's `model_iter_18_*.pt` artifact. The sampled campaign environment records BoTorch 0.17.0. Its qLogNEHVI class has a default MC sample shape of 128; this is a checked implementation default, not a substitute for auditing all executed proposal settings.

The actionable response plan is [reviewer1_round1_revision_tasks.md](../revisions/reviewer1_round1_revision_tasks.md).
