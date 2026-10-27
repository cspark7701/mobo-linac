# Task Completion Summary: Task 00266

## Summary
Complete consolidated round2 task C2-02. Identify the executed constrained acquisition consistently, and attribute the feasible-sampling advantage to violated constraint channels using the archived primary evaluations only.

## Key Changes
- Add `scripts/analyze_revision_attribution.py`. It classifies each post-initialization evaluation (17–160) into exclusive violated-channel categories under the production profile. It checks the recomputed feasibility against the recorded labels, divides each paired feasible-fraction gap exactly among the categories, and reports upper ACC3/4-quarter occupancy per batch and the feasible fraction conditional on the energy band, with 10,000-resample paired bootstrap intervals.
- New evidence: `r2_attribution_{runs,batches,paired,gap}.csv` and `r2_attribution_metadata.json`, with input checksums. New figure: `figures/revision_attribution.pdf`.
- Findings. The advantage is not mainly the energy boundary:
  - Against unconstrained MOBO, transverse-only violations account for 62 % of the 0.276 gap, and the energy-involving categories for 34 %.
  - Against scalarized BO, energy-involving categories account for 63 % and transverse-only violations for 31 % of the 0.311 gap.
  - Among energy-acceptable evaluations, the constraint-aware median feasible fraction is 0.578, against 0.254 and 0.231; the paired differences are 0.328 and 0.342, positive in all ten groups.
  - The upper ACC3/4 quarter holds 15.3 % of constraint-aware post-initialization evaluations, against 22.6 % and 24.7 %; every evaluation there violates the energy band.
- Manuscript edits:
  - Section 3.2 states that the energy weight is an effective step, and that the compared method is the raw-residual implementation.
  - Section 4.1 describes three specified pipelines that differ in more than the acquisition formula.
  - The offline-sensitivity subsection states the q = 1, unpruned, one-run probe limits.
  - A new Results subsection with a figure gives the attribution.
  - The Discussion, Conclusions and abstract carry the transverse-limit finding qualitatively.

## Validation Results
- `ruff check` passed.
- `tests/test_revision_attribution.py`: 13 passed (exclusive categories, inclusive limits, exact gap decomposition, quarter boundary).
- The paper and revision suites: 86 passed.
- `latexmk` built a 32-page PDF without undefined references or overfull boxes. The figure was inspected visually.

## Status
Completed and committed locally. No push performed. The round2 simulations continue in the background.
