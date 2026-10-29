# Round2 revision overview

Reviewed baseline: `9077875`.

The round2 work items are C2-01 to C2-14 in the [consolidated task list](consolidated_round2_revision_tasks.md); C2-15 (Zenodo deposition) is optional and has not been started. The revision keeps every production simulation, feasibility label, seed and acquisition definition unchanged. New classifications and analyses are kept in separate derived evidence files under `evidence/`, and those added after the fact are labelled post hoc. The author authorized all of the optional simulations, which are recorded separately from the production campaigns.

The author closed C2-11 on 2026-10-29, which supersedes the closure rule of 2026-10-28 for this task. C2-10 stays open for the funding text and `\finaltrue`.

## Responses and change inventory

- [Reviewer 1 response](../reviews/reviewer1_round2_response.md): six major (M1–M6) and seven minor comments.
- [Reviewer 2 response](../reviews/reviewer2_round2_response.md): four numbered major comments (N1–N4) and ten minor comments, with an assessment against the reviewer's criteria.
- [Manuscript source diff](round2_manuscript.diff): `main.tex`, the bibliography and the manuscript and evidence `.tex` inputs, against the reviewed baseline. The diff includes the conversion to the PRAB format, so it is large.
- [Analysis code diff](round2_analysis_code.diff): `scripts/`, `tests/`, `src/` and `tools/`, kept apart from the narrative edits.
- [Changed-file inventory](round2_changed_files.json): every file changed relative to the baseline, with its current SHA-256 hash: 102 files, 91 added and 11 modified. It excludes the packaging files and the closing task summary, to avoid self-reference. Raw simulation outputs are identified through `../supplement/ledger_manifest.json`.
- Supplement S1 (`../supplement/`) maps every evidence file to the manuscript location it supports.

## Optional simulations

All of these were authorized by the author and run:

| Simulation | Task | Runs | Outcome |
|---|---|---|---|
| Re-evaluation of the MOGA-derived nominal setting, with 50 lattice-jitter trials | C2-07 | 51 | Production-feasible; misses the TDR inequalities only in vertical divergence (2.7 µrad); no pipeline found a feasible setting that dominates it |
| Lattice jitter of TDR candidates A and B | C2-08 | 100 | Production-feasible in 50/50 trials each; TDR-feasible in 36/50 and 44/50 |
| Offline GP refit with inferred noise | C2-05 | no tracking | Explains part, but not all, of the surrogate undercoverage |
| TDR-constrained campaigns, seeds 42–44 | C2-13 | 480 | No TDR-feasible observation; closest miss 0.4 % |
| Budget-matched Sobol arm, seeds 42–51 | C2-14 | 1,600 | 2.8 % feasible after initialization; every pipeline exceeds it in all ten matched groups |
| Numerical-resolution check of ten reported settings | C2-12 | 150 | Emittances not converged at the inherited resolution (12–43 % lower at the fine level); other quantities and the production classifications are stable; TDR membership near the limits is not resolved |

**Not run** (each is stated as a limitation in the manuscript):
- a constraint-aware scalarized arm;
- a new MOGA benchmark;
- a repeat of the comparison at a converged tracking resolution;
- tracked RF-amplitude, alignment and source errors (RF-amplitude errors are bounded to first order only).

## Explicit scope dispositions

- **Earlier convergence confirmation withdrawn.** The author withdrew, on 2026-10-29, the earlier confirmation that convergence of the present settings had been established in the previous study (C2-04 and C2-12). All values remain nominal-resolution results. Absolute emittances are not quoted as converged, and the method comparison holds within the fixed numerical model.
- **Feasibility profile.** Feasibility is the deliberately relaxed production profile. The TDR reclassification and the TDR-constrained campaigns describe the reach of the TDR region; they do not certify machine acceptance.
- **Acquisition tested.** The tested acquisition is the executed raw-residual pipeline. The offline normalization probes supply no physical-performance evidence for a corrected method.
- **No claim of journal acceptance.** Neither empirical Pareto comparisons nor checklist completion establishes global optimality or journal acceptance.

## Front matter and format

- **Journal and format.** The target journal is Physical Review Accelerators and Beams (author decision, 2026-10-29). The manuscript uses REVTeX 4.2 with no table of contents. The review copy uses the one-column `preprint` option and builds to 52 pages; the two-column `reprint` layout builds to 30 pages.
- **Added statements.** A statement of contributions closes the Introduction. A Data availability statement offers the data on request and names no public repository.
- **Pending.** Funding and acknowledgments remain deferred to the author, and the manuscript keeps `\finalfalse`.

## Final checks

The validation receipt is in the closing task summary (Task 00286):
- `ruff`, the documentation-sync check and the full test suite with 100 % coverage of `mobo_linac`;
- the supplement manifest check;
- a clean `latexmk` build without undefined references or overfull boxes.
