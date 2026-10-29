# Revision tasks for Reviewer 2 — round3

**Source report:** [reviewer2_round3_report.md](../reviews/reviewer2_round3_report.md)
**Previous round:** [reviewer2_round2_revision_tasks.md](reviewer2_round2_revision_tasks.md), [consolidated_round2_revision_tasks.md](consolidated_round2_revision_tasks.md)
**Reviewed manuscript revision:** `00190d8`
**Recommendation:** Minor revision. No new simulations are required; acceptance is expected once T1–T3 and the minor tasks are done.

Each task lists the review item it answers, the work involved, and what counts as done.
- **Priority:** **P0** required for acceptance, **P1** expected, **P2** editorial.
- **Optional** marks a simulation the reviewer suggests but does not require. 🖥 marks tasks that need ASTRA runs.
- **Ground rules:** archived production results must not be rewritten. New analyses go in separate derived-evidence files under `docs/paper/revisions/evidence/`, labelled post hoc where applicable.

---

## P0 — Required for acceptance

### T1. State the attribution per baseline (R1)
Manuscript changes only; the evidence is `evidence/r2_attribution_gap.csv`.
- [ ] Abstract: replace "which arises mainly from meeting the transverse beam-size and
      divergence limits". Use a formulation true for both baselines. It must say that the
      advantage persists among energy-acceptable evaluations, that it is mainly transverse
      against unconstrained MOBO, and that the energy band contributes the larger share
      against weighted-sum BO. Keep the abstract free of numbers, and do not lengthen it.
- [ ] Contribution 2 (Introduction):
  - Make the same per-baseline correction.
  - Replace "It is not produced by the setting of the energy-band weight or by the upper
    ACC3/ACC4 phase window" with a statement of partial contribution, e.g. "not explained by
    … alone".
- [ ] Discussion (first paragraph of Sec. VI) and Conclusions (second paragraph): replace
      "comes largely/mainly from the transverse size and divergence limits" with the
      per-baseline statement.
- [ ] Sec. V C: optionally quantify the upper-quarter share. The occupancy differences of 7–9
      percentage points, all infeasible, are roughly a quarter to a third of the gaps.
      "Not the main source" may stay.
- **Done when:** no sentence anywhere in the manuscript attributes the advantage to the
  transverse limits without naming the unconstrained baseline. No sentence says the energy
  weight or the upper window plays no part.

### T2. Bound the primary comparison under the observed refinement shifts (R2)
Analysis of existing data only; no simulations.
- [ ] New script `scripts/analyze_revision_resolution_bounds.py`, with a test. It reclassifies
      the 4,800 primary evaluations under bounding diagnostic shifts taken from
      `evidence/r2_convergence_summary.csv`:
  - a common scale factor on σ_x, σ_y, σ_x′ and σ_y′, from 1.0 down to the largest observed
    reduction (about 0.78);
  - σ_z × (1 ± 0.01);
  - E_kin ± 0.05 MeV;
  - transmission unchanged.
- [ ] Report, per shift combination:
  - each method's feasible fraction over all 160 evaluations and after initialization;
  - the paired constraint-aware-minus-baseline differences, with group-bootstrap intervals
    and the number of positive groups.
  - Also report them for the Sobol arm, so that the space-filling comparison is covered.
- [ ] Evidence: `evidence/r3_resolution_bounds_{runs,paired}.csv` and a metadata JSON that
      records the shifts and their source. Add the files to Supplement S1 (new item or S1.13)
      and rebuild the manifest.
- [ ] Manuscript, in Sec. V B or V C, add one short paragraph or table:
  - the range of feasible fractions and paired differences under the bounds;
  - whether every paired difference stays positive;
  - that the constraint-aware fraction is the most sensitive to the bunch-length limit,
    because the pipeline samples near it;
  - that the shifts are bounds taken from ten settings, not a per-point refinement model.
- [ ] Add one sentence where the front-quality indicators are interpreted (Sec. V B and the
      Discussion). It should say that these comparisons are conditional on the fixed source
      realization and the production resolution, more strongly than the feasibility
      comparison. The reasons are the nonuniform emittance shifts (12–43 %, Spearman 0.79 for
      ε_x) and the random-source spread of 1–12 %.
- [ ] Update the Limitations and, if the outcome changes the statement, the Conclusions
      sentence "the method comparisons hold within this fixed numerical model".
- **Done when:** the manuscript states, with evidence, whether the feasible-fraction advantage
  survives the measured refinement shifts. The front-quality caveat is in place.
- **Optional 🖥:** re-track the 53 pooled-reference points at the `combined_medium` level, at
  about 20 min per run (roughly 2 h with eight workers). Report whether each method keeps its
  points on the refined pooled front. Record this separately from the production campaigns,
  as with the C2-12 resolution check.

### T3. Align summary statements with the detailed results (R3)
Manuscript changes only.
- [ ] **(a) Conclusions, refined TDR membership.** Replace "Under refined tracking their
      closest observation and the MOGA-derived nominal setting do meet them" with a statement
      that matches Sec. VI B. Both meet the inequalities at the combined medium and fine
      levels but fail with four of five regenerated sources. Membership near the limits is
      therefore not resolved.
- [ ] **(b) Sobol-arm share (Sec. V C and Conclusions).**
  - The share is (0.418 − 0.142)/0.418 = 0.66 and (0.418 − 0.107)/0.418 = 0.74. Replace "at
    least two thirds" with "about two thirds", or give both shares.
  - Rephrase the sentence for readability, e.g. "the constraint-blind pipelines account for
    at most about one third of the constraint-aware gain over the Sobol arm".
  - Make the same correction in the Conclusions sentence beginning "most of the
    constraint-aware advantage over that search …".
- [ ] **(c) Contribution 1.** Do not present "a fixed reference point and predeclared
      endpoints" as a property of the comparison. State that the feasible fraction was
      predeclared and that the predeclared fixed-reference hypervolume endpoint failed. Also
      state that it was replaced by labelled post-hoc indicators.
- [ ] Check the abstract, Introduction, Discussion and Conclusions once more for any other
      summary claim that is stronger than the corresponding Results or Discussion text.
- **Done when:** every summary sentence can be traced to a detailed statement that says the
  same thing.

---

## P1 — Expected

### T4. Sobol energy-band sentence (minor 1)
- [ ] Sec. V C: make the energy-band comparison direction-specific. Energy-band violations
      fall for unconstrained MOBO (39.0 % → 32.2 %; paired −0.069) and rise slightly for
      scalarized BO (→ 42.6 %; paired +0.035, 0.017–0.052). Source:
      `evidence/r2_sobol_arm_paired.csv`.

### T5. RF-amplitude estimate against the TDR energy margins (minor 2)
- [ ] In the TDR-candidate jitter paragraph (Sec. V I), compare the 0.28–0.40 MeV RMS
      amplitude-induced energy shift with the TDR lower-energy margins of candidates A and B.
      These margins are 0.31 and 0.14 MeV (Table III), i.e. about 0.4–1.1 standard deviations.
      State that amplitude jitter alone would fail a substantial fraction of trials under
      the TDR energy bound.
- [ ] Keep it a first-order estimate; no tracked amplitude study is requested.

### T6. Precision of reported values (minor 3)
- [ ] State once, in the caption of Table X and in Sec. V H, that the quoted digits identify
      archived evaluations at the production resolution and are not resolved physical values.
- [ ] Round emittances and energy spreads in the running text to two or three significant
      figures. Keep full precision in tables and evidence files. Affected places include:
  - Secs. V H, V J and VI A;
  - the settings and MOGA reference values.

### T7. Qualify "deterministic" (minor 4)
- [ ] Sec. III A: add that ASTRA is deterministic for the fixed source file, and that the
      file's sampling error (1–12 % in emittance, Sec. II A) is common to all methods and is
      not represented by the GP noise.

### T8. Make the Data availability statement and Supplement S1 consistent (minor 5)
- [ ] Decide whether Supplement S1, or its evidence files and the ≈10 MB of ledgers, is
      submitted as PRAB Supplemental Material, or whether all of it is available on request.
- [ ] Make Appendix A ("accompanies this manuscript"), the Data availability statement and
      the README of the supplement say the same thing.
- [ ] Do not add a public repository or a deposit to the text.

---

## P2 — Editorial

### T9. Length and placement (minor 6)
- [ ] Move the details of Sec. V F ("Offline sensitivity of constraint smoothing") to an
      appendix. Keep a short summary in the main text: the rankings depend on residual units
      (Spearman 0.79–0.88), and no normalized campaign was run.
- [ ] Move the stage- and region-resolved coverage paragraph, and the details of the
      inferred-noise refit, from Sec. V G to Appendix D. Keep the 79–89 % coverage, the three
      causes and "part, but not all" in the main text.
- [ ] Shorten the resolution-check description in Sec. II A to its findings. Move the level
      definitions to Appendix A or Supplement S1.13.
- [ ] Rebuild the one-column review copy and the two-column `reprint` copy, and update the
      page counts quoted in the response letter.

### T10. APS reference style (minor 7)
- [ ] Use "Ref." for in-text references: Sec. I, "reviewed in ref.", and Sec. II B, "published
      in ref.".
- [ ] Write "Sec. 4.3" for Kim et al.'s section 4.3 in Secs. II A and VI A.

### T11. Source hygiene (minor 8)
- [ ] Remove `% C05 replacement for the acquisition-reference explanation.` from Sec. III C
      (`main.tex`, about line 562).
- [ ] Search `main.tex` and the included `.tex` inputs for any remaining `% C0…`, `% C1…`,
      `% Q…` or revision-integration comments. Keep only the structural comments, such as the
      macro descriptions.
- [ ] Add a test that fails on revision-tag comments in the manuscript source.

### T12. Abstract readability (minor 9)
- [ ] Split the sentence beginning "Feasibility is defined by a deliberately relaxed
      computational acceptance profile". Make the T1 correction without lengthening the
      abstract. Keep it free of numbers.

### T13. Response letter
- [ ] Write `docs/paper/reviews/reviewer2_round3_response.md`, a point-by-point response to
      R1–R3 and minors 1–9. Include a manuscript diff against `00190d8` and links to the new
      evidence files.
- [ ] Correct the round-2 response statement that all revision-integration comments had been
      removed (minor 3 of round 2), noting the leftover comment fixed under T11.

---

## Suggested order of work
1. Analysis of existing data: T2. The optional 🖥 re-tracking of the reference front only if
   the author chooses it.
2. Manuscript corrections: T3, then T1 (they touch the same summary sentences), then T4–T7.
3. Decision and text: T8.
4. Editorial: T9–T12. T9 last among them, because it moves text changed by T1–T3.
5. T13 last.
