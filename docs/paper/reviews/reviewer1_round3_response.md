# Response to Reviewer 1 — round3

**Status:** Point-by-point response for author review, against reviewed revision `00190d8`. It does not claim journal acceptance or submission readiness. Funding and acknowledgments, and `\finaltrue`, remain author decisions.

We thank the reviewer for a careful report. It separates what the resolution finding still supports from what it no longer supports. We have taken the first of the two routes the reviewer describes. The paper is now explicitly a comparison of the specified pipelines on a nominal numerical model, and the measured resolution sensitivity is reported as a central result. No physically resolved ranking of the methods and no engineering-ready Pareto setting is claimed. Every change to the manuscript in this round draws on data that existed at the reviewed revision. No production result was changed. The [round3 overview](../revisions/round3_revision_overview.md) links the diffs, the change inventory and the validation.

## Major comments

### M1. Propagate the measured numerical sensitivity into the central claim

1. **Scope.**
   - **Abstract:** it now opens with the pipeline comparison and its feasible-sampling result. It then states that tracking uses a fixed nominal resolution at which the absolute emittances are not converged. It ends by saying the results compare the specified pipelines within the nominal numerical model and are not a physically resolved optimization of the injector.
   - **Introduction:** a new sentence ties every Pareto and algorithm comparison to the fixed source file and tracking resolution of Sec. II.
   - **Contributions:** a fifth contribution reports the measured numerical sensitivity as a stated limitation of the model, not as a convergence result. The closing sentence of the contributions excludes a physically resolved ranking of the methods, global optimality and engineering acceptance.
   - **Results and Conclusions:** the opening sentences of both place the comparison within the nominal numerical model.
   - **Title:** unchanged, since it already names a model.
2. **Visible display.** New Table `tab:resolution` in Sec. II A gives the changes of the exit-plane quantities of the ten re-tracked settings under refinement, relative to the production resolution. It separates the fixed-source step and grid changes from the particle-count and regenerated-source changes, and gives the classification changes. Sec. II A now says that a regenerated source reproduces the marginals of the production file, not necessarily its multidimensional distribution, and that the step-only refinement uses the production file itself.
3. **Population of every stability statement.** Sec. II A, the Limitations and the Conclusions say that the ten settings are feasible and come mostly from constraint-aware searches. They contain no rejected or baseline observation, so their stable classification does not show that the primary classifications are stable. The unqualified statement in the Conclusions now names "those ten settings".
4. **Effect on the primary comparison (existing data).** The 4,800 primary evaluations and the 1,600 Sobol-arm evaluations were reclassified under bounding shifts taken from the refinement check. There were 27 combinations: sizes and divergences ×0.78, ×0.89 or ×1; bunch length ±1 %; mean energy ±0.05 MeV. The median feasible fraction ranges over:
   - 0.369–0.466 for constraint-aware MOBO;
   - 0.147–0.213 for unconstrained MOBO;
   - 0.113–0.181 for weighted-sum BO.

   The post-initialization paired differences stay between 0.239 and 0.335, with every interval above zero and every difference positive in all ten groups. The text says these shifts are bounds taken from ten settings, not a per-point refinement model and not an error bound (Sec. V B, Limitations).
5. **Front quality.** Sec. V B and the Discussion say that the front-quality comparisons depend on the fixed source realization and the production resolution more strongly than the feasibility comparison. They are not tested at a converged resolution.
6. **Further tracking.** No physically resolved claim is retained, so no validation tracking enters the manuscript. The Conclusions name a comparison at a converged tracking resolution as future work.

**Location:** abstract; Introduction and contributions; Sec. II A and Table `tab:resolution`; Secs. V and V B; Discussion; Limitations; Conclusions. **Supplement:** S1.13 (`r3_resolution_bounds_*`).

### M2. Uncertainty model for the Sobol arm

1. **Removed:** the pooled "exact binomial" interval for 41/1,440.
2. **Run-level uncertainty instead.** Sec. V C reports:
   - the observed fraction, 2.8 %;
   - the ten run-level fractions, 1.4–4.9 % with s.d. 1.3 points;
   - a percentile bootstrap over the ten runs, 2.1–3.6 %, labelled approximate and probably too narrow with ten replicates.
3. **Audit of `analyze_revision_space_filling.py`.** The pooled intervals for the shared initial design and the adaptive BO observations are superseded by run-level summaries in new evidence files. The round2 evidence is left unchanged.
4. **Kept unchanged:**
   - the paired group bootstrap of the BO-minus-Sobol differences;
   - the executed 144-point post-initialization segments;
   - the design-specific intervals for the independent jitter draws.

**Location:** Sec. V C; Conclusions. **Supplement:** S1.6 (`r3_sobol_uncertainty_*`).

### M3. Domain geometry and causal mechanism

1. **"At the edge of the explored domain" is removed** from the abstract, contribution 3, the TDR-reach subsection and the Conclusions. They now state what was observed:
   - rare TDR-feasible observations at the nominal resolution;
   - micrometre-scale diagnostic margins;
   - membership that changes under refinement.
2. **Control-space location.** The TDR-reach subsection gives the normalized controls: candidate A lies between 0.48 and 0.86 in every coordinate; candidate B is interior except for the gun phase, at 0.96. The text says that two points do not locate a region in six dimensions. It also says that three finite-budget campaigns do not show the region to be inaccessible. The additional RF and matching controls of the full TDR linac are named as design options, not a demonstrated remedy.
3. **Attribution.** Sec. V C calls the exclusive categories an accounting decomposition of the observed gaps, not a causal identification of acquisition terms. It calls the energy-conditional fractions comparisons of method-selected populations.
4. **Attribution per baseline.** The abstract, contribution 2, the Discussion and the Conclusions state the attribution separately for each baseline:
   - mainly transverse against unconstrained MOBO;
   - mainly the energy band against weighted-sum BO;
   - persisting among energy-acceptable evaluations in both cases.

   No comparator-independent "mainly transverse" statement remains.

**Location:** abstract; contributions 2 and 3; Sec. V C; Discussion, "Reach of the TDR acceptance region"; Conclusions.

### M4. RF-amplitude argument

1. **Inputs and assumptions named.** The robustness subsection names the reference setting: the re-evaluated MOGA-derived nominal setting, with gains of 4.1, 93.3 and 102.8 MeV. It also names the linear gain-scaling approximation at fixed phase and the two correlation assumptions.
2. **0.28 and 0.40 MeV RMS** are called conditional linearized estimates of the mean-energy variation, not a bound.
3. **Removed:**
   - the inference that the 3.11 MeV lower-energy headroom preserves full production-profile feasibility;
   - the scaling of the energy spread.
4. **Stated as not estimated:** the bunch-length and upper-energy margins, phase slippage, focusing and chirp.
5. **Comparison with the TDR margins.** The TDR-candidate paragraph compares the estimate with the TDR lower-energy margins of candidates A and B (0.31 and 0.14 MeV), as an indication, not a bound.
6. **Kept:** the tracked lattice-only results stand as their own evidence.

**Location:** Results, "Robustness to lattice jitter"; Discussion.

### M5. Regeneration claim of the supplement

1. **Removed:** the statement that about 10 MB of ledgers regenerate every evidence file, from Appendix A and the supplement README.
2. **Input inventory.** The new `docs/paper/supplement/input_inventory.csv` lists, for each generator, its input classes, its run files and its reproduction level:
   - level 1: tables and figures from the distributed derived evidence;
   - level 2a: from the minimal ledgers;
   - level 2b: also needs GP checkpoints, retained tracking outputs or re-tracking records;
   - level 3: re-tracking with ASTRA.

   The README gives examples: GP checkpoints for the predictive checks, a retained `astra.Zemit.001` for the RF estimate, and the convergence records. It also says proposals cannot be replayed bitwise.
3. **Check enforcement.** `scripts/build_supplement_manifest.py` now fails on any generator without a valid inventory entry.
4. **Regeneration test.** The new `scripts/check_supplement_regeneration.py` builds a scratch tree with only the 215 minimal ledger files. It reruns three level-2a generators there: the resolution bounds, the Sobol uncertainty and the attribution. All three match the committed evidence (`r3_regeneration_check.json`). The levels 2b and 3 are stated as inventory only, not tested.
5. **Availability.** Appendix A, the Data availability statement and the README now agree. S1 is supplied for review and is otherwise available on request. The run directories are available from the author, and the snapshot is identified by the commit of the review package. No public deposit is made.

**Location:** Appendix A; Data availability; Supplement S1 README. **Supplement:** S1 map and inventory.

## Minor comments

1. **Dominance wording.** Sec. V J, the Discussion and the Conclusions now say that no primary feasible observation Pareto-dominates the MOGA-derived nominal setting at the nominal resolution. The single-objective improvements are kept, and the reference is not described as an optimum.
2. **Surrogate explanations.**
   - **Hypotheses:** Sec. V G introduces fixed noise, kernel misspecification and adaptive test points as three hypotheses, none isolated. The inferred-noise refit is described as showing sensitivity to the regularization only.
   - **Fallback refits:** the 88 refits restored to initial hyperparameters are called non-equivalent fits.
   - **Split not done:** the archived refit records carry no fallback flag, so separating them would require redoing the refits. The wording is therefore descriptive, as the reviewer allows.
3. **Precision and figures.**
   - **Labels:** Tables IV, V and X and both Pareto figures are labelled as nominal-resolution results.
   - **Quoted digits:** the caption of Table X and Sec. V H say that the digits identify archived evaluations and are not resolved physical values.
   - **Rounding:** running-text values are rounded to three significant figures.
   - **Display:** the refinement result is shown in Table `tab:resolution`.
4. **Readability.**
   - **Abstract and contributions:** they lead with the specified-pipeline comparison and the measured numerical limitation.
   - **Diagnostic subsections:** the offline smoothing probe and the detailed predictive-check breakdown move to appendices, with short summaries kept.
   - **Layout:** the one-column review layout, scatter points, grid lines and shaded constraint regions are unchanged. The review copy now has 56 pages, and the two-column layout 31.

## Evidence boundary

Every manuscript change of this round uses data available at `00190d8`: the archived ledgers, the round2 evidence and the round2 resolution records. No production result, feasibility label, seed or acquisition definition was changed. The checks run for this response are listed in the [round3 overview](../revisions/round3_revision_overview.md).
