# C14 — Consistent scientific tables

## Status
Completed. All main survey extrema now use jointly feasible observations; raw observations and archived tables remain unchanged.

## Reproduction and checks
Run `python scripts/prepare_revision_tables.py` after the original paper reproduction steps. It verifies the seven survey-run evaluation CSV completion hashes, calculates feasible-only extrema and nondominated counts, and regenerates results_table.tex and phase1_cases_table.tex. The five-case derived summary and input hashes are retained here. The primary-table generator now uses readable short method headers and normal small table text instead of whole-table resizing. C10 supplies the component-based robustness table.

## Changes
Replace internal Phase labels and unsupported FEL/operational-mode names with method and weighting names. Remove unused reference-point language. Put physical units in table captions/headers using siunitx and preserve the meaning of coordinate-wise extrema. All weighting cases use 176 evaluations; their aggregate is explicitly 880 versus 176 per MOBO survey. Primary budget and paired-run bootstrap interpretation remain unchanged. Weighted fractions display rounded values; full executed weight vectors are in the evidence CSV.

Several previously attractive case minima were infeasible. For example, the emittance-emphasis case's all-valid minimum energy spread of 0.2984 MeV is replaced by its feasible minimum of 0.3672 MeV. The spread-emphasis case has a feasible minimum of 0.3969 MeV; its name identifies objective weighting, not a guaranteed best outcome. These corrections change the presentation population, not the measured data.

Seven focused population/manuscript tests passed, including a synthetic rejected point with better objectives that must not enter the feasible extrema. The paper builds without overfull table boxes or undefined references.
