# Task Completion Summary: Task 00382

## Summary
Step 1 of the emittance-convergence follow-up. Measured from the completed round 6 re-tracking whether the ordering of settings by each objective is stable across numerical levels, even though the absolute emittances are not converged. No simulation was run, and the manuscript and supplement are unchanged, as the author instructed.

## Key Changes
- **`scripts/analyze_rank_stability.py`.**
  - Reads the round 6 journal after checking the journal against its completion record and each record against its checksum. It joins the records to the sample manifest.
  - Reports, for six level pairs and three objectives, overall and per method:
    - Spearman correlation, with a cluster-bootstrap interval over the ten groups;
    - Kendall correlation;
    - the share of setting pairs in the same order: all pairs, pairs more than 1/5/10 % apart, and pairs from the same campaign;
    - the median signed shift.
- **`tests/test_rank_stability.py`** (5 tests): pair-order arithmetic with gaps and groups, perfect stability under scaling, detection of a reversed level, rejection of a tampered journal, and writing of the outputs.
- **New folder `docs/paper/revisions/convergence_followup/`**, kept outside `evidence/` so the supplement map stays unchanged. It holds:
  - `rs_rank_stability.csv` and `rs_rank_summary.json`;
  - a README with the results table;
  - the particle-only ladder draft, moved here and marked superseded, not adopted.

## Results
- **Production → combined fine.**
  - Spearman 0.979 (ε_x) and 0.962 (ε_y).
  - Same order in 94.1 % and 92.0 % of all pairs; 95.6 % and 93.6 % of pairs more than 5 % apart.
  - The median shift is −23 % and −31 %.
- **Fixed medium → fixed fine:** Spearman 0.993 and 0.989; 97.0 % and 96.2 % of pairs in the same order.
- **10k → 40k at fine:** Spearman 0.999.
- **Energy spread:** Spearman 1.000 at every level pair.
- **Per method:** results are similar across the three methods.
- **Reading:** rankings depend only weakly on resolution, but a minority of pairs swap order. This does not show that the absolute emittances converge.

## Validation Results
- `tests/test_rank_stability.py`: 5 passed (script coverage 99 %; only the `__main__` line is uncovered).
- `tests/test_supplement_map.py` and `tests/test_docs_links.py`: passed.
- `ruff check` on the new files: passed.
- Full suite not rerun; `mobo_linac` is unchanged.

## Status
Completed and committed locally. Manuscript and supplement not modified. No push performed.
