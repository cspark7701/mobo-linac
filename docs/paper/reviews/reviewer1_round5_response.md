# Response to Reviewer 1 — round5

**Status:** Point-by-point response for author review, against reviewed revision `c1e9d21`. It does not claim journal acceptance or submission readiness. Funding and acknowledgments, and `\finaltrue`, remain author decisions.

We thank the reviewer for the cumulative assessment and the recommendation. Both optional suggestions were adopted. No simulation, GP refit or optimization arm was run, and no production value changed. The [round5 overview](../revisions/round5_revision_overview.md) links the diffs, the change inventory and the validation.

## Optional editorial suggestions

### E1. What may be quoted (adopted)

The Conclusions now say that "absolute emittances should not be interpreted as numerically converged physical predictions". This replaces "should not be quoted without a converged calculation", which conflicted with the qualified nominal-model values that the paper itself quotes. Every value, the nonconvergence finding and the scope are unchanged.

**Location:** Conclusions.

### E2. Naming the added checks (adopted)

The sentence now speaks of "sensitivity checks", not "scenarios", and states exactly what they show: they "leave every paired difference positive in all ten groups". This also settles Reviewer 2's comment that "give the same result" was loose.

At Reviewer 2's optional request, a third check was added. It applies a common upward scale of ×1.17, which covers the largest increase of a size or divergence at any refinement or source level. The differences are 0.276 and 0.300, and all ten groups stay positive. The sentence therefore names three further sensitivity checks. The statement that none of them is re-tracking, a refinement model for every evaluation or a worst-case error bound now reads "None of these checks …".

**Location:** Sec. V B. **Supplement:** S1.13 (`r5_upward_max_*`).

## Correction to our round4 response

In C1, item 4, we wrote that the refinement records "show up to 13 % for one size on the 64-cell grid". That is the grid maximum. The largest increase in the records is 16.2 %: σ_y of the crowding-distance setting with one regenerated source. The manuscript statement, "larger for some single-factor and regenerated-source levels at individual settings", was correct; the ×1.17 check covers this value.

## Other changes of this round (Reviewer 2)

For completeness, these changes made at Reviewer 2's request also affect passages you assessed. All are narrowing or precision edits:
- **Sec. V I.** The jitter outcome of the two TDR candidates is stated per candidate under the archived 0.8 threshold: candidate A is fragile; candidate B passes, but its interval reaches below the threshold.
- **Sec. VI A.** The Kim et al. emittance argument rests on the setting dependence of the refinement change and on the different sources. The energy spread is not compared quantitatively, because the published definition is not established to match.
- **Contribution 3.** It now says "every refinement and source level".
- **Table I.** The mean-energy source spread is given as below the 0.01 MeV recording step.
- **Supplement S1 README.** It notes that "bounds" in the archived round3 file names and notes means the manuscript's common-shift scenarios. The files themselves are unchanged, as you found acceptable.

## Evidence boundary

Every change uses data available at `c1e9d21`. The only new evidence, `r5_upward_max_*`, is a post-hoc reclassification of archived diagnostics. The checks run for this response are listed in the [round5 overview](../revisions/round5_revision_overview.md).
