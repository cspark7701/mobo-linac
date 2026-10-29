# Task Completion Summary: Task 00295

## Summary
Consolidated round3 task C3-03: state the attribution of the feasible-sampling advantage per baseline, as an accounting decomposition (Reviewer 2 R1, Reviewer 1 M3).

## Key Changes
- **Abstract** (still without numbers): the advantage persists among energy-acceptable settings. It lies mainly in the transverse limits against unconstrained optimization, and in the energy band against weighted-sum optimization.
- **Contribution 2:** renamed an accounting, and stated per baseline. "It is not produced by …" becomes "Neither the effective step weight of the energy band nor the upper ACC3/ACC4 phase window explains it alone."
- **Sec. V C:**
  - the categories are an accounting of observed gaps, not a causal identification of acquisition terms;
  - the upper quarter "contributes, but is not the main source". Its lower mean occupancy, by 0.060 and 0.094, corresponds to about a fifth and a third of the gaps (`r2_attribution_runs.csv`);
  - the energy-conditional fractions compare method-selected populations and do not isolate an energy-independent mechanism.
- **Discussion and Conclusions:** the same per-baseline statement. The Discussion adds that both the energy band and the upper window contribute.
- **Task list:** C3-03 is ticked.

## Validation Results
- `tests/test_paper_outputs.py` passed (53), including the number-free abstract check.
- `latexmk` builds `main.pdf` (54 pages) without errors, undefined references or overfull boxes.
- A search for "mainly from", "largely from" and "not produced" returns no remaining overstatement.

## Status
Completed and committed locally. No push performed.
