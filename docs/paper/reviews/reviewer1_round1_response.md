# Response to Reviewer 1 — round1

**Status:** Complete point-by-point response for author review, against manuscript `fe459f2c08ef5c1a992d65a0a26288c5926ae104`. This is not a claim of journal acceptance or submission readiness. Funding/acknowledgments remain author-deferred.

The revision uses the retained production simulations. At the author's explicit direction, no new MOGA/NSGA-II simulations, published-MOGA-setting reevaluations, corrected-acquisition campaigns, constrained-scalarized/Sobol controls or expanded error-model campaigns were run. C02 and C09 are closed as scope dispositions with missing calibration/error-bound evidence retained as limitations. The responses below distinguish changed analysis from unperformed validation requests. Original reviewer reports and simulation evidence remain unchanged.

Figure/table locations refer to their current captions and section names because the revised survey is now in an appendix. The [revision overview](../revisions/round1_revision_overview.md) links the baseline diff and separate analysis-change inventory.

## Major comments

### M1. Pareto quality and convergence

Added additive epsilon, IGD+, bidirectional coverage, checkpoint histories, relaxed-target attainment and post-hoc reference-sensitivity hypervolume. The empirical reference is identified and a leave-group-out sensitivity is included; it is not the true Pareto front. Paired effects and a twelve-comparison Holm family replace unsupported universal rankings. The original zero endpoint is preserved as a limitation.

**Tasks:** C03/C04. **Manuscript:** Primary comparison; Exploratory front-quality appendix.

**Evidence:** [C03 report](../revisions/evidence/c03_report.md), [C04 report](../revisions/evidence/c04_report.md).

### M2. Physical acceptance and phase domain

The official October 2025 KLS TDR is now the engineering reference. A separate reclassification gives two constrained observations and no baseline observations passing its optimization inequalities; both also pass the relative-spread specification. The broad production profile is explicitly different and is not full injection certification. Absolute ASTRA phases, nominal coordinates and inherited bounds are documented. The author closes the crest-calibration request without a scan: no engineering justification of those unequal windows or calibrated off-crest phases is claimed.

**Tasks:** C01/C02/C08. **Manuscript:** Injector model and optimization problem; Limitations.

**Evidence:** [C01 report](../revisions/evidence/c01_acceptance.md), [C02 report](../revisions/evidence/c02_phase_report.md), [C08 report](../revisions/evidence/c08_report.md).

### M3. Acquisition specification and dimensional smoothing

The actual sampled qLogNEHVI constraint weights, model outputs, eight inequalities, raw units, effective noise floor, MC defaults and reference construction are reconciled with saved artifacts and call sites. Offline fixed-model probes quantify unit-sensitive ranking and dimensionless invariance. No corrected physical campaign was run under the author-approved existing-data scope; historical outcomes remain those of the original raw-residual method.

**Tasks:** C05/C06. **Manuscript:** Surrogates and acquisition Methods; Offline sensitivity results.

**Evidence:** [C05 report](../revisions/evidence/c05_report.md), [C06 report](../revisions/evidence/c06_report.md).

### M4. Novelty and baselines

Cite and distinguish the earlier JINST MOGA, JKPS errors, NAPAC BO/MOGA study and verified ICABU oral presentation. The current paper focuses on the recorded MOBO comparison. The scalarized arm is specifically equal-weight, while the independent multiweight survey has a larger aggregate budget. New constrained-scalarized, Sobol and MOGA controls are not adopted; no advantage over those unrun controls or matched MOGA speedup is asserted.

**Tasks:** C07/C12/C16. **Manuscript:** Introduction; primary comparison protocol; prior-study Discussion.

**Evidence:** [C07 report](../revisions/evidence/c07_report.md), [C12 report](../revisions/evidence/c12_prior_work.md).

### M5. Numerical fidelity and surrogate adequacy

The author previously confirmed completed convergence work and asked to use Kim et al., JINST 19 P01023. Its particle/grid/image-charge settings are compared with the current records, but no traceable refinement-error bound or full solver-transition equivalence was found. C09 is closed with that limitation, not certified as numerical convergence. Separately, all 540 saved models predict their unseen next batch; errors and undercoverage are reported, including boundary subsets and the physical-unit variance-floor distinction. Constant transmission cannot validate loss discrimination.

**Tasks:** C09/C11. **Manuscript:** Beamline and simulation; Predictive checks and appendix; Limitations.

**Evidence:** [C09 report](../revisions/evidence/c09_convergence_report.md), [C11 report](../revisions/evidence/c11_report.md).

### M6. Reproducible operating settings and physical interpretation

Provide all six representative control vectors, objectives and every signed constraint margin, together with source-file moments and sampled trajectories. Both quadrupoles are between accelerating structures. The downstream asymmetry and projected energy chirp are described without causal over-attribution. No primary record matches the nominal vector exactly, so no measured nominal-lattice improvement is claimed. Source-generation provenance and isolated mechanism tests remain unestablished.

**Tasks:** C08. **Manuscript:** Interpretation of selected settings; operating-settings appendix.

**Evidence:** [C08 report](../revisions/evidence/c08_report.md).

### M7. Robustness meaning and score

Report exact per-design binomial limits, objective means/spreads/ratios and limiting margins. Explain threshold versus energy half-band normalization and retain physical headroom. Independent recalculation reproduces all archived scores; exact ties arise from clipping and equal recorded margins, while another pair only agrees after rounding. The main table reports components instead of a score ranking. Common random numbers, paired-cavity correlations and design identities are explicit; heterogeneous trials are not pooled. Broader error models are not claimed.

**Tasks:** C10. **Manuscript:** Robustness Methods/results and table.

**Evidence:** [C10 report](../revisions/evidence/c10_report.md).

### M8. Paired inference and reproducibility

Report run-level paired effects, confidence intervals and corrected tests; separate initialization from adaptive search. Code/input/executable identities and actual device, worker and acquisition settings are recorded, distinguishing CLI overrides from defaults. Paired relative cost ratios and overlap-aware evaluation intervals substantiate the speed statement. Unmeasured fitting/acquisition/orchestration overhead remains combined; absolute runtimes and seed identities stay in supporting records.

**Tasks:** C04/C13. **Manuscript:** Primary comparison protocol/results; computational comparison.

**Evidence:** [C04 report](../revisions/evidence/c04_report.md), [C13 report](../revisions/evidence/c13_report.md).

## Minor comments

| Comment | Tasks | Response and disposition |
|---|---|---|
| 1 | C14 | All survey-case minima now use jointly feasible observations, with a reproducible population check. |
| 2 | C14 | Method/weighting names replace internal Phase labels and unsupported FEL/operational modes. |
| 3 | C15 | Full-range constraint plots retain all points and add accepted-region zooms; Pareto views remain scatter-only. |
| 4 | C10/C14 | The robustness table uses physical labels, readable type, exact feasibility uncertainty and component statistics. |
| 5 | C12 | The JINST abstract summary is distinguished from its tracked setting; unlike source/acceptance conventions are not interpreted as dominance. |
| 6 | C16/C17 | Emmerich pages 421–439 are verified from the author-group bibliography. ICABU is cited as an oral presentation. The abstract stays qualitative. Funding/acknowledgments remain explicitly author-deferred, so submission readiness is not claimed. |
| 7 | C15/C16 | Move detailed survey material to an appendix, shorten plotting explanations and consolidate limitations while retaining the scientific evidence. |

## Remaining scientific and author-controlled limits

Crest calibration and a quantitative tracking-refinement error bound remain unavailable. New corrected-method, constrained-scalarized, Sobol, broader-jitter and MOGA campaigns were not performed. Source-generation provenance and isolated causal mechanisms remain unestablished. These scope decisions may still concern the reviewer; neither reviewer agreement nor acceptance is presumed. Funding/acknowledgments must be supplied before submission.
