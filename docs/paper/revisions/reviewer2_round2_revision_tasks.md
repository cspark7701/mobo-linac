# Revision tasks for Reviewer 2 — round2

**Source report:** [reviewer2_round2_report.md](../reviews/reviewer2_round2_report.md)
**Previous round:** [reviewer2_round1_revision_tasks.md](reviewer2_round1_revision_tasks.md), [consolidated_round1_revision_tasks.md](consolidated_round1_revision_tasks.md)
**Reviewed manuscript revision:** `9077875`
**Recommendation:** Major revision. No new optimization campaigns are required; acceptance is expected once Q1–Q4 and the minor tasks are done.

Each task lists the review item it answers, the work involved, and what counts as done.
Priority: **P0** required for acceptance, **P1** expected, **P2** editorial. **Optional** marks
simulations the reviewer encourages but does not require; 🖥 marks tasks that need ASTRA runs.
Archived production results must not be rewritten, and new analyses go in separate
derived-evidence files under `docs/paper/revisions/evidence/`.

> **Numerical convergence.** The convergence study was already done in the previous study of
> this injector. No new convergence simulations are requested in this round. Task Q4(b) only
> asks that the manuscript report the existing result.

---

## P0 — Required for acceptance

### Q1. Reframe the KLS relevance around the TDR result (N1)
Manuscript changes only.
- [ ] State the origin of the production limits (1 mm, 1 mrad, 1 mm, 195–205 MeV, T ≥ 0.90):
      an earlier design stage, a deliberately relaxed exploration profile, or a configuration
      default. If there is no engineering basis, say so in section 2.2. Replace the sentence
      "The TDR does not justify replacing its requirements with the production limits."
- [ ] Revise the title so it does not imply a KLS-acceptance design study, e.g. "…of a
      KLS-derived 200 MeV injector-linac model".
- [ ] Abstract and conclusions: state qualitatively that the acceptance profile is looser than
      the TDR optimization requirements and that few sampled settings meet the TDR
      requirements. Keep the abstract free of numbers, as the author prefers.
- [ ] Add a short discussion of whether the TDR region is reachable with the six
      fixed-lattice controls, or needs controls held fixed here (RF amplitudes, the matching
      quadrupoles of the full TDR linac).
- [ ] Note that the two TDR-passing settings are marginal: σ_x = 0.291 and 0.298 mm against
      0.30 mm, σ_z ≈ 0.992 mm against 1.0 mm, and one with a relative spread of 0.44 %. Source:
      `evidence/c01_tdr_candidates.csv`.
- **Done when:** the title, abstract, section 2.2, the Discussion and the Conclusions
  consistently describe the study as a method comparison under a relaxed profile on a
  KLS-derived model.
- **Optional 🖥:** one or more constraint-aware campaigns under the TDR optimization
  constraints, to show whether the method finds TDR-acceptable settings.

### Q2. Identify which constraints produce the feasible-sampling advantage (N2)
Analysis of existing data only; no simulations.
- [ ] For each method and each post-initialization batch, classify every infeasible evaluation
      by violated channel. Use exclusive categories (energy band only; transverse size or
      divergence only; bunch length only; combinations) and also report "any violation".
- [ ] Divide the paired feasible-fraction gap (constraint-aware minus each baseline) among these
      categories.
- [ ] Per batch and method, report the fraction of evaluations in the upper ACC3/4 quarter
      (325.5561–341.0588°). Show how quickly each method leaves it.
- [ ] Compute the conditional feasible fraction among evaluations that satisfy the energy band
      (transverse and bunch-length feasibility given energy acceptance), with paired
      intervals.
- [ ] Add a figure or table and one paragraph to Results. If the advantage comes mainly from
      the energy boundary, say so in the abstract, the Discussion and the Conclusions.
- [ ] Do not present this as a prediction of rankings in a restricted domain; it is a
      descriptive attribution.
- **Done when:** a script, tests and evidence file (e.g. `evidence/r2q2_*`) exist and the
  manuscript states which constraints account for the gain.

### Q3. Add a space-filling reference from the shared initial designs (N3)
Analysis of existing data only.
- [ ] Report the feasible rate of the 160 shared Sobol initial points (5/160 = 3.1 %) with its
      exact Clopper–Pearson interval, clearly labelled as an initialization-only reference and
      not a matched arm.
- [ ] Using the per-channel breakdown from Q2, explain why constraint-blind acquisition already
      raises feasibility above the space-filling rate (e.g. emittance minimization favours
      smaller divergences).
- [ ] Use the reference to qualify the claims in section 4.2 and the Limitations section; keep
      the statement that no advantage over a full Sobol search is established.
- **Done when:** Results reports the reference and its interval, and the Discussion explains the
  baseline feasibility gain.
- **Optional 🖥:** a budget-matched Sobol arm, 10 seeds × 160 evaluations with the same initial
  designs (about 1 h of tracking per campaign), with the front-quality indicators of
  section 4.2.

### Q4. Reconcile surrogate calibration and the numerical-resolution statement (N4)
**(a) Surrogate calibration.** Analysis only.
- [ ] Discuss the likely causes of the 79–89 % coverage of nominal 95 % intervals: fixed
      near-zero noise (η = 10⁻⁶), kernel misspecification, adaptively selected test points.
      Explain the consequences for the constraint-feasibility weights.
- [ ] Optional, no ASTRA runs: refit the saved training sets with inferred homoscedastic
      noise, repeat the next-batch coverage check, and report whether coverage improves.

**(b) Numerical resolution.** Documentation only; **the convergence study is already done**.
- [ ] Locate the existing convergence record from the previous study of this injector: the
      resolutions tested and the residual changes in ε_n and σ_E at the adopted settings.
- [ ] Report those values in section 2.1, cite their source, and compare them in one or two
      sentences with the reported method differences and the smallest feasibility margins.
- [ ] Revise the section 6.2 sentence "numerical uncertainty … is therefore unquantified" to
      match. Keep that sentence only if the record cannot be located, and in that case link the
      Q4(a) undercoverage to possible numerical roughness.
- **Done when:** sections 2.1 and 6.2 agree with each other and with the author's response
  record.

---

## P1 — Expected

### Q5. RF-amplitude jitter estimate (minor 4)
- [ ] Add a short analytic estimate: about 0.2 % amplitude jitter shifts the mean energy at
      200 MeV by roughly 0.4 MeV, against the 3.11 MeV lower-energy headroom, plus an estimate
      of the phase-dependent contribution to σ_E. Or state why the estimate does not apply.

### Q6. Local convergence check of the selected settings (minor 6)
- [ ] From the archived jitter samples, count perturbed samples that Pareto-dominate their
      nominal setting, especially for the spread extreme (D = 0.988) and centroid point
      (D = 0.9985).
- [ ] Add one sentence on what this implies about the local convergence of the selected front.

### Q7. Lead with effect sizes in the paired statistics (minor 5)
- [ ] State that 0.0234 is the smallest Holm-adjusted p-value the design allows: n = 10, exact
      two-sided p = 2/1024, multiplied by 12.
- [ ] Lead the paired-results paragraph with the effect sizes and paired intervals, with the
      p-values second.

### Q8. Energy-channel weighting statement (minor 8)
- [ ] In section 3.2, state explicitly that τ_c = 10⁻³ eV makes the energy-band weight an
      effective step with vanishing gradient, alongside the existing beam-size values.

### Q9. Optional 🖥: jitter assessment of the TDR-passing settings (minor 7)
- [ ] Run 50 lattice-jitter trials for each of the two TDR-passing settings, about 100
      simulations, evaluated against the TDR profile. Report Clopper–Pearson bounds.

---

## P2 — Editorial

### Q10. Abstract (minor 1)
- [ ] Qualify "weighted-sum optimization completes campaigns faster" as overhead of the present
      implementation, or remove it.
- [ ] Add the qualitative TDR statement from Q1.

### Q11. Length and density (minor 2)
- [ ] Move implementation-forensic detail to an appendix: sampler counts, smoothing constants,
      the inclusion–exclusion description, Adam-recovery counts, effective likelihood floors
      and evaluation-interval unions.
- [ ] State each limitation once in section 6.2, and remove repeated "does not establish…"
      caveats elsewhere.
- [ ] Remove the table of contents.
- [ ] Target a main-text length suited to the chosen journal.

### Q12. Source hygiene (minor 3)
- [ ] Remove internal revision comments from `main.tex` (`% C05 …`, `% C09 …`, `% C03 …`,
      `% C04 …`, `% Integrate before …`, `% Discussion limitation …`) and the campaign-output
      comment block before the Results section.
- [ ] Check the appendix inputs under `revisions/evidence/*.tex` for the same kind of comment.

### Q13. Target journal and front matter (minors 9, 10)
- [ ] Confirm the target journal, and adapt the class, bibliography style and length to it.
- [ ] Supply the funding and acknowledgments, then set `\finaltrue` (no line numbers, no
      `\pending` markers).

### Q14. Response letter
- [ ] Write `docs/paper/reviews/reviewer2_round2_response.md` with a point-by-point response to
      N1–N4 and minors 1–10, a latexdiff against `9077875`, and links to the new evidence
      files.

---

## Suggested order of work
1. Analysis of existing data: Q2, Q3, Q6, Q4(a) refit if attempted.
2. Documentation: Q4(b) convergence record, Q1 origin of the production limits.
3. Manuscript: Q1 reframing, then Q5, Q7, Q8, Q10, Q11.
4. Optional simulations, if the author chooses: the Q1 TDR campaign, the Q3 Sobol arm, Q9.
5. Q12 and Q13, then Q14 last.
