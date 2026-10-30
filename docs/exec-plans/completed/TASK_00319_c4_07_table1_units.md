# Task Completion Summary: Task 00319

## Summary
C4-07 of the round4 revision (Reviewer 1 C3). Table I (`tab:resolution`) now gives every entry one unambiguous unit and convention. No value was changed.

## Key Changes
- **Units.** The column headings no longer say percent. A "Relative change [%]" block holds the emittance, energy-spread, size, divergence and bunch-length rows. A separate "Absolute change [MeV]" block holds the mean energy.
- **Conventions in the caption.**
  - "Fine" and "step only": signed changes relative to the production value.
  - "Fine vs medium": the largest magnitude of the difference between the two combined levels, relative to the medium value.
  - "Source s.d.": the standard deviation over five random sources, relative to the production value.
  - Mean energy is recorded to 0.01 MeV.
- **Missing entry filled.** The step-only mean-energy cell was a dash. It now gives the recorded range −0.04 to 0.01 MeV from the same evidence file.
- **Layout.** Column spacing widened slightly.
- Task C4-07 is marked done in the consolidated round4 task list.

## Validation Results
- Every entry was recomputed from `docs/paper/revisions/evidence/r2_convergence_values.csv`:
  - signed fine and step-only ranges relative to the production value;
  - |fine − medium| / medium;
  - sample s.d. of the five random sources relative to the production value.

  All match the table. The denominators stated in the caption are the ones that reproduce the values.
- The preprint builds to 57 pages and the reprint check copy to 31, both without errors, undefined references or overfull boxes. The rendered table was inspected; the check copy was deleted afterwards.

## Status
Completed and committed locally. No push performed. No simulation was run.
