# Task Completion Summary: Task 00297

## Summary
Consolidated round3 task C3-05: describe the reach of the TDR acceptance region without claims about the geometry of the control domain or about which controls are needed (Reviewer 1 M3), and correct the Conclusions on refined TDR membership (Reviewer 2 R3(a)).

## Key Changes
- **Abstract** (no numbers): TDR requirements are met by only a few sampled settings "with small diagnostic margins". "At the edge of the explored domain" is removed.
- **Contribution 3:** TDR-feasible observations are rare at this budget and resolution, lie within micrometres of the diagnostic limits, and change membership under refinement.
- **Sec. VI B:**
  - It opens with the observed scarcity and closeness to the limits.
  - It gives the normalized controls of the candidates. Candidate A lies between 0.48 and 0.86 in every coordinate; candidate B is interior except for a gun phase of 0.96. These are computed from the primary ledgers and the Table I bounds.
  - It states that two points do not locate a feasible region in six dimensions, and that three finite-budget campaigns do not show the region is inaccessible.
  - The additional RF and matching controls of the full TDR linac become design options for future studies.
- **Conclusions:**
  - The refined-membership sentence now matches Sec. VI B: the settings meet the inequalities at the combined medium and fine levels but fail with four of five regenerated sources.
  - "Reach the TDR region only at the edge of the explored domain" and "probably the additional … controls" are replaced.
- **Task list:** C3-05 is ticked. The refined TDR membership will be updated when the stage A ladder results exist.

## Validation Results
- `tests/test_paper_outputs.py` passed (53).
- `latexmk` builds `main.pdf` without errors, undefined references or overfull boxes.
- No "edge of the explored domain" wording remains.

## Status
Completed and committed locally. No push performed.
