# Response to Reviewer 2 — round4

**Status:** Point-by-point response for author review, against reviewed revision `887673c`. It does not claim journal acceptance or submission readiness. Funding and acknowledgments, and `\finaltrue`, remain author decisions.

We thank the reviewer for the careful re-reading and for the two calculations on the archived data. The required items (comments 1–4) and both recommended items (5 and 6) are done. Of the editorial items, 7 is done, 9 is settled with Reviewer 1's wording, and the optional moves of comment 8 were not made. No simulation, GP refit or optimization arm was run, and no production value changed. The [round4 overview](../revisions/round4_revision_overview.md) links the diffs, the change inventory and the validation.

## Required comments

### 1. Refined TDR membership in contribution 3

Contribution 3 now says that the TDR-feasible observations "lie within micrometres of the diagnostic limits, where membership is not resolved numerically: one candidate passes at every refinement level and the other fails at some". This agrees with:
- Sec. VI B: candidate B passes at all fifteen levels; candidate A fails on the 64-cell grid and with two of five sources;
- the Conclusions: "membership near the limits is not numerically resolved".

The abstract makes no membership claim.

**Location:** contribution 3.

### 2. Regeneration claim of the Conclusions

"The archived runs and analysis scripts support regeneration of all reported values" is replaced. The Conclusions now say that:
- Supplement S1 identifies the inputs of every reported value;
- representative analyses that need only the evaluation ledgers were regenerated from that minimal set;
- the other analyses need further archived records;
- the proposals cannot be replayed bitwise.

This is the claim of Appendix A and the supplement README; levels 2b and 3 are not described as replayed.

**Location:** Conclusions.

### 3. Accuracy of our response to Reviewer 1

You are right: only Sec. II A said that the ten re-tracked settings are feasible and come mostly from constraint-aware searches. We took the first option. The Limitations now say that the shifts "come from ten settings, which are feasible and mostly from constraint-aware searches". The Conclusions name "those ten settings" only. The [round4 response to Reviewer 1](reviewer1_round4_response.md) records this correction.

We also re-read both round3 responses against the manuscript. The further inaccuracies are listed under "Corrections to our round3 response" below and in the response to Reviewer 1.

**Location:** Limitations.

### 4. Pareto-set size in the Discussion

- **Discussion, first sentence.** It now states only the larger feasible fraction.
- **Objective-quality sentence.** The larger feasible Pareto set moved here: "Evidence for objective quality, including its larger feasible Pareto set, is weaker in kind". The conditioning sentence names it: "These objective-space results, the set size among them, also hold only for the fixed source file at the production resolution".
- **Sec. V B.** The median cardinalities (13.5, 7.0 and 4.0) are labelled as depending on the objective values at the nominal resolution.
- **Abstract and Conclusions.** They state only that feasible nondominated settings exist, not how many.

**Location:** Discussion; Sec. V B (primary comparison).

## Recommended comments

### 5. Upward and differential scenarios

Both were computed from the archived ledgers by a new script, `scripts/analyze_revision_shift_scenarios.py`, with a test. The evidence is in new files, `evidence/r4_shift_scenarios_{upward_runs,upward_paired,differential}.csv` and `_metadata.json`. They are mapped to S1.13 and listed in the input inventory (level 2a); the `r3_*` files are unchanged. The results reproduce your calculation:
- **(a) Upward scale.** ×1.012 is the largest step-only increase of a size or divergence.
  - The post-initialization differences are 0.279 and 0.311 at nominal bunch length and energy, and 0.246–0.295 and 0.280–0.329 with the bunch-length and energy shifts.
  - Every interval excludes zero, and every group is positive.
- **(b) Differential case.** In each group, the lowest constraint-aware fraction over the 27 scenarios is paired with each baseline's highest.
  - Means are 0.166 against unconstrained MOBO and 0.211 against weighted-sum BO.
  - The smallest group differences are 0.062 and 0.132, and all ten groups are positive.

Sec. V B reports both in one passage as "two further post-hoc scenarios". Following Reviewer 1 (see comment 9), they are not called bounds.

**Location:** Sec. V B. **Supplement:** S1.13 (`r4_shift_scenarios_*`).

### 6. Comparison with Kim et al.

Sec. VI A now says that the emittance differences between the present ideal-distance point and the tracked example of Ref. [Kim2024], about 10–25 %, are of the order of the refinement changes and the source spread of Table I. Both calculations use a comparable nominal resolution, so the differences are not resolved numerically.

One clause adds that the energy-spread difference (0.403 against 0.333 MeV, about 21 %) is larger than its refinement change (at most about 4 %). Applying the caveat to the energy spread as well would understate what the refinement check shows.

**Location:** Sec. VI A.

## Editorial comments

### 7. Fallback wording

Appendix D now says that the 88 offline refits whose optimizers both failed "apply the production fallback rule, which no saved production fit triggered (Appendix A)".

### 8. Length

The two suggested moves were not made: the reclassification under the NAPAC, JKPS and JINST limits, and the detailed published values of Sec. VI A. Moving them to an appendix would not shorten the manuscript, and both passages are short and support the comparisons next to them.

The review copy now has 57 pages, against 56 at `887673c`; the growth comes from the corrections above. The two-column layout still has 31 pages.

### 9. Abstract precision

We used Reviewer 1's wording, "persists in the tested diagnostic-shift scenarios", instead of "under bounding shifts taken from the refinement check". Reviewer 1 asked that the 27 transformations not be called bounds. They apply one common shift to every evaluation, and they do not enclose every measured change (the upward changes; see comment 5). "Scenarios" therefore describes them more exactly and meets your request for precision. The same wording is used in contribution 5, Secs. II A and V B, the Discussion, the Limitations and the Conclusions. The abstract stays at 262 words, with no numbers.

## Corrections to our round3 response

- **R3(b).** We quoted "at most about one third (shares 0.34 and 0.26)" for Sec. V C and the Conclusions. Only Sec. V C gives the shares; the Conclusions say "at most about one third".
- **Minor 2.** The response reported the sentence "This indicates that amplitude jitter would cause further TDR failures". At Reviewer 1's request (round4 C2), that sentence is now a conditional risk statement based on the nominal-reference estimate, with no failure count inferred.
- **Minor 3.** The archived-digits statement and the nominal-resolution label are in the caption of Table XI (objectives of the selected settings), not Table X (their controls).

Every other location named in the round3 response contains the statement attributed to it, apart from statements this round deliberately changed: the bound wording (comment 9) and contribution 3 (comment 1).

## Evidence boundary

Every change of this round uses data available at `887673c`: the archived ledgers and the round2 and round3 evidence. The only new evidence, `r4_shift_scenarios_*`, is a post-hoc reclassification of archived diagnostics. The checks run for this response are listed in the [round4 overview](../revisions/round4_revision_overview.md).
