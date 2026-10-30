# Round4 revision overview

Reviewed baseline: `887673c`.

The round4 work items are C4-01 to C4-11 in the [consolidated task list](consolidated_round4_revision_tasks.md). Reviewer 1 recommended minor revision and Reviewer 2 acceptance after minor revision. Neither asked for new simulations, and none was run. Every change uses data available at the baseline: the archived ledgers and the round2 and round3 evidence. No production simulation, feasibility label, seed or acquisition definition was changed. The only new evidence (`evidence/r4_shift_scenarios_*`) is a post-hoc reclassification of archived diagnostics.

## Responses and change inventory

- [Reviewer 1 response](../reviews/reviewer1_round4_response.md): comments C1–C3, the scope confirmation and corrections to the round3 response.
- [Reviewer 2 response](../reviews/reviewer2_round4_response.md): comments 1–9 and corrections to the round3 response.
- [Manuscript source diff](round4_manuscript.diff): `main.tex` against the reviewed baseline. No other `.tex` input or the bibliography changed.
- [Analysis code diff](round4_analysis_code.diff): the new scenario analysis and its test.
- [Changed-file inventory](round4_changed_files.json): every file changed relative to the baseline, with its current SHA-256 hash. It excludes the packaging files and the closing task summary, to avoid self-reference.
- Supplement S1 (`../supplement/`) maps the new evidence files to S1.13 and lists their generator in `input_inventory.csv`.

## Main changes

In the last column, "R1" and "R2" name Reviewer 1 and Reviewer 2, followed by the comment numbers of their reports.

| Task | Change | Reviewer items |
|---|---|---|
| C4-01 | The 27 transformations are described as post-hoc common-shift sensitivity scenarios, not bounds, in the abstract ("persists in the tested diagnostic-shift scenarios"), contribution 5, Secs. II A and V B, the Discussion, the Limitations and the Conclusions. Sec. V B states the common shift, the omitted upward changes and what stability in the scenarios does not establish. | R1 C1; R2 9, 5 (text) |
| C4-02 | Upward (×1.012) and per-group differential scenarios from the archived ledgers; one passage in Sec. V B; new `r4_shift_scenarios_*` evidence, mapped to S1.13. | R2 5 |
| C4-03 | Contribution 3: TDR membership near the limits is not resolved numerically; one candidate passes at every level, the other fails at some. | R2 1 |
| C4-04 | Conclusions: S1 identifies the inputs of every value; representative ledger-only analyses were regenerated from the minimal set. | R2 2 |
| C4-05 | The Pareto-set size moved into the conditioned objective-quality statement of the Discussion; the cardinalities in Sec. V B are labelled as nominal-resolution values. | R2 4 |
| C4-06 | RF amplitude: a conditional, scale-based risk statement for the TDR candidates, based on the nominal-reference estimate; no failure count inferred. | R1 C2 |
| C4-07 | Table I: separate relative and absolute blocks; the caption defines every column's convention and denominator; values verified and unchanged; the empty step-only energy cell filled from the same evidence. | R1 C3 |
| C4-08 | Sec. VI A: the emittance differences from Kim et al. are not resolved numerically; the energy-spread difference exceeds its refinement change. | R2 6 |
| C4-09 | Appendix D: the offline refits apply the production fallback rule, which no saved production fit triggered. | R2 7, 8 |
| C4-10 | Limitations: the ten re-tracked settings are feasible and mostly from constraint-aware searches. Both round3 responses re-read; their inaccuracies are corrected in the round4 responses. | R2 3 |
| C4-11 | Responses, this package and the validation. | R1 R4-04; R2 T10 |

## Not done

- The optional moves of two passages to appendices (Reviewer 2 comment 8). Moving them would not shorten the manuscript.
- The `r3_resolution_bounds_*` evidence and its metadata note are kept as archived. The manuscript wording carries the interpretation correction.

## Explicit scope dispositions

- **Nominal-model scope.** All objective values, classifications and margins are nominal-resolution results. The feasible-sampling comparison persists in the tested diagnostic-shift scenarios. The front-quality comparisons and the Pareto-set size are conditional on the fixed source realization and the resolution.
- **No physically resolved claim.** The paper claims no physically resolved ranking of the methods, no physical validation of Pareto ranks, no global optimality, no engineering acceptance of any setting and no efficacy of a corrected constraint method.
- **Excluded at the author's direction.** Funding and acknowledgments, `\finaltrue` and any Zenodo deposition are not part of this round.
- **No claim of journal acceptance.** Closing the task list does not establish reviewer agreement or journal acceptance.

## Front matter and format

The review copy uses the one-column REVTeX 4.2 `preprint` layout and builds to 57 pages (56 at the baseline), with the abstract on page 1 and the Introduction from page 2. The two-column `reprint` layout builds to 31 pages. The abstract has 262 words and no numbers. The manuscript keeps `\finalfalse`.

## Final checks

The validation receipt is in the closing task summary (Task 00322):
- `ruff`, the documentation-sync check and the full test suite with 100 % coverage of `mobo_linac`;
- the supplement manifest check and the regeneration check;
- clean `latexmk` builds of both layouts, without undefined references or overfull boxes.
