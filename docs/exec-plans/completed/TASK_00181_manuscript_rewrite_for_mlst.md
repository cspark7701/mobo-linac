# Task Completion Summary: Task 176

## Summary
Rewrote `docs/paper/main.tex` for submission to *Machine Learning: Science and Technology* (IOP). The previous manuscript's results could not be traced to campaign data:
- No source runs exist on this host.
- Its configuration's 30 s time limit was below the ~280 s ASTRA runtime.
- Its text contradicted its own tables.

The author chose to restructure the paper around the planned campaign (`scripts/production`). Methods and protocol are written in full. Every campaign-dependent value or figure is a red `\pending{...}` marker or a placeholder box until the campaign outputs are copied in.

## Key Changes
- **`docs/paper/main.tex`**: new title, abstract and structure.
  - Introduction with related work.
  - Injector model, with corrected simulation facts from `astra.in`, `pal_photo2.ini` and the publication configuration.
  - Methods as implemented: GP surrogates, qLogNEHVI with constraint weighting, qLogNEI baseline, reference points, provenance.
  - Experimental design: paired 3 × 10-seed comparison, endpoints, statistics, audit protocol, operating-point survey.
  - Results (pending), discussion with limitations, conclusions, data availability.
  - Corrected facts: bunch charge 1.0 nC (was 250 pC); 2D 32×32 space-charge grid to z = 5.25 m, then 3D 32³ (was "2D, 25×50"); six representative roles (was five); fixed reporting reference (1.5 µm·rad, 1.5 µm·rad, 1.5 MeV); verification tolerances 0.1 %/10 %; robustness score as implemented.
  - Generated tables and figures are included only when present (`\IfFileExists`); otherwise a labelled placeholder appears. Line numbers are on while drafting; `\finaltrue` removes them.
- **`docs/paper/references.bib`**: new; IOP numeric style (`iopart-num`).
- **Stale artifacts removed** (they remain in git history): `results_table.tex`, `verification_table.tex`, `phase1_cases_table.tex` and `figures/*.png`. `figures/.gitkeep` keeps the directory.
- **`scripts/production/07_paper_outputs.sh`** also stages:
  - the primary comparison figures and summary CSV;
  - the Step 6 robustness table;
  - the Step 6 verification table, relabelled `tab:audit_verification`.

  It also prints the copy commands into `docs/paper/`. The production README is updated to match.

## Issues Reported to the Author (not changed)
1. **Constraint weighting scale.** BoTorch applies its feasibility sigmoid with temperature η = 10⁻³ to residuals in SI units. Beam size, divergence and bunch length residuals (~10⁻⁴) are therefore almost unweighted, while energy acts as a hard step. Normalizing residuals by their thresholds is recommended before the campaign. The manuscript marks this as pending.
2. **Paired statistical analysis is not implemented.** The design calls for per-seed paired differences, an exact Wilcoxon test and Holm correction. `analyze-benchmark` computes only per-algorithm medians with bootstrap intervals.
3. **Placeholder identifiers.** The DOIs in `release/publication_artifact_manifest.json` and `CITATION.cff`, and the ORCID, are placeholders.
4. **Author statements still needed.** The journal's statements on funding and on the use of generative AI in preparing the manuscript must be written by the author.

## Validation Results
- `pdflatex` + `bibtex` build: no errors, undefined references or overfull boxes.
  - 11 pages with placeholders.
  - 12 pages with every generated table and figure in place (mock rehearsal outputs).
- `tests/test_paper_outputs.py`, `tests/test_scalarized_suite.py`, `tests/test_production_scripts.py`, `tests/test_docs_links.py`: 45 passed, 30 skipped (no campaign data).
- Step 7 rerun on a rehearsal copy staged all inputs.
- `scripts/verify_docs_sync.py` passes.

## Status
Completed (manuscript awaiting campaign results).
