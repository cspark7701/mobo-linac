# Referee Report — Reviewer 2 (Round 1)

**Manuscript:** *Multi-objective Bayesian optimization of a 200 MeV electron injector linac for the Korea Light Source*
**Author:** C. S. Park (Korea University)
**Target journal:** JINST
**Source reviewed:** `docs/paper/main.tex` (commit `fe459f2`), with the generated tables and figures it includes
**Date:** 2026-10-26 (revised 2026-10-26)

> **Revision note.** The original major comment on numerical fidelity (a macroparticle and
> space-charge-grid convergence study) is withdrawn. The author has confirmed that numerical
> convergence of these ASTRA settings was established in the previous study of this injector.
> What remains is a minor request (minor comment 16) to document this in the manuscript.
> Major comments M5–M8 have been renumbered M4–M7.

---

## Recommendation

**Major revision.** The manuscript cannot be accepted in its current form.

The topic is relevant to JINST. The software pipeline appears careful: paired seeds, matched
budgets, failure-inclusive accounting and provenance. The problems are elsewhere. The
manuscript's main quantitative endpoint failed, two of its key implementation choices are hard
to defend on physics or numerical grounds, and the baselines are too weak for the conclusions
drawn from them. What remains is a set of descriptive statistics that mostly confirm what the
method is built to do: constraint-aware acquisition samples more feasible points than methods
that ignore the constraints. I think these problems can be fixed, and I would be glad to see a
revised version.

---

## Summary of the submission

The author optimizes six machine settings of an ASTRA model of the KLS 200 MeV S-band injector:
the solenoid field, two quadrupole gradients, the gun phase and two paired structure phases.
There are three minimized objectives (ε_n,x, ε_n,y and σ_E) and eight inequality constraints on
seven exit-plane diagnostics. Three methods are compared over ten paired runs of 160
simulations each: constraint-aware qLogNEHVI, unconstrained qLogNEHVI and equal-weight
qLogNEI. A five-weighting scalarization survey and a lattice-jitter robustness test of six
representative points complete the study. The main results are:

- median feasible fractions of 40.6 %, 15.0 % and 12.5 %;
- pooled feasible Pareto sets of 49, 27 and 17 points;
- 100 % feasibility under 0.1 % magnet and 0.1° phase jitter.

The predeclared fixed-reference hypervolume was zero for every campaign.

---

## Major comments

### M1. The primary performance endpoint failed, and nothing replaces it

Section 5.2 reports that the predeclared hypervolume is zero for every campaign. The reference
point (1.5 µm·rad, 1.5 µm·rad, 1.5 MeV) lies below every observed emittance (the minimum is
about 2.55 µm·rad). The author drops the metric and uses feasible fraction and Pareto
cardinality instead. Neither measures front quality:

- **Pareto cardinality** rewards many points, not good ones. Figure 3 shows that the
  constraint-aware set contains points that are feasible but have no practical value. Examples
  are σ_E ≈ 1.2–2.2 MeV at ε_n,x ≈ 2.6 µm·rad, and the extreme end at ε_n,x ≈ 7 µm·rad. Such
  points raise the count without improving the front. A method can have a larger set and a
  worse front.
- **Feasible fraction** largely restates the design goal of the constraint-aware acquisition.
  See M3.

Openness about the failed endpoint is commendable. Still, the paper needs a valid measure of
front quality before it can claim anything about MOBO for this problem. I request:

1. A post-hoc hypervolume of the **feasible** observations with a physically justified
   reference point, for example a nadir taken from the pooled feasible set, or engineering
   upper limits such as (6 µm·rad, 6 µm·rad, 1 MeV). It should be clearly labelled as post hoc
   and reported with its sensitivity to two or three reasonable reference choices.
2. At least one reference-free indicator, for example IGD+ against the pooled
   all-method feasible front, or empirical attainment surfaces/functions across the ten seeds.
3. Per-run hypervolume traces against evaluations, which show sample efficiency. A single
   end-of-campaign number does not.

Without these, the title and abstract promise a MOBO study that the evidence does not deliver.

### M2. The phase bounds have no physical meaning as percentages

Table 1 sets the phase bounds at "±10 % of nominal". Percentages of an absolute phase in
degrees depend on where the phase origin happens to be:

- φ_gun: 35.62° ± 3.56°
- φ_acc1/2: −39.51° ± 3.95°
- φ_acc3/4: 310.05° ± **31.0°**

The ACC3/4 window is about eight times wider than the others only because its nominal number
is large. A 62° window around a high-energy structure pair covers a very wide range of off-crest
operation. This is probably why so many candidates fall outside the 195–205 MeV band in
Fig. 7(c). The range of the search space, the location of the front, and the comparative
feasible fractions all depend on this arbitrary choice.

Please:

- give every RF phase relative to crest (maximum energy gain), or relative to the
  minimum-energy-spread phase;
- justify each window in degrees on physical grounds;
- either rerun with physically motivated bounds, or show that the conclusions do not depend on
  the bounds.

Each phase should also be stated as an off-crest angle at the nominal point and at the
representative solutions. Readers cannot interpret the energy-spread results without this.

### M3. The constraint handling and the baselines are too weak to support the comparison

**(a) The smoothing temperature is badly scaled.** Section 3.2 states that the constraint
residuals c_k enter the sigmoid in SI units with a common τ = 10⁻³. The author treats this as a
footnote-level limitation. It is more serious than that:

- For the beam sizes, divergences and bunch length, the limit is itself 10⁻³ m or 10⁻³ rad. The
  sigmoid's transition width therefore equals the whole allowed range. A candidate with
  σ_x = 0 m gets an indicator of only about 0.73 instead of about 1. A candidate at 2 mm, twice
  the limit, still gets about 0.27. These channels are smoothed so strongly that they barely
  constrain the acquisition.
- For the energy bounds, written in eV, τ = 10⁻³ eV is effectively a hard step. Its gradient is
  zero almost everywhere.

As implemented, the "constraint-aware" method weights the channels very unevenly and in an
uncontrolled way. Its advantage in feasible fraction is real, but it cannot be credited to the
constraint model as described. Please:

- normalize the residuals, for example c_k/limit_k, with τ chosen in normalized units;
- rerun the constraint-aware arm, at least for the ten primary seeds;
- report how often each channel actually affected the acquisition.

If the rerun is not possible, the paper should quantify the effective transition widths per
channel. It should also describe the method as "partially constraint-weighted" rather than
constraint-aware.

**(b) The baselines are mismatched or missing.** Neither baseline sees the constraints. A
higher feasible fraction for the only method that models them is therefore expected. The paper
needs comparisons that separate *multi-objective* from *constraint-aware*:

- a constrained scalarized baseline (qLogNEI with the same constraint models), which isolates
  the effect of the hypervolume acquisition;
- a Sobol/random-search baseline at the same 160-evaluation budget, which shows whether BO
  beats space-filling sampling at all on this six-dimensional problem;
- ideally, NSGA-II (or the MOGA of ref. [Kim2024]) at the same budget and at a moderately
  larger one (e.g. 1,000–2,000 evaluations). The introduction motivates BO by saying GAs need
  "tens of thousands of simulations". That claim is never tested, and section 5.1 explicitly
  declines to support it.

**(c) The "evaluations to first feasible point" result follows from the design.** The medians
are 12.5, 13.0 and 12.5, with identical confidence intervals. They are all below 16, the size
of the shared Sobol initial design. The first feasible point is therefore usually found in the
initial design, which is identical across methods. This row tells us nothing about the
algorithms. It should be removed or explained.

### M4. The physics behind the trade-offs is not explained

The paper is close to a black-box benchmark. For a JINST readership, the physics needs to be
discussed:

- **ε_n,x ≠ ε_n,y.** The gun, solenoid and structures are nominally cylindrically symmetric.
  Feasible Pareto points still show ε_n,y/ε_n,x of up to about 4 (e.g. min_emit_x: 2.81 vs
  6.85 µm·rad). Which mechanism breaks the symmetry? Candidates include coupling from the
  solenoid's Larmor rotation with the quadrupoles, chromatic effects in the quadrupoles, 3D
  space charge downstream of 5.25 m, field-map asymmetry, or asymmetry in the initial
  distribution. Explain it and show where the quadrupoles sit along z. If the quadrupoles are
  downstream of the linac, at 200 MeV where space charge is weak, they should leave the
  normalized emittance nearly unchanged and act mainly on the size and divergence constraints.
  If so, say so, and show it with the GP length-scales or a sensitivity analysis.
- **Energy spread.** Is σ_E the total RMS spread, including the correlated chirp from
  off-crest phasing and RF curvature? The slice or uncorrelated value? For a storage-ring
  injector, the downstream booster acceptance determines which quantity matters, and a
  correlated chirp can be removed or compensated. Justify the choice of objective.
- **Motivation.** The introduction motivates small emittance and energy spread with XFELs and
  UED. The machine is a *storage-ring* injector, where the injected emittance is damped and the
  real requirements are injection efficiency and booster/transport-line acceptance. The
  objectives and constraint limits (1 mm, 1 mrad, 1 mm bunch length, ±5 MeV) should be tied to
  actual KLS booster or transfer-line requirements. If they are not real requirements, the
  paper should say they were chosen for illustration.
- **Source parameters.** The initial distribution should be described: laser spot size, pulse
  length and shape, thermal emittance or cathode model, and how `pal_photo2.ini` was generated.
  Positions of all elements should be given.
- **Inactive constraints.** Every primary evaluation has 100 % transmission (Fig. 7d), so the
  transmission constraint is never active, and the upper energy bound of 205 MeV is never
  approached. Say this explicitly, because it reduces the problem to about six active
  inequalities.

### M5. Statistical treatment

- With n = 10, a percentile bootstrap of the median gives poorly calibrated, discrete intervals
  (for example 0.0 [0.0, 0.0], and bounds such as 4.975). The paired design is the study's
  strength, yet the analysis never uses it. Report paired differences between methods per seed,
  with Wilcoxon signed-rank tests or paired bootstrap intervals of the differences.
- The paper says repeatedly that "no ranking is claimed", yet the abstract and conclusions
  rank the methods on feasible fraction. With a paired analysis, the author could make a
  justified quantitative statement instead of hedging.

### M6. Robustness assessment

- **The error budget is too small.** It is smaller than in the earlier study it is compared
  with: 0.1° phase errors versus 0.2° in JKPS, with no RF-amplitude, alignment or source
  jitter. RF-amplitude jitter drives the energy spread and mean energy directly. These are
  the very constraints that limit the representatives (lower-energy margin 0.016). At a
  minimum, add RF-amplitude jitter and repeat with the JKPS error model so the two results can
  be compared directly.
- **Zero failures in 50 trials do not mean zero risk.** They give a one-sided 95 % upper bound
  on the failure probability of about 6 % (rule of three). Report Clopper–Pearson bounds. Given
  the small margin (μ_min = 0.016), a feasibility of 1.00 may hide a substantial failure
  probability under slightly larger errors. A tolerance scan, P_feas against the error
  amplitude (0.1, 0.2 and 0.5 times the nominal error), would be much more informative.
- **The robustness score is ad hoc.** The score S, with its max(0.5, ·) and max(1, ·) clips, is
  never justified. The values are suspicious: two different pairs of representatives have
  identical scores (1.0191 for min_sigma_energy and balanced; 0.9592 for min_emit_y and
  crowding_distance_max). This suggests the clipping saturates. Verify these values and report
  P_feas, D and μ_min separately in Table 6. They are described in the text but missing from
  the table.
- **The run choice is unclear.** Specify which seed is "the predeclared primary run" and why
  it was chosen. The sentence "Each robustness assessment used 300 distinct perturbed parameter
  vectors" is unclear when read next to "50 perturbed simulations per representative". Is 300
  equal to 6 × 50?

### M7. Comparison with the earlier KLS MOGA study

The MOGA solution in ref. [Kim2024] has σ_E = 0.307 MeV. This is lower than any feasible
energy spread found here: the minimum is 0.339 MeV in the survey and 0.363 MeV at the
min_sigma_energy representative. The present knee has a smaller ε_n,x but a larger σ_E. This
deserves discussion. Did the MOGA study vary more parameters, use different constraints, or
use a different source? Is the present search domain excluding that solution? Re-evaluating
the published MOGA setting in the present model, if the setting is available, would settle the
question and is a cheap, high-value addition.

---

## Minor comments

1. **Internal project jargon.** Tables 3–4 and Fig. 6 use labels such as "Phase 1
   (Scalarized)", "Phase 2", "Phase 3" and "Phases 1–3". These are repository milestones and
   mean nothing to readers. Use method names throughout.
2. **Table 5 (weighting cases).**
   - "Operating Mode" labels such as "High-Brightness FEL Mode" and "representative
     operational linac archetypes" are not supported and should be removed.
   - The minima use *all valid* observations, including infeasible ones, while Table 4 uses
     feasible ones. The 0.2984 MeV entry is presumably infeasible. Use feasible minima
     consistently.
   - The caption mentions a "shared fixed reporting reference point" that is no longer used.
3. **Fig. 6 (survey feasible fraction).**
   - The scalarized curve concatenates five independent campaigns into an 880-evaluation line
     with five markers, which looks like one long run.
   - The figure has an embedded title and is a PNG.
   - Its colours are inverted relative to Figs. 3 and 7 (constrained = orange here,
     blue elsewhere).
   - Make the figures consistent, use vector output, and plot each weighting separately or as
     a band.
4. **Fig. 7.** In panels (a) and (b), the feasible cluster is fully hidden under thousands of
   overplotted open markers. Add zoomed insets of the feasible region, or plot the density of
   the infeasible points. Panel (d) has no content, since transmission is always 100 %. Replace
   it, for example with σ_E against E_kin.
5. **Fig. 3.** Add the attainment surfaces or the per-seed fronts (see M1). Consider marking
   the representatives of section 4.3 on the plot. Use a consistent ε_n,y axis range across
   panels.
6. **Survey section (4.4 / 5.3).** It has unequal budgets and independent initial designs, and
   the paper itself says it "supports no algorithm ranking". It repeats the primary results
   at weaker evidential quality. Shorten it substantially or move it to an appendix.
7. **Wall-clock claim.** The abstract states that "weighted-sum optimization completes campaigns
   faster", but the paper never quantifies this. The archived summaries give median campaign
   times of about 3.4 h, 2.4 h and 1.2 h. Report the times with a breakdown into ASTRA time
   versus GP fitting/acquisition time. Otherwise remove the claim from the abstract. The
   overhead of the 11-output constraint-aware model is a fair cost to discuss. It is probably
   negligible next to real machine time.
8. **The acquisition reference point** r_acq is "offset from the worst values of the valid
   observations". Do these include infeasible observations, and is it recomputed in negated
   model space? A reference set by infeasible extremes may steer the search toward
   uninteresting regions.
9. **Missing references.** "Earlier weighted-sum BO studies ... presented at ICABU 2025" has no
   citation. The data/code availability statement is missing, as are the acknowledgments,
   which are still marked `\pending`. JINST requires the latter to be resolved before
   publication.
10. **Writing style.** The manuscript repeats disclaimers ("descriptive", "no ranking is
    claimed", "does not establish") at least a dozen times. In several places it reads like
    an audit log. The last paragraph of section 4.2 and most of section 5.4 explain plotting
    conventions that belong in figure captions. Section 3.2 states an implementation
    limitation ("no residual scaling was changed during or after the campaigns") in
    provenance language. Each limitation should be stated once, in section 6.2, and the
    surrounding prose tightened. This could shorten the paper by about 20 %.
11. **Abstract.** "Sampled lattice perturbations preserve feasibility" should state the
    amplitudes (0.1 %, 0.1°) and the sample size. As written, it overstates the robustness.
12. **Section 2.2.** Please spell out "the eight inequalities" next to the table, since Table 2
    lists seven rows.
13. **Units.** Write normalized emittance consistently as mm·mrad or µm (rad is dimensionless).
    The conversion note in section 6.1 ("using 1 mm mrad = 1 µm rad") then becomes
    unnecessary.
14. **Consistency.** Section 5.5 says "six distinct representatives", while section 4.3 says a
    role may select the same setting. State whether any coincided in this run.
15. **Layout.** The `\resizebox` on Tables 4–6 makes the fonts inconsistent. Use `\small` or a
    `tabularx` layout instead. The `hyperref` `pagecolor` warning in the build log is harmless
    but should be cleaned up.
16. **Numerical resolution.** Section 2.1 gives 10⁴ macroparticles and a 32×32 / 32³
    space-charge grid without justification. Section 6.2 also says that "the numerical
    resolution limits absolute emittance accuracy". Read together, these invite doubt about
    whether differences of about 0.1 µm·rad between methods are resolved. If convergence of
    these settings was established in previous work on this injector, cite it in section 2.1.
    State that the present settings are identical, and quote the residual emittance and
    energy-spread uncertainty, so that readers can judge the trade-off differences against
    it. Then revise the sentence in section 6.2. Please also state briefly why fixed,
    near-zero observation noise (η = 10⁻⁶) suits the residual numerical noise at these
    settings.

---

## Assessment against journal criteria

| Criterion | Assessment |
|---|---|
| Originality | Moderate. Constrained qNEHVI for injectors is established (e.g. Roussel et al. 2021). The contribution is the application to KLS and the paired, failure-inclusive protocol. |
| Technical soundness | Not yet adequate: failed endpoint (M1), arbitrary phase bounds (M2), and mis-scaled constraint smoothing (M3a). |
| Fair comparison | Partly. Budgets and seeds are matched, but the baselines are mismatched (M3b). |
| Physics content | Thin for JINST (M4). |
| Reproducibility | Strong in principle (provenance, checksums, fixed seeds). A public archive and code statement are still missing. |
| Presentation | Readable but repetitive and defensive. Internal jargon in tables and figures. |

## Conclusion

The protocol and engineering are of good quality, and the author is unusually honest about the
study's limits. But the central claims rest on a failed endpoint, a search domain defined by
percentages of absolute phases, and a constraint-smoothing scheme that leaves most channels
almost unconstrained. In the end the paper shows only that a method which sees the constraints
samples more feasible points than methods that do not. I recommend **major revision**. The
essential items are M1–M3 and M6, with M4 strongly encouraged. I would be happy to review a
revised version.

*— Reviewer 2*
