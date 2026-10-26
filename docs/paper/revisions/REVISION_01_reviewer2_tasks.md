# Revision Task List — Response to Reviewer 2 (Review 01)

**Source review:** `docs/paper/reviews/REVIEW_01_reviewer2.md`
**Decision:** Major revision
**Manuscript:** `docs/paper/main.tex` (as of commit `fe459f2`)

Each task lists the review item(s) it answers, the work involved, and what counts as done.
Priority: **P0** must be done for resubmission, **P1** strongly expected, **P2** editorial.
Tasks that need new ASTRA campaigns are marked 🖥. Archived production results must not be
rewritten; new campaigns go in new run directories.

---

## P0 — Essential

### R1. Replace the failed hypervolume endpoint with valid front-quality metrics (M1)
- [ ] Define a physically justified post-hoc reference point for the feasible hypervolume, for
      example the pooled feasible nadir plus a margin, or engineering limits such as
      (6 µm·rad, 6 µm·rad, 1 MeV). Record it in a new metadata file and leave
      `reporting_metadata.json` unchanged.
- [ ] Compute the feasible HV per seed and per method from the archived primary runs. No rerun
      is needed.
- [ ] Run a sensitivity analysis over two or three reference choices.
- [ ] Add a reference-free indicator: IGD+ against the pooled all-method feasible front.
- [ ] Add empirical attainment surfaces (or 50 % attainment) for the three pairwise projections.
- [ ] Add per-seed HV traces against evaluations (median ± CI), so that sample efficiency is
      visible.
- [ ] Label all of the above as post hoc in the text. Keep the paragraph that reports the
      original zero-HV endpoint.
- **Done when:** Table 4 and a new figure report the post-hoc HV and IGD+, and the scripts and
  tests are committed.

### R2. Fix the constraint-smoothing scale and rerun the constraint-aware arm 🖥 (M3a)
- [ ] Normalize the constraint residuals (c_k / limit_k, or the band half-width for E_kin), and
      choose τ in normalized units (e.g. 10⁻²). Make this a config option and keep the
      historical behaviour reproducible.
- [ ] Quantify the effective transition width per channel under the original setting, to
      document the issue in the paper.
- [ ] Rerun constraint-aware qLogNEHVI for seeds 42–51 with the same initial designs.
- [ ] Report the original and corrected variants side by side, or replace the original with
      clear disclosure.
- **Done when:** Section 3.2 describes the normalized constraints, and results exist for the
  corrected arm.

### R3. Justify the RF-phase bounds physically (M2)
- [ ] Determine the crest phase for the gun, ACC1/2 and ACC3/4 in the fixed model (energy-gain
      scan).
- [ ] Rewrite Table 1 with off-crest phases and windows in degrees (e.g. ±5° or ±10°), each with
      a physical justification. Remove the "±10 % of nominal" definition for phases.
- [ ] Either rerun the primary comparison with corrected bounds 🖥, or show (e.g. with a
      restricted re-analysis or a sub-study) that the conclusions do not depend on the ACC3/4
      window of about 62°.
- [ ] Report the off-crest phases of all six representatives.
- **Done when:** Table 1 and section 2.2 use physically defined phase windows, and the impact on
  the results is shown.

### R4. Add the missing baselines 🖥 (M3b, M3c)
- [ ] Sobol/random search, 10 seeds × 160 evaluations, using the same initial designs.
- [ ] Constrained scalarized qLogNEI, using the same constraint models as the constraint-aware
      arm.
- [ ] NSGA-II (e.g. via pymoo) at 160 evaluations and at about 1,600 evaluations, 10 seeds. This
      tests the claim in the introduction that GAs need many more simulations. If it is not
      done, remove that claim.
- [ ] Remove the "evaluations to first feasible point" row, or explain that it is determined by
      the shared Sobol initial design. Optionally, report it counting post-initialization
      proposals only.
- **Done when:** Table 4 and Fig. 4 include the new baselines.

### R5. Numerical convergence and fidelity check 🖥 (M4)
- [ ] Run convergence scans at the nominal point and the knee point: particle number 10⁴,
      5×10⁴, 2×10⁵; grid 32 and 64 (both the r–z and 3D solvers).
- [ ] Measure the local numerical noise: ε_n and σ_E at about 20 inputs within 10⁻⁴ (normalized)
      of the knee.
- [ ] Re-evaluate the six representatives at high fidelity, and check that their order and
      feasibility are preserved.
- [ ] Discuss whether η = 10⁻⁶ fixed noise is appropriate. Optionally, compare against a
      fitted-noise GP on the archived data.
- **Done when:** a new subsection or appendix with a convergence table exists, and section 6.2
  is updated.

### R6. Strengthen the robustness assessment 🖥 (M7)
- [ ] Add RF-amplitude jitter. Rerun the tests with the JKPS error model (0.2 %, 0.2°, 0.1 %
      magnets), and alignment errors if they are feasible in ASTRA.
- [ ] Run a tolerance-amplitude scan (×1, ×2, ×5 the nominal errors) and plot P_feas against the
      amplitude.
- [ ] Report Clopper–Pearson 95 % bounds on P_feas. Consider raising the number of samples to
      ≥ 200 for the knee and balanced points.
- [ ] Check the duplicated robustness scores (1.0191, 0.9592) in `robustness_table.tex`.
      Fix the score or justify it, or drop S in favour of reporting P_feas, D and μ_min
      separately.
- [ ] Add the D and μ_min columns, and the limiting channel, to Table 6.
- [ ] State which seed is the "predeclared primary run", and clarify the 300 = 6 × 50
      sentence.
- **Done when:** the revised section 4.3 / 5.5 and Table 6 are in place, and the abstract states
  the error amplitudes.

---

## P1 — Strongly expected

### R7. Physics interpretation (M5)
- [ ] Explain the ε_n,x ≠ ε_n,y asymmetry. Identify the mechanism with ASTRA runs at the
      representatives: quadrupoles off, the 3D solver switched at a different z, a check of the
      initial-distribution symmetry, and Larmor-frame coupling.
- [ ] Give the z positions of all elements (add them to Fig. 1 or a table).
- [ ] Show the GP ARD length-scales or Sobol sensitivity indices per objective and constraint,
      to demonstrate the role of the quadrupoles.
- [ ] Define σ_E precisely (total or correlated vs. uncorrelated). Discuss its relevance to the
      acceptance of the KLS booster or transfer line.
- [ ] Tie the constraint limits to KLS injection requirements, or state that they were chosen
      for illustration.
- [ ] Revise the introduction so the motivation is the storage-ring injector, not XFEL/UED.
- [ ] Describe the source: laser spot, pulse duration and shape, thermal emittance, and the
      generator settings of `pal_photo2.ini`.
- [ ] State that the transmission constraint and the upper energy bound were never active.

### R8. Paired statistical analysis (M6)
- [ ] Compute per-seed paired differences for all method pairs: feasible %, post-hoc HV, IGD+
      and Pareto size.
- [ ] Report Wilcoxon signed-rank p-values with a multiplicity correction (Holm), and paired
      bootstrap intervals of the differences.
- [ ] Align the language of the abstract and conclusions with the tested statements, and remove
      the redundant "no ranking" hedges.

### R9. Revisit the comparison with the KLS MOGA study (M8)
- [ ] Obtain the published MOGA setting from ref. [Kim2024] and evaluate it in the present
      model.
- [ ] Discuss why the present feasible σ_E minimum (0.339 MeV) exceeds the MOGA value
      (0.307 MeV): domain, constraints, source, or variables.

### R10. Report wall-clock and overhead honestly (minor 7)
- [ ] Add the median campaign times (3.4 h, 2.4 h, 1.2 h, with CIs) to Table 4, split into ASTRA
      time and surrogate/acquisition time.
- [ ] Revise the abstract sentence accordingly, or remove it.

### R11. Clarify the acquisition reference point (minor 8)
- [ ] State whether r_acq uses infeasible observations, and in which space it is computed.

---

## P2 — Editorial and presentation

### R12. Remove internal jargon and fix the tables (minor 1, 2)
- [ ] Replace "Phase 1/2/3" labels with method names in `results_table.tex`, the
      `phase1_cases_table.tex` caption and the figure legends (fix them in the generator
      scripts).
- [ ] Remove the "Operating Mode"/"archetype" labels in Table 5.
- [ ] Use feasible minima consistently in Table 5, and remove the stale mention of the
      reference point.

### R13. Figure fixes (minor 3, 4, 5)
- [ ] Fig. 6: per-weighting curves or a band, no embedded title, vector PDF, and the same colour
      mapping as Figs. 3 and 7.
- [ ] Fig. 7: zoomed insets of the feasible region in (a) and (b). Replace panel (d), where
      transmission is always 100 %, with σ_E against E_kin.
- [ ] Fig. 3: consistent axis ranges, the six representatives marked, and attainment surfaces
      (from R1).

### R14. Shorten or move the survey to an appendix (minor 6)

### R15. Prose consolidation (minor 10, 11, 12, 13, 14)
- [ ] State each limitation once, in section 6.2. Move the plotting conventions from
      sections 4.2 and 5.4 into the captions.
- [ ] Abstract: give the jitter amplitudes and the sample size.
- [ ] Section 2.2: list the eight inequalities explicitly.
- [ ] Use one emittance unit convention throughout (mm·mrad or µm).
- [ ] Say whether any representative roles coincided.
- [ ] Target a length reduction of about 20 %.

### R16. Front matter and compliance (minor 9, 15)
- [ ] Add the ICABU 2025 citation.
- [ ] Add data and code availability statements (public archive DOI).
- [ ] Fill in the acknowledgments and funding, then set `\finaltrue`.
- [ ] Replace the `\resizebox` tables with `\small`/`tabularx`, and clean up the hyperref
      warning.

### R17. Response letter
- [ ] Write a point-by-point response to Reviewer 2 in
      `docs/paper/reviews/RESPONSE_01_reviewer2.md`, with a latexdiff against `fe459f2`.

---

## Suggested order of work
1. Analysis-only work on the archived data: R1, R8, R10, R11, and R6's score check.
2. Short simulation studies: R3's crest scan, R5, R9.
3. New campaigns: R2, R3's rerun if needed, R4, R6.
4. Physics and writing: R7, R12–R16.
5. R17 last.
