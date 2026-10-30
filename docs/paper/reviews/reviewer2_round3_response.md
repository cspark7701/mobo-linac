# Response to Reviewer 2 — round3

**Status:** Point-by-point response for author review, against reviewed revision `00190d8`. It does not claim journal acceptance or submission readiness. Funding and acknowledgments, and `\finaltrue`, remain author decisions.

We thank the reviewer for a constructive report and for the spot check of the archived ledgers, which the new bounding analysis confirms and extends. Every change to the manuscript in this round draws on data that existed at the reviewed revision, and no production result was changed. The paper is now explicitly a comparison of the specified pipelines on a nominal numerical model, with the measured resolution sensitivity as a stated result (a fifth contribution). The [round3 overview](../revisions/round3_revision_overview.md) links the diffs, the change inventory and the validation.

**Correction of our round2 response.** It stated that all revision-integration comments had been removed. That was wrong: `% C05 replacement for the acquisition-reference explanation.` remained in Sec. III C. It is now removed. A new test, `tests/test_manuscript_hygiene.py`, fails on any revision-tag comment in `main.tex` or the files it includes.

## Major comments

### R1. Attribution of the feasible-sampling advantage

1. **Per baseline.** The abstract, contribution 2, the Discussion and the Conclusions now state the attribution for each baseline. The advantage persists among evaluations that meet the energy band. Against unconstrained MOBO it lies mainly in the transverse size and divergence limits. Against weighted-sum BO the energy band accounts for the larger share.
2. **Partial contribution.**
   - **Wording:** "is not produced by" is replaced by "neither the effective step weight of the energy band nor the upper ACC3/ACC4 phase window explains it alone".
   - **Upper quarter quantified (Sec. V C):** the constraint-aware pipeline's lower mean occupancy there, 0.060 and 0.094, is about a fifth and a third of the two gaps.
   - **Interpretation:** Sec. V C also calls the exclusive categories an accounting decomposition, not a causal identification. It calls the energy-conditional fractions comparisons of method-selected populations.

**Location:** abstract; contribution 2; Sec. V C; Discussion; Conclusions.

### R2. Stability of the primary comparison under the refinement shifts

1. **Bounding reclassification (existing data).** The 4,800 primary evaluations and the 1,600 Sobol-arm evaluations were reclassified under 27 combinations of bounding shifts:
   - sizes and divergences ×0.78, ×0.89 or ×1, where 0.78 is the largest reduction observed;
   - bunch length ±1 %;
   - mean energy ±0.05 MeV.
2. **Results (Sec. V B).**
   - **Median feasible fraction:** 0.369–0.466 for constraint-aware MOBO, 0.147–0.213 for unconstrained MOBO and 0.113–0.181 for weighted-sum BO.
   - **Paired differences after initialization:** 0.239–0.294 against unconstrained MOBO and 0.279–0.335 against weighted-sum BO. Every bootstrap interval lies above zero.
   - **Every group:** every difference, including each pipeline's difference from the Sobol arm, is positive in all ten groups.
   - **Bunch-length sensitivity:** as the reviewer observed, the constraint-aware fraction is the most sensitive to the bunch-length limit. A +1 % bunch length lowers its mean from 0.405 to 0.364, and the text says so.
   - **Status of the shifts:** they are bounds taken from ten settings, not a model of refinement at every point.
3. **Front quality.** Sec. V B and the Discussion say that the front-quality comparisons depend on the fixed source realization and the production resolution more strongly than the feasibility comparison. The reasons given are the nonuniform emittance shifts (12–43 %; Spearman 0.79 for ε_x) and the 1–12 % random-source spread.
4. **Visible display.** New Table `tab:resolution` in Sec. II A summarizes the refinement result.
5. **Optional re-tracking of the 53 pooled-reference points.** Not run. The front-quality comparisons are instead stated as conditional on the source realization and the resolution, and as not tested at a converged resolution.

**Location:** Sec. II A and Table `tab:resolution`; Sec. V B; Discussion; Limitations; Conclusions. **Supplement:** S1.13 (`r3_resolution_bounds_*`).

### R3. Summary statements against the detailed results

- **(a) Refined TDR membership.** The Conclusions now match the TDR-reach subsection. The closest TDR-constrained observation and the MOGA-derived nominal setting meet the TDR inequalities at the combined medium and fine levels, but fail with four of five regenerated sources, so membership near the limits is not numerically resolved.
- **(b) Sobol-arm share.** Sec. V C and the Conclusions now say: "the constraint-blind pipelines account for at most about one third (shares 0.34 and 0.26) of the constraint-aware gain over the Sobol arm".
- **(c) Contribution 1.** It now says that the feasible fraction was predeclared, and that the predeclared fixed-reference hypervolume endpoint failed and is replaced by labelled post-hoc front-quality indicators.

## Minor comments

1. **Sobol energy-band sentence.** It is now direction-specific: unconstrained MOBO falls from 39.0 % to 32.2 % (paired −0.069), while weighted-sum BO rises to 42.6 % (paired +0.035, interval 0.017–0.052).
2. **RF amplitude and the TDR energy limit.**
   - **Comparison added:** the TDR-candidate jitter paragraph compares the linearized estimate (0.28–0.40 MeV RMS) with the TDR lower-energy margins of candidates A and B, 0.31 and 0.14 MeV. This indicates that amplitude jitter would cause further TDR failures.
   - **Status of the estimate:** following Reviewer 1, it is described as a conditional linearized estimate, not a bound.
3. **Precision.**
   - **Archived digits:** the caption of Table X and Sec. V H say that the quoted digits identify archived evaluations and are not resolved physical values.
   - **Labels:** Tables IV, V and X and both Pareto figures carry a nominal-resolution label.
   - **Rounding:** running-text emittances and energy spreads are rounded to three significant figures. Published values of earlier studies are kept as published.
4. **"Deterministic".** Sec. III A adds that the calculation is deterministic for the fixed source file. It also says that the file's sampling error, 1–12 % in emittance, is common to all methods and is not represented by the GP noise.
5. **Data availability and Supplement S1.**
   - **Consistent statements:** Appendix A, the Data availability statement and the supplement README now agree. S1 is supplied for review and is otherwise available on request, and the run directories are available from the author.
   - **"Accompanies":** the word is no longer used for an undistributed snapshot; the snapshot is identified by the commit of the review package. No public deposit is made.
   - **What each item needs:** a new input inventory records the inputs and reproduction level of each S1 item.
6. **Length and placement.**
   - **Sec. V F:** reduced to a summary (the unit dependence and Spearman 0.79–0.88). The probe moves to a new appendix.
   - **Sec. V G:** keeps the 79–89 % coverage and "part, but not all", with the causes worded as hypotheses. The stage-, region- and refit-resolved detail moves to Appendix D.
   - **Sec. II A:** shortened to the findings of the resolution check. The level definitions move to Appendix A.
7. **APS style.** "Ref." is used for in-text references, and Kim et al.'s section is cited as "Sec. 4.3".
8. **Leftover source comment.** Removed; see the correction above.
9. **Abstract.**
   - **Split sentence:** the three-clause sentence is split.
   - **Order:** the abstract now leads with the pipeline comparison and the numerical limitation, and includes the R1 attribution per baseline and the nominal-model scope.
   - **Length:** it is not longer than before, at 262 words against 263 at `00190d8`. To make room, the weighting survey is no longer mentioned in it.
   - **Numbers:** it still contains none.

## Evidence boundary

Every manuscript change of this round uses data available at `00190d8`: the archived ledgers, the round2 evidence and the round2 resolution records. No production result, feasibility label, seed or acquisition definition was changed. The checks run for this response are listed in the [round3 overview](../revisions/round3_revision_overview.md).
