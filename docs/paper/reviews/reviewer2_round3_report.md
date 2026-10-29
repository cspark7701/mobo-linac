# Reviewer 2 report — round3

**Manuscript:** *Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design*
**Author:** C. S. Park (Korea University)
**Target journal:** Physical Review Accelerators and Beams
**Source reviewed:** `docs/paper/main.tex` at commit `00190d8` (one-column REVTeX 4.2 review copy, 51 pages), with the generated tables, figures and appendix inputs it includes
**Previous round:** [reviewer2_round2_report.md](reviewer2_round2_report.md); author response [reviewer2_round2_response.md](reviewer2_round2_response.md)
**Date:** 2026-10-29

---

## Recommendation

**Minor revision.** The manuscript is not acceptable in its present form. However, the
remaining problems concern the consistency of claims with the evidence the author has already
produced, and one bounding analysis of existing data. **No new simulations are required.** I
expect to recommend acceptance once R1–R3 and the minor comments below are addressed.

The author ran every optional study I suggested in round 2, and more. These were the
TDR-constrained campaigns, a budget-matched Sobol arm, jitter of the TDR candidates, an offline
noise refit and a numerical-resolution check. The author reported their outcomes candidly,
including unwelcome ones:
- no TDR-feasible point in the targeted campaigns;
- no pipeline improved on the MOGA-derived nominal setting;
- the withdrawal of an earlier convergence statement;
- emittances that are not converged at the production resolution.

This is the standard of reporting I would want in PRAB. The paper is now a careful, honestly
scoped method comparison on a KLS-derived model.

Three issues remain:
1. The headline attribution of the feasible-sampling advantage is stated more strongly in the
   abstract, contributions, discussion and conclusions than the author's own decomposition
   supports (R1).
2. The resolution check covers ten production-feasible settings. It therefore does not show
   whether the *primary comparison*, a count of evaluations near the production limits, is
   stable under the observed refinement shifts. A bounding reclassification of the archived
   ledgers can settle this (R2).
3. A few summary sentences contradict the detailed results: one in the Conclusions about
   refined TDR membership, and one arithmetic statement about the Sobol arm (R3).

---

## Assessment of the round-2 responses

| Round-2 item | Status | Comment |
|---|---|---|
| N1 KLS framing | **Resolved** | The title, abstract, Sec. II B, the TDR-reach subsection and the Conclusions now describe a relaxed-profile comparison on a KLS-derived model. The origin of the production limits is stated. The TDR-constrained campaigns, which I had only encouraged, answer the question KLS readers will ask. |
| N2 Source of the advantage | **Resolved in the analysis, overstated in the summaries** | The exclusive-category decomposition, the upper-quarter occupancy and the energy-conditional fraction are what I asked for. They refute the purely "mundane" reading. However, the decomposition differs between the two baselines, and the abstract and contribution 2 report only one of them; see R1. |
| N3 Space-filling reference | **Resolved** | The budget-matched Sobol arm (2.8 %, 41/1,440) is a clean reference. One arithmetic statement is wrong; see R3(b). |
| N4(a) Undercoverage | **Resolved** | The causes are discussed, and the inferred-noise refit tests the first of them. The conclusion "part, but not all" is correctly drawn. |
| N4(b) Numerical resolution | **Resolved as disclosure; one consequence open** | The 150-run refinement check is a substantial addition. Emittances 12–43 % lower at the fine level, mainly from the step size, are now reported plainly. What is still missing is the effect on the primary comparison; see R2. |
| Minor 1 Abstract | Resolved | |
| Minor 2 Length | Partly resolved | The implementation appendix helps. At 51 one-column pages the paper is still long; see minor 6. |
| Minor 3 Source comments | **Not fully resolved** | The response states that all revision-integration comments were removed, but `% C05 replacement for the acquisition-reference explanation.` remains at the end of a sentence in Sec. III C (source line 562). |
| Minor 4 RF amplitude | Resolved for the production profile | The estimate is correct (√(93.3² + 102.8²) × 0.002 ≈ 0.28 MeV; 200 × 0.002 = 0.40 MeV). It is not applied to the TDR energy margins; see minor 2. |
| Minor 5 Signed-rank floor | Resolved | |
| Minor 6 D < 1 | Resolved | The dominating perturbed samples are a useful, honest finding. |
| Minor 7 TDR-candidate jitter | Resolved | |
| Minor 8 Energy weight | Resolved | |
| Minor 9 Target journal | Resolved | PRAB, REVTeX 4.2. |

---

## Major comments

### R1. The attribution of the feasible-sampling advantage is overstated outside Sec. V C

Section V C is accurate. Against **unconstrained MOBO**, transverse-only violations account for
62 % of the 0.276 post-initialization gap, and energy-involving categories for 34 %. Against
**scalarized BO**, the energy-involving categories account for 63 % of the 0.311 gap, and
transverse-only violations for only 31 % (`r2_attribution_gap.csv`). The author's round-2
response states this correctly: "Against the scalarized baseline, energy plays the larger part."

The summary statements do not reflect this:
- **Abstract:** "a higher feasible sampling fraction for constraint-aware acquisition, which
  arises mainly from meeting the transverse beam-size and divergence limits."
- **Contribution 2:** "The advantage comes mainly from satisfying the transverse size and
  divergence limits more often … It is not produced by the setting of the energy-band weight or
  by the upper ACC3/ACC4 phase window."
- **Discussion:** "comes largely from the transverse size and divergence limits."
- **Conclusions:** "comes mainly from the transverse size and divergence limits."

Two parts of these statements are not supported:
1. **"Mainly transverse" holds against one baseline only.** Against the weighted-sum
   baseline, most of the gap involves the energy band.
2. **"Not produced by" the energy weight or the upper window is too strong.**
   - What the evidence shows is that the advantage *persists* among energy-acceptable
     evaluations (conditional fractions 0.578 against 0.254 and 0.231). That establishes a
     component beyond the energy boundary. It does not exclude an energy-boundary component.
   - The upper quarter is also not negligible. Constraint-aware MOBO placed 15.3 % of its
     evaluations there, against 22.6 % and 24.7 %, and every one of those evaluations is
     infeasible. The difference of 7–9 percentage points therefore accounts for roughly a
     quarter to a third of the gaps.
   - "Not the main source", as Sec. V C says, is accurate. "Not produced by" is not.

Required:
1. In the abstract, contribution 2, the Discussion and the Conclusions, state the attribution
   per baseline, or use a formulation that is true for both. For example: "the advantage
   persists among evaluations that meet the energy band and, against unconstrained MOBO, comes
   mainly from the transverse size and divergence limits; against weighted-sum BO the energy
   band contributes the larger share."
2. Replace "is not produced by" with a statement of partial contribution: for example, "is
   not explained by the energy-band weight or the upper ACC3/ACC4 window alone."

### R2. Show that the primary comparison is stable under the observed refinement shifts

The refinement check reports per-quantity changes for ten settings, all of them comfortably
production-feasible:
- sizes and divergences fall by up to 22 %;
- bunch length changes by at most 1 %;
- mean energy changes by at most 0.05 MeV.

The paper concludes that "all ten settings remain feasible … at every level" and that the
"method comparisons hold within this fixed numerical model". The second statement is true by
construction. It does not tell the reader whether the main result, the feasible *fraction*,
would survive a better-resolved model.

That result is a count of evaluations on either side of the limits, and the constraint-aware
pipeline deliberately samples close to them. Bunch-length-only violations are slightly more
frequent for it, and bunch length is the limiting channel for several selected settings. A
1 % change in σ_z can therefore move many of its evaluations across the limit.

A rough check of the archived primary ledgers (S1) illustrates the point. I applied the
refinement bounds to the recorded diagnostics: sizes and divergences scaled by 0.78–1.0, and
σ_z by ±1 %.
- **The constraint-aware feasible fraction moves between about 0.36 and 0.47** (nominal 0.405).
- **The baselines move between 0.15–0.21 and 0.11–0.17** (nominal 0.157 and 0.125).

The gap survives within these bounds, which is reassuring. However, the constraint-aware
fraction is visibly more sensitive to the bunch-length limit than the baselines, because that
pipeline concentrates its samples at that boundary. The reader should see this.

Required (existing data only):
1. Reclassify the 4,800 primary evaluations under bounding shifts taken from the refinement
   check, and report the per-method feasible fractions and the paired differences with
   intervals. The shifts are a common scale factor on sizes and divergences, from 1 down to
   the largest observed reduction, a ±1 % bunch-length change and a ±0.05 MeV energy shift.
   Give the result in one short table or paragraph in Sec. V B or V C. State that the shifts
   are bounds taken from ten settings, not a model of refinement at every point.
2. Add one sentence on the objective-quality indicators. The emittance refinement shifts are
   large (12–43 %) and not uniform: Spearman 0.79 for ε_x across the ten settings. The
   random-source spread of 1–12 % is comparable to many paired epsilon and IGD+ differences.
   Front-quality comparisons are therefore conditional on the fixed source realization and the
   production resolution, more strongly than the feasibility comparison. Say so where these
   indicators are interpreted (Sec. V B and the Discussion).

Optional 🖥, not required for acceptance: re-track the 53 pooled-reference points at the
medium level and report whether the method that contributed each point keeps it on the
refined pooled front. At about 20 minutes per run with eight workers, this costs roughly two
hours. It would show directly whether the front-quality ordering survives refinement.

### R3. Summary statements that contradict the detailed results

**(a) Refined TDR membership (Conclusions).** The Conclusions state: "Under refined tracking
their closest observation and the MOGA-derived nominal setting do meet them". Section VI B
("Reach of the TDR acceptance region") gives the full result:
- both settings meet the TDR inequalities at the medium and fine levels;
- each fails with four of the five random 10k sources;
- the nominal setting also fails with every single-factor refinement.

The Conclusions sentence selects the favourable levels. Since the paper's own conclusion is
that membership near the limits "is not numerically resolved", the sentence should say that
they meet the inequalities at the combined refinement levels but not with most regenerated
sources.

**(b) "At least two thirds" (Sec. V C).** The text says that at least two thirds of the
constraint-aware gain over the Sobol arm exceeds what either constraint-blind pipeline
achieves. The paired means are 0.418, 0.142 and 0.107. The share relative to the better
baseline is (0.418 − 0.142)/0.418 = 0.660, which is below two thirds. Write "about two thirds"
or give the two shares (0.66 and 0.74). The sentence is also hard to parse; for example: "the
constraint-blind pipelines account for at most about one third of the constraint-aware gain
over the Sobol arm." The same wording appears in the Conclusions ("most of the
constraint-aware advantage over that search exceeds what the constraint-blind pipelines
achieve") and should be rephrased in the same way.

**(c) Contribution 1.** Contribution 1 lists "a fixed reference point and predeclared
endpoints". The predeclared fixed-reference hypervolume endpoint was zero for every campaign
(Limitations), and every front-quality result in the paper is post hoc. The contribution
should say that the feasible fraction was predeclared and that the failed hypervolume endpoint
was replaced by labelled post-hoc indicators. As written, it credits the design with a
property that the Limitations section withdraws.

---

## Minor comments

1. **Sobol energy-band sentence (Sec. V C).** "Energy-band violations change little: from
   39.0 % to 32.2 % for unconstrained MOBO and 42.6 % for scalarized BO, a small but consistent
   increase (paired difference 0.035 …)." The "increase" applies only to scalarized BO, while
   unconstrained MOBO *decreases*. Please make the sentence direction-specific.
2. **RF amplitude and the TDR energy limit.** The first-order estimate (0.28–0.40 MeV RMS) is
   compared only with the 3.11 MeV production headroom. Candidates A and B clear the TDR lower
   energy bound by only 0.31 and 0.14 MeV (Table III), i.e. by 0.4–1.1 standard deviations
   of the estimated amplitude-induced shift. Add one sentence to the TDR-candidate jitter
   paragraph. It should say that, under 0.2 % amplitude jitter, the energy limit alone would
   fail a substantial fraction of trials, which strengthens the conclusion that these settings
   offer no jitter-tolerant TDR operation.
3. **Precision of reported values.** Emittances are quoted to five significant figures
   (e.g. 2.8061, 6.8492, 3.4728 µm rad), and energy spreads to 0.36286 MeV. These values
   change by 12–43 % under refinement and by 1–12 % between source realizations. State once,
   for example in the caption of Table X and in Sec. V H, that the digits identify
   archived evaluations and are not resolved physical values. In the running text, round to
   two or three significant figures.
4. **"Deterministic" (Sec. III A).** "Because ASTRA is deterministic for a fixed input" is
   correct, but next to the new source-spread result it can be misread as "free of numerical
   error". Add a clause: the calculation is deterministic for the fixed source file, whose
   sampling error (1–12 % in emittance) is common to all methods and is not represented by the
   GP noise.
5. **Data availability and Supplement S1.** Appendix A describes Supplement S1 as "the
   versioned `mobo_linac` 1.0.0 repository snapshot that accompanies this manuscript". The
   Data availability statement says the data are available on request, and Appendix A says the
   run directories are not distributed. Please make the three statements consistent. State
   whether S1, or its evidence files and the ≈10 MB of ledgers, is submitted as PRAB
   Supplemental Material, or whether all of it is available only on request. In the latter
   case, avoid "accompanies".
6. **Length and placement.** Two subsections of Sec. V are methodological diagnostics, not
   results about the injector:
   - "Offline sensitivity of constraint smoothing" (V F);
   - the detailed stage- and region-resolved coverage and refit paragraphs of "Predictive
     checks on unseen batches" (V G).

   Please keep a short summary of each in the main text: the unit dependence and Spearman
   0.79–0.88; and the 79–89 % coverage, "part, but not all" removed by inferred noise. Move
   the details to an appendix. The reported resolution check in Sec. II A, which runs to two
   paragraphs, could likewise be shortened to its findings, with the level definitions moved
   to the appendix.
7. **APS style.** Use "Ref." and "Sec." consistently, e.g. "in Ref. [x]" instead of "in
   ref. [x]" (Secs. I and II B). Kim et al.'s "section 4.3" should read "Sec. 4.3" in
   Secs. II A and VI A.
8. **Leftover source comment.** Remove `% C05 replacement for the acquisition-reference
   explanation.` (Sec. III C).
9. **Abstract.** At about 260 words the abstract is long. The sentence beginning "Feasibility
   is defined by a deliberately relaxed computational acceptance profile" contains three
   clauses and is hard to read. Please split it. The R1 correction should be made without
   lengthening the abstract further.

---

## Assessment against journal criteria

| Criterion | Round 2 | Round 3 |
|---|---|---|
| Originality | Moderate | Moderate. A careful paired application study rather than a new method; acceptable for PRAB. |
| Technical soundness | Gaps in attribution and calibration | Good. The analyses are complete. The remaining gaps are the summary claims (R1, R3) and the resolution bound for the main result (R2). |
| Fair comparison | Space-filling reference missing | Good. Includes a budget-matched Sobol arm; the missing constraint-aware scalarized control is stated. |
| Relevance to the stated application | Weak | Adequate. The framing is honest, and the TDR reach is quantified and tested directly. |
| Physics content | Adequate | Adequate. The resolution check is a valuable, if sobering, addition. |
| Reproducibility | Strong | Strong. Clarify the status of Supplement S1 (minor 5). |
| Presentation | Too long and hedged | Improved; still long (minor 6). Several summary sentences need alignment with the results. |

## Conclusion

The author has answered round 2 thoroughly, and the paper is close to acceptable. What
remains is to make the summaries say exactly what the detailed sections show:
- the attribution differs between the two baselines (R1);
- refined TDR membership is not resolved (R3a);
- the Sobol-arm share is about, not at least, two thirds (R3b);
- the failed predeclared endpoint (R3c).

The paper should also show, from data already in hand, that the feasible-fraction comparison
survives the refinement shifts the author measured (R2). No new simulations are required. I
recommend **minor revision** and expect to recommend acceptance once these items are
addressed.

*— Reviewer 2*
