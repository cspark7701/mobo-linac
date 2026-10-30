# Response to Reviewer 2 — round5

**Status:** Point-by-point response for author review, against reviewed revision `c1e9d21`. It does not claim journal acceptance or submission readiness. Funding and acknowledgments, and `\finaltrue`, remain author decisions.

We thank the reviewer for the recommendation and for the checks on Table I and the scenario evidence. All seven comments were adopted, including the two optional ones. No simulation, GP refit or optimization arm was run, and no production value changed. The [round5 overview](../revisions/round5_revision_overview.md) links the diffs, the change inventory and the validation.

## Requested before acceptance

### 1. Jitter tolerance of the TDR candidates

The undefined "these marginal settings already do not provide jitter-tolerant TDR operation" is gone. Sec. V I now states, under the lattice-only model and the archived threshold of 0.8:
- candidate A is fragile (36/50, interval 0.58–0.84);
- candidate B passes the threshold (44/50), but its interval (0.76–0.95) does not exclude values below it;
- neither retains TDR acceptance in every trial.

No other passage makes a jitter claim about the candidates. The abstract, contribution 3, the Discussion, Sec. VI B and the Conclusions were checked.

**Location:** Sec. V I, paragraph on candidates A and B.

## Editorial comments

### 2. Kim et al.

- **(a) Emittances.** The differences are now described as unresolved because the refinement change depends on the setting (12–34 % in ε_x and 17–43 % in ε_y across the ten re-tracked settings) and the two sources differ. The text notes that a common refinement offset at the shared nominal resolution would largely cancel.
- **(b) Energy spread.** The difference exceeds its refinement change. The published value is not established to be the projected RMS spread including chirp used here, so it is not compared quantitatively.

**Location:** Sec. VI A.

### 3. Contribution 3

It now says "one candidate passes at every refinement and source level and the other fails at some".

### 4. Mean-energy source spread in Table I

The entry is now "<0.01", and the caption says that the source spread lies below the 0.01 MeV recording step. The largest recorded value is 0.0055 MeV.

### 5. Interpretation note in Supplement S1

The supplement README now has an interpretation note. It says that "bounds" and "bounding shifts" in the `r3_resolution_bounds_*` files, their metadata note and the docstring of `scripts/analyze_revision_resolution_bounds.py` are to be read as the manuscript's post-hoc common-shift sensitivity scenarios. The archived files and the script are unchanged; Reviewer 1 found that acceptable.

## Optional comments

### 6. Larger upward scales (done)

- **Analysis.** A new script, `scripts/analyze_revision_upward_max.py`, with a test, finds the largest increase of a size or divergence at any refinement or source level: σ_y of the crowding-distance setting with one regenerated source, +16.2 %. It applies the scale ×1.17, rounded up, with the nine bunch-length and energy shifts.
- **Results.** They reproduce your check:
  - 0.276 and 0.300 at nominal bunch length and energy;
  - 0.242–0.292 and 0.267–0.317 over the shifts;
  - smallest lower interval limits of 0.200 and 0.240;
  - all ten groups positive for every pair.
- **Evidence.** It is in new files, `r5_upward_max_{runs,paired}.csv` and `_metadata.json`, mapped to S1.13 and listed in the input inventory (level 2a); the `r4_*` files are unchanged.
- **Manuscript.** Sec. V B reports the check in one half-sentence as a sensitivity check, not a bound.
- **Correction.** The round5 response to Reviewer 1 corrects the 13 % figure of our round4 response to 16.2 %.

**Location:** Sec. V B. **Supplement:** S1.13 (`r5_upward_max_*`).

### 7. "Give the same result" (done)

Sec. V B now says that the further checks "leave every paired difference positive in all ten groups". Following Reviewer 1's E2, they are called "sensitivity checks", not "scenarios". With comment 6 there are three of them.

## Evidence boundary

Every change uses data available at `c1e9d21`. The only new evidence, `r5_upward_max_*`, is a post-hoc reclassification of archived diagnostics. As in the previous rounds, the abstract is unchanged: 262 words and no numbers. The checks run for this response are listed in the [round5 overview](../revisions/round5_revision_overview.md).
