# Reviewer 2 report — round2

**Manuscript:** *Multi-objective Bayesian optimization of a 200 MeV electron injector linac for the Korea Light Source*
**Author:** C. S. Park (Korea University)
**Source reviewed:** `docs/paper/main.tex` at commit `9077875`, with the generated tables, figures and appendix inputs it includes
**Previous round:** [reviewer2_round1_report.md](reviewer2_round1_report.md); author response [reviewer2_round1_response.md](reviewer2_round1_response.md)
**Date:** 2026-10-27

---

## Recommendation

**Major revision.** The manuscript cannot be accepted in its current form. Acceptance is
within reach, however, and the remaining required work needs **no new campaigns**.

The author has responded thoroughly and honestly, and the manuscript is much better for it.
The failed hypervolume endpoint now has proper replacements. The statistics use the paired
design. The constraint smoothing is described as it was actually executed. The physics of the
selected settings is explained, and claims have been narrowed throughout. I accept the
author's decision not to run new comparison campaigns, provided the claims stay within what
the existing simulations support.

That narrowing, together with the new analyses, has exposed two problems the paper does not
yet face:

1. Against the KLS Technical Design Report requirements, only 2 of the 4,800 primary
   simulations are acceptable. The study's acceptance profile is therefore not the KLS one,
   yet the title and abstract still present it as a KLS design study (N1).
2. The headline result is a 2.7–3.2× higher feasible fraction for constraint-aware acquisition.
   It now has a plausible mundane explanation that the paper does not test: about one fifth of
   all baseline evaluations fall in one phase region that is infeasible by construction, and
   the energy constraint is enforced almost as a hard step (N2).

Both can be resolved with the existing data and with revised framing. If N1–N3 are addressed
as described below, I expect to recommend acceptance.

---

## Assessment of the round-1 responses

| Round-1 item | Status | Comment |
|---|---|---|
| M1 Failed hypervolume endpoint | **Resolved** | Additive epsilon, IGD+, directional coverage, attainment and reference-sensitive HV are added and clearly labelled post hoc. The leave-one-group-out IGD+ check is a good addition. |
| M2 Phase bounds | **Disclosed, not resolved** | The windows are now given in degrees and called inherited and uncalibrated, which is honest. The new count in the Limitations section turns this into a substantive issue; see N2. |
| M3(a) Constraint smoothing | **Disclosed, not resolved** | The executed weights are described exactly (0.81 at σ_x = 0 and 0.19 at twice the limit; effectively a step for energy), and the offline rank-sensitivity test is useful. No corrected arm was run. Acceptable only with the attribution analysis in N2. |
| M3(b) Missing baselines | **Declined; claims narrowed** | The scope statement in section 4.2 is correct. A space-filling reference can still be extracted from the existing data; see N3. |
| M3(c) First-feasible metric | **Resolved** | It was removed from the table, and post-initialization feasible fractions are given. |
| M4 Physics | **Largely resolved** | Quadrupole positions, the emittance trajectory, chirp correlation, source moments and the inactive inequalities are now reported. The asymmetry mechanism is left open, which is acceptable as stated. |
| M5 Statistics | **Resolved** | Paired group resampling, exact signed-rank tests and Holm correction are used appropriately. See minor 5. |
| M6 Robustness | **Partly resolved; scope accepted** | Clopper–Pearson bounds, physical margins and per-objective changes are added, and the composite score is retired. RF-amplitude jitter is still omitted; see minor 4 for a cheap way to close this. |
| M7 Earlier MOGA study | **Resolved** | Distinguishing the abstract values from the actually tracked setting is exactly what was needed. |
| Minors 1–15 | **Resolved or reasonably declined** | I accept the author's preference for a number-free abstract. |
| Minor 16 Numerical resolution | **Not resolved in the text** | The settings correspondence with Kim et al. is documented. However, the manuscript now says numerical uncertainty is "unquantified", while the response record states that convergence was established previously. See N4(b). I do **not** ask for a new convergence study. |

---

## Major comments

### N1. The acceptance profile is not the KLS profile, so the paper's KLS framing must change

The new TDR comparison in section 2.2 is the most important addition of this revision. It
shows that the production profile is far looser than the KLS optimization requirements:

| Diagnostic | Production profile | TDR requirement | Ratio |
|---|---|---|---|
| σ_x, σ_y | ≤ 1.0 mm | < 0.30 mm | 3.3× looser |
| σ_x′, σ_y′ | ≤ 1.0 mrad | < 0.2663 mrad | 3.8× looser |
| Transmission | ≥ 0.90 | > 0.9999 | 10³ times more loss allowed |

Under the TDR requirements, **2 of 4,800** primary simulations are acceptable, both from
constraint-aware MOBO; under the production profile, 1,099 are. The two TDR-passing points
are also marginal, as `c01_tdr_candidates.csv` shows:

- σ_x = 0.291 and 0.298 mm, against a 0.30 mm limit;
- σ_z ≈ 0.992 mm, against 1.0 mm;
- one has a relative spread of 0.44 %, against the 0.5 % specification.

The paper therefore maps trade-offs in a region that the KLS design does not accept. Its
feasible fronts, representative settings and robustness results all refer to that region.
This is not a flaw in the method comparison, which is internally consistent. But it
contradicts the title ("…for the Korea Light Source") and the closing sentence of the
abstract, and it leaves the practical value of the reported operating points for KLS unclear.

The manuscript also never says where the production limits came from. Section 2.2 says only
that "the TDR does not justify replacing its requirements with the production limits". That
leaves the reader to wonder why the study used them at all.

Required:

1. State the origin of the production limits: an earlier design stage, a deliberately relaxed
   exploration profile, or a historical configuration default. If there is no engineering
   basis, say so plainly.
2. Reframe the title, abstract and conclusions to match the evidence. For example, describe
   the work as a method comparison on a KLS-derived injector model under a relaxed acceptance
   profile. The abstract should state, qualitatively, that the profile is looser than the TDR
   requirements and that few sampled settings meet them. A title such as "…of a KLS-derived
   200 MeV injector-linac model" would be accurate.
3. Discuss what the TDR result implies about the design domain. Is the TDR region reachable
   within the six-variable fixed-lattice model, or does it require controls that are fixed
   here (RF amplitudes, the additional matching quadrupoles in the full TDR linac)? The two
   marginal passes suggest it lies at the edge of the explored domain.

Strongly encouraged, though not required for acceptance: one constraint-aware campaign
(or a few seeds) under the TDR constraints. This would show directly whether the method can
find TDR-acceptable settings, which is the question KLS readers will ask. Because the
infrastructure exists, the cost is small.

### N2. The source of the feasible-sampling advantage must be identified

The paper's best-supported result is a feasible fraction of 40.6 % for constraint-aware
acquisition, against 15.0 % and 12.5 % for the baselines. Two facts reported in the revision
suggest that much of this gap may come from learning one simple infeasible boundary, not from
balancing the eight inequalities:

- **The phase domain.** Section 6.2 reports that the upper quarter of the ACC3/4 window
  (325.6–341.1°) contains 259, 345 and 394 evaluations from the three methods, and that every
  one of them is outside the energy band. The two baselines therefore spend 22–25 % of their
  budget in a region that the inherited percentage-based window included by accident
  (round-1 M2).
- **The smoothing.** Section 3.2 shows that, with residuals in eV and τ_c = 10⁻³, the
  energy-band weight is effectively a 0/1 step, while the size and divergence weights are
  very soft (0.81 inside the limit, still 0.19 at twice the limit).

Taken together, a plausible reading is this. Constraint-aware MOBO quickly learns the
energy-band boundary, which the step weighting enforces sharply, and so leaves the
high-ACC3/4 region. The transverse constraints, weighted weakly, contribute much less. If
that is right, the advantage is real but narrow. It would mean the method avoids an obviously
infeasible region more quickly, which is different from successfully handling a constrained
multi-objective problem. The paper should test this. The archived evaluations are enough;
nothing needs to be rerun.

Required, using existing data only:

1. For each method, a breakdown of infeasible evaluations by violated channel after
   initialization. Use exclusive categories as well as "any violation" (e.g. energy only,
   transverse only, both), so that the gap in feasible fraction can be divided among the
   channels.
2. The fraction of each method's post-initialization evaluations in the upper ACC3/4 quarter,
   per batch. This shows how quickly each method leaves the region.
3. The feasible fraction recomputed among evaluations that satisfy the energy band, i.e.
   conditional transverse and bunch-length feasibility. If constraint-aware MOBO still has a
   substantially higher fraction there, the advantage goes beyond the energy boundary. If not,
   the abstract and conclusions should say that the gain comes mainly from the energy
   constraint.

I understand that a restricted reanalysis cannot predict rankings after rerunning in a smaller
domain, and I am not asking for that. The request is to identify, descriptively, *which
constraints* produced the observed gain.

### N3. Space-filling reference and the scope of the "BO" claim

No Sobol arm was run, and the manuscript now correctly declines to claim an advantage over
space-filling search. A useful reference already exists, however. The 160 shared initial Sobol
points (16 × 10 seeds) are a space-filling sample of the same domain, and only **5 of the 160
(3.1 %)** are feasible (`c04_initialization.csv`). Even the constraint-blind methods (15.0 % and
12.5 %) therefore raise feasibility well above uniform sampling, presumably because the
objectives and the constraints are correlated.

Required:

1. Report the initial-design feasible rate, with its binomial interval, as a space-filling
   reference. It must not be presented as a matched arm: the sample is small, and it covers
   only initialization.
2. Discuss why constraint-blind acquisition already improves feasibility. For example,
   minimizing emittance may favour smaller divergences. Use the per-channel breakdown from N2.

Strongly encouraged: a budget-matched Sobol arm. It needs no surrogate and, from the reported
cost fractions, takes roughly 1 h of tracking per 160-evaluation campaign. Ten seeds would
settle the space-filling comparison and supply a reference for the front-quality indicators.

### N4. Surrogate calibration and numerical uncertainty

**(a) Overconfident surrogates.** The new predictive check is valuable. It shows that nominal
95 % intervals cover only about 79–89 % of next-batch observations. The cause is not
discussed. A likely candidate is the fixed, near-zero observation noise (η = 10⁻⁶), which
forces the GP to interpolate every observation exactly. If the ASTRA response has small-scale
roughness, from finite particle number and grid discretization, the posterior becomes
overconfident. Overconfident constraint posteriors also distort the feasibility weights that
are central to N2. Please:

- discuss the likely sources of undercoverage (fixed noise, kernel misspecification,
  adaptively selected test points) and their consequences for acquisition;
- optionally, refit the saved training sets with an inferred homoscedastic noise and report
  the coverage. This needs no ASTRA runs and would show whether the fixed-noise choice is
  responsible.

**(b) Numerical resolution.** I withdrew my round-1 request for a convergence study after the
author confirmed that convergence had been established in the previous study of this injector.
The revised text does not reflect that confirmation. Section 6.2 says that "numerical
uncertainty relative to the objective differences and feasibility margins is therefore
unquantified". The paper now argues against its own resolution choice, and the reader cannot
tell which statement holds. **No new convergence study is requested.** Please locate the
existing convergence record and report its result: the resolution tested and the residual
change in ε_n and σ_E at the adopted settings. Then compare it, in one or two sentences, with
the reported differences between methods and the smallest margins. If no such record can be
located, the sentence in section 6.2 may stand. In that case, the undercoverage in (a) should
be discussed as possible evidence of numerical roughness.

---

## Minor comments

1. **Abstract.**
   - "Weighted-sum optimization completes campaigns faster" is an implementation-overhead
     observation (median paired duration ratios 2.74 and 1.89), not a scientific finding.
     Qualify it as overhead of the present implementation, or remove it.
   - Add the qualitative TDR statement from N1.
   - "Limited lattice-jitter assessment" is appropriately worded.
2. **Length and density.** The manuscript is now about 30 pages, and the paper's main thread
   is hard to follow. Implementation-forensic detail belongs in an appendix: sampler counts,
   smoothing constants, the inclusion–exclusion description, Adam-recovery counts, the
   effective likelihood floors and the evaluation-interval unions. Caveats of the form
   "does not establish…" still appear well over a dozen times. Please state each limitation
   once in section 6.2. A table of contents is unusual for a journal article and can be
   removed.
3. **Internal comments in the source.** Revision notes such as `% C05 replacement for the
   acquisition subsection's equation and explanation`, `% Integrate before the unchanged
   scalarized-baseline paragraph`, `% C09: …` and the campaign-output block before section 5
   should be removed before submission. Journals often publish or archive the LaTeX source.
4. **RF-amplitude jitter.** I accept that new robustness campaigns are out of scope. A short
   estimate would close most of the concern at no cost. The limiting margin is the lower
   energy bound, with 3.11 MeV headroom. At about 0.2 % amplitude jitter, the corresponding
   mean-energy shift at 200 MeV is of order 0.4 MeV, plus a phase-dependent contribution to
   σ_E. Please add this estimate, or state why it does not apply.
5. **Signed-rank floor.** With n = 10 and all differences of one sign, the exact two-sided
   p-value is 2/1024. Holm's factor of 12 then gives 0.0234, the smallest adjusted value the
   design can produce. Several reported p-values sit at this floor. Please say so. The
   effect sizes and paired intervals are then the informative quantities, and the text should
   lead with them.
6. **D < 1 under jitter.** For the spread extreme and centroid point, D = 0.988 and 0.9985:
   perturbed settings are on average *better* than the nominal one. Please check whether any
   perturbed sample Pareto-dominates its nominal point. If some do, the selected settings are
   not locally converged along the jitter directions, which is worth one sentence.
7. **Robustness of the TDR-passing points.** The two TDR-passing settings sit on several limits
   at once. Fifty lattice-jitter trials for each, about 100 tracking runs, would show whether
   any setting found here is usable under the TDR profile. Recommended, not required.
8. **Energy-channel weighting.** Section 3.2 gives the indicator values for the beam-size
   channel. Please also state explicitly that, for the energy channel, τ_c = 10⁻³ eV makes the
   weight an effective step with vanishing gradient. N2 depends on this.
9. **Target journal.** The manuscript has moved from the JINST class to a generic article
   format. Please confirm the target journal; length expectations and the treatment of the
   supporting appendices depend on it.
10. **Front matter.** Funding and acknowledgments are still marked `\pending`, and line
    numbers remain enabled (`\finalfalse`). This is fine for review but must be completed
    before acceptance.

---

## Assessment against journal criteria

| Criterion | Round 1 | Round 2 |
|---|---|---|
| Originality | Moderate | Unchanged. The contribution is a careful, paired application study, not a new method. |
| Technical soundness | Inadequate | Much improved. Remaining gaps: the source of the main effect (N2) and surrogate calibration (N4). |
| Fair comparison | Partial | The scope is now stated honestly. The space-filling reference is still missing (N3). |
| Relevance to the stated application | Not assessed | **Weak.** The acceptance profile is not the KLS profile (N1). |
| Physics content | Thin | Adequate for the stated scope. |
| Reproducibility | Strong | Strong. Run identities, manifests and evidence files are exemplary. |
| Presentation | Repetitive | Still too long and hedged (minor 2–3). |

## Conclusion

This revision is a serious and transparent response, and the analysis is now careful. What
remains concerns what the results *mean*. First, the acceptance region studied is much broader
than the KLS requirements (N1). Second, the main reported advantage may come largely from one
sharply enforced energy boundary and one phase region that should not have been in the domain
(N2). Third, the comparison with space-filling sampling can be quantified from data already in
hand (N3). Fourth, the surrogate calibration and the numerical-resolution statement need to be
reconciled (N4).

None of the required items needs new optimization campaigns; the TDR-constrained campaign
and the Sobol arm are encouraged but optional. I recommend **major revision**, and I expect
to recommend acceptance once N1–N4 and the minor comments are addressed.

*— Reviewer 2*
