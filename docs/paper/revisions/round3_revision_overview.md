# Round3 revision overview

Reviewed baseline: `00190d8`.

The round3 work items are C3-01 to C3-12 in the [consolidated task list](consolidated_round3_revision_tasks.md). Reviewer 1 recommended major revision and Reviewer 2 minor revision. Both described a route to acceptance without new simulations: a sharply framed comparison of the specified pipelines on the nominal numerical model. The author chose that route (route (a), 2026-10-30). Every manuscript change of this round uses data available at the baseline: the archived ledgers, the round2 evidence and the round2 resolution records. No production simulation, feasibility label, seed or acquisition definition was changed. New analyses are kept in separate derived evidence files (`evidence/r3_*`) and are labelled post hoc.

## Responses and change inventory

- [Reviewer 1 response](../reviews/reviewer1_round3_response.md): five major (M1–M5) and four minor comments.
- [Reviewer 2 response](../reviews/reviewer2_round3_response.md): three major (R1–R3) and nine minor comments. It also corrects the round2 statement that all revision-integration comments had been removed.
- [Manuscript source diff](round3_manuscript.diff): `main.tex`, the bibliography and the manuscript and evidence `.tex` inputs, against the reviewed baseline.
- [Analysis code diff](round3_analysis_code.diff): `scripts/`, `tests/`, `src/` and `tools/`, kept apart from the narrative edits.
- [Changed-file inventory](round3_changed_files.json): every file changed relative to the baseline, with its current SHA-256 hash: 53 files, 42 added and 11 modified. It excludes the packaging files and the closing task summary, to avoid self-reference. Raw simulation outputs are identified through `../supplement/ledger_manifest.json`.
- Supplement S1 (`../supplement/`) maps every evidence file to the manuscript location it supports. The new `input_inventory.csv` records the inputs and reproduction level of each generator.

## Main changes

In the last column, "R1" and "R2" name Reviewer 1 and Reviewer 2, followed by the comment numbers of their reports.

| Task | Change | Reviewer items |
|---|---|---|
| C3-01 | Scope: a comparison of the specified pipelines on the nominal numerical model. The abstract leads with the comparison and the numerical limitation, and a fifth contribution reports the resolution sensitivity as a stated limitation. The abstract is 262 words, against 263 at the baseline. | R1 M1, minor 4; R2 minor 9 |
| C3-02 | Bounding reclassification of the 4,800 primary and 1,600 Sobol-arm evaluations under the measured refinement shifts. New Table `tab:resolution`, population statements, and the front-quality caveat. | R1 M1, minor 3; R2 R2 |
| C3-03 | Attribution of the feasible-sampling advantage stated per baseline, as an accounting decomposition. | R1 M3; R2 R1 |
| C3-04 | Run-level uncertainty for the Sobol arm and the pooled initial-design and BO intervals; "at most about one third"; direction-specific energy-band sentence. | R1 M2; R2 R3(b), minor 1 |
| C3-05 | TDR reach described as observed coverage, without domain-geometry or necessity claims; Conclusions aligned on refined membership. | R1 M3; R2 R3(a) |
| C3-06 | RF-amplitude estimate restricted to a conditional linearized estimate of the mean energy; compared with the TDR energy margins. | R1 M4; R2 minor 2 |
| C3-07 | Supplement input inventory, reproduction levels, a regeneration test from the minimal ledgers, and consistent availability statements. | R1 M5; R2 minor 5 |
| C3-08 | Summary-claims audit: contribution 1, dominance wording for the MOGA-derived reference. | R1 minor 1; R2 R3(c) |
| C3-09 | Surrogate-undercoverage explanations worded as hypotheses. | R1 minor 2 |
| C3-10 | Nominal-resolution labels, precision, "deterministic", relocation of diagnostic detail to appendices, APS style, source hygiene with a test. | R1 minor 3; R2 minors 3, 4, 6–8 |
| C3-11 | Further re-tracking: withdrawn; nothing from it enters the manuscript. | R1 M1 (conditional); R2 R2 (optional) |

## Not done

- The optional split of the 88 refit fallbacks (Reviewer 1 minor 2). The archived refit records carry no fallback flag; the wording is descriptive instead.
- The optional re-tracking of the 53 pooled-reference points (Reviewer 2 R2). The front-quality comparisons are stated as conditional on the source realization and the resolution.
- A comparison at a converged tracking resolution. It is named as future work.

## Repository note (not part of the manuscript)

The analysis-code diff and the inventory also contain the driver and the tests of the withdrawn route (b) validation (`scripts/evaluate_revision_validation.py`, `tests/test_revision_validation.py`). Its stage A ran on 2026-10-29; stage B was not run. Neither the manuscript nor Supplement S1 uses it. The record is in the task list under C3-01.

## Explicit scope dispositions

- **Nominal-model scope.** All objective values, classifications and margins are nominal-resolution results. The feasible-sampling comparison is supported under the bounding shifts. The front-quality comparisons are conditional on the fixed source realization and the resolution.
- **No physically resolved claim.** The paper claims no physically resolved ranking of the methods, no global optimality and no engineering acceptance of any setting.
- **Excluded at the author's direction.** Funding and acknowledgments, `\finaltrue` and any Zenodo deposition are not part of this round.
- **No claim of journal acceptance.** Closing the task list does not establish reviewer agreement or journal acceptance.

## Front matter and format

The review copy uses the one-column REVTeX 4.2 `preprint` layout and builds to 56 pages, with the abstract on page 1 and the Introduction from page 2. The two-column `reprint` layout builds to 31 pages. The manuscript keeps `\finalfalse`.

## Final checks

The validation receipt is in the closing task summary (Task 00308):
- `ruff`, the documentation-sync check and the full test suite with 100 % coverage of `mobo_linac`;
- the supplement manifest check and the regeneration check;
- clean `latexmk` builds of both layouts, without undefined references or overfull boxes.
