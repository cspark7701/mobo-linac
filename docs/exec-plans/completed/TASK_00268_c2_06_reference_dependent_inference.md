# Task Completion Summary: Task 00268

## Summary
Complete consolidated round2 task C2-06. Separate feasible-fraction inference, which uses no estimated reference, from the reference-dependent quality indicators, and lead with effect sizes. Add the optional offline sensitivity analysis in which the empirical reference is rebuilt inside every group resample.

## Key Changes
- Add `scripts/analyze_revision_reference_resampling.py`. It resamples the ten matched groups 2,000 times and, in each resample, rebuilds the empirical reference front and the HV(25 %) reference from the resampled groups. The indicator definitions are those of the round1 C03 analysis; no p-values are derived. Output: `r2_rebuilt_reference_effects.csv` and its metadata.
- Results: the observed mean differences reproduce `c04_paired_effects.csv` exactly. Every constraint-aware interval excludes zero under both the fixed and the rebuilt reference:
  - against unconstrained MOBO: epsilon −0.481 to −0.161, IGD+ −0.293 to −0.071, HV 2.89 to 12.16;
  - against scalarized BO: −0.470 to −0.176, −0.244 to −0.066, and 3.76 to 16.09.
  - The HV intervals widen markedly, and all baseline-to-baseline intervals include zero.
- Manuscript, section 4.2: state that 0.0234 is the smallest Holm-adjusted value the design allows. Explain why sign enumeration after a shared data-derived transformation does not establish calibration, label the quality-indicator p-values exploratory, and describe the rebuilt-reference procedure.
- Results: the paired paragraph now leads with the feasible-fraction effects (ten of ten groups, no reference). It then gives the quality effects with both interval constructions, and reports the signed-rank values as uncalibrated. The Discussion is aligned.

## Validation Results
- `ruff check` passed. `tests/test_revision_reference_resampling.py`: 2 passed. `tests/test_paper_outputs.py`: 53 passed.
- Every quoted value was checked against `c04_paired_effects.csv` and `r2_rebuilt_reference_effects.csv`.
- `latexmk` built a 32-page PDF without undefined references or overfull boxes.

## Status
Completed and committed locally. No push performed.
