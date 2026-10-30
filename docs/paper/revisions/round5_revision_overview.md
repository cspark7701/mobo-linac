# Round5 revision overview

Reviewed baseline: `c1e9d21`.

The round5 work items are C5-01 to C5-09 in the [consolidated task list](consolidated_round5_revision_tasks.md). Reviewer 1 recommended acceptance on scientific grounds and Reviewer 2 acceptance, with one sentence to be corrected first. Neither asked for new simulations, and none was run. Every change uses data available at the baseline. No production simulation, feasibility label, seed or acquisition definition was changed. The only new evidence (`evidence/r5_upward_max_*`) is a post-hoc reclassification of archived diagnostics.

## Responses and change inventory

- [Reviewer 1 response](../reviews/reviewer1_round5_response.md): E1 and E2, and the correction of the round4 response (13 % to 16.2 %).
- [Reviewer 2 response](../reviews/reviewer2_round5_response.md): comments 1–7.
- [Manuscript source diff](round5_manuscript.diff): `main.tex` against the reviewed baseline. No other `.tex` input or the bibliography changed.
- [Analysis code diff](round5_analysis_code.diff): the new upward-scale analysis and its test.
- [Changed-file inventory](round5_changed_files.json): every file changed relative to the baseline, with its current SHA-256 hash. It excludes the packaging files and the closing task summary, to avoid self-reference.
- Supplement S1 (`../supplement/`) maps the new evidence to S1.13, lists its generator in `input_inventory.csv`, and adds an interpretation note for the archived round3 scenario files.

## Main changes

In the last column, "R1" and "R2" name Reviewer 1 and Reviewer 2, followed by their comment labels.

| Task | Change | Reviewer items |
|---|---|---|
| C5-01 | Sec. V I: the jitter outcome of each TDR candidate is stated against the archived 0.8 threshold; candidate A is fragile, and candidate B passes but its interval reaches below the threshold. | R2 1 |
| C5-02 | Sec. VI A: the Kim et al. emittance argument rests on the setting-dependent refinement change and the different sources; the energy spread is not compared quantitatively. | R2 2 |
| C5-03 | Contribution 3: "every refinement and source level". | R2 3 |
| C5-04 | Table I: the mean-energy source spread is given as below the 0.01 MeV recording step. | R2 4 |
| C5-05 | Supplement S1 README: an interpretation note for "bounds" in the archived round3 files. | R2 5 |
| C5-06 | Sec. V B: the added constructions are called sensitivity checks that leave every paired difference positive in all ten groups. | R1 E2; R2 7 |
| C5-07 | Conclusions: absolute emittances "should not be interpreted as numerically converged physical predictions". | R1 E1 |
| C5-08 | A common upward scale of ×1.17, covering the largest single-level increase; one half-sentence in Sec. V B; new `r5_upward_max_*` evidence in S1.13. | R2 6 |
| C5-09 | Responses, this package and the validation. | R1 R5-03; R2 U8 |

## Not done

- The full test suite was not rerun, at the author's direction, because the machine is shared with another production job. The changed code consists of one new analysis script and its test. Both are outside the `mobo_linac` coverage target, and focused tests were run instead (see the closing task summary).

## Explicit scope dispositions

- **Nominal-model scope.** All objective values, classifications and margins are nominal-resolution results. The feasible-sampling comparison persists in the tested diagnostic-shift scenarios and sensitivity checks. The front-quality comparisons and the Pareto-set size are conditional on the fixed source realization and the resolution.
- **No physically resolved claim.** The paper claims no physically resolved ranking of the methods, no physical validation of Pareto ranks, no global optimality, no engineering acceptance of any setting and no efficacy of a corrected constraint method.
- **Excluded at the author's direction.** Funding and acknowledgments, `\finaltrue` and any Zenodo deposition are not part of this round.
- **No claim of journal acceptance.** Closing the task list does not establish reviewer agreement or journal acceptance.

## Front matter and format

The review copy uses the one-column REVTeX 4.2 `preprint` layout and builds to 57 pages, with the abstract on page 1 and the Introduction from page 2. The two-column `reprint` layout builds to 30 pages (31 at the baseline). The abstract is unchanged: 262 words and no numbers. The manuscript keeps `\finalfalse`.

## Final checks

The validation receipt is in the closing task summary (Task 00334):
- `ruff`, the documentation-sync check, and focused tests of the changed analyses, the supplement map, the documentation links, the manuscript hygiene and the paper outputs;
- the supplement manifest check and the regeneration check;
- clean `latexmk` builds of both layouts, without undefined references or overfull boxes.
