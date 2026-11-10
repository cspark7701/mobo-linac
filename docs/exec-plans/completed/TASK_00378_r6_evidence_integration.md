# Task Completion Summary: Task 00378

## Summary
Integrated the completed round6 studies into the manuscript and supplement (A6-08). Both results are reported as measured, including the adverse ones. The re-tracking keeps the feasible-sampling comparison but leaves the emittances unconverged at the finest level, and the tested normalized-residual convention lowered feasible sampling in every group.

## Key Changes
- **Evidence (`scripts/summarize_revision_round6.py`, test `tests/test_revision_round6_summary.py`).**
  - `--collect` checks each analysis output against its receipt, the frozen specification and the completion record, then copies it to `docs/paper/revisions/evidence/` (`r6_collection.json`). It also tabulates the proposal tiers (`r6_scaling_proposals.csv`).
  - Without `--collect`, it rewrites `r6_resolution_summary.json`, `r6_scaling_summary.json` and the three tables the manuscript inputs, using only the evidence files.
- **Re-tracking (387 settings, 5 levels, 1,935 valid attempts).**
  - 4 classifications changed, all infeasible to feasible. All 4 are constraint-aware, with bunch length within 6.5 µm of the limit.
  - Weighted constraint-aware fraction: 0.405 to 0.460 (design SE 0.027). The baselines are unchanged.
  - Paired advantages over unconstrained and scalarized BO: 0.248/0.280 at production, 0.303/0.335 at fine, positive in all groups.
  - Emittances, fine vs production: median −21 % (horizontal) and −29 % (vertical).
  - Emittances, fine vs medium: median 5.5 % and 7.4 %. The 1 % tolerance is met by only 3–7 % of settings, so the objectives are not converged.
- **Scaling (20 campaigns, 3,200 valid attempts).**
  - Normalized minus raw: −0.118 [−0.136, −0.099] over all attempts and −0.131 after initialization. No group was positive.
  - Proposal tiers: 3 retry batches, no Sobol fallback.
  - The result concerns the tested convention, which also changes the smoothing widths.
- **Manuscript (`docs/paper/main.tex`).**
  - New subsections: "Prospective validation studies", "Re-tracked sample of primary evaluations" and "Constraint-residual scaling", with Tables `tab:retracking`, `tab:retracking_values` and `tab:scaling`.
  - Abstract: still number-free, and the phrase "persists in the tested diagnostic-shift scenarios" is kept.
  - Also updated: the six-item contribution list, Sec. II B pointer, methods pointer, discussion, limitations, conclusions and smoothing appendix.
- **Supplement.**
  - New item S1.16, with S1.15 retitled.
  - Two generators added to `input_inventory.csv`, both at level 2b.
  - README section rewritten.
  - `tests/test_supplement_map.py` now expects S1.1–S1.16.
- **Status records.** Dated results notes and per-task status lines added to the consolidated list, the validation plan and the overview. C6-09/A6-09 stay open.

## Validation Results
- Summary tests: 7 passed. Round6 tests together: 38 passed.
- Manuscript, supplement and documentation-related test files (7 files): 76 passed, 1 failure caused by the new S1.16 item. After updating that expectation, `tests/test_supplement_map.py` passes (4).
- `ruff check src scripts tests`, `scripts/build_supplement_manifest.py` and `scripts/verify_docs_sync.py` passed.
- Builds: `main.tex` 61 pages and `main_twocolumn.tex` 34 pages, with no errors, undefined references or overfull boxes. The new tables were inspected visually in the two-column PDF.
- **Full test suite: not rerun in this step.** It runs again at the round close (step 8).

## Status
Completed and committed locally. No push performed. Reviewer responses, the overview diff/hash inventory, the upload folder and the final full validation (C6-09/A6-09) remain.
