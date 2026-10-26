# Round1 revision overview

Reviewed baseline: `fe459f2c08ef5c1a992d65a0a26288c5926ae104`.

All adopted C01–C17 work is complete. The revision retains the existing simulations and adds auditable offline analyses, corrected feasible-only tables, independent survey histories, predictive validation and bounded scientific claims.

## Responses and change inventory

- [Reviewer 1 response](../reviews/reviewer1_round1_response.md): eight major and seven minor comments.
- [Reviewer 2 response](../reviews/reviewer2_round1_response.md): nine major headings and sixteen minor comments.
- [Manuscript source diff](round1_manuscript.diff): narrative, references and manuscript table changes against the reviewed baseline.
- [Analysis code diff](round1_analysis_code.diff): scripts and tests, separately from narrative edits.
- [Changed-file inventory](round1_changed_files.json): baseline-relative revision files and current SHA-256 hashes; excludes this packaging inventory, diffs, overview, validation receipt and Task 251 to avoid self-reference. Derived evidence and figures are identified by their paths; raw simulations and models are not included.
- [Validation receipt](evidence/c17_validation.json).

## Explicit scope dispositions

C02 does not establish calibrated crest phases or engineering validity of the historical phase windows. C09 documents resolution correspondence with the published JINST study but does not establish a traceable numerical-error bound. These are author-directed closures with limitations, not completed physical validation.

C06 supplies frozen-model unit sensitivity; corrected-acquisition physical performance is unmeasured. C07 retains the existing comparison arms without new constrained-scalarized, Sobol or MOGA runs. C10 remains lattice-only robustness; source/alignment/RF-amplitude uncertainty and new scans were not added. The TDR reclassification is distinct from the production feasibility profile and does not certify full machine acceptance. Neither empirical Pareto comparisons nor checklist completion establishes global optimality or journal acceptance.

Funding and acknowledgments are explicitly deferred to the author. The manuscript retains `\finalfalse` and is not declared submission-ready.

## Final checks

The focused revision/paper suite passed 79 tests. The 30-page JINST PDF builds without undefined references/citations or overfull boxes. Visual inspection covered front matter, primary results, survey plots/tables and predictive/selected-setting appendices. Remaining publisher-style warnings concern the hyperref pagecolor option and font substitution.

The evidence check verified 1,328 original production-file hashes, 49 cited bibliography keys and nine included figures. No new simulations were executed. Emmerich's previously unresolved page range was corrected to 421–439 using the [authors' institutional bibliography](https://moda.liacs.nl/index.php?page=publications).
