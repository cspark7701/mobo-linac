# Consolidated revision tasks — round3

**Reviewers:** Reviewer 1 and Reviewer 2

**Recommendations:**
- Reviewer 1: **major revision**.
- Reviewer 2: **minor revision**.

Both reviewed the manuscript at `00190d8`. Neither finds it acceptable in its present form, and both describe a route to acceptance that needs **no new simulations**. The route is a sharply framed comparison of the specified pipelines on the nominal numerical model.

**Purpose:** A single working queue that merges the two round3 task lists. Overlapping requests are merged, each reviewer's specific concerns are kept, and conflicts are resolved explicitly. The individual reviewer documents remain the source records. This document does not authorize simulations, manuscript edits or publication actions. **All tasks C3-01 to C3-12 are closed (2026-10-30).**

**Excluded at the author's direction (2026-10-29):** funding and acknowledgments, together with `\finaltrue` (remainder of C2-10), and the Zenodo deposition (C2-15). They are not tracked here.

## Status (2026-10-30)

| ID | Status | Commit(s) | Remaining |
|---|---|---|---|
| C3-01 | Done: **route (a)** (author, 2026-10-30), replacing route (b) | this commit | — |
| C3-02 | Done | see below | — |
| C3-03 | Done | see below | — |
| C3-04 | Done | see below | — |
| C3-05 | Done | see below | — |
| C3-06 | Done | see below | — |
| C3-07 | Done | see below | — |
| C3-08 | Done (final audit after the route (a) scope text) | see below | — |
| C3-09 | Done (optional fallback split not done) | see below | — |
| C3-10 | Done (lead-with restructuring with the C3-01 scope text) | see below | — |
| C3-11 | Closed (2026-10-30): withdrawn with route (b); stage A run, stage B not run | this commit | — |
| C3-12 | Done (2026-10-30) | this commit | — |

All work is committed locally only; nothing has been pushed.

## Sources

- [Reviewer 1 round3 report](../reviews/reviewer1_round3_report.md) and [its revision tasks](reviewer1_round3_revision_tasks.md) (R3-01 to R3-07).
- [Reviewer 2 round3 report](../reviews/reviewer2_round3_report.md) and [its revision tasks](reviewer2_round3_revision_tasks.md) (T1 to T13).
- Background:
  - [consolidated round2 tasks](consolidated_round2_revision_tasks.md);
  - [round2 revision overview](round2_revision_overview.md);
  - the round2 responses in `../reviews/`.

## Ground rules carried into round3

- **Production data stay unchanged.** Keep the production campaigns, provenance, feasibility labels, seeds, acquisition definitions and numerical settings. The same applies to the round2 revision runs: the TDR campaigns, the Sobol arm, the jitter runs and the resolution check. New classifications and analyses go in separate derived evidence files under `evidence/`, labelled post hoc where applicable.
- **Nominal resolution.** All values are nominal-resolution results. The C2-12 check measured sensitivity at ten settings. It is not a convergence result or an error bound, and no task may relabel it as one.
- **Abstract.** The abstract stays qualitative and without numbers.
- **Layout.** The one-column review layout, scatter-only Pareto projections, grid lines and shaded constraint regions stay. Reviewer 1 asks explicitly that they be preserved.
- **No public deposition.** No public repository, deposit, upload or push is implied by any task.
- **Not acceptance.** A completed checklist is not reviewer agreement or journal acceptance, and a narrowed claim is not new validation.

## Overlaps and how they are resolved

| Issue | Reviewer 1 | Reviewer 2 | Consolidated treatment |
|---|---|---|---|
| Scope after the resolution finding | M1: choose between a nominal-model benchmark and a physically resolved comparison. Attach the tested population to every stability statement, and add a compact resolution display. | R2: bound the primary feasible fractions under the measured shifts using the archived ledgers. Front-quality comparisons are conditional on source and resolution. | C3-01 (scope) and C3-02 (bounding analysis and display). **Recommended route: the nominal-model benchmark.** Both reviewers accept it without new simulations. The bounding reclassification gives the population-level evidence that Reviewer 1 finds missing from the ten-setting check. |
| Attribution of the feasible-sampling advantage | M3: the exclusive categories are an accounting decomposition, not causation. Energy conditioning compares method-selected populations, so "mainly transverse" must not be merged across comparators. | R1: state the attribution per baseline; "not produced by" the energy weight or the upper window is too strong. | C3-03 combines both. The per-baseline statement, the accounting (non-causal) wording and partial contribution apply in the abstract, contributions, Discussion and Conclusions. |
| Sobol arm | M2: the pooled "exact binomial" interval treats dependent QMC points as independent; use the ten scrambles as units; audit the analogous pooled intervals. | R3(b): "at least two thirds" is 0.66. Minor 1: the energy-band sentence must be direction-specific. | C3-04 combines both. The counts and paired group-bootstrap differences stay. |
| TDR reach | M3: "edge of the explored domain" is not supported in control space, since candidate A is interior. Three campaigns do not show inaccessibility or the need for extra controls. | R3(a): the Conclusions overstate refined TDR membership. | C3-05 combines both: describe sparse coverage, small diagnostic margins and membership that is not resolved. |
| RF-amplitude estimate | M4: a conditional linearized estimate, not a bound. Remove the all-constraint classification implication and the scaling assumption for σ_E. | Minor 2: compare the estimate with the TDR energy margins of A and B (0.31 and 0.14 MeV). | C3-06. **Compatible.** The estimate is relabelled as conditional and linearized, and the TDR comparison is added as an indication, not a bound. Both point the same way: the claims become narrower. |
| Supplement and data availability | M5: the ledgers alone do not regenerate every evidence file (GP checkpoints, tracking outputs and convergence records are also needed). Provide an item-level input inventory and reproduction levels. | Minor 5: make "accompanies this manuscript", "on request" and "not distributed" consistent. | C3-07 combines both. Local documentation only; no deposit. |
| Summary claims and wording | Minor 1: replace "no pipeline exceeded / improved on" the nominal reference with "no primary feasible observation Pareto-dominated it at the nominal resolution". | R3(c): contribution 1 credits a predeclared endpoint that failed. | C3-08: a claims audit of the summary sections. |
| Surrogate explanations | Minor 2: kernel misspecification and adaptive selection are hypotheses; distinguish the 88 refit fallbacks if a causal reading is kept. | Considered N4(a) resolved; no new request. | C3-09. Follow Reviewer 1's wording request; the fallback split is optional. |
| Precision, length and presentation | Minors 3–4: label key tables and figures as nominal-resolution; make the resolution finding visible beside the fronts; lead with the main result. | Minors 3, 4, 6–9: precision, "deterministic", move V F and the detail of V G to appendices, APS style, leftover source comment, abstract readability. | C3-10. One editorial pass. |
| Further tracking | M1: only if physically resolved claims are kept, and then a tolerance-based, method-balanced validation design with separate approval. | R2 optional: re-track the 53 pooled-reference points at the medium level (about 2 h). | C3-11, optional and **not authorized**. It is not needed on the recommended route. |

## Consolidated work queue

Priority: **P0** is required by at least one reviewer (a major comment); **P1** is expected; **P2** is editorial or response work.

| ID | Priority | Workstream | Work category | Dependencies |
|---|---|---|---|---|
| C3-01 | P0 | Scope decision: nominal-model benchmark | Author decision; manuscript | None (do first) |
| C3-02 | Done | see below | — | C3-01 |
| C3-03 | Done | see below | — | C3-01 |
| C3-04 | Done | see below | — | None |
| C3-05 | Done | see below | — | C3-01 |
| C3-06 | Done | see below | — | None |
| C3-07 | Done | see below | — | C3-02, C3-04 (new evidence files) |
| C3-08 | Done (final audit after the route (a) scope text) | see below | — | C3-01 to C3-06 |
| C3-09 | Done (optional fallback split not done) | see below | — | None |
| C3-10 | Done (lead-with restructuring with the C3-01 scope text) | see below | — | C3-01 to C3-09 |
| C3-11 | Closed | Refined re-tracking of selected points | ASTRA runs; analysis | Not needed on route (a) |
| C3-12 | Done | Point-by-point responses and validation | Documentation; focused checks; PDF build | All of the above |

---

### C3-01. Decide the scope: comparison on the nominal numerical model

**Sources:** Reviewer 1 M1 (R3-01, first item); Reviewer 2 R2 (context).

**Decision (author, 2026-10-30): route (a), a comparison of the specified pipelines on the nominal numerical model.** It replaces route (b), which the author chose on 2026-10-29 and withdrew after stage A (see the record below). At the author's direction, the manuscript contains nothing about route (b), including the stage A results.

*Route (b) record (not used in the manuscript).* The predeclared design (driver `scripts/evaluate_revision_validation.py`, commit `e32f63a`) extended the C2-12 fine level (40k particles, 64-cell grids, H/4) one factor at a time for the ten C2-12 settings (stage A), and would then have re-tracked a method-balanced sample of 704 archived observations (stage B). Stage A finished on 2026-10-29 (40 runs, all valid; `results/revision_round3/ladder/`). Under the predeclared 3 % rule:
- step: H/8 vs H/4 changes ε_y by 3.6 % (fail), H/16 vs H/8 by at most 1.4 % (pass), so H/8;
- particles: 80k vs 40k changes ε_y by 3.2 % (fail), so 80k, not shown converged;
- grid: 96 vs 64 cells (at 80k) lowers ε_x by up to 4.4 % and ε_y by up to 7.6 % (fail), so 96 cells, not shown converged;
- only emittances fail. Sizes and divergences change by at most 2.6 %, bunch length by 0.2 %, mean energy by at most 0.01 MeV, and transmission does not change.

The selected level (80k, 96 cells, H/8) would have taken about 14–16 days for stage B with 20 workers, beyond the 3-day gate. The author then chose route (a). Stage B was not run. The design files were removed from the supplement evidence directory (see C3-07); they remain in commit `e32f63a`, and the stage A outputs remain under `results/revision_round3/`.

- [x] **Author decision.** Route (a) (2026-10-30). The options were:
  - **(a)** a comparison of the specified pipelines on the nominal numerical model, with the measured resolution sensitivity as a stated result (**recommended**; no new simulations);
  - **(b)** a physically resolved injector-optimization comparison, which requires C3-11 or a broader validation design with separate authorization.
- [x] Under (a): align the title (if needed), abstract, contributions, Results framing and Conclusions so that every Pareto and algorithm comparison sits explicitly within the nominal numerical model.
- [x] Remove implications of physical rank stability or engineering-ready settings.
- [x] Make the resolution limitation a visible result, e.g. a fifth contribution or an explicit sentence in the contributions paragraph. It must not be presented as a convergence result.

**Done when:** the chosen scope is recorded here, and the title, abstract, contributions and Conclusions make the same claim.

**Done:** The abstract now leads with the pipeline comparison and the measured numerical limitation. It states that tracking is at a fixed nominal resolution, that the emittances are not converged there, that the feasible-sampling advantage persists under the measured refinement shifts, and that the results are not a physically resolved optimization of the injector. The Introduction states that every Pareto and algorithm comparison refers to the fixed source file and tracking resolution. A fifth contribution reports the measured numerical sensitivity as a stated limitation, not a convergence result. The closing sentence of the contributions excludes a physically resolved ranking of the methods. The Results opening and the first paragraph of the Conclusions say that the comparison is made within the nominal numerical model. The title already names a model and is unchanged. "Engineering" appears only in negations or in references to the TDR.

### C3-02. Bound the primary comparison under the measured refinement shifts, and show the resolution result

**Sources:** Reviewer 2 R2 (T2); Reviewer 1 M1 (R3-01, remaining items) and minor 3.

*Bounding reclassification (existing data only):*
- [x] New script `scripts/analyze_revision_resolution_bounds.py`, with a test. It reclassifies the 4,800 primary evaluations and the Sobol arm under bounding shifts taken from `evidence/r2_convergence_summary.csv`:
  - a common scale factor on σ_x, σ_y, σ_x′ and σ_y′, from 1.0 down to the largest observed reduction (about 0.78);
  - σ_z × (1 ± 0.01);
  - E_kin ± 0.05 MeV;
  - transmission unchanged.
- [x] Report, for each shift combination:
  - per-method feasible fractions, overall and after initialization;
  - paired differences with group-bootstrap intervals and the number of positive groups.
- [x] Note that the constraint-aware fraction is the most sensitive to the bunch-length limit. The Reviewer 2 spot check gave 0.36–0.47 against a nominal 0.405.
- [x] Evidence: `evidence/r3_resolution_bounds_{runs,paired}.csv` and a metadata JSON recording the shifts and their source.
- [x] State that the shifts are bounds taken from ten settings, not a per-point refinement model and not an error bound.

*Resolution display and population statements:*
- [x] Add a compact table or figure of the C2-12 result for the ten settings:
  - the production, medium and fine levels;
  - fixed-source step and grid changes, separated from particle and source changes;
  - classification changes.
- [x] Attach the tested population to every stability statement: "ten selected settings, mostly from constrained searches". This applies especially to "production classifications are stable" in the Conclusions.
- [x] Say that a reproduced source marginal does not establish an identical multidimensional distribution. The fixed-source step-only effects stand on their own.
- [x] Add the front-quality caveat in Sec. V B and the Discussion. Those comparisons depend on the fixed source realization and on the production resolution, more strongly than the feasibility comparison does. The reasons are the nonuniform emittance shifts (12–43 %, Spearman 0.79 for ε_x) and the 1–12 % random-source spread.
- [x] Update the Limitations, and the Conclusions if the outcome changes the statement.

**Done when:**
- the manuscript states, with evidence, whether the feasible-fraction advantage survives the measured shifts;
- every stability statement names its population;
- the resolution result is visible in a display item.


**Done:** Bounds over 27 shift combinations (sizes and divergences ×0.78/0.89/1, σ_z ±1 %, E ±0.05 MeV): median feasible fraction 0.369–0.466 constraint-aware, 0.147–0.213 unconstrained, 0.113–0.181 scalarized; post-initialization paired differences 0.239–0.294 and 0.279–0.335, every interval above zero and every difference (including each pipeline over the Sobol arm) positive in all ten groups; +1 % bunch length lowers the constraint-aware mean from 0.405 to 0.364. New Table `tab:resolution` (Sec. II A), population statements, front-quality caveat (Sec. V B, Discussion), Limitations and Conclusions. Evidence `evidence/r3_resolution_bounds_*` (S1.13). On route (a) the bounds are the population-level resolution evidence.
### C3-03. State the attribution per baseline, as an accounting decomposition

**Sources:** Reviewer 2 R1 (T1); Reviewer 1 M3, second part (R3-03, items 4–6).

- [x] Abstract (no numbers), contribution 2, Discussion and Conclusions: say that the advantage persists among energy-acceptable evaluations. Then state the comparison per baseline:
  - against unconstrained MOBO, the gap is concentrated in transverse-only violations;
  - against weighted-sum BO, energy-involving categories account for the larger share.
- [x] Replace "is not produced by the energy-band weight or the upper ACC3/ACC4 window" with a statement of partial contribution ("not explained by … alone").
- [x] Optionally quantify the share of the upper quarter. The occupancy differences of 7–9 percentage points, all infeasible, are roughly a quarter to a third of the gaps.
- [x] Describe the exclusive categories as an accounting decomposition of observed gaps, not as causal identification of acquisition terms.
- [x] Describe the energy-conditional fractions as comparisons of method-selected populations, not as an isolated, energy-independent mechanism.

**Done when:**
- no sentence attributes the advantage to the transverse limits without naming the unconstrained baseline;
- no sentence says the energy weight or the upper window plays no part;
- no sentence infers a causal mechanism.


**Done:** Abstract (no numbers), contribution 2, Sec. V C, the Discussion and the Conclusions state the attribution per baseline: mainly transverse against unconstrained MOBO, mainly energy band against weighted-sum BO, persisting among energy-acceptable evaluations. "Not produced by" is replaced by "neither … explains it alone". Sec. V C calls the categories an accounting, not a causal identification, describes the conditional fractions as method-selected populations, and quantifies the upper quarter: lower mean occupancy by 0.060 and 0.094, about a fifth and a third of the gaps.
### C3-04. Correct the Sobol uncertainty and the Sobol-arm statements

**Sources:** Reviewer 1 M2 (R3-02); Reviewer 2 R3(b) and minor 1 (T3b, T4).

- [x] Remove the pooled "exact binomial" interval for 41/1,440. Report instead the ten run-level fractions and their dispersion, or a run-level interval with its construction and small-sample limits stated.
- [x] Audit `scripts/analyze_revision_space_filling.py` and its outputs for the same pooled construction:
  - the 5/160 initial-design interval;
  - any pooled interval on adaptive BO points.

  Correct the affected derived evidence in new files; do not overwrite the round2 evidence.
- [x] Keep the paired complete-group bootstrap for the BO-minus-Sobol differences. Keep the executed sequences, the 160-point budgets and the 144-point post-initialization comparison.
- [x] Keep the design-specific binomial intervals for independent jitter draws; this correction does not apply to them.
- [x] Replace "at least two thirds" in Sec. V C and the matching Conclusions sentence:
  - the shares are (0.418 − 0.142)/0.418 = 0.66 and 0.74;
  - use "about two thirds" or give both values, e.g. "the constraint-blind pipelines account for at most about one third of the constraint-aware gain over the Sobol arm".
- [x] Make the energy-band sentence direction-specific:
  - unconstrained MOBO falls from 39.0 % to 32.2 % (paired −0.069);
  - scalarized BO rises to 42.6 % (paired +0.035, 0.017–0.052).
- [x] Update the manuscript, the round2 overview table entry if it is quoted, and Supplement S1.6.

**Done when:** the observed counts are unchanged, every interval names its sampling unit, and the Sobol statements match `evidence/r2_sobol_arm_paired.csv`.


**Done:** Run-level uncertainty in `evidence/r3_sobol_uncertainty_{runs,summary}.csv` (S1.6), which supersedes the pooled binomial intervals of `r2_space_filling_initial.csv` (left unchanged). Sobol arm: 41/1,440 (2.8 %), run-level fractions 1.4–4.9 %, s.d. 1.3 points, bootstrap over ten runs 2.1–3.6 % (approximate). "At least two thirds" becomes "the constraint-blind pipelines account for at most about one third (shares 0.34 and 0.26)" in Sec. V C and the Conclusions; the energy-band sentence is direction-specific (−0.069 unconstrained, +0.035 scalarized). Counts and paired differences unchanged; jitter intervals untouched. The round2 overview quotes no interval.
### C3-05. Describe the TDR reach without claims about domain geometry or necessity

**Sources:** Reviewer 1 M3, first part (R3-03, items 1–3); Reviewer 2 R3(a) (T3a).

- [x] Replace "at the edge of the explored domain" in the abstract, contribution 3, Sec. VI B and the Conclusions with what was observed:
  - sparse coverage at the nominal resolution;
  - small diagnostic margins;
  - membership that changes under refinement.

  If "edge" is kept, define it as the diagnostic acceptance boundary, not a boundary in control space.
- [x] If control-space location is discussed, use the normalized controls:
  - candidate A is interior (about 0.48–0.86);
  - candidate B has the gun phase near 0.96, with its other controls interior.

  Do not generalize from these two points.
- [x] Present the three TDR-constrained campaigns as finite-budget, nominal-resolution observations. They do not show that the region is inaccessible, nor that further RF or matching controls are necessary. Those controls may be named as future design options.
- [x] Conclusions: replace "Under refined tracking their closest observation and the MOGA-derived nominal setting do meet them". The statement must match Sec. VI B: both meet the inequalities at the combined medium and fine levels, but fail with four of five regenerated sources, so membership near the limits is not resolved.

**Done when:** the abstract, contribution 3, Sec. VI B and the Conclusions make the same observational claim about the TDR region.


**Done:** "At the edge of the explored domain" is removed from the abstract, contribution 3, Sec. VI B and the Conclusions; they now state rare TDR-feasible observations with micrometre-scale diagnostic margins and membership that changes under refinement. Sec. VI B gives the normalized controls (candidate A 0.48–0.86 in every coordinate; candidate B interior except gun phase 0.96), says two points do not locate a region in six dimensions, and that three finite campaigns do not show inaccessibility. The extra RF and matching controls are design options, not a demonstrated remedy. The Conclusions sentence on refined membership matches Sec. VI B (meets at combined medium/fine, fails with four of five regenerated sources).

**Route (a) (2026-10-30):** No refined TDR membership is added. The manuscript states that membership near the TDR limits is not numerically resolved: the closest TDR-constrained observation and the MOGA-derived nominal setting pass at the medium and fine levels but fail with four of five regenerated sources.
### C3-06. Restrict the RF-amplitude estimate to what it estimates

**Sources:** Reviewer 1 M4 (R3-04); Reviewer 2 minor 2 (T5).

- [x] Name the reference setting used: the re-evaluated MOGA-derived nominal setting, with gains of 4.1, 93.3 and 102.8 MeV.
- [x] Also name the gain-scaling approximation and the two correlation assumptions.
- [x] Describe 0.28 and 0.40 MeV RMS as conditional linearized estimates. Replace "bounds their effect".
- [x] Remove the inference that the 3.11 MeV lower-energy headroom preserves the full production-profile feasibility of every representative. The bunch-length and upper-energy margins, and the effects on phase slippage, focusing and chirp, are not estimated.
- [x] Explain the assumption behind scaling the energy spread by the same fraction (about 0.8 keV), or remove it.
- [x] In the TDR-candidate jitter paragraph, compare the same estimate with the TDR lower-energy margins of candidates A and B: 0.31 and 0.14 MeV, about 0.4–1.1 RMS shifts. State this as an indication, not a bound, that amplitude jitter would cause further TDR failures.
- [x] Keep the tracked lattice-only results as their own evidence.

**Done when:** every conclusion is limited to the quantity the estimate actually provides. No new error campaign is needed.


**Done:** Sec. V I names the reference setting (re-evaluated MOGA-derived nominal; gains 4.1, 93.3, 102.8 MeV), the linear gain-scaling approximation at fixed phase and the two correlation assumptions, and calls 0.28/0.40 MeV RMS a conditional linearized estimate, not a bound. The all-constraint classification inference and the σ_E scaling sentence are removed; the text states the margins and effects the estimate does not cover. The TDR-candidate paragraph compares the estimate with the TDR lower-energy margins (0.31 and 0.14 MeV) as an indication of further TDR failures. The Discussion sentence on JKPS errors is aligned.
### C3-07. Make the reproduction dependencies and the data availability statement accurate

**Sources:** Reviewer 1 M5 (R3-05); Reviewer 2 minor 5 (T8).

- [x] Correct the claim in Appendix A and the supplement README that about 10 MB of evaluation ledgers regenerate every evidence file.
- [x] Map each S1 item to the inputs it requires:
  - evaluation ledgers, configuration and completion records;
  - GP checkpoints (`analyze_revision_predictions.py`, the frozen-model scaling probe);
  - retained tracking outputs (`astra.Zemit.001` for the RF estimate);
  - convergence results, plan and source records.
- [x] Distinguish three reproduction levels:
  1. rebuilding tables and figures from the distributed derived evidence;
  2. regenerating the analyses from raw ledgers, checkpoints and tracking outputs;
  3. replaying simulations or proposals. Proposals cannot be replayed bitwise, because sampler base draws were not archived.
- [x] State the exact snapshot identifier. Also state which inputs accompany the review package and which are available from the author on request.
- [x] Make Appendix A ("accompanies this manuscript"), the Data availability statement and the supplement README consistent. State whether S1 or its evidence is submitted as PRAB Supplemental Material, or whether all of it is available on request. Add no public repository or deposit.
- [x] Test representative regeneration paths with the claimed input set, or label the result an inventory-only check. Extend `scripts/build_supplement_manifest.py` to record the input class of each item.
- [x] Add the C3-02 and C3-04 evidence files to S1 and rebuild the manifest.

**Done when:** a reader can tell which inputs are needed for each reproduction level, and the three statements about availability agree. Local packaging only; no upload or push.


**Done:** New `docs/paper/supplement/input_inventory.csv` maps every generator to its input classes, run files and reproduction level (1 / 2a / 2b / 3); `build_supplement_manifest.py` now fails on a generator without a valid inventory entry. The README replaces the blanket 10 MB claim with a reproduction-level table and examples (GP checkpoints, `astra.Zemit.001`, convergence records). `scripts/check_supplement_regeneration.py` regenerated three level-2a generators (resolution bounds, Sobol uncertainty, attribution) in a scratch tree with only the 215 minimal ledger files and matched the committed evidence (`r3_regeneration_check.json`). Appendix A, the Data availability statement and the README now agree: S1 is supplied for review and otherwise on request, the run directories are available from the author, and the snapshot is identified by the commit in the review package. No deposit or upload.

**Route (a) cleanup (2026-10-30):** The route (b) design files (`r3_validation_design.json`, `r3_validation_sample.csv`) are removed from the evidence directory, together with their evidence-map rows and the inventory entry of `scripts/evaluate_revision_validation.py`. The supplement therefore contains nothing about route (b). The ledger helpers that the C3-02 and C3-04 generators share moved from the route (b) driver to `scripts/revision_ledgers.py`. Their outputs are unchanged, and the regeneration check still passes.
### C3-08. Audit the summary claims

**Sources:** Reviewer 2 R3(c) (T3c, T3 last item); Reviewer 1 minor 1 (R3-06, first item).

- [x] **Contribution 1.** State that the feasible fraction was predeclared. Also state that the predeclared fixed-reference hypervolume endpoint failed and was replaced by labelled post-hoc indicators. Do not list "a fixed reference point and predeclared endpoints" as a property of the comparison.
- [x] **MOGA-derived nominal setting (Sec. V J, Discussion, Conclusions).** Replace "no pipeline exceeded it" and "do not demonstrate an improvement on it" with "no primary feasible observation Pareto-dominated it at the nominal resolution". Keep the single-objective improvements (247/40/42, 65/8/9, 67/32/10). The reference is not established as an optimum.
- [x] Check the abstract, Introduction, Discussion and Conclusions for any other summary sentence that is stronger than the corresponding Results or Discussion text.

**Done when:** every summary sentence can be traced to a detailed statement that says the same thing.


**Done:** Contribution 1 no longer lists "a fixed reference point and predeclared endpoints": the feasible fraction was predeclared, and the failed fixed-reference hypervolume endpoint is replaced by labelled post-hoc indicators. Sec. V J, the Discussion and the Conclusions say that no primary feasible observation Pareto-dominates the MOGA-derived nominal setting at the nominal resolution, keep the single-objective improvements, and add that the reference is not established as an optimum. Audit of the summary sections: the abstract now says that objective-quality comparisons depend on the fixed numerical model and that the jitter assessment is lattice-only, and the Conclusions sentence on regeneration points to the S1 input inventory.

**Final audit (2026-10-30, after the C3-01 scope text):** The abstract, the five contributions, the Discussion, the Limitations and the Conclusions agree on four points:
- the comparison is made within the nominal numerical model;
- the feasible-sampling advantage persists under the bounding shifts;
- front quality is conditional on the empirical reference and the fixed numerical model;
- TDR membership near the limits is not resolved.

No sentence claims a physically resolved ranking, uniform superiority or an engineering-ready setting. The remaining uses of "outperform" and "superiority" are negations or references to the literature.
### C3-09. Word the surrogate undercoverage as hypotheses

**Sources:** Reviewer 1 minor 2 (R3-06, second item). Reviewer 2 has no further request.

- [x] In Sec. V G and the Limitations, label kernel misspecification and adaptive test points as hypotheses for the remaining undercoverage. The inferred-noise refit shows sensitivity to regularization only.
- [x] Do not count the 88 refit fallbacks to initial hyperparameters as equivalent fits.
- [ ] *Optional, offline (not done; the refit records carry no fallback flag):* repeat the coverage comparison with the fallback cases separated, using existing refit records. Otherwise keep the wording descriptive.

**Done when:** no causal explanation of undercoverage is stated as established.


**Done:** Sec. V G now introduces fixed noise, kernel misspecification and adaptive test points as three hypotheses, none isolated. The inferred-noise refit is described as showing sensitivity to the regularization; kernel misspecification and adaptive selection remain untested hypotheses for the remainder. The 88 refits restored to initial hyperparameters are stated to be non-equivalent fits that the archived refit records do not identify, so the refit coverage includes them. The optional split was not done: the records carry no fallback flag, so it would require redoing the refits. The Limitations wording was already descriptive.
### C3-10. Precision, length, style and source hygiene

**Sources:** Reviewer 1 minors 3–4 (R3-06, last items); Reviewer 2 minors 3, 4, 6–9 (T6, T7, T9–T12).

*Precision and labels:*
- [x] Label the Pareto figures and key tables (Tables III, IV, V and X) as nominal-resolution results.
- [x] State once, in the caption of Table X and in Sec. V H, that the quoted digits identify archived evaluations and are not resolved physical values.
- [x] Round emittances and energy spreads in the running text to two or three significant figures, e.g. in Secs. V H, V J and VI A. Keep full precision in tables and evidence.
- [x] Sec. III A: qualify "deterministic". The calculation is deterministic for the fixed source file, whose sampling error (1–12 % in emittance) is common to all methods and is not represented by the GP noise.

*Length and readability:*
- [x] Lead with the pipeline comparison and the measured numerical limitation (Reviewer 1 minor 4). *Done with the C3-01 scope text: the abstract opens with the comparison, then the limitation.*
- [x] Move the details of Sec. V F (offline smoothing sensitivity) to an appendix, keeping a short summary in the main text.
- [x] Move the stage-, region- and refit-detail paragraphs of Sec. V G to Appendix D, keeping the 79–89 % coverage, the causes (as hypotheses, C3-09) and "part, but not all".
- [x] Shorten the resolution-check description in Sec. II A to its findings, alongside the C3-02 display item. Move the level definitions to an appendix or to S1.13.
- [x] Abstract: split the sentence beginning "Feasibility is defined by a deliberately relaxed computational acceptance profile". Do not lengthen the abstract with the C3-03 and C3-05 corrections.

*Style and source:*
- [x] APS style: "Ref." instead of "ref." (Secs. I and II B), and "Sec. 4.3" for Kim et al. (Secs. II A and VI A).
- [x] Remove `% C05 replacement for the acquisition-reference explanation.` (Sec. III C).
- [x] Search `main.tex` and the included `.tex` inputs for other revision-tag comments.
- [x] Add a test that fails on revision-tag comments in the manuscript source.
- [x] Rebuild the one-column review copy and the two-column `reprint` copy, and update the quoted page counts.

**Done when:** the labels and captions carry the nominal-resolution scope, the source is clean, and both layouts build without errors, undefined references or overfull boxes.


**Done:** Nominal-resolution labels on Tables IV, V and X (also in the two table generators) and on both Pareto figures; Sec. V H states that quoted digits identify archived evaluations; running-text emittances and spreads rounded to three significant figures (published values of earlier studies kept as published). Sec. III A qualifies determinism with the 1–12 % source-sampling spread. Sec. V F is a short summary with the probe moved to new Appendix `app:smoothing`; the stage, region and refit detail of Sec. V G moved to Appendix D with a summary kept; Sec. II A reduced to its findings with the level definitions in Appendix A. Abstract sentence split. APS style: Ref., Sec. 4.3. The `% C05` comment removed; `tests/test_manuscript_hygiene.py` fails on revision-tag comments in main.tex and its included inputs (unincluded evidence snippets keep their headers). Table `tab:resolution` is full-width. Builds: one-column 56 pages, two-column 31 pages, both without errors, undefined references or overfull boxes. The lead-with reordering was done with the C3-01 scope text (2026-10-30). The abstract was then shortened to 262 words, against 263 at `00190d8`, so the corrections do not lengthen it. The weighting survey is no longer mentioned, and the TDR-campaign clause reads "approach but do not meet them at the nominal resolution".
### C3-11. 🖥 Refined re-tracking of selected points (closed)

**Sources:** Reviewer 2 R2, optional; Reviewer 1 M1, conditional on route (b). **Authorized by the author on 2026-10-29 together with route (b), with 20 workers.** The design is the one recorded under C3-01; it covers both reviewers' variants. The 53 pooled-reference points are part of the per-run front stratum.

- [x] *Reviewer 2 variant:* **not run** (closed). re-track the 53 pooled-reference points at the `combined_medium` level, at about 20 min per run (roughly 2 h with eight workers). Report whether each method keeps its points on the refined pooled front.
- [x] *Reviewer 1 variant (route (b) only):* **design written and stage A run; stage B not run** (closed). first write a tolerance-based, method-balanced validation design. It must include rejected and boundary observations of every arm and state what the design can and cannot establish. Obtain separate approval before tracking. Full campaign replication is not the first step.
- [x] Record any run separately from the production campaigns, as with C2-12. Stage A is in `results/revision_round3/ladder/`, apart from production.

**Done when:** not applicable unless authorized.

**Closed (2026-10-30):** Withdrawn together with route (b) at the author's direction. Stage A ran and stage B did not. Neither variant is pursued, and nothing from this task enters the manuscript or Supplement S1. The responses record the 53-point re-tracking as not run. See the route (b) record under C3-01.

### C3-12. Responses and validation

**Sources:** Reviewer 1 R3-07; Reviewer 2 T13.

- [x] Write `docs/paper/reviews/reviewer1_round3_response.md` and `reviewer2_round3_response.md`. Map each major and minor comment to the changes made, the evidence, or a reasoned non-adoption.
- [x] In the Reviewer 2 response, correct the round2 statement that all revision-integration comments had been removed.
- [x] Package the manuscript diff against `00190d8`, the analysis-code diff, the changed-file inventory and a round3 overview, as in round2.
- [x] Validate:
  - `ruff`, the documentation-sync check and the full test suite with 100 % coverage;
  - the supplement manifest check;
  - both PDF builds.
- [x] Inspect the changed tables and figures and their nominal-resolution captions.
- [x] Distinguish narrower claims from new validation. Do not equate task closure with reviewer agreement or journal acceptance.

**Done when:** every comment of both reviewers has a traceable disposition, the retained claims match the evidence, and the validation status is reported honestly.

**Done:**
- **Responses.** `reviewer1_round3_response.md` (M1–M5 and four minors) and `reviewer2_round3_response.md` (R1–R3 and nine minors). Each comment is mapped to its manuscript change and evidence, or to a reasoned non-adoption: the fallback split, the 53-point re-tracking and a converged-resolution comparison. The Reviewer 2 response corrects the round2 statement on revision comments. Following the author's direction for the manuscript, neither response mentions route (b).
- **Package.** `round3_manuscript.diff`, `round3_analysis_code.diff`, `round3_changed_files.json` (against `00190d8`) and `round3_revision_overview.md`.
- **Validation.** It is recorded in Task 00308. The overview distinguishes the narrower claims from new validation, and says that task closure is not reviewer agreement or acceptance.

---

## Suggested order of work
1. **C3-01:** the author's scope decision.
2. **Analyses of existing data:** C3-02 (bounding script and evidence) and C3-04 (Sobol uncertainty). They are independent and can run in parallel.
3. **Manuscript claims:** C3-03, C3-05, C3-06, C3-08 and C3-09. They touch the same summary sentences, so make them in one pass.
4. **C3-07:** the supplement inventory and data availability, after the new evidence files exist.
5. **C3-10:** the editorial pass, last among the manuscript tasks, because it moves text changed above.
6. **C3-11:** only if the author authorizes it.
7. **C3-12:** last.
