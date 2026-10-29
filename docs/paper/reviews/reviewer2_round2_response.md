# Response to Reviewer 2 — round2

**Status:** Point-by-point response for author review, against reviewed revision `9077875`. This is not a claim of journal acceptance or submission readiness. The author has chosen Physical Review Accelerators and Beams: the manuscript is now in the REVTeX 4.2 PRAB format and has no table of contents. Funding and acknowledgments, and `\finaltrue`, remain author decisions.

We thank the reviewer for a precise report. The two problems it identifies, the KLS framing (N1) and the source of the feasible-sampling advantage (N2), have changed the paper substantially.

All required items use existing data. The author also authorized every optional run the reviewer suggested, and these are recorded separately from the production campaigns:
- three constraint-aware campaigns under the TDR constraints (seeds 42–44);
- a ten-seed budget-matched Sobol arm;
- 50 lattice-jitter trials for each TDR candidate;
- the offline refit with inferred noise;
- one re-evaluation of the MOGA-derived nominal setting, with 50 jitter trials, which the reuse assessment proposed;
- a numerical-resolution check of ten reported settings (150 runs; see N4(b)), initiated by the author.

No production result was changed. The [revision overview](../revisions/round2_revision_overview.md) links the diff, the change inventory, the validation and the run list. Supplement S1 ([evidence map](../supplement/README.md)) identifies every evidence file.

## Major comments

### N1. Acceptance profile and KLS framing

1. **Origin of the production limits.** They were traced to the constraint rationale written at the configuration freeze on 2026-07-24, before any campaign. Section II B now calls them a deliberately relaxed computational acceptance profile. Earlier near-TDR limits left most early space-filling samples infeasible in this domain. The production transverse limits are 3–4 times looser than the TDR's, and there is no engineering basis for treating them as a KLS requirement. The sentence the reviewer quoted is replaced.
2. **Title, abstract and conclusions.**
   - **Title:** "Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design".
   - **Abstract:** without numbers, it describes a pipeline comparison on a KLS-derived fixed-lattice model under a relaxed profile, and states that few sampled settings meet the TDR requirements.
   - **Conclusions:** they state the limited engineering conclusion.
   - **Population and candidates:** the counts now refer to the 4,800 primary evaluations. A new table lists the two TDR candidates (A, B) with signed physical margins and relative spread, and describes them as marginal and from different runs.
3. **Reach of the TDR region.** A new Discussion subsection argues that the region lies at the edge of the six-control domain:
   - the MOGA-derived nominal setting misses the TDR by 2.7 µrad in vertical divergence;
   - 12 of its 50 jittered neighbours pass;
   - the full TDR linac has controls that are fixed here, namely the RF amplitudes and further matching quadrupoles.

**Optional TDR-constrained campaigns (run).** Three constraint-aware campaigns used the TDR optimization inequalities as constraints, with the primary protocol and the initial designs of the first three matched groups (480 evaluations):
- **None found a TDR-feasible setting.** The closest observation of each campaign missed by 4.2 % in vertical divergence, by 0.4 % in both horizontal size and vertical divergence (about 1.3 µm and 1.1 µrad), and by 3.6 % in horizontal size.
- **Comparison with the same groups' primary runs.** Reclassified under the TDR inequalities, the production-profile constraint-aware runs contain candidate A and otherwise miss by 2.3 % and 9.4 %. Targeting the TDR inequalities did not increase TDR coverage at this budget.
- **Binding constraints.** After initialization, horizontal size had the worst relative margin in 62 % of the targeted campaigns' evaluations and vertical divergence in 24 %.
- **No improvement on the references.** No TDR-feasible point exists, so none improves on candidates A and B or on the MOGA-derived setting, which misses by 1.0 % in vertical divergence. Each campaign still produced 52–58 production-feasible observations.

The Discussion subsection, the abstract (qualitatively) and the Conclusions now say that the region is approached to within a few micrometres and microradians but not entered reliably.

**Location:** title; abstract; section II B and table of TDR candidates; Discussion, "Reach of the TDR acceptance region"; Conclusions. **Supplement:** S1.4, S1.11.

### N2. Source of the feasible-sampling advantage

All three requested breakdowns were produced from existing data, with exclusive violated-channel categories after initialization and paired bootstrap intervals. The result does **not** support the "mundane" reading:

1. **Gap decomposition.**
   - Against unconstrained MOBO, transverse-only violations account for 62 % of the 0.276 feasible-fraction gap, and the energy-involving categories for 34 %.
   - Against scalarized BO, the energy-involving categories account for 63 % and transverse-only violations for 31 % of the 0.311 gap.
2. **Upper ACC3/4 quarter.** It holds 15.3 % of constraint-aware post-initialization evaluations, against 22.6 % and 24.7 %. Every evaluation there violates the energy band. The per-batch occupancy is shown in the new figure.
3. **Feasibility conditional on the energy band.** The median is 0.578, against 0.254 and 0.231. The paired differences are 0.328 and 0.342, positive in all ten groups.

The advantage therefore goes beyond the energy boundary. Against the unconstrained baseline, it comes mainly from the transverse size and divergence limits. Against the scalarized baseline, energy plays the larger part. Section III B now states that the energy weight is an effective step (minor 8). The abstract and conclusions carry the transverse finding qualitatively.

**Location:** section III B; new subsection "Sources of the feasible-sampling difference" and its figure; Discussion; Conclusions. **Supplement:** S1.5.

### N3. Space-filling reference

1. **Initial-design reference.** 5 of the 160 shared Sobol points are feasible: 3.1 %, with an exact 95 % interval of 1.0–7.1 %. It is reported as an initialization-only reference, not a matched arm.
2. **Why constraint-blind acquisition helps.** The violation shares of the initial points can be compared with those of the constraint-blind baselines:
   - transverse violations: 95.6 % against 76 %;
   - bunch-length violations: 55.0 % against 32–33 %;
   - energy-band violations: 40.0 % against 32.2 % and 42.6 %.

   Minimizing emittance and spread therefore favours smaller sizes, divergences and bunch lengths. Nothing in the baselines' targets steers the mean energy.

**Optional budget-matched Sobol arm (run).** Ten seeds, 160 points each; each seed's first 16 points are verified to equal its shared design. Results (section V C, "Sources of the feasible-sampling difference"; Supplement S1.6):
- **Feasible fraction.** 41 of the 1,440 post-initialization points are feasible: 2.8 %, with an exact 95 % interval of 2.1–3.8 %, consistent with the 3.1 % of the initial designs.
- **Paired differences.** Every pipeline exceeds the Sobol arm in all ten matched groups. The mean paired differences in feasible fraction are 0.418 (0.384–0.453) for constraint-aware MOBO, 0.142 (0.115–0.172) for unconstrained MOBO and 0.107 (0.088–0.127) for scalarized BO. At least two thirds of the constraint-aware gain over the Sobol arm therefore exceeds what either baseline achieves.
- **Channels.** Transverse violations fall from 95.3 % of the Sobol points to 76.0 % for both baselines, and bunch-length violations from 55.1 % to 32–33 %. Energy-band violations change little; they are slightly more frequent for scalarized BO than for the Sobol arm (paired difference 0.035, 0.017–0.052).
- **Front quality (post hoc).** Against the unchanged empirical reference, the Sobol arm's terminal feasible fronts have median epsilon 1.45 and IGD+ 1.14. Every pipeline improves on it, with paired intervals excluding zero. None of the Sobol arm's feasible points dominates a reference point.
- **Text changes.** The section IV B scope statement and the Limitations no longer list the Sobol arm as missing; the constraint-aware scalarized control remains listed as missing.

**Location:** "Sources of the feasible-sampling difference"; section IV B scope statement; Limitations. **Supplement:** S1.6.

### N4. Surrogate calibration and numerical resolution

**(a) Undercoverage.**
- **Causes.** "Predictive checks on unseen batches" (section V G) now discusses fixed near-zero noise, kernel misspecification and adaptively selected test points. Overconfident constraint predictions make the feasibility weights too sharp in both directions and change the proposals. The tracked diagnostics are unaffected.
- **Location of the undercoverage.** Stage- and region-resolved summaries locate it in the infeasible region. For constraint-aware horizontal emittance, coverage is 89.9 % for feasible observations and 69.5 % for infeasible ones.
- **Optional refit (run offline on all 540 training sets).**
  - The fixed-noise refits reproduce the saved-snapshot coverage to within 0.5 percentage points.
  - Inferred homoscedastic noise raises the constraint-aware objective coverage from 78.6/79.7/88.8 % (saved snapshots) to 83.4/86.6/92.7 %, and the diagnostics to 86.9–93.9 %.
  - The RMSE changes by at most 14 %, except for energy, which falls from 0.89 to 0.14 MeV.
  - The fitted noise is 10⁻⁴–10⁻³ of the training variance. For energy and bunch length it sits at the lower bound of the fitting constraint, so it acts as regularization; no simulation noise is detected.
  - The fixed noise therefore explains part, but not all, of the undercoverage. The rest is consistent with kernel misspecification and adaptive test points.

**(b) Numerical resolution.** We searched for the convergence record of the previous study in the round-1 records, the previous study's directories and the repository history. Every injector deck uses the previous study's settings, but no particle or mesh scan and no quantitative residual could be recovered.

We therefore measured the residuals ourselves (section II A; Supplement S1.13). An earlier statement on our side that convergence of these settings had been established in the previous study is withdrawn: the check shows that its conclusion does not carry over to the present settings.

Results:

- **Settings and levels.** Ten reported settings were re-tracked at 15 levels (150 runs). The settings are the MOGA-derived nominal, TDR candidates A and B, the closest observation of the TDR-constrained campaigns, and the six representatives. The levels are 20k and 40k particles from a reconstructed generator input that reproduces the source file's marginals; 48 and 64 cells in every space-charge grid dimension; half and a quarter of the integration steps; each factor alone and all combined (medium and fine); and five independently seeded random 10k sources.
- **Determinism.** Production-level reruns reproduce the archived values to floating-point precision.
- **Emittances are not converged at the inherited resolution.** At the fine level they are lower by 12–34 % (x) and 17–43 % (y), mainly through the integration step. They still change by up to 9 % between the medium and fine levels.
- **Other quantities are stable.** Energy spread changes by at most 4 % and keeps its order across the settings. Bunch length changes by at most 1 %, mean energy by at most 0.05 MeV, and transmission not at all. Sizes and divergences fall by up to 22 %.
- **Margins and classifications.**
  - All ten settings stay production-feasible at every level.
  - Candidate B meets the TDR inequalities at all 15 levels. Candidate A fails in σ_x at the 64-cell grid and with two of five random sources.
  - The MOGA-derived nominal and the closest TDR-campaign observation meet the TDR inequalities at the medium and fine levels, although they miss at production.
  - TDR membership within a few percent of the limits is therefore not resolved, and the manuscript now says so.

The Limitations keep the nominal-resolution wording, add that the method comparison has not been repeated at a converged resolution, and do not interpret the small TDR-candidate margins or differences of order 0.1 µm·rad as resolved.

The undercoverage discussion in (a) is in place. The undercoverage is concentrated in the infeasible region, and inferred noise sits at its lower bound for energy and bunch length. Numerical roughness is therefore not needed to explain it, but it is not excluded either. The refinement check shows that the emittance surface itself depends on the tracking resolution, which is a further possible contributor to the GP misspecification.

**Location:** sections II A and V G; Limitations. **Supplement:** S1.8, S1.13.

## Minor comments

1. **Abstract.** The duration statement is now a statement about the computational overhead of the present implementation. The qualitative TDR statement from N1 is added. "Limited lattice-jitter assessment" is kept.
2. **Length and density.**
   - The forensic detail now sits in a new Appendix A, "Executed implementation details": sampler counts, smoothing constants, the inclusion–exclusion description, fitting and Adam-recovery counts, effective likelihood floors and evaluation-interval unions.
   - Repeated caveats were removed, and the limitations are collected in the Limitations subsection.
   - The required new analyses add material, so the PDF is 52 pages in the one-column review format (30 pages in the two-column PRAB layout).
   - The table of contents is removed. The author chose PRAB, which does not use one (minor 9).
3. **Source comments.** All revision-integration comments and the campaign-output block were removed from `main.tex` and its inputs.
4. **RF-amplitude jitter.**
   - Tracked structure gains of 93.3 and 102.8 MeV for the ACC1/2 and ACC3/4 pairs give a 0.28–0.40 MeV mean-energy shift for 0.2 % amplitude error, depending on whether the pairs are independent or fully correlated.
   - That is about 10 times the shift from the simulated phase jitter, and at least 7.8 standard deviations inside the 3.11 MeV headroom.
   - The effect on σ_E is about 0.8 keV.
5. **Signed-rank floor.** Section IV B states that 0.0234 is the smallest Holm-adjusted value the design allows. The paired results now lead with effect sizes and intervals. The quality-indicator values are labelled exploratory, and nested intervals with the reference rebuilt in each resample were added.
6. **D < 1.** Perturbed settings do dominate their nominal points. For the spread-extreme and centroid-distance settings, 14 and 8 of 50 perturbed settings dominate the nominal setting, all of them feasible. The selected settings are therefore not locally converged along the jitter directions, and the text says so.
7. **Robustness of the TDR candidates (run).** Both remain production-feasible in 50 of 50 trials. They meet the TDR inequalities in only 36/50 (exact interval 0.58–0.84) and 44/50 (0.76–0.95). They fail mainly on horizontal size, and candidate B also on vertical divergence. Neither offers jitter-tolerant TDR operation.
8. **Energy-channel weighting.** Section III B states that τ_c = 10⁻³ eV makes the energy weight an effective step with vanishing gradient.
9. **Target journal.** The author chose Physical Review Accelerators and Beams. The manuscript is converted to REVTeX 4.2 in the PRAB style (APS front matter, references and cross-reference style), and the table of contents is removed.
10. **Front matter.** Funding and acknowledgments remain author-deferred. `\finalfalse` is retained until they are supplied.

## Assessment against the reviewer's criteria

| Criterion | Change in this revision |
|---|---|
| Technical soundness | The source of the main effect is identified (N2). Surrogate calibration is diagnosed and partly tested (N4a). A refinement check measures the numerical residuals of the reported settings (N4b). |
| Fair comparison | Space-filling reference added (N3), including a ten-seed budget-matched Sobol arm that every pipeline exceeds in feasible fraction. |
| Relevance to the stated application | Reframed as a relaxed-profile comparison on a KLS-derived model; TDR reach discussed and tested with TDR-constrained campaigns, which found no TDR-feasible setting. |
| Presentation | Implementation detail moved to an appendix, caveats consolidated, source cleaned; PRAB format without a table of contents. |
