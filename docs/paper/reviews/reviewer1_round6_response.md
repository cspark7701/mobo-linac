# Response to Reviewer 1 — round6

**Status:** Point-by-point response for author review. It does not claim journal acceptance, that Reviewer 1 agrees, or submission readiness. Funding and acknowledgments and `\finaltrue` remain author decisions. This report formalizes Task 00340, so it and that task are one assessment, not two.

Thank you for the two validation requests. The author adopted both (R6-01, R6-02) on 31 October 2026, froze their protocol before any outcome (`r6_protocol.md`, `r6_specification.json`), and ran them in full. The optional comparator (R6-04) was not adopted. One result supports the main comparison, and two are adverse; all are reported as measured. Section numbers refer to the current two-column build. The new subsections renumber Results from V C onward: the predictive checks, formerly V G, are now V H.

## R6-01. Representative numerical validation — adopted, completed; objective convergence unresolved

**Design (Sec. IV E).**
- **Sample.** Stratified simple random sampling of all 4,800 primary evaluations by method, matched group, production feasibility, search stage and distance to the nearest limit. Two evaluations were taken per nonempty stratum, giving 387 settings: 132 constraint-aware, 129 unconstrained and 126 scalarized. The sample includes rejected, baseline-method, near-boundary and interior observations.
- **Levels.**
  - Production.
  - Fixed-source medium and fine: the production file with 48/64-cell grids and half/quarter steps.
  - Combined medium and fine: additionally 20,000/40,000 particles from the reconstructed source.
- **Nominal reproduction.** Production-level reruns had to reproduce the archived values (rtol 1e-9) before refinement. All 387 did.
- **Estimation.** Weighted per-run fractions use the inclusion probabilities and stratified design variances, with ten-group bootstrap intervals conditional on the sample.

**Results (Sec. V C, Tables VI–VII).**
- **Validity.** All 1,935 attempts were valid; there were no failures to account for.
- **Classifications.** 4 of 387 changed (3 at medium, a fourth at fine), all from infeasible to feasible.
  - All four are constraint-aware evaluations whose largest violation was a bunch length at most 6.5 µm over the limit.
  - No baseline classification changed, and no feasible evaluation became infeasible.
- **Feasible-sampling comparison: supported at the tested levels.**
  - The weighted constraint-aware fraction rises from 0.405 to 0.460 (design SE 0.027). The baseline fractions are unchanged.
  - The paired advantages over all 160 evaluations go from 0.248/0.280 at production to 0.303/0.335 at both fine levels.
  - The fine-level intervals are 0.254–0.352 and 0.290–0.383, and the advantage is positive in all ten groups.
- **Objective values: adverse, unresolved.**
  - Fine vs production: emittances lower by a median 21 % and 29 % (range +4 to −75 %).
  - Fine vs medium: they still differ by a median 5.5 % and 7.4 %, and only 3–7 % of settings meet the declared 1 % objective tolerance.
  - The emittances are therefore not converged at the finest tested level. The protocol forbids further refinement chosen after seeing this, so convergence of the objectives remains an open limitation (Secs. V C and VI C, Conclusions).
- **Other quantities.**
  - Energy spread meets its tolerance at 82–85 % of settings.
  - Beam sizes meet theirs at 66–76 % and mean energy at 61–64 %.
  - Fixed and combined levels give identical classifications.

**Achieved precision.** Design SE 0.023 (medium) and 0.027 (fine) for each constraint-aware run-level estimate. These re-tracked historical settings are not refined optimization trajectories, and the front-quality indicators are still not tested at a converged resolution.

**Evidence:** S1.16 (`r6_resolution_*`, from `scripts/analyze_revision_round6.py` and `scripts/summarize_revision_round6.py`).

## R6-02. Matched residual-convention comparison — adopted, completed; adverse to the tested convention

**Design (Sec. IV E).**
- **Campaigns.** Ten pairs of new constraint-aware campaigns (groups 42–51), 160 evaluations each, with identical initial Sobol designs, model and acquisition budgets, and per-iteration random streams within each pair.
- **Normalized arm.**
  - Residuals are divided by 1e-3 (sizes, divergences, bunch length), 5 MeV (each energy side) and 0.1 (transmission), at temperature 1e-3.
  - Its physical widths are 1 µm, 1 µrad, 5 keV and 1e-4, against 1 mm, 1 mrad, 0.001 eV and 1e-3 in the raw arm.
  - The test is therefore of this normalization-and-temperature convention, as you asked us to state.
- **Pre-run checks.** Mock and analytic tests passed before any campaign ran. They covered residual signs and unit consistency, real q=8 acquisition gradients on CPU and CUDA, and mode-preserving checkpoint restoration (round6 overview).

**Results (Sec. V G, Table VIII).**
- **Validity and proposals.** All 3,200 evaluations were valid. Three of 360 batches used the retry tier after a non-finite gradient, and none fell back to Sobol.
- **Primary endpoint.** Normalized minus raw is −0.118 over all evaluations (95 % paired bootstrap interval −0.136 to −0.099). It is negative in every group, from −0.169 to −0.063.
- **Supporting endpoint.** After initialization the difference is −0.131 (−0.151 to −0.110).
- **Violations.** The normalized arm had more multi-group and transverse-only violations and fewer bunch-length-only ones. The violation counts are not used to infer a mechanism.
- **Cost.** Normalized campaigns were on average 0.43 h shorter (8 of 10 groups); this is descriptive, on a shared host.
- **Resolution of ten groups.** The effect is large relative to its interval and consistent in sign, so ten groups resolve the direction of the tested convention's effect. They cannot separate normalization from the width change, because no width-preserving arm was run (Limitations).

**Manuscript changes.**
- The unit-dependence statements stay.
- The abstract, contributions, discussion, limitations and conclusions now state that this convention lowered feasible sampling.
- No convention that improves on the recorded one is claimed.

**Evidence:** S1.16 (`r6_scaling_*`).

## R6-03. Exploratory status of objective-quality analyses — retained

The failed fixed-reference hypervolume endpoint and the post-hoc labels of the replacement indicators are unchanged. The new studies add no front-quality endpoint; their predeclared endpoints are feasible fractions only. The text keeps feasible sampling and front quality separate.

## R6-04. Constraint-aware scalarized comparator — not adopted

The author omitted this optional arm on 31 October 2026. The limitation stays explicit (Sec. VI C), and no unique MOBO advantage over constraint-aware scalarization is claimed. The raw/normalized comparison does not substitute for it.

## R6-05. Response, evidence and validation

- Every item above has a status: adopted and completed (R6-01, R6-02), retained (R6-03), or not adopted with its limitation (R6-04).
- **Unresolved items:** convergence of the objective values, and separating normalization from smoothing width.
- **Preserved:** the original runs, prior reviews and responses.
- **New evidence:** mapped file by file in S1.16 with generators and inventory levels.
- **Validation:** see the [round6 overview](../revisions/round6_revision_overview.md). Completing these tasks is not taken to mean that you accept the manuscript.
