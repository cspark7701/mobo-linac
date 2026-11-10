# Response to Reviewer 2 — round6

**Status:** Point-by-point response for author review. It does not claim journal acceptance or submission readiness. Funding and acknowledgments and `\finaltrue` remain author decisions.

Thank you for the recommendation and the careful diff against round 5. All four editorial comments were adopted. On comment 5, the author ran the additional validation that Reviewer 1 requested; its results are summarized below because they change the text you accepted. Section numbers refer to the current two-column build. The new subsections renumber Results from V C onward: the predictive checks, your Sec. V G, are now V H.

## Requested before acceptance

### 1. Definition of the weighted-sum cost — adopted

Sec. III B now reads: "The weighted-sum baseline minimizes the scalarized cost, the sum of the physical objective values each divided by its reporting scale and multiplied by its weight, using a single GP."
- The scales (1 µm rad, 1 µm rad, 1 MeV) and the equal weights 1/3 are unchanged.
- The "weighted cost" of the attribution subsection and the "scalarized cost" of the predictive checks now refer to this definition.
- No displayed formula or implementation-sign explanation was added, in line with the author's earlier instruction.

## Editorial comments

### 2. Undercoverage hypotheses — adopted (second option)

"Kernel misspecification" was removed from Appendix D. The appendix now says that adaptive test points could account for the remainder and that this check does not test that hypothesis. The categorical kernel statement was not restored in the main text.

### 3. Abstract — adopted

- "specified" is restored: "We compare specified Bayesian optimization pipelines…".
- The closing sentence states what the results are not: "These findings apply to the nominal numerical model and acceptance profile and do not establish a physically resolved injector optimization."
- "persists in the tested diagnostic-shift scenarios" is kept.
- After comment 5's studies, the abstract also adds two number-free sentences: the advantage persists in the re-tracked stratified sample, and the tested normalized residuals sampled feasible settings less often. It is now 305 words (whitespace count).

## Optional comments

### 4. Source formatting — adopted

The paragraph "Several mechanisms could explain the undercoverage" was rewrapped. Its whitespace-normalized tokens are identical before and after.

### 5. The separate assessment (Task 00340 / Reviewer 1) — additional validation run

We understand that you did not make this a condition. The author nevertheless adopted Reviewer 1's re-tracking and normalized-residual requests; the constraint-aware scalarized arm was not adopted. Your medium-level suggestion is covered by the medium levels of the re-tracking.

- **Re-tracking (Sec. V C, Tables VI–VII).**
  - 387 stratified primary evaluations, including infeasible and baseline-method ones, were re-tracked at production and four refined levels.
  - 4 classifications changed, all toward feasibility, and the constraint-aware advantage stays positive in every group: 0.303/0.335 at the fine levels, against 0.248/0.280 at production, over 160 evaluations.
  - The emittances still differ by a median 5.5–7.4 % between the medium and fine levels. The non-convergence you anticipated referees would raise therefore remains, and the text says so.
- **Residual scaling (Sec. V G, Table VIII).** Ten matched pairs of campaigns found that threshold-normalized residuals at a common temperature lowered the feasible fraction by 0.118 (−0.136 to −0.099), in every group. The convention also changes the smoothing widths, so the effect of normalization alone remains unknown.

The scope statements you reviewed are unchanged except where these results add to them: Secs. II A, V B, VI C and the Conclusions.

## Validation

The two-column build has no undefined references or overfull boxes. Further checks are listed in the [round6 overview](../revisions/round6_revision_overview.md).
