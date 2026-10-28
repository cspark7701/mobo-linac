# Task Completion Summary: Task 00282

## Summary
Complete consolidated round2 task C2-14: analyze the ten-seed budget-matched Sobol arm (seeds 42–51, 160 scrambled-Sobol points each, no acquisition) and integrate it into the manuscript, the supplement and the task list.

## Key Changes
- **Analysis (`scripts/analyze_revision_space_filling.py`, `tests/test_revision_space_filling.py`).**
  - New `sobol_quality`: additive epsilon and IGD+ of each Sobol arm's terminal feasible front against the unchanged empirical reference (`c03_empirical_reference.csv`), with the pipelines' values at 160 evaluations taken from `c03_run_histories.csv`. It also counts the reference points dominated by Sobol feasible points. Paired bootstrap intervals are computed against each pipeline.
  - `--part sobol` now also writes `r2_sobol_arm_quality.csv` and `r2_sobol_arm_quality_paired.csv`.
  - New test checking the quality scores against a small reference.
  - The existing checks remain: each seed's first 16 points equal the shared initial design, the ledger checksums match, and recomputed feasibility agrees with the recorded labels.
- **Evidence:** `docs/paper/revisions/evidence/r2_sobol_arm_{runs,paired,quality,quality_paired}.csv`; `r2_space_filling_metadata.json` regenerated.
- **Result.**
  - 41 of the 1,440 post-initialization points are feasible: 2.8 % (exact 95 % interval 2.1–3.8 %).
  - Mean paired differences in feasible fraction against the Sobol arm: 0.418 (0.384–0.453) for constraint-aware MOBO, 0.142 (0.115–0.172) for unconstrained MOBO and 0.107 (0.088–0.127) for scalarized BO. All are positive in all ten matched groups.
  - Transverse violations: 95.3 % against 76.0 % for the baselines. Bunch-length violations: 55.1 % against 32–33 %. Energy-band violations: 39.0 % against 32.2 % and 42.6 %.
  - Post hoc front quality: the Sobol arm's median epsilon is 1.45 and median IGD+ 1.14. Every pipeline is better, with paired intervals excluding zero.
- **Manuscript (`docs/paper/main.tex`).**
  - The space-filling paragraph in "Sources of the feasible-sampling difference" is rewritten around the matched arm.
  - The section 4.2 scope statement and the Limitations now name only the constraint-aware scalarized control as missing.
  - One qualitative clause in the abstract (no numbers) and one sentence in the Conclusions.
  - Contribution 4 of the Introduction now says "specific to the constraint-aware pipeline".
- **Supplement:** four evidence files mapped to S1.6. The README S1.6 row is updated, and `ledger_manifest.json` is rebuilt with the Sobol ledgers (215 ledgers, 8 step records).
- **Task list:** the C2-14 section, the status table and the run notes are updated. Contribution 4 is confirmed in C2-10, and C2-12 is marked running.
- The Reviewer 2 response (N3 and the assessment table) was updated, but remains an uncommitted C2-11 draft.

## Validation Results
- `ruff check scripts tests` and `scripts/verify_docs_sync.py` passed.
- `tests/test_revision_space_filling.py` and `tests/test_supplement_map.py` passed (6 tests).
- `scripts/build_supplement_manifest.py` check passed.
- `latexmk` built `main.pdf` (37 pages) without undefined references.

## Status
Completed and committed locally. No push performed. The resolution check (C2-12) started automatically at 21:40 on 2026-10-28.
