# Reviewer 2 report — round6

**Manuscript:** *Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design*
**Author:** C. S. Park (Korea University)
**Target journal:** Physical Review Accelerators and Beams
**Source reviewed:** `docs/paper/main.tex` at commit `9fd076a` (two-column REVTeX 4.2 submission layout, 31 pages), with the generated tables, figures and appendix inputs it includes
**Responses considered:** [reviewer2_round5_response.md](reviewer2_round5_response.md) and [reviewer1_round5_response.md](reviewer1_round5_response.md)
**Previous round:** [reviewer2_round5_report.md](reviewer2_round5_report.md)
**Date:** 2026-10-31

---

## Recommendation

**Accept**, as in round 5. Every round-5 comment is resolved in the current text.

Since round 5 the manuscript has also been rewritten for readability, in Tasks 00337–00339. The rewriting kept every number, apart from one intended change to the particle-count statement. It also kept the scope statements and the distinctions between validity, production feasibility, TDR acceptance and machine reliability. The rewriting did introduce three small inconsistencies:
- the weighted-sum cost lost its definition, though the text still refers to it (item 1);
- an undercoverage hypothesis is now named only in the appendix (item 2);
- the agreed abstract was changed (item 3).

Item 1 should be corrected before acceptance; the editor can verify it. The others are editorial. No new simulations or further review round are needed.

---

## Assessment of the round-5 responses

| Item | Status | Comment |
|---|---|---|
| 1 Jitter tolerance of the TDR candidates | **Resolved** | Sec. V I states the outcome per candidate under the archived threshold of 0.8: A is fragile, B passes but its interval reaches below the threshold, and neither retains TDR acceptance in every trial. No unqualified "jitter-tolerant" claim remains. |
| 2 Kim et al. | **Resolved** | Sec. VI A names the setting dependence and the source difference, and it does not compare the energy-spread definitions quantitatively. |
| 3 Contribution 3 | **Resolved** | It says "at every refinement and source level". |
| 4 Table I mean-energy source spread | **Resolved** | The entry is "<0.01", consistent with the caption. |
| 5 S1 interpretation note | **Resolved** | The supplement README has the note; the archived files are unchanged. |
| 6 Larger upward scale | **Resolved** | ×1.17 is in Sec. V B with the values I reported (0.276 and 0.300; 0.242–0.292 and 0.267–0.317), from new `r5_upward_max_*` evidence. |
| 7 "Same result" wording | **Resolved** | "Leave every paired difference positive in all ten groups". |

The round-5 response states that the abstract was unchanged (262 words). That was true at `c1e9d21`. It has since been rewritten; see item 3.

## Changes since round 5

I compared the reviewed source with the round-5 closing version (`12953d4`) and with the pre-rewrite backup, `main.tex.before-humanizing-20261031.bak`.

- **Numbers.** Compared with the backup, the numeric tokens differ only by the documented intentional changes:
  - the 9,999-particle transmission count was removed;
  - the duplicated refit coverage ranges are no longer repeated outside Appendix D;
  - "about ten times" became "about 6 to 30 times", which matches the stated values;
  - the `inputenc` line was removed.
- **Sec. V I, local convergence.** The new wording separates the four settings with dominating trials from the two without. It is more exact than before, and I agree with it.
- **Sec. V B.** The sensitivity checks are now in separate paragraphs. The content is unchanged and easier to follow.
- **Discussion.** "All six selected operating points and the nominal setting remain feasible under the simulated lattice jitter" agrees with Sec. V I and Sec. V J (50 of 50 trials each).
- **Conclusions.** The channel and inequality counts are again attributed to the model.

---

## Remaining comments

### Requested before acceptance (editor can verify)

**1. Definition of the weighted-sum cost (Sec. III B).** The equation $g(\mathbf{x})=\sum_m w_m f_m(\mathbf{x})/s_m$ was replaced by prose: "a single GP for the weighted combination of objectives, normalized by the reporting scales". The prose does not say that the combination is a sum of the scaled objectives, or that it is minimized. Yet Sec. V C still refers to the baseline's "weighted cost", and Sec. V G reports the coverage of the "scalarized cost". For a methods comparison, the baseline's target should be defined exactly. Please restore the equation, or an equivalent one-line definition, and call it the scalarized cost where it is defined.

### Editorial

**2. Undercoverage hypotheses (Sec. V G and Appendix D).** The sentence on a single Matérn-5/2 length scale per control was removed from Sec. V G, because it was stated categorically. Appendix D still says that "kernel misspecification and adaptive test points could account for the remainder". Kernel misspecification is therefore no longer introduced in the main text. Either:
- restore it in Sec. V G as a hypothesis, e.g. "A stationary kernel with one length scale per control may not represent both the smooth interior response and the sharp changes near energy loss or beam-size growth"; or
- drop it from Appendix D.

**3. Abstract.** The rewrite keeps the content, adds no numbers, and keeps Reviewer 1's wording "persists in the tested diagnostic-shift scenarios". Two scope signals were weakened, however:
- "specified" was dropped from "We compare specified Bayesian optimization pipelines". The word was part of the round-3/4 scoping, which presents the study as a comparison of the executed implementations.
- The closing sentence now reads "a physically resolved injector optimization remains to be done". That reads as a commitment, where it was a statement of what the results are not. The round-5 wording was "are not a physically resolved injector optimization", and it was more exact.

Please restore both, or confirm the new wording deliberately. The abstract is now 267 words.

### Optional

**4. Source formatting.** In Sec. V G, the paragraph beginning "Several mechanisms could explain the undercoverage" has irregular source line breaks; one line ends in "the reported". This does not affect the PDF.

**5. A separate assessment in the repository.** The repository also holds a separate assessment, Task 00340, which recommends major revision. It asks for:
- re-tracking a sample across methods and feasibility boundaries;
- a normalized-residual campaign;
- a constraint-aware scalarized arm.

All three were raised in earlier rounds. They were settled by restricting the claims to the executed pipelines on the nominal model, which is the route Reviewer 1 offered in round 3 and both reviewers accepted. The current text states each limitation where the claims are made: Secs. II A, V B and VI C, and the Conclusions. I do not reopen them as conditions.

As advice for submission: a referee new to the paper will most likely question the non-converged emittances. If the author can afford it, re-tracking at the medium level would pre-empt that question. A few matched groups per method, including infeasible and baseline observations, would suffice. This needs new ASTRA runs and the author's approval. It is not a condition of my recommendation.

---

## Assessment against journal criteria

| Criterion | Round 5 | Round 6 |
|---|---|---|
| Originality | Moderate; acceptable for PRAB | Unchanged. |
| Technical soundness | Good | Good. Item 1 restores a definition lost in rewriting. |
| Fair comparison | Good | Good. |
| Relevance | Adequate | Adequate. |
| Physics content | Adequate | Adequate. |
| Reproducibility | Strong | Strong. S1 mapping unchanged; the upload builder now checks that the bibliography includes every cited reference. |
| Presentation | Long but well organized | Improved. Shorter sentences and clearer paragraphs at the same length (31 pages in two columns). |

## Conclusion

I recommend **acceptance**. Item 1 should be corrected before acceptance and can be checked by the editor. Items 2–3 are editorial, and 4–5 are optional. I do not need to see the manuscript again.

## Review trace

I read the full manuscript at `9fd076a`. I diffed the abstract and every changed passage against `12953d4`, and compared the numeric tokens against the pre-rewrite backup. I rebuilt the two-column PDF:
- 31 pages;
- no undefined references and no overfull boxes;
- only REVTeX float-deferral notices remain, and every float appears after its first citation.

I checked section numbers in `main.aux`, and the round-5 items against the text. No ASTRA run, GP refit or optimization was made.

| Reviewed file | SHA-256 |
|---|---|
| `docs/paper/main.tex` | `8d6814ab67e41aa2384af6e0bf95dabe9a90dc73ecf2bf7a8a9ee106e6244eb9` |
| `docs/paper/main.pdf` | `ac4d418df6dfd72774fa25faf21786f91c776fdfd615653b542fa8c76a6bd544` |

The proposed actions are in [Reviewer 2 round6 revision tasks](../revisions/reviewer2_round6_revision_tasks.md).

*— Reviewer 2*
