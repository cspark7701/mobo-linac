# Reviewer 2 report — round4

**Manuscript:** *Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design*
**Author:** C. S. Park (Korea University)
**Target journal:** Physical Review Accelerators and Beams
**Source reviewed:** `docs/paper/main.tex` at commit `887673c` (one-column REVTeX 4.2 review copy, 56 pages), with the generated tables, figures and appendix inputs it includes
**Responses considered:** [reviewer1_round3_response.md](reviewer1_round3_response.md) and [reviewer2_round3_response.md](reviewer2_round3_response.md)
**Previous round:** [reviewer2_round3_report.md](reviewer2_round3_report.md)
**Date:** 2026-10-30

---

## Recommendation

**Accept after minor revision.** The remaining points are a few sentences that state slightly
more than the evidence shows, one inaccuracy in the response to Reviewer 1, and two optional
additions that use existing data. No new simulations are required. I do not need to see the
manuscript again if the required items below (T1–T4) are made as described.

Round 3 asked the author to choose between a benchmark on the nominal numerical model and a
physically resolved comparison. The author chose the first, and the manuscript now says so
consistently:
- the abstract leads with the pipeline comparison and the numerical limitation;
- a fifth contribution reports the resolution sensitivity as a stated limitation, not as a
  convergence result;
- the Results and the Conclusions place every comparison within the nominal model.

The central claim, a higher feasible sampling fraction for the constraint-aware pipeline, is
now supported by paired evidence that needs no estimated reference and by a bounding
reclassification under the measured refinement shifts. The front-quality claims are correctly
weaker and conditional. This is a careful and honest application study, appropriate for PRAB.

---

## Assessment of the round-3 responses

### My round-3 items

| Item | Status | Comment |
|---|---|---|
| R1 Attribution per baseline | **Resolved** | Abstract, contribution 2, Discussion and Conclusions state it per baseline. "Neither … explains it alone" replaces "not produced by". Sec. V C calls the categories an accounting and quantifies the upper quarter (about a fifth and a third of the gaps; I checked 0.060/0.276 and 0.094/0.311). |
| R2 Bounding reclassification | **Resolved** | 27 shift combinations over 4,800 primary and 1,600 Sobol-arm evaluations. I recomputed from `r3_resolution_bounds_paired.csv`: post-initialization differences 0.239–0.294 and 0.279–0.335, smallest lower interval limits 0.192 and 0.247, all ten groups positive under every shift and for every pair. The bunch-length sensitivity is stated. See T5 for a small extension. |
| R2 Front-quality caveat | **Resolved** | Sec. V B, the Discussion and the Limitations. |
| R3(a) Refined TDR membership | **Resolved** | The Conclusions now match Sec. VI B. |
| R3(b) Sobol share | **Resolved** | "At most about one third (shares 0.34 and 0.26)". |
| R3(c) Contribution 1 | **Resolved** | The failed predeclared hypervolume endpoint is named. |
| Minor 1 Energy-band direction | Resolved | |
| Minor 2 RF amplitude and TDR margins | Resolved | It is now a conditional linearized estimate of the mean energy, and it is compared with the 0.31 and 0.14 MeV margins. |
| Minor 3 Precision | Resolved | Labels on the key tables and figures, a statement on archived digits, and rounding in the text. |
| Minor 4 "Deterministic" | Resolved | |
| Minor 5 Data availability | Resolved | The three statements agree. One overclaim remains in the Conclusions; see T2. |
| Minor 6 Length | **Partly resolved** | Diagnostic detail moved to appendices, but the review copy grew from 51 to 56 pages (two-column 30 → 31). See T8. |
| Minor 7 APS style | Resolved | |
| Minor 8 Source comment | Resolved | A hygiene test now guards against recurrence, and the response corrects the round-2 statement. |
| Minor 9 Abstract | Resolved | 262 words, against 263 before, with the sentence split. |

### Reviewer 1's round-3 items, as far as they bear on my assessment

| Item | My assessment |
|---|---|
| M1 Scope | Resolved by the nominal-model framing. The response overstates one detail; see T3. |
| M2 Sobol uncertainty | Resolved. Run-level fractions 1.4–4.9 %, s.d. 1.3 points; the bootstrap is labelled approximate. The paired group bootstrap is kept. |
| M3 Domain geometry and mechanism | Resolved. The normalized controls of candidates A and B are given, and "edge of the explored domain" is gone. Contribution 3 still generalizes membership changes; see T1. |
| M4 RF amplitude | Resolved. |
| M5 Regeneration claim | Resolved in Appendix A and the supplement: input inventory, reproduction levels and a tested level-2a regeneration. The Conclusions still say "all reported values"; see T2. |
| Minors 1–4 | Resolved, except that the manuscript did not become shorter (see T8). |

---

## Remaining comments

### Required (minor)

**1. Contribution 3 generalizes the refined TDR membership.** Contribution 3 says that
TDR-feasible observations "lie within micrometres of the diagnostic limits, and their
membership changes under numerical refinement". Section VI B reports two different outcomes:
- candidate B meets the TDR inequalities at all fifteen refinement and source levels;
- candidate A fails on the 64-cell grid and with two of five random sources.

The sentence should say that membership changes for some of these settings, or that it is not
resolved near the limits, as the Conclusions already do.

**2. Regeneration claim in the Conclusions.** The Conclusions state that "the archived runs
and analysis scripts support regeneration of all reported values". The revised Appendix A and
supplement are more careful. Only the ledger-only (level 2a) evidence was tested, on three
representative generators. Levels 2b and 3 are inventory statements, and proposals cannot be
replayed bitwise. The Conclusions sentence should match Appendix A: for example, the
inventory identifies the inputs each reported value needs, and representative ledger-only
analyses were regenerated from the minimal input set.

**3. Accuracy of the response to Reviewer 1 (M1, item 3).** The response states that "Sec. II
A, the Limitations and the Conclusions say that the ten settings are feasible and come mostly
from constraint-aware searches". Only Sec. II A says this. The Limitations say that the shifts
"come from ten settings" without describing them. The Conclusions say "at those ten settings".
Either add a half-sentence on the population to the Limitations, or correct the response.
Responses should describe the manuscript exactly.

**4. Pareto-set size in the Discussion.** The first sentence of the Discussion says that
constraint-aware acquisition produced "a larger feasible Pareto set". Pareto cardinality is an
objective-space quantity: it depends on the unconverged emittances in the same way as the
front-quality indicators. The Discussion conditions the indicators on the fixed source file
and resolution, but places the set size next to the feasible fraction without that condition.
Attach the nominal-resolution condition to the set size as well, or move it to the
front-quality sentence.

### Recommended (existing data; no simulations)

**5. Two directions the bounds do not cover.**
- **(a) Upward shifts.** The bounding shifts scale sizes and divergences only downward (×0.78
  to ×1). Table I shows increases of up to 1.2 % (step only). I checked this with the archived
  ledgers: a ×1.012 scale leaves the post-initialization differences at 0.279 and 0.311, with
  all ten groups positive. The text can say that the omitted increases are immaterial.
- **(b) Differential shifts.** The 27 combinations apply the *same* shift to every method.
  Refinement could act differently in the regions that different pipelines sample. A simple
  worst case pairs, in every group, the lowest constraint-aware post-initialization fraction
  over all 27 shifts with each baseline's highest. My computation from
  `r3_resolution_bounds_runs.csv` gives:
  - against unconstrained MOBO: mean 0.166, smallest group difference 0.062;
  - against weighted-sum BO: mean 0.211, smallest 0.132;
  - all ten groups positive in both comparisons.

  One sentence reporting this would make "persists under the refinement shifts" robust to the
  obvious objection, and justify the abstract's wording.

**6. Comparison with Kim et al. in Sec. VI A.** The text contrasts the present ideal-distance
point (3.00 and 3.52 µm rad, 0.403 MeV) with the tracked example of Ref. [Kim2024] (3.96 and
3.94 µm rad). Both are at nominal resolution, and the differences (about 10–25 % in emittance)
are of the same order as the refinement shifts (12–43 %) and the source spread (1–12 %). The
paragraph already rules out an algorithmic attribution. It should also say that the
difference is not resolved numerically, consistent with the statement in the Conclusions that
absolute emittances should not be quoted without a converged calculation.

### Editorial

**7. Fallback wording, Appendices A and D.** Appendix A says that "no saved fit used a
restored-prior fallback". Appendix D says that 88 offline refits restored the initial
hyperparameters "as in production". Both statements are correct, but the reader may take them
as contradictory. Say that the offline refits use the same fallback rule, which was never
triggered in the saved production fits.

**8. Length.** The review copy grew from 51 to 56 pages, mostly through the new resolution
material and the expanded caveats. I do not insist on cuts. Two candidates for the appendix
are:
- the paragraph reclassifying the primary evaluations under the NAPAC, JKPS and JINST limits
  (end of Sec. II B);
- the detailed published values in the first paragraph of Sec. VI A.

**9. Abstract precision.** "The feasible-sampling advantage persists under the measured
refinement shifts" would be more exact as "under bounding shifts taken from the refinement
check". The shifts were measured at ten settings and applied to all evaluations.

---

## Assessment against journal criteria

| Criterion | Round 3 | Round 4 |
|---|---|---|
| Originality | Moderate | Moderate. A careful paired application study; acceptable for PRAB. |
| Technical soundness | Good, with summary gaps | Good. The summaries now match the results, apart from items 1, 2 and 4. |
| Fair comparison | Good | Good. Budget-matched baselines, a Sobol arm and stated missing controls. |
| Relevance | Adequate | Adequate. The TDR reach is stated as observed coverage. |
| Physics content | Adequate | Adequate. The resolution limitation is now a visible result, with a display item and bounds. |
| Reproducibility | Strong | Strong. Item-level input inventory and a tested regeneration path. |
| Presentation | Improved; still long | Clear framing; still long (item 8). |

## Conclusion

The author addressed every required item of my round-3 report, and in my reading also the
substance of Reviewer 1's major comments. The nominal-model framing is now consistent from the
abstract to the Conclusions. The main result survives the bounding reclassification, and in my
check also a differential worst case. I recommend **acceptance after the minor revisions T1–T4**.
T5 and T6 are recommended, and T7–T9 are editorial. No further review round is needed for
these changes.

## Review trace

I read the manuscript source in full and checked these points:
- the bounding results against `r3_resolution_bounds_{runs,paired}.csv` and the metadata;
- the upper-quarter shares;
- the energy-margin arithmetic of the RF estimate;
- the claims of both responses against the manuscript text.

Two calculations are mine, from the archived ledgers and the bounds evidence: the upward-shift
check (T5a) and the differential worst case (T5b). They are not evidence files of the
manuscript. No ASTRA run was made.

| Reviewed file | SHA-256 |
|---|---|
| `docs/paper/main.tex` | `4d6b3891ac65cad453168b6b3997209f8d57295223293d797d85e0cc5263d45c` |
| `docs/paper/main.pdf` | `c3b0d2356506bd892256c1c5e3ffd4dc23485b6aaf1b9cad813ce5f2e9c1c76b` |

The proposed actions are in [Reviewer 2 round4 revision tasks](../revisions/reviewer2_round4_revision_tasks.md).

*— Reviewer 2*
