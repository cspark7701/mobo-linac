# Task Completion Summary: Task 00299

## Summary
Consolidated round3 task C3-07: make the reproduction dependencies of Supplement S1 accurate (Reviewer 1 M5), and make the availability statements consistent (Reviewer 2 minor 5). Local documentation only; nothing is deposited or uploaded.

## Key Changes
- **Input inventory (`docs/paper/supplement/input_inventory.csv`).**
  - It covers every generator in `evidence_map.csv`, with its input classes, the run files it reads and its reproduction level.
  - The input classes are ledgers, run records, GP checkpoints, tracking outputs, re-tracking records and derived evidence.
  - The levels are: 1, tables and figures from evidence; 2a, minimal ledgers; 2b, full run directories; 3, ASTRA.
  - The classification was taken from each generator's source code.
- **Manifest check (`scripts/build_supplement_manifest.py`).** It now fails if a generator has no inventory entry, or an entry with an unknown class or level. The docstring says the check does not regenerate evidence. Test added in `tests/test_supplement_map.py`.
- **Regeneration test (`scripts/check_supplement_regeneration.py`).**
  - It assembles a scratch tree with the scripts, the evidence files and only the 215 minimal ledger files (`evaluations.csv`, `config.json` and `run_complete.json` per run).
  - It runs the resolution-bounds, Sobol-uncertainty and attribution generators there.
  - All seven compared outputs match the committed evidence (`evidence/r3_regeneration_check.json`, mapped to S1.1).
- **Supplement README.**
  - S1 is "supplied with the manuscript for review", otherwise available on request, and identified by the commit in the review package.
  - The blanket claim that about 10 MB of ledgers regenerate every evidence file is replaced by a reproduction-level table, with level-2b examples (GP checkpoints, `astra.Zemit.001`, the convergence records).
  - The page notes that proposals cannot be replayed bitwise, and that the manifest check is not a regeneration test.
- **Manuscript.**
  - Appendix A ("Supporting package") now uses the same wording as the README.
  - The Data availability statement says what S1 contains and that it is supplied for review. It still names no public repository.
- **Task list:** C3-07 is ticked.

## Validation Results
- The regeneration check passed (3 generators, 7 files).
- `tests/test_supplement_map.py` and `tests/test_paper_outputs.py` passed (57).
- `ruff`, the documentation-sync check and the manifest check passed.
- `latexmk` builds `main.pdf` (54 pages) without errors, undefined references or overfull boxes.

## Status
Completed and committed locally. No push, upload or deposit. The route (b) re-tracking evidence will be added to the inventory when it exists.
