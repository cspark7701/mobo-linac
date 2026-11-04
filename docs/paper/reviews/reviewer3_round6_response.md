# Response to Reviewer 3 — round6

**Status:** In progress. Only comment 2 has a disposition so far; the remaining comments are mapped in the [consolidated task list](../revisions/consolidated_round6_revision_tasks.md#reviewer-3-reconciliation--2026-11-02) and will be answered when the round closes. This record does not claim journal acceptance.

## Comment 2. RF phase convention and velocity bunching

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
- **Bunch length.** The beam enters ACC1 at 4.05–4.13 MeV, slightly below the ~5 MeV of your comment. Its RMS bunch length from the ACC1 entrance to the ACC2 exit changes by −3.6 % to +2.3 % across the settings (median −0.8 %). That is not the substantial compression the proposed sentence would describe, and these phases are not near a zero crossing, so we do not state that off-crest operation provides velocity bunching.
- **Limits.** The fit describes the gain maximum of this model, not an RF calibration of a machine, so the manuscript's statement that physical crest calibration is unavailable stands. The ACC1/ACC2 window spans only 8°, so the crest there rests on the amplitude fit without an offset; the two amplitudes agree, and ACC1's fit residual is 0.24 MeV RMS. The bunch-length figures are RMS values at production resolution.

**Location:** Sec. II B. **Evidence:** `r6_rf_phase_fit.json` (S1.15), from `scripts/analyze_revision_round6_rf_phase.py`.
