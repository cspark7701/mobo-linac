# Response to Reviewer 1 — round4

**Status:** Point-by-point response for author review, against reviewed revision `887673c`. It does not claim journal acceptance or submission readiness. Funding and acknowledgments, and `\finaltrue`, remain author decisions.

We thank the reviewer for a focused report and for accepting the narrower scope chosen in round3. All three comments are corrections of interpretation or presentation. Each was made with existing data. No simulation, GP refit or optimization arm was run, and no production value changed. The [round4 overview](../revisions/round4_revision_overview.md) links the diffs, the change inventory and the validation.

## Comments

### C1. Common-shift scenarios are not bounds

1. **Wording.** Every description of the 27 transformations as a bound is gone:
   - "To bound the effect of the numerical resolution" (Sec. V B);
   - "Sec. V B bounds that effect" (Sec. II A);
   - "bounding shifts" (contribution 5, the Discussion, the Limitations and the Conclusions).

   They are now "post-hoc common-shift sensitivity scenarios motivated by the refinement check", shortened to "common-shift scenarios" in the summary sections.
2. **Abstract.** The sentence now reads "persists in the tested diagnostic-shift scenarios", as suggested. The abstract stays at 262 words, with no numbers.
3. **Main result (Sec. V B).** The text now says that:
   - each scenario applies the same transverse factor, bunch-length factor and energy shift to every evaluation of every method;
   - the scenarios are not re-tracking of the primary campaigns, a refinement model for every evaluation or a worst-case error bound;
   - stability in them does not establish stability under setting- or channel-dependent changes or under converged tracking.
4. **Coverage of the grid.** Sec. V B says that the grid does not enclose every measured change. It omits the increases of sizes and divergences: up to 1.2 % in the step-only column of Table I, and larger for some single-factor and regenerated-source levels at individual settings. The refinement records show up to 13 % for one size on the 64-cell grid.
5. **Unchanged.** The 27 scenarios, their values and the `r3_resolution_bounds_*` files, including the metadata note, which still reads "bounds". The manuscript wording is the interpretation correction; the round3 evidence files are kept as archived.
6. **Additional scenarios (Reviewer 2's request).** You did not ask for further scenarios. Reviewer 2 asked for an upward scale and a differential case, and both were computed from the archived ledgers (new `r4_shift_scenarios_*` evidence, S1.13). Sec. V B reports them in one passage, described as further post-hoc scenarios, and the caveat in item 3 covers them as well.

**Location:** abstract; contribution 5; Secs. II A and V B; Discussion; Limitations; Conclusions.

### C2. Conditional RF-amplitude implication for the TDR candidates

1. **Removed:** "which indicates that amplitude jitter would cause further TDR failures".
2. **Added (Sec. V I, "Robustness to lattice jitter").**
   - The 0.28–0.40 MeV RMS shift is estimated from the energy gains of the MOGA-derived nominal reference, not from a tracked amplitude response of candidates A and B.
   - Because the scales are comparable to the candidates' 0.31 and 0.14 MeV margins, the omitted amplitude errors could reduce their TDR acceptance further and merit a candidate-specific study.
   - No failure count or probability is inferred.
3. **Kept:** the measured lattice-only counts, 36/50 and 44/50, with their exact intervals. The statement that these marginal settings do not provide jitter-tolerant TDR operation is now tied to the lattice-only model.

**Location:** Sec. V I, paragraph on candidates A and B.

### C3. Units and convention of Table I

1. **Units.** The column headings no longer carry a unit. A "Relative change [%]" block holds the emittance, energy-spread, size, divergence and bunch-length rows. A separate "Absolute change [MeV]" block holds the mean-energy row.
2. **Conventions in the caption.**
   - "Fine" and "step only": signed changes relative to the production value.
   - "Fine vs medium": the largest magnitude of the difference between the two combined levels, relative to the medium value.
   - "Source s.d.": the standard deviation over five random sources, relative to the production value.
   - Mean energy is recorded to 0.01 MeV.
3. **Verification.** Every entry was recomputed from `evidence/r2_convergence_values.csv` with these denominators; all values are unchanged. The step-only mean-energy cell was empty (a dash). It now gives the recorded range, −0.04 to 0.01 MeV.

**Location:** Table I (`tab:resolution`), Sec. II A.

## Scope

The accepted narrower scope is intact. The manuscript claims no physically resolved ranking of the methods, no physical validation of Pareto ranks, no machine acceptance of any setting, and no efficacy of a corrected constraint method. The round4 changes narrow statements; none widens a claim.

## Corrections to our round3 response

Reviewer 2 found that item 3 of our M1 response named the Limitations and the Conclusions for a statement that only Sec. II A made: that the ten re-tracked settings are feasible and come mostly from constraint-aware searches. The Limitations now make it as well. The Conclusions name "those ten settings" only, which the second half of that item describes correctly.

We then re-read the whole round3 response against the manuscript and found three further inaccuracies. The round3 file is left as submitted; the corrections are:
- **M1, item 2.** We wrote that Table I separates the grid changes and gives the classification changes. Table I has fine, step-only, fine-vs-medium and source-spread columns. The grid-only and particle-count levels are in S1.13. The classification changes are stated in the text of Sec. II A, not in the table.
- **Minor 3, labels and digits.** The nominal-resolution label and the statement on archived digits are in the caption of Table XI (objectives of the selected settings), not Table X (their controls). Tables IV and V and both Pareto figures carry the label, as stated.
- **Minor 3, rounding.** We wrote that running-text values are rounded to three significant figures. This holds for emittances and energy spreads. Margins, phase limits and published values of earlier studies are quoted at their recorded or published precision.

Every other location named in the round3 response contains the statement attributed to it. The exceptions are statements that this round deliberately changed: the bound wording (C1), the refined TDR membership in contribution 3 (Reviewer 2 comment 1) and the amplitude sentence (C2).

## Evidence boundary

Every change of this round uses data available at `887673c`: the archived ledgers and the round2 and round3 evidence. The only new evidence, `r4_shift_scenarios_*`, is a post-hoc reclassification of archived diagnostics. The checks run for this response are listed in the [round4 overview](../revisions/round4_revision_overview.md).
