# Response to Reviewer 2 — round1

**Status:** Complete point-by-point response for author review, against manuscript `fe459f2c08ef5c1a992d65a0a26288c5926ae104`. This is not a claim of journal acceptance or submission readiness. Funding/acknowledgments remain author-deferred.

The revision uses the retained production simulations. At the author's explicit direction, no new MOGA/NSGA-II simulations, published-MOGA-setting reevaluations, corrected-acquisition campaigns, constrained-scalarized/Sobol controls or expanded error-model campaigns were run. C02 and C09 are closed as scope dispositions with missing calibration/error-bound evidence retained as limitations. The responses below distinguish changed analysis from unperformed validation requests. Original reviewer reports and simulation evidence remain unchanged.

Figure/table locations refer to their current captions and section names because the revised survey is now in an appendix. The [revision overview](../revisions/round1_revision_overview.md) links the baseline diff and separate analysis-change inventory.

## Major comments

### M1. Primary endpoint and front quality

Added reference-free epsilon/IGD+ and directional coverage, convergence histories, empirical attainment, and explicitly post-hoc hypervolume reference sensitivity. References/scales and empirical-reference bias are documented. The original reporting endpoint is neither overwritten nor retrospectively declared valid; the new evidence supports endpoint-dependent conclusions rather than uniform superiority.

**Tasks:** C03/C04/C15. **Manuscript:** Primary comparison and front-quality appendix.

**Evidence:** [C03 report](../revisions/evidence/c03_report.md), [C04 report](../revisions/evidence/c04_report.md).

### M2. Phase bounds

Report actual absolute-phase windows, nominal coordinates, pair coupling and observed coverage. The previous JINST off-crest convention cannot calibrate the present trajectory. At the author's request C02 is closed without new scans/reruns; the missing engineering justification and crest calibration remain explicit. Data filtering is not presented as a rerun under a restricted domain.

**Tasks:** C02. **Manuscript:** Design variables; Limitations.

**Evidence:** [C02 report](../revisions/evidence/c02_phase_report.md).

### M3(a). Constraint scaling

Reconcile the real raw-residual fat-tailed smoothing with physical units, and quantify its unit-sensitive acquisition ranks on frozen surrogates. Dimensionless residuals give equivalent-unit values to numerical precision. The highest-ranked probe remains unchanged in this limited test; no optimized-proposal or beam-quality improvement is inferred. The requested corrected primary arm is not adopted under the author's existing-simulation decision.

**Tasks:** C05/C06. **Manuscript:** Acquisition Methods; offline sensitivity results.

**Evidence:** [C05 report](../revisions/evidence/c05_report.md), [C06 report](../revisions/evidence/c06_report.md).

### M3(b). Missing baselines

Provide an explicit comparison matrix. No constrained-scalarized or full-budget Sobol arm was performed; the author elected to retain existing simulations. Equal-weight scalarized BO is not claimed to represent every scalarization, and the unequal-budget survey is not used as a matched control. No BO-over-Sobol or vector-over-constrained-scalarization conclusion is asserted. New MOGA/NSGA-II runs are also excluded.

**Tasks:** C07/C12. **Manuscript:** Primary comparison protocol; scope Discussion.

**Evidence:** [C07 report](../revisions/evidence/c07_report.md), [C12 report](../revisions/evidence/c12_prior_work.md).

### M3(c). Initialization

Audit shared initial designs and separate initialization from adaptive results. First-feasible counts are omitted from the main comparative table because they can reflect common initialization rather than algorithm behavior.

**Tasks:** C04. **Manuscript:** Primary protocol and table.

**Evidence:** [C04 report](../revisions/evidence/c04_report.md).

### M4. Physics and constraints

Add fixed-source moments, complete controls/objectives/margins and retained trajectory samples. Quadrupoles lie between structures; downstream asymmetry is not attributed solely to ideal focusing. Energy spread is projected full-bunch RMS including chirp. The TDR/production distinction is explicit. Transmission and the upper energy limit are unviolated only in the observed sample, not declared redundant throughout the domain. Generator provenance and isolated mechanisms remain bounded.

**Tasks:** C01/C08. **Manuscript:** Injector model; selected-setting interpretation and appendix.

**Evidence:** [C01 report](../revisions/evidence/c01_acceptance.md), [C08 report](../revisions/evidence/c08_report.md).

### M5. Statistics

Use paired run-level differences, exact signed-rank tests and Holm adjustment over twelve comparisons, with pointwise bootstrap intervals and explicit assumptions. Feasible sampling is supported under the recorded profile; objective-quality evidence varies by endpoint/comparator.

**Tasks:** C04. **Manuscript:** Primary comparison protocol/results.

**Evidence:** [C04 report](../revisions/evidence/c04_report.md).

### M6. Robustness

Add exact per-design intervals, objective distributions and physical/normalized margins; independently reproduce historical scores and explain ties. Clarify predeclared run selection, six distinct designs, common draws and phase-pair correlations. Expanded RF-amplitude/JKPS/alignment tests and the ambiguous tolerance scan are explicitly not performed. Claims remain limited to the actual small lattice-jitter model and cannot establish wider reliability or superiority over other BO solutions.

**Tasks:** C10. **Manuscript:** Robustness Methods/results and table.

**Evidence:** [C10 report](../revisions/evidence/c10_report.md).

### M7. Earlier KLS MOGA

Cite the published studies and distinguish abstract extrema from the actual tracked setting, including fractional-to-absolute spread conversion. Do not infer a matched ranking from different controls, source conventions or acceptance limits. The author excludes new MOGA runs and published-setting reevaluation because this paper concerns MOBO; those requests are not represented as performed.

**Tasks:** C12. **Manuscript:** Introduction; relation to prior KLS studies.

**Evidence:** [C12 report](../revisions/evidence/c12_prior_work.md).

## Minor comments

| Comment | Tasks | Response and disposition |
|---|---|---|
| 1 | C14 | Use method names instead of Phase 1/2/3 labels in manuscript tables and new figures. |
| 2 | C14 | Replace operational/FEL labels with weighting names, regenerate feasible-only minima and remove stale reference-point wording. |
| 3 | C15 | Show each scalarized campaign separately to 176 evaluations, use consistent colors and vector output without a redundant manuscript title. |
| 4 | C15 | Add transverse acceptance zooms. Retain constant transmission as an explicit observation-count/value/threshold annotation rather than an empty panel; do not invent an energy-spread constraint. |
| 5 | C03/C08/C15 | Include empirical attainment and checkpoint analyses plus complete representative settings. Pareto projections retain shared coordinate limits and no smooth lines. |
| 6 | C15 | Move detailed unequal-budget survey tables/figures into an appendix with a short main-text summary. |
| 7 | C13 | Report paired relative durations and evaluation-interval unions. Absolute durations remain in evidence per author instruction; logs do not separately time GP and acquisition overhead. |
| 8 | C05 | Clarify recomputed negated-model-space acquisition references based on all valid observations, including infeasible ones, separately from the fixed reporting reference. |
| 9 | C13/C16 | Add verified ICABU oral-presentation citation and reproduction identities. Do not restore the author-removed Data availability section or invent a public archive DOI. Funding/acknowledgments remain author-deferred. |
| 10 | C15/C16 | Move plotting conventions into captions, shorten the survey and consolidate related limitations. |
| 11 | C10/C16 | Retain the author-requested qualitative abstract. Put exact jitter amplitudes, sample counts and uncertainty in Methods/Results; qualify the abstract as a limited lattice-jitter assessment. |
| 12 | C01/C16 | State seven diagnostic channels and eight inequalities, including both energy bounds. |
| 13 | C14/C16 | Use consistent micrometre-radian and MeV quantities with siunitx; captions identify units and populations. |
| 14 | C08/C10 | Verify and state six distinct parameter vectors in each assessment; preserve exact role/run/evaluation mappings. |
| 15 | C14/C16 | Remove whole-table resizing from main tables. Preserve the distributed JINST style and document its harmless pagecolor warning rather than modify publisher code. |
| 16 | C05/C09 | Cite the verified JINST resolution correspondence, but do not assert unproven full solver equivalence or an unavailable refinement bound. Fixed GP noise is regularization, not a numerical-error estimate; C09 is author-closed with this limitation. |

## Remaining scientific and author-controlled limits

Crest calibration and a quantitative tracking-refinement error bound remain unavailable. New corrected-method, constrained-scalarized, Sobol, broader-jitter and MOGA campaigns were not performed. Source-generation provenance and isolated causal mechanisms remain unestablished. These scope decisions may still concern the reviewer; neither reviewer agreement nor acceptance is presumed. Funding/acknowledgments must be supplied before submission.
