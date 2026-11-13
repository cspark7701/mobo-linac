# Task Completion Summary: Task 00385

## Summary
At the author's request on 2026-11-13, made a check of the step 2 convergence matrix that needs no new runs, then drafted a step 3a protocol for convergence of the quarter step. No simulation was run. The draft is not frozen or authorized. The manuscript and supplement are unchanged.

## Key Changes
- **`scripts/explore_convergence_sensitivity.py`** (new, post hoc, labelled exploratory). From the completed step 2 journal it computes:
  - per-setting sensitivity to particles, grid and step;
  - the exit-plane properties of each setting at `half_g64_n640k`;
  - Spearman associations, with unadjusted p-values;
  - feasible / infeasible strata.
- **Outputs** in `docs/paper/revisions/convergence_followup/`: `rm_sensitivity_by_setting.csv`, `rm_sensitivity_correlations.csv`, `rm_sensitivity_strata.csv` and `rm_sensitivity_summary.json`.
- **`rq_protocol_draft.md`** (new, DRAFT). It covers 15 settings at 64 cells and 160k particles.
  - **Levels:** step half, quarter and eighth; `Max_count` 10 and 1; and three rotated quasi-random source replicates for a sample-noise band. That is 120 attempts in total.
  - **Pre-freeze checks:** confirm what `Max_count` does in ASTRA, and check the rotated sources.
  - **Endpoints:** the mechanism (update interval versus step), the observed order with Richardson extrapolation, and a 1 % adequacy rule that accounts for the noise band.
  - **Rules and estimate:** interpretation rules, and an estimate of about 210–420 CPU-h.
  - **Open decisions** are left for the author.
- **`convergence_followup/README.md`:** the exploratory findings, and the file list.
- **`tests/test_convergence_matrix.py`:** one test of the exploratory functions on synthetic data.

## Findings (exploratory, 15 settings)
- **Sensitivity is a property of the setting.** The particle, grid and step changes rank the settings alike (Spearman 0.65–0.81).
- **Infeasible settings change more.** The six infeasible settings all have a transverse rms size above 1 mm. Their median change is 4.9 %, against 1.4 % for the nine feasible settings (p = 0.012, unadjusted).
- **Exit-plane associations.** Sensitivity follows beam size (ρ 0.56) and size × divergence (ρ 0.61), not the aspect ratio. Transmission is 1 everywhere.
- **The step change remains among feasible settings:** −2.1 to −2.4 % (ε_x) and −3.0 to −3.2 % (ε_y), with 0 of 9 within 1 %.
- **Particles are nearly converged for feasible settings:** 8 of 9 stay within 1 % for 160k → 640k at 64 cells.
- **A space-charge cause is possible.** The template's space-charge field reuse (`Max_count=10`, `Max_scale=0.01`) makes the update interval scale with `H_max`. This is a candidate cause of the step change.

## Validation Results
- `tests/test_convergence_matrix.py`, `tests/test_rank_stability.py` and the documentation-link, documentation-sync and supplement-map tests: 22 passed.
- `ruff check` on the new and changed Python files: passed.

## Status
Committed locally. No push performed. Step 3a needs the author's decisions on the open items and separate authorization before any freeze or run.
