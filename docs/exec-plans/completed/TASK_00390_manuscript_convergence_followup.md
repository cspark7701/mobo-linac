# Task Completion Summary: Task 00390

## Summary
Added the emittance-convergence follow-up (steps 1, 2 and 3a; Tasks 00384–00387) to the manuscript at the author's request on 2026-11-20: "Was paper/main.tex updated with recent simulation results? If not, update it and compile it to generate pdf." The manuscript had not been updated since the round 6 close (`92c2914`). Both PRAB layouts were rebuilt. The supplement is unchanged.

## Key Changes
- **`docs/paper/main.tex`:**
  - **Abstract:** the emittances still fall with the integration step at refined grids and particle counts, while the ordering of settings is preserved.
  - **Contributions list:** one sentence on the 15-setting follow-up (up to 640k particles, 64 cells, an eighth of the production step, observed order about 1.5).
  - **Sec. problem:** pointer to the new subsection.
  - **New Sec. V D, "Follow-up convergence study"** (`sec:convergence_followup`):
    - step 1 rank stability of the 387 re-tracked evaluations;
    - the step 2 matrix and the step 3a step/update test;
    - Table `tab:convergence_followup` with the median changes and the share within 1 %;
    - order, Richardson remainders, adequacy, noise band, ranking and scope.
  - **Discussion and conclusions:** the remaining change is located mainly in the integration step; the eighth step lies about 0.5 % above the extrapolated limit.
  - **Appendix, "Follow-up convergence study" paragraph:** sources, levels, `Max_count`/`Max_scale`, rotated replicates, gates, pre-specification, the order formula and the cost.
- **`convergence_followup/README.md`:** records where the results now appear in the manuscript.

## Validation Results
- `latexmk` builds `main.pdf` and `main_twocolumn.pdf` with no errors, no undefined references and no overfull boxes (the new table was narrowed for the two-column layout).
- Paper-output, PRAB-submission, manuscript-hygiene, documentation-link and step-test tests: 69 passed.
- Every number in the new text was checked against `rs_*`, `rm_*` and `rq_*` outputs in `docs/paper/revisions/convergence_followup/`.

## Status
Committed locally. PDFs are regenerated locally and not tracked. Not pushed. The supplement and reviewer responses do not yet mention the follow-up.
