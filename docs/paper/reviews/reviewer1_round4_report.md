# Reviewer 1 report — round4

**Manuscript:** Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design

**Date:** 30 October 2026

**Review type:** Internal scientific pre-submission assessment as Reviewer 1, not an external journal decision.

**Target/version:** Physical Review Accelerators and Beams; 56-page one-column REVTeX review copy.

**Reviewed revision:** `887673c99cb148ec97e045304374a86dbc022884`.

## Recommendation to the editor

**Minor revision. I consider the manuscript scientifically acceptable after the focused corrections below, for its explicitly restricted nominal-numerical-model scope.** I do not recommend unconditional acceptance of the present wording. The remaining issues can be addressed with the existing evidence and limited editing; no new ASTRA simulation or optimization campaign is required by this review.

This is a change from my round3 major-revision recommendation. The authors have now made the numerical limitation central to the paper, corrected the Sobol uncertainty model, separated the attribution by comparator, removed unsupported control-domain geometry claims, and supplied an input inventory with a demonstrated regeneration check. The study no longer presents a physically resolved injector optimization or a general proof of constrained-MOBO superiority. Within that stated scope, the matched comparison and its documented limitations form a coherent contribution.

The empirical feasibility advantage on the fixed numerical model is supported by paired observations; the empirical Pareto-quality results remain exploratory and conditional on reference construction, source realization and tracking resolution. Neither the new scenario analysis nor this favorable review establishes numerical convergence, engineering acceptance or calibrated machine reliability. The editor retains responsibility for judging PRAB significance and fit. My recommendation does not require reversing the author's scope choice or resurrecting previously declined studies.

## Assessment across both reviewers' response histories

I considered the responses to Reviewers 1 and 2 for rounds 1–3 as a sequence. Later responses supersede earlier non-adoptions or assertions where new evidence was added. In particular, the previously absent Sobol arm and numerical-resolution check now exist, while the earlier convergence assurance has been explicitly withdrawn. Historic response wording is not treated as a current manuscript claim.

| Issue raised across the reviews | Current assessment |
|---|---|
| Three-method comparison, shared initialization and fair accounting | Resolved for the specified pipelines and evaluation budget. The methods are not claimed to differ only in the acquisition formula or to have equal computational costs. |
| Feasible-front quality beyond point counts | Addressed with per-run indicators, directional coverage, attainment and histories. Empirical references, post-hoc status and conditional uncertainty are disclosed. Global optimality is not claimed. |
| Fixed-reference hypervolume failure | Disclosed without altering the historical endpoint. Replacement analyses are labelled post hoc; the zero endpoint is not confused with absence of feasible points. |
| Production profile versus KLS engineering acceptance | Resolved for the computational-model scope. The relaxed profile, TDR subset, candidate margins, jitter results and resolution-dependent membership are distinguished. |
| Numerical convergence and phase calibration | No longer misrepresented as established. Numerical sensitivity is now displayed and limits the claims; the inherited absolute-phase domain remains explicitly historical. I do not demand new crest scans or a converged campaign for the chosen restricted study. |
| Raw-residual constraint smoothing and missing controls | The actual unit-dependent implementation is specified. No corrected-method efficacy or advantage over constrained scalarization is claimed. The added matched Sobol arm supports a separate space-filling comparison. No new MOGA benchmark is required. |
| Attribution of the feasibility advantage | The current summaries distinguish transverse-dominated accounting against unconstrained MOBO from energy-involving categories against scalarized BO. Conditional populations and noncausal interpretation are stated. |
| Sobol uncertainty | Resolved: the pooled exact-binomial claim is removed and ten-run variation/approximate run-level bootstrap uncertainty is reported. Paired comparisons retain the group as the unit. |
| Predictive validation | Saved-model, stage/region and refit analyses are reported without claiming calibrated local reliability. Remaining causal explanations are hypotheses; fallback refits are not treated as equivalent successful fits. |
| Robustness and the adapted nominal reference | Lattice-only scope and individual uncertainty are clear. Absence of Pareto dominance is distinguished from improvement in individual objectives. One residual RF-amplitude sentence needs qualification below. |
| Reproduction package | Substantially resolved: S1 distinguishes derived-output reproduction, minimal-ledger analysis, checkpoint/output-dependent analysis and re-tracking. Representative regeneration succeeds; unavailable bitwise proposal replay is disclosed. |
| Figures, precision and presentation | Nominal-resolution labels, scatter-only fronts, shaded diagnostic regions and separate weighting histories are suitable. The new resolution table has one unit-label ambiguity. |

## Remaining required corrections

### C1. Call the 27 transformations a scenario sensitivity analysis, not a bound on numerical error

**Locations:** Abstract; contribution 5; Beamline and simulation; final paragraph of Primary comparison; Discussion; Limitations; Conclusions; related response/overview wording. **Task:** R4-01.

The new calculation is useful and its numerical results reproduce. It applies a common transverse scale factor (0.78, 0.89 or 1), a common bunch-length factor (0.99, 1 or 1.01), and a common energy shift (−0.05, 0 or +0.05 MeV) to all observations. The same transformation is shared across channels in each group and across methods. It therefore establishes stability under these 27 specified common-shift scenarios, not under all setting-dependent changes consistent with the refinement data.

The manuscript still says “To bound the effect of the numerical resolution” and that the earlier section “bounds that effect.” The abstract says the advantage persists “under the measured refinement shifts,” which can be read as if every primary observation had been re-tracked. Those statements are stronger than the actual calculation. The qualification that the shifts are not a per-point model is helpful but does not fully repair the headline wording.

There is also a small factual reason not to describe the selected grid as enclosing all measured changes: Table I reports transverse increases up to 1.2% for step-only refinement and a 0.2% divergence increase at the fine level, whereas the scenario transverse factor never exceeds one. More generally, a single shared transverse factor cannot represent arbitrary channel-dependent or setting-dependent shifts. These facts do not invalidate the reported scenario values, and do not imply that the ordering would reverse outside them.

Use “post-hoc common-shift sensitivity scenarios motivated by the ten-setting refinement check,” or equivalent concise wording. Explicitly say in the main result that the diagnostic transformation is common to all observations and that it does not establish stability under a converged re-evaluation or under arbitrary setting-dependent errors. In the abstract, “persists in the tested diagnostic-shift scenarios” is sufficient. Preserve the 27-scenario results and their limitations. No extra scenarios, adversarial perturbation model, re-tracking or algorithm rerun is necessary for this correction; the acceptance condition is accurate interpretation.

### C2. Keep the TDR RF-amplitude implication conditional

**Location:** Robustness to lattice jitter, paragraph discussing candidates A and B. **Task:** R4-02.

The revised amplitude paragraph now correctly identifies a linearized mean-energy estimate at the MOGA-derived nominal setting and disclaims a full-feasibility bound. The subsequent sentence nevertheless says the comparison with the TDR energy margins “indicates that amplitude jitter would cause further TDR failures.” The candidate-specific amplitude response and its joint action with the other diagnostics were not tracked or derived.

Replace this with a conditional risk statement: the comparable scales suggest that omitted amplitude errors could reduce TDR acceptance and merit candidate-specific study. Do not infer an added failure count, probability or demonstrated classification change. The measured 36/50 and 44/50 lattice-only outcomes remain valid as reported under their model. This is a wording correction, not a request for amplitude simulations.

### C3. Remove the mixed-unit ambiguity in the numerical-resolution table

**Location:** Table I, `tab:resolution`. **Task:** R4-03.

All numerical column headings state percent, but the mean-energy row gives absolute changes in MeV, including −0.05 to +0.01 and ≤0.02. The row label identifies MeV, yet the conflicting column headings make a unit error possible. State in the caption/header that entries are percentages except the mean-energy row, or separate the absolute-energy row into a labelled block. Define whether the “fine vs medium” maxima use the medium value as the relative-change denominator, and distinguish absolute magnitudes in that column from signed changes in the first two columns. These are presentation clarifications using the existing values.

## Why the remaining numerical limitation does not trigger another major-revision cycle

The authors have accepted the narrower route offered in the preceding reviews. The abstract explicitly excludes physically resolved injector optimization; the introduction identifies a fixed source and tracking resolution; the new table exposes the nonconvergence; and the conclusions exclude a physically resolved method ranking. I assess that actual claim, rather than requiring evidence for a stronger claim the authors no longer make.

The paper can therefore report that the recorded constraint-aware pipeline found more nominal-model feasible observations than its comparators and characterize its observed trade-offs. It cannot promote the scenario analysis into an error guarantee, recommend the selected settings as validated machine settings, or generalize the raw-residual result to a corrected constrained method. C1 is important precisely because maintaining this distinction makes minor revision appropriate.

No new constrained-scalarized, MOGA, source/alignment-jitter, crest-calibration or converged optimization campaign is requested. A physically validated design claim would require a different evidentiary standard, but adding that claim is outside this revision. The exclusions requested by the author are respected; administrative publication items are not acceptance tasks in this report.

## Independent checks and evidence boundary

I inspected the current manuscript source and extracted PDF text, the new resolution table and Pareto figure as rendered, both reviewers' responses across rounds 1–3, the round3 overview, and the scripts implementing the common-shift and Sobol uncertainty analyses. Earlier source-verification results are treated as historical evidence; I did not independently reverify external accelerator papers in this round.

Targeted checks:

- The scenario table has 1,080 run-scenario records: 27 scenarios × four methods × ten groups.
- All 135 post-initialization scenario/pair summaries report ten positive group differences and positive lower bootstrap endpoints. These are pointwise results within the tested scenario grid, not simultaneous guarantees over numerical errors.
- Recomputed ranges of per-scenario median feasible fractions agree with the manuscript: 0.36875–0.465625 (constraint-aware), 0.146875–0.2125 (unconstrained), and 0.1125–0.18125 (scalarized).
- The new Sobol summary retains 41/1,440, mean 0.028472, run range 0.013889–0.048611 and run standard deviation 0.013277. Its 0.020833–0.036111 bootstrap interval is explicitly approximate.
- I ran the supplement manifest checker successfully and independently reran the scratch-tree regeneration check with its report written outside the repository. It copied 215 minimal ledger files plus scripts and distributed derived evidence. All three selected generators reproduced the seven checked CSV files to the checker's tolerance. This verifies those representative paths, not every S1 generator or a standalone ledger-only reconstruction of the full study.
- No ASTRA calculations, GP refits, campaign changes or manuscript edits were made. I did not repeat the full test suite or certify the full raw simulation archive; those are unnecessary for these review-only outputs.

### Review snapshot

| File | SHA-256 |
|---|---|
| `docs/paper/main.tex` | `4d6b3891ac65cad453168b6b3997209f8d57295223293d797d85e0cc5263d45c` |
| `docs/paper/main.pdf` | `c3b0d2356506bd892256c1c5e3ffd4dc23485b6aaf1b9cad813ce5f2e9c1c76b` |
| `docs/paper/revisions/evidence/r3_resolution_bounds_runs.csv` | `b311ebd9afe74b5ed7cd3b61a716e9c5a74351b76717e21191e25819081cc908` |
| `docs/paper/revisions/evidence/r3_resolution_bounds_paired.csv` | `3b540c8e30ab2356db67f134d1b1b19766ebaf3b02ee5b474583d86d9a2922ee` |
| `docs/paper/revisions/evidence/r3_sobol_uncertainty_summary.csv` | `3789117d322f2087aade0a17bcfc3d642e3f6ffb78181e06950210c58ee8fafa` |

See the [Reviewer 1 round4 task list](../revisions/reviewer1_round4_revision_tasks.md). Once C1–C3 are corrected and the response is checked, I would recommend acceptance of the explicitly scoped computational study, subject to the editor's judgment.
