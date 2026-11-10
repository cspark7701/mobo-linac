# Response to Reviewer 3 — round6

**Status:** Point-by-point response for author review. It does not claim journal acceptance or submission readiness. Funding and acknowledgments and `\finaltrue` remain author decisions.

Thank you for the review. Comments 1, 3, 4 and 5 were adopted. Comment 2 was adopted in part: the phase convention is clarified, but the velocity-bunching statement is not added. On comment 6, the author ran a larger re-tracking than you suggested, for Reviewer 1.

One correction to the report: the primary comparison uses 160 evaluations per campaign (30 campaigns, 4,800 evaluations). 176 is the budget of each survey campaign. Section numbers refer to the current two-column build. New subsections renumber Results from V C onward, so the predictive checks, your Sec. V G, are now V H.

## 1. Scalarized baseline target — adopted

Sec. III B now reads: "The weighted-sum baseline minimizes the scalarized cost, the sum of the physical objective values each divided by its reporting scale and multiplied by its weight, using a single GP."
- The scales and equal weights are unchanged.
- The "weighted cost" and "scalarized cost" passages now refer to this definition.
- The prose form follows the author's instruction not to restore the displayed formula.

## 2. RF phase convention and velocity bunching — convention adopted, bunching statement not adopted

**Disposition:** the phase convention is clarified as requested. The velocity-bunching statement is not adopted, because the tracked data do not support it.

- **Phase reference.** Automatic phasing is off (`Auto_phase=F` in `astra.in`), so the inputs are absolute wave phases at the start of tracking. Zero phase is neither the crest nor the zero crossing, and a phase of −39.5° is not an off-crest angle of −39.5°.
- **Gain maxima.** We fitted the tracked gain of each structure to A cos(φ − φ_max) across the 387 stored production-resolution settings. No new simulation was run.

| Structure | φ_max | Nominal phase minus φ_max | Fitted amplitude |
|---|---|---|---|
| ACC1 | −26.8° | −12.7° | 47.2 MeV |
| ACC2 | −39.3° | −0.2° | 47.3 MeV |
| ACC3 | 309.4° | +0.6° | 52.0 MeV |
| ACC4 | 298.3° | +11.7° | 52.0 MeV |

  So ACC2 and ACC3 run close to their gain maxima at the nominal phases, and ACC1 and ACC4 about 12–13° away on opposite sides.
- **Bunch length.**
  - The beam enters ACC1 at 4.05–4.13 MeV, slightly below the ~5 MeV of your comment.
  - Its RMS bunch length from the ACC1 entrance to the ACC2 exit changes by −3.6 % to +2.3 % across the settings (median −0.8 %). That is not the substantial compression the proposed sentence would describe.
  - These phases are also not near a zero crossing, so we do not state that off-crest operation provides velocity bunching.
- **Limits.**
  - The fit describes the gain maximum of this model, not an RF calibration of a machine, so the manuscript's statement that physical crest calibration is unavailable stands.
  - The ACC1/ACC2 window spans only 8°, so the crest there rests on the amplitude fit without an offset; the two amplitudes agree, and ACC1's fit residual is 0.24 MeV RMS.
  - The bunch-length figures are RMS values at production resolution.

**Location:** Sec. II B. **Evidence:** `r6_rf_phase_fit.json` (S1.15), from `scripts/analyze_revision_round6_rf_phase.py`.

## 3. Undercoverage hypotheses — adopted (first option)

"Kernel misspecification and" was removed from Appendix D. The adaptive-test-point hypothesis stays conditional, and the appendix still says that the check does not test it.

## 4. Abstract scope — adopted

- "specified" is restored.
- The closing sentence now reads "These findings apply to the nominal numerical model and acceptance profile and do not establish a physically resolved injector optimization." This keeps your boundary wording, with "do not establish" in place of "are not".
- The abstract remains number-free. After the new studies it also states their two findings, and it is now 305 words.

## 5. Source formatting — adopted

The undercoverage paragraph was rewrapped. Its whitespace-normalized tokens are unchanged.

## 6. Re-tracking — performed, at a larger scale than suggested

You considered this unnecessary for acceptance. Reviewer 1 requested it, and the author adopted it. The study used the frozen stratified sample of 387 primary evaluations rather than 5–10 Pareto points, at production and four refined levels with up to 40,000 particles (Sec. V C):
- 4 classifications changed, all toward feasibility.
- The feasible-sampling advantage stays positive in every group.
- The emittances still differ by a median 5.5–7.4 % between the two finest levels, so the paper keeps its statement that they are not converged.

A matched normalized-residual comparison (Sec. V G) found that the tested convention lowered feasible sampling in every group.

## 7. Response and validation

This response and those to Reviewers 1 and 2 are attributed separately. Validation is listed in the [round6 overview](../revisions/round6_revision_overview.md).
