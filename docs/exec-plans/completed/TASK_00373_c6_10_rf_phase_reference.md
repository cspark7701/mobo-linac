# Task Completion Summary: Task 00373

## Summary
Closed C6-10 (Reviewer 3 comment 2). The RF phase convention is now clarified in Sec. II B from the input deck and a fit of stored runs. The requested statement that off-crest ACC1/ACC2 operation provides velocity bunching is not adopted, because the stored runs show no substantial compression. No simulation was run.

## Key Changes
- **Analysis.** `scripts/analyze_revision_round6_rf_phase.py` (test `tests/test_revision_round6_rf_phase.py`) fits each structure's tracked gain to A cos(φ − φ_max) across the 387 stored production-resolution settings and reads the RMS bunch length at the structure edges. Output: `r6_rf_phase_fit.json`.
- **Findings.**
  - Gain maxima: ACC1 −26.8°, ACC2 −39.3°, ACC3 309.4°, ACC4 298.3°.
  - Nominal phase minus maximum: −12.7°, −0.2°, +0.6°, +11.7°. So −39.5° is an absolute wave phase, not an off-crest angle.
  - ACC1 entry energy 4.05–4.13 MeV, below the reviewer's ~5 MeV.
  - Bunch length from the ACC1 entrance to the ACC2 exit: −3.6 % to +2.3 %, median −0.8 %.
- **Manuscript (`main.tex`, Sec. II B).** One passage after "not calibrated off-crest angles" gives the zero-phase statement, the maxima, the nominal offsets, the entry energy and the bunch-length change. The limitation that physical crest calibration is unavailable stands: the fit describes this model, not a machine.
- **Records.** `reviewer3_round6_response.md` is started with this disposition only; the S1.15 map, input inventory and README cover the evidence; C6-10 is ticked in the consolidated list.

## Validation Results
- Focused tests passed (65): the RF-phase, supplement-map, documentation-link, manuscript-hygiene and paper-output tests.
- `ruff check scripts tests`, `scripts/verify_docs_sync.py` and `scripts/build_supplement_manifest.py` passed.
- `latexmk`: `main.tex` (one column) 57 pages and `main_twocolumn.tex`, without undefined references or overfull boxes.
- **Full test suite: not run in this step.**

## Status
Completed and committed locally. No push performed. The rest of the Reviewer 3 response remains for C6-09.
