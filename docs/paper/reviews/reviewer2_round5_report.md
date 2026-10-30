# Reviewer 2 report — round5

**Manuscript:** *Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design*
**Author:** C. S. Park (Korea University)
**Target journal:** Physical Review Accelerators and Beams
**Source reviewed:** `docs/paper/main.tex` at commit `c1e9d21` (one-column REVTeX 4.2 review copy, 57 pages), with the generated tables, figures and appendix inputs it includes
**Responses considered:** [reviewer1_round4_response.md](reviewer1_round4_response.md) and [reviewer2_round4_response.md](reviewer2_round4_response.md)
**Previous round:** [reviewer2_round4_report.md](reviewer2_round4_report.md)
**Date:** 2026-10-30

---

## Recommendation

**Accept.** Every item of my round-4 report is resolved:
- the four required items exactly as requested;
- both recommended additions;
- the editorial items, with the optional length moves reasonably declined.

The author also made Reviewer 1's three corrections and corrected the round-3 responses openly, which I appreciate.

What remains are small precision points. One sentence on jitter tolerance is not quite consistent with the stated threshold (item 1). The other items are editorial. None needs new simulations or another review round. The editor can verify item 1 from the text.

The paper is now a carefully scoped comparison of specified pipelines on a nominal numerical model. Its central result, a higher feasible-sampling fraction for the constraint-aware pipeline, is supported by paired evidence and by sensitivity scenarios worded as scenarios. Its limitations are stated where the claims are made.

---

## Assessment of the round-4 responses

### My round-4 items

| Item | Status | Comment |
|---|---|---|
| 1 Refined TDR membership | **Resolved** | Contribution 3 now says that membership near the limits is not resolved numerically, with one candidate passing at every level and the other failing at some. This agrees with Sec. VI B and the Conclusions. See item 3 for a wording detail. |
| 2 Regeneration claim | **Resolved** | The Conclusions now match Appendix A and the supplement README. |
| 3 Response accuracy | **Resolved** | The Limitations contain the population statement. The round-4 responses also list five further inaccuracies of the round-3 responses, which I checked: Table I contents, Table XI rather than X, the scope of the rounding claim, the shares only in Sec. V C, and the superseded amplitude sentence. See item 6 for one new detail. |
| 4 Pareto-set size | **Resolved** | It moved into the conditioned objective-quality statement of the Discussion, and the cardinalities in Sec. V B are labelled. |
| 5 Upward and differential scenarios | **Resolved** | I reproduced both from the new `r4_shift_scenarios_*` files and from the archived ledgers: 0.279 and 0.311 at ×1.012, and the differential means 0.166 and 0.211 (smallest 0.062 and 0.132, all ten groups positive). The wording is "further post-hoc scenarios". |
| 6 Kim et al. | **Resolved**, with a precision point | See item 2. |
| 7 Fallback wording | Resolved | |
| 8 Length | Declined, reason accepted | Moving text to appendices would not shorten the paper. The review copy has 57 pages (two-column 31). |
| 9 Abstract | Resolved with Reviewer 1's wording | "Persists in the tested diagnostic-shift scenarios" is more exact than my suggestion, and I agree with the author's reasoning. |

### Reviewer 1's round-4 items

| Item | My assessment |
|---|---|
| C1 Common-shift scenarios | Resolved. "Bound" no longer describes the scenarios anywhere in the manuscript. Sec. V B states the common shift, the omitted increases and what stability in the scenarios does not establish. See item 5 for the supplement. |
| C2 RF amplitude | Resolved. The estimate is attributed to the nominal reference, and no failure count is inferred. See item 1 for the adjacent sentence. |
| C3 Table I | Resolved. I recomputed every entry from `r2_convergence_values.csv` with the stated denominators. The filled step-only energy cell (−0.04 to 0.01 MeV) matches the records. See item 4 for one remaining detail. |

---

## Remaining comments

### Requested before acceptance (editor can verify)

**1. "Jitter-tolerant TDR operation" for both candidates (Sec. V I).** The paragraph classifies only candidate A as fragile under the archived threshold of 0.8. Candidate B met the TDR inequalities in 44 of 50 trials (0.88; interval 0.76–0.95). The closing sentence then says that "these marginal settings already do not provide jitter-tolerant TDR operation". "Jitter-tolerant" is not defined. Under the only stated criterion, candidate B is not fragile, although its interval reaches below 0.8. Please state the conclusion per candidate, or define the term. For example:
- candidate A is fragile under the archived threshold;
- candidate B passes it, but its interval does not exclude values below it;
- neither retains TDR acceptance in every trial.

### Editorial

**2. Kim et al., Sec. VI A.**
- **(a) Emittance argument.** Both calculations are at the same nominal resolution, so a common refinement offset would largely cancel in the comparison. What makes the difference unresolved is the setting dependence of the refinement change (12–34 % in ε_x and 17–43 % in ε_y across the ten settings) together with the source difference. The sentence should name these, not the size of the refinement changes as such.
- **(b) Energy-spread sentence.** "The energy-spread difference is larger than its refinement change" may be read as a resolved physical difference. The present quantity is the projected RMS spread including chirp (Sec. II B). The manuscript does not establish whether the published 0.165 % is defined the same way. Add that the definitions are not established to be identical, or restrict the sentence to the numerical point.

**3. Contribution 3 precision.** "Passes at every refinement level and … fails at some": the fifteen levels include the regenerated-source levels, and candidate A fails at two of those, not only on the 64-cell grid. Say "at every refinement and source level".

**4. Mean-energy source spread in Table I.** The caption now says that mean energy is recorded to 0.01 MeV. The source-spread entry, ≤ 0.005 MeV, is a standard deviation of values quantized at twice that size, so it is not resolved. Write "below the recording step", or "< 0.01".

**5. Interpretation note in Supplement S1.** The manuscript no longer calls the 27 transformations bounds. The archived evidence still does:
- the metadata note of `r3_resolution_bounds_metadata.json` reads "Bounds from ten settings, …";
- the docstring of `scripts/analyze_revision_resolution_bounds.py` speaks of "bounding shifts".

Keeping the archived files unchanged is right. Add one sentence to the S1 README, at S1.13 or under the reproduction notes, saying that "bounds" in these file names and notes is to be read as the common-shift scenarios of the manuscript (round-4 interpretation correction).

### Optional (existing data only)

**6. Larger upward scales.** Sec. V B notes that some single-factor and regenerated-source levels increase sizes and divergences by more than the 1.2 % step-only value. The records give at most 16.2 %: σ_y of the crowding-distance setting with one random source. The round-4 response to Reviewer 1 quotes "up to 13 % … on the 64-cell grid", which is true for the grid but not the overall maximum.

I checked larger common upward scales with the published scripts and the archived ledgers. At ×1.17 the post-initialization differences are 0.276 and 0.300 at nominal bunch length and energy, and 0.242–0.292 and 0.267–0.317 over the nine bunch-length and energy shifts. The smallest lower interval limits are 0.20 and 0.24, and all ten groups are positive in every case.

A half-sentence would close the obvious question: "a common increase up to the largest single-level value, ×1.17, leaves every difference positive". If added, it belongs in the `r4_` evidence, worded as a scenario. In the round-5 response, correct the 13 % figure to 16 %.

**7. Wording of "give the same result" (Sec. V B).** The differential means (0.166 and 0.211) are smaller than the common-shift differences. "Leave every paired difference positive in all ten groups" is the exact statement.

---

## Assessment against journal criteria

| Criterion | Round 4 | Round 5 |
|---|---|---|
| Originality | Moderate | Moderate. A careful paired application study; acceptable for PRAB. |
| Technical soundness | Good, with summary gaps | Good. The summaries match the results; item 1 is a local wording inconsistency. |
| Fair comparison | Good | Good. |
| Relevance | Adequate | Adequate. |
| Physics content | Adequate | Adequate. The resolution limitation is a stated result with a table and scenarios. |
| Reproducibility | Strong | Strong. Item-level inventory, a tested level-2a regeneration, and the new scenario evidence mapped in S1. |
| Presentation | Clear framing; still long | Clear framing; long but well organized. |

## Conclusion

I recommend **acceptance**. Item 1 should be corrected before acceptance and can be checked by the editor. Items 2–5 are editorial, and 6–7 are optional. I do not need to see the manuscript again.

## Review trace

I read the changed passages of the manuscript in full against `887673c` and re-read the abstract, the contributions, Secs. II A, V B, V I, VI A and VI B, the Limitations and the Conclusions. I checked:
- Table I against `r2_convergence_values.csv`, with the stated denominators;
- the `r4_shift_scenarios_*` results, recomputed from the archived ledgers;
- the claims of both round-4 responses against the manuscript, including the corrections to the round-3 responses;
- the S1 map, the inventory row and the README entry for S1.13.

One calculation is mine: the common upward scales ×1.03, ×1.07, ×1.13 and ×1.17, from the published scripts and the archived ledgers (item 6). It is not an evidence file of the manuscript. No ASTRA run was made.

| Reviewed file | SHA-256 |
|---|---|
| `docs/paper/main.tex` | `0b19581d07335973601550f031429f4dbf8296d3a87f9b1f91c9dc8a04d93b67` |
| `docs/paper/main.pdf` | `653713ba1dead00c95b8fa59231838f682d36ef59bbe535ea05599c8151954be` |

The proposed actions are in [Reviewer 2 round5 revision tasks](../revisions/reviewer2_round5_revision_tasks.md).

*— Reviewer 2*
