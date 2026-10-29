# Task Completion Summary: Task 00294

## Summary
Consolidated round3 task C3-02: bound the primary comparison under the refinement shifts measured by C2-12, and make the resolution result visible. This task uses existing data only, and the route (b) stage A ladder keeps running.

## Key Changes
- **Analysis (`scripts/analyze_revision_resolution_bounds.py`, test `tests/test_revision_resolution_bounds.py`).**
  - It reclassifies the 4,800 primary and 1,600 Sobol-arm evaluations under 27 shift combinations:
    - sizes and divergences ×0.78, 0.89 or 1 (0.78 is the largest fine-level reduction);
    - σ_z ×0.99, 1 or 1.01;
    - E ±0.05 MeV.
  - It writes per-run fractions and paired group-bootstrap differences (10,000 resamples). Comparisons with the Sobol arm are made after initialization only.
  - Evidence: `evidence/r3_resolution_bounds_{runs,paired}.csv` and `_metadata.json`, mapped to S1.13.
- **Results.**
  - Median feasible fraction:
    - constraint-aware: 0.369–0.466 (nominal 0.406);
    - unconstrained: 0.147–0.213;
    - scalarized: 0.113–0.181.
  - Post-initialization paired differences:
    - against unconstrained MOBO: 0.239–0.294;
    - against scalarized BO: 0.279–0.335.
  - Every interval excludes zero, and every difference, including each pipeline over the Sobol arm, is positive in all ten groups under every shift.
  - A bunch that is 1 % longer lowers the constraint-aware mean from 0.405 to 0.364, against 0.157 → 0.145 and 0.125 → 0.113 for the baselines.
- **Manuscript (`docs/paper/main.tex`).**
  - New Table `tab:resolution` in Sec. II A: fine-level, step-only, fine-vs-medium and source-spread changes per quantity.
  - Sec. II A separates the fixed-source step refinement from the regenerated sources, and states that the ten tested settings contain no rejected or baseline observation.
  - New bounding paragraph and front-quality caveat in Sec. V B; caveat in the Discussion.
  - The Conclusions and Limitations name the tested population and the bounding result.
- **Task list.** C3-02 is ticked, with its result.

## Validation Results
- `tests/test_revision_resolution_bounds.py` (2) and `tests/test_paper_outputs.py` (53) passed; `ruff check scripts tests` passed.
- The supplement manifest check passed.
- `latexmk` builds `main.pdf` (54 pages, one column) without errors, undefined references or overfull boxes.

## Status
Completed and committed locally. No push performed. On route (b), the stage B refined classifications will supersede these bounds as the main evidence.
