# Task Completion Summary: Task 00338

## Summary
Resolved the review findings on the humanized manuscript (Task 00337) with minimal text changes, at the author's direction. The acknowledgments and data-availability statements were left unchanged. No result, value or argument changed, apart from the removal of the 9,999-particle statement requested by the author.

## Key Changes
- **Particle count.** Sec. II.A now states a fixed 1.0 nC file with 10,000 particles. The record count and the 9,999-particle transmission count were removed, as the author requested. The convention that transmission counts exclude the reference particle is not stated in the text, also as requested.
- **Typo.** Fixed a capital "The" mid-sentence in Sec. V.B ("and the full-reference calculation").
- **Discussion.**
  - "Several selected operating points" became "All six selected operating points and the nominal setting". All six representatives and the nominal setting passed their 50 production-profile trials.
  - The opening paragraph was split in two. Its stray manual line breaks were removed, and the sentence repeating that all methods found feasible nondominated settings was dropped; the Results and Conclusions keep that statement.
- **Conclusions.** The seven channels and eight inequalities are again attributed to the model, not to the paired study design.
- **Predictive checks (Sec. V).**
  - The reason that overconfident predictions sharpen the feasibility weights was restored: the constraint weights use the same predictions.
  - The inferred-noise refit coverage ranges are no longer repeated from Appendix C. Sec. V keeps the conclusion, and the appendix keeps the numbers.
- **RF-amplitude estimate.** "about ten times" became "about 6 to 30 times". The ratio of 0.28–0.40 MeV to 0.014–0.046 MeV is about 6 to 29.
- **Repeated caveats.** Three in-line repeats of the resolution caveat were removed:
  - the Results introduction;
  - the Fig. 2 caption;
  - Sec. V.G, which kept the pointer to Table II.

  The final sentence of the abstract, which reviewers requested in rounds 3–5, was kept.
- **Preamble.** `\usepackage[utf8]{inputenc}` was removed; it has no effect under current LaTeX.
- **Source wrapping.** 59 long body lines were re-wrapped near 100 characters. A whitespace-normalized comparison confirmed that the wrapping changed whitespace only.

## Validation Results
- **Numbers.** Compared with the pre-humanizing backup, the numeric tokens differ only by the intended changes:
  - `9999` was removed;
  - one copy each of 83.4, 86.9, 92.7 and 93.9 was removed (the duplicated refit ranges);
  - `6` and `30` were added;
  - `8` was removed (`utf8`).
- **`latexmk -cd -pdf docs/paper/main.tex`:** 31 pages, no undefined references or overfull boxes. The warnings are the REVTeX float-placement notices recorded in Task 00337 and the `nameref` notice; the `inputenc` warning is gone.
- **PDF text:** `pdftotext` shows each edited passage.
- **Tests:** `pytest tests/test_manuscript_hygiene.py tests/test_paper_outputs.py tests/test_docs_links.py tests/test_build_prab_submission.py` reported 32 passed and 30 skipped.
- `git diff --check` passed.

## Status
Completed and committed locally. No push performed.
