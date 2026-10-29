# Task Completion Summary: Task 00301

## Summary
Consolidated round3 task C3-09: word the explanations of surrogate undercoverage as hypotheses (Reviewer 1 minor 2).

## Key Changes
- **Sec. V G.**
  - "Three causes plausibly contribute" becomes "Three hypotheses could explain the undercoverage; none is isolated here."
  - The inferred-noise refit is described as showing that coverage is sensitive to the regularization. Kernel misspecification and adaptive test points remain hypotheses for the remainder, and the check does not test them.
  - The 88 refits restored to initial hyperparameters are stated to be non-equivalent fits that the archived refit records do not identify, so the reported refit coverage includes them.
- **Optional item not done.** `r2_calibration_refit_predictions.csv.gz` has no fallback flag, so splitting the coverage would require redoing the refits. The item is left unchecked in the task list.
- **Limitations.** Already descriptive ("only partly removed by inferred noise"); unchanged.
- **Task list:** C3-09 is ticked, apart from the optional item.

## Validation Results
- `tests/test_paper_outputs.py` passed (53).
- `latexmk` builds `main.pdf` without errors, undefined references or overfull boxes.

## Status
Completed and committed locally. No push performed.
