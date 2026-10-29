# Response to Reviewer 1 — round2

**Status:** Point-by-point response for author review, against reviewed revision `9077875`. This is not a claim of journal acceptance or submission readiness. The author has chosen Physical Review Accelerators and Beams: the manuscript is now in the REVTeX 4.2 PRAB format and has no table of contents. Funding and acknowledgments, and `\finaltrue`, remain author decisions.

We thank the reviewer for a careful and constructive report. The revision keeps every production simulation unchanged. Most of the work is manuscript revision and offline analysis of the existing records. The author also authorized a set of small, separately recorded simulations. None is a requirement of this report, and none changes a production result:

- one re-evaluation of the MOGA-derived nominal setting, with 50 lattice-jitter trials;
- 50 lattice-jitter trials for each TDR candidate;
- three constraint-aware campaigns under the TDR constraints;
- a ten-seed budget-matched Sobol arm;
- a numerical-resolution check of ten reported settings (150 runs; see M2).

These runs mainly answer Reviewer 2. Results that bear on this report are noted where they apply.

The [revision overview](../revisions/round2_revision_overview.md) links the manuscript diff, the change inventory, the validation and the list of authorized runs. Supplement S1 ([evidence map](../supplement/README.md)) identifies the evidence behind each result.

## Major comments

### M1. Scientific target and acceptance population

**Change.** The study is now framed throughout as a comparison of three specified pipelines on a fixed injector model derived from the KLS design, under a stated relaxed profile.

- **Title:** "Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design".
- **Abstract:** without numbers, it states that feasibility is judged against a relaxed computational profile and that few sampled settings meet the TDR requirements.
- **Origin of the production profile (section II B):** a deliberately relaxed computational acceptance profile, frozen before the campaigns. Earlier near-TDR limits left most early space-filling samples infeasible in this domain. The profile has no engineering basis as a KLS requirement, and the text says so.
- **Population:** the counts now refer to the 4,800 **primary** evaluations: 648, 251 and 200 production-feasible, and 2, 0 and 0 under the TDR inequalities.
- **New table of the two TDR candidates.** They carry stable labels A and B and are listed with objectives, relative spread and signed physical margins. The text states that:
  - both are marginal and come from different matched runs;
  - they are not the jitter representatives;
  - two against none is observed coverage, not a method ranking.
- **New Discussion subsection, "Reach of the TDR acceptance region",** which lies at the edge of the six-control domain. The Conclusions state the limited engineering conclusion.

**Additional evidence (authorized runs, not requested here):**
- Under the same lattice jitter, candidates A and B meet the TDR inequalities in only 36 and 44 of 50 trials.
- The three TDR-constrained campaigns found no setting that meets the TDR inequalities. Their closest observations miss by 0.4–4.2 %, the closest by about 1.3 µm in horizontal size and 1.1 µrad in vertical divergence. This supports the reach statement in the Discussion and does not change the method comparison.

**Location:** title; abstract; section II B and table of TDR candidates; Discussion, "Reach of the TDR acceptance region"; Conclusions. **Supplement:** S1.4, S1.10.

### M2. Numerical accuracy at the relevant margins

**Disposition: a measured refinement check, with nominal-resolution wording retained.** We first searched for the earlier convergence evidence: the round-1 records, the previous study's directories (`linac/beam_tracking`, `linac/cmkim`), and the repository documents and history. Every injector deck uses the previous study's settings, but no particle or mesh scan and no refinement residual could be recovered. The search is recorded in supplement S1.13. We therefore measured the residuals ourselves. An earlier statement on our side that convergence of these settings had been established in the previous study is withdrawn: the check shows that its conclusion does not carry over to the present settings.

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

Section II A reports this check. Section VI B ("Reach of the TDR acceptance region") gives its consequence for the TDR classifications. The Limitations state that all values are nominal-resolution results and that the method comparison has not been repeated at a converged resolution. The small TDR-candidate margins and objective differences of order 0.1 µm·rad are still not interpreted as resolved. The check supports the reviewer's concern: absolute emittances should not be quoted without a converged calculation, and the abstract and Conclusions now say so qualitatively.

**Location:** section II A; section VI B (TDR reach); Limitations (section VI C); abstract; Conclusions. **Supplement:** S1.13.

### M3. The raw-residual acquisition is the tested implementation

**Change.**
- **Section IV A** describes three specified optimization pipelines that share the physical model, initial designs and simulation budget. They differ in target construction, model count, constraint information and Monte Carlo sample counts.
- **Section III B** identifies the compared constrained method as the raw-residual implementation. It states explicitly that τ_c = 10⁻³ eV makes the energy-band weight an effective step with vanishing gradient.
- **The offline sensitivity subsection** states its limits (q = 1, no pruning, one run). It states that an unchanged top probe does not show that the production q = 8 optimizer is invariant, and that the probe does not validate a corrected campaign.
- **No unit-invariant or corrected acquisition is claimed.** A short synthesis separates what the three-pipeline comparison measures from what the diagnostic shows.

**New attribution (existing data only).** This analysis shows which constraints produced the measured advantage.
- Against unconstrained MOBO, 62 % of the feasible-fraction gap comes from transverse-only violations.
- Among energy-acceptable evaluations, constraint-aware MOBO is still feasible far more often: medians 0.578 against 0.254 and 0.231, positive in all ten groups.

**Location:** sections III B and IV A; "Offline sensitivity of constraint smoothing"; new subsection "Sources of the feasible-sampling difference" and its figure; Discussion; Conclusions. **Supplement:** S1.5, S1.7.

### M4. Exact enumeration versus inference with a shared estimated reference

**Change.**
- **The feasible-fraction effects lead the paired results.** They need no objective reference, and constraint-aware feasibility is higher in all ten matched groups against each baseline.
- **Section IV B explains the remaining limits of the quality-indicator tests:**
  - sign enumeration after a shared, data-derived transformation does not establish calibration;
  - Holm correction cannot repair this;
  - 0.0234 is the smallest adjusted value the design allows.
- **The quality-indicator signed-rank values are labelled exploratory and uncalibrated.** Effect sizes and paired intervals are the reported quantities.
- **Optional nested analysis.** It resamples the matched groups 2,000 times and rebuilds the empirical reference front and the HV reference inside each resample. It addresses only the uncertainty from estimating the reference from the same groups, and it yields no p-values. Every constraint-aware interval still excludes zero under both constructions:
  - against unconstrained MOBO: epsilon −0.481 to −0.161, IGD+ −0.293 to −0.071;
  - against scalarized BO: −0.470 to −0.176 and −0.244 to −0.066.
  - The HV intervals widen markedly. All baseline-to-baseline intervals include zero.

**Location:** section IV B; paired results in "Primary comparison" (section V B); Appendix B; Discussion. **Supplement:** S1.2, S1.3.

### M5. Predictive errors where decisions are made

**Change.** "Predictive checks on unseen batches" (section V G) explains three likely causes of the undercoverage and their consequence: overconfident constraint predictions sharpen the feasibility weights and change the proposals, but not the tracked diagnostics. The causes are:
- the near-zero fixed noise;
- a stationary kernel that cannot follow sharp boundaries;
- adaptively selected test points.

As the reviewer suggested, the existing records are now resolved by stage and region, with counts and run-level quartiles:
- **Whole-trajectory RMSE mixes regions.** For constraint-aware MOBO, horizontal-emittance coverage is 89.9 % for feasible next-batch observations and 69.5 % for infeasible ones. The RMSE is 2.60 against 10.33 µm·rad, and 0.98 µm·rad for late feasible observations.
- **By stage**, the transverse diagnostics rise from 75.6–80.0 % early to 88.3–91.0 % late. Emittance coverage does not improve monotonically.
- **No claim of calibrated local prediction is made.** Even feasible-region intervals remain below their nominal coverage.

An offline refit with inferred noise was added at Reviewer 2's request; this report did not require it. It raises coverage but does not restore nominal coverage. The constant transmission channel is still stated to give no evidence of loss discrimination.

**Location:** section V G; Limitations. **Supplement:** S1.8.

### M6. An identifiable supplement

**Change.**
- **Supplement S1** is the versioned `mobo_linac` 1.0.0 repository snapshot that accompanies the manuscript. Its evidence map numbers the results S1.1–S1.15 and links each to its evidence file, its generator and the run ledgers.
- **A new paragraph in Appendix A** identifies:
  - the clean production commits: primary `8ad6c2c`, survey `239c466`, audit and jitter `f6ce000`, and revision simulations from `bfb0be0`;
  - the revision-analysis code, which is distinct from the production code;
  - the command-line overrides of the configuration defaults;
  - the undistributed run directories (about 44 GB) and the 10 MB of checksummed ledgers that suffice to regenerate the evidence;
  - the unarchived sampler base draws.
- **Specific pointers.** The generic "supporting data/manifest/results" pointers now name specific items.
- **Validation.** A checker validates the map against the evidence directory, the manuscript labels and the ledger checksums.
- **Data availability.** A Data availability statement now says that the ledgers, run directories, configurations and analysis scripts identified in S1 are available from the corresponding author upon reasonable request. Nothing was uploaded or pushed; a public deposition is a separate author decision.

**Location:** Appendix A, "Supporting package"; Results introduction. **Supplement:** S1.1 and the map itself.

## Minor comments

1. **"Knee".** Replaced everywhere by "ideal-distance point", described as a distance criterion. "Centroid-distance point" is named for its criterion and is not described as physically balanced.
2. **GP wording.** "Without smoothing the data" is replaced by a description of numerical regularization with a nonzero effective likelihood variance.
3. **Budget matching.** See M3. The arms are specified pipelines, and equal evaluation budgets are not described as equal computation.
4. **Labels.** Section IV D and Table VI use the same labels: equal weight and emittance, spread, horizontal or vertical emphasis. "High brightness" is removed.
5. **Conclusions.** Rewritten around the paired feasible-sampling result and its source, the qualified front quality, the MOGA-derived reference, the limited engineering conclusion, and robustness conditional on the lattice-only error model. Repeated pooled counts are removed.
6. **Presentation.** The revision-integration comments and the campaign-output block are removed, and PDF title, author and keyword metadata are added. The abstract remains qualitative. Funding is still author-deferred.
7. **Length.** Implementation-audit detail has moved to the new Appendix A. That detail covers the likelihood floors, fitting counts, smoothing constants, sample counts and evaluation-interval method, and it is identified through S1.7. The unit-smoothing issue and acceptance definitions remain in the main text. The new required analyses add material, so the PDF is now 51 pages in the one-column review format (30 pages in the two-column PRAB layout).

## Conditions for reconsideration

The minimum revision asked for in the report is complete:
- the computational and engineering target is stated;
- the numerical evidence is a measured refinement check of the reported settings, with nominal-resolution wording retained;
- method claims match the executed acquisition;
- the reference-dependent inference is qualified;
- the surrogate errors are interpreted;
- the supplement is identified.

No claim requiring a corrected campaign, numerically resolved settings or a MOGA benchmark is made.
