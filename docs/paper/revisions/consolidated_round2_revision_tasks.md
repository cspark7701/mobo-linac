# Consolidated revision tasks — round2

**Reviewers:** Reviewer 1 and Reviewer 2

**Recommendation shared by both:** Major revision. The manuscript reviewed at `9077875` is not acceptable in its present form, but both reviewers describe a route to acceptance that needs **no mandatory new optimization campaigns**.

**Purpose:** A single working queue that merges the two round2 task lists and the MOGA-data reusability assessment. Overlapping requests are merged, each reviewer's specific concerns are kept, and the dispositions are explicit. The individual reviewer documents remain the source records. This document does not authorize new simulations; every ASTRA run listed below needs separate author authorization.

## Sources

- [Reviewer 1 round2 report](../reviews/reviewer1_round2_report.md) and [its revision tasks](reviewer1_round2_revision_tasks.md) (R2-01 to R2-08).
- [Reviewer 2 round2 report](../reviews/reviewer2_round2_report.md) and [its revision tasks](reviewer2_round2_revision_tasks.md) (Q1 to Q14).
- [MOGA data reusability assessment](moga_reuse_assessment.md) (recommendations 1–5).
- Background: [consolidated round1 tasks](consolidated_round1_revision_tasks.md), [round1 revision overview](round1_revision_overview.md), and the round1 responses in `../reviews/`.

## Ground rules carried into round2

- Keep the production campaigns, provenance, feasibility labels, seeds and acquisition definitions unchanged. New classifications and analyses go in separate derived evidence files, labelled post hoc where applicable.
- **The numerical convergence study is already done** (author confirmation recorded in [Task 00226](../../exec-plans/completed/TASK_00226_withdraw_convergence_review_comment.md) and [Task 00227](../../exec-plans/completed/TASK_00227_record_completed_convergence_study.md); round1 C09). Neither reviewer asks for a new convergence campaign. Round2 only asks for the existing result to be reported, or, if the record cannot be found, for the claims to be restricted.
- The abstract stays qualitative and without numbers, as the author prefers. Both reviewers accept this; quantitative conditions go in Methods, Results and captions.
- The generic article format, keywords, scatter-only Pareto projections and grid lines stay. Reviewer 1 explicitly does not ask for a return to the JINST format.
- A completed checklist is not reviewer agreement or journal acceptance. A narrowed claim is not new validation.

## Overlaps and how they are resolved

| Issue | Reviewer 1 | Reviewer 2 | Consolidated treatment |
|---|---|---|---|
| KLS relevance and TDR profile | M1: frame as a fixed-model study under a stated acceptance profile; tabulate the two TDR candidates and their margins; a TDR campaign is not required. | N1: state where the production limits come from; change the title; discuss whether the TDR region is reachable; a TDR campaign is optional. | C2-01 combines both. The title change is recommended (Reviewer 2) and compatible with Reviewer 1. The TDR-constrained campaign remains optional. |
| Numerical accuracy | M2: locate the existing convergence record and compare it with margins (2.47/8.93 µm in σ_x, 8.16/7.96 µm in σ_z, 0.31/0.14 MeV in energy); otherwise restrict claims to nominal resolution. | N4(b): the same; no new study. | C2-04. Both reviewers agree; the study is already done, and the task is to report it. |
| Constraint-aware acquisition | M3: treat the raw-residual implementation as the tested method; describe "three specified pipelines". | N2: break the feasible-fraction gap down by violated constraint, by time spent in the upper ACC3/4 quarter, and conditional on the energy band; state the energy-channel step explicitly. | C2-02 does both: identify the method correctly and attribute its effect, using existing data only. |
| Space-filling reference | Not requested (Sobol arm not required). | N3: report the 5/160 initial-design rate; a full Sobol arm is optional. | C2-03. This reports existing data only, so it doesn't conflict with Reviewer 1. The Sobol arm stays optional. |
| Statistical inference | M4: the quality-indicator tests share a data-derived reference; treat them as exploratory or justify the inference construction. | Minor 5: note the Holm floor (0.0234) and lead with effect sizes. | C2-06 applies both. Feasible-fraction inference, which uses no shared reference, is kept separate from the quality indicators. |
| Surrogate accuracy | M5: interpret undercoverage and RMSE; optional stage-resolved summaries; no refitting needed. | N4(a): discuss the causes; optional refit with inferred noise. | C2-05. Discussion is required; the stage summaries and the noise refit are both optional and offline. |
| MOGA comparison | No MOGA campaign requested. | Round1 M7: the published MOGA is context only. | C2-07 follows the reuse assessment. The **MOGA-derived nominal setting** (identical to `mobo-linac/astra.in`) may be reused as one reference point. It is not the published MOGA solution and not a MOGA benchmark. Round1 declined to re-evaluate the *published* MOGA setting; re-evaluating the paper's *own nominal* is a different, single-run request that needs author authorization. |
| Robustness | Minor 5: state the robustness result as conditional on the lattice-only error model. | Minors 4, 6, 7: an RF-amplitude estimate, a dominance check for D < 1, optional jitter of the TDR candidates. | C2-08. The analytic estimate and the existing-data check are required; the jitter runs are optional. |
| Length and presentation | Minors 1–4, 6–7: terminology, supplement for the audit detail, metadata. | Minors 1–3, 9–10: abstract, length, comment cleanup, target journal. | C2-10. Move the audit detail to an identified supplement (C2-09), not out of the record. |
| Reproducibility | M6: a supplement or software identity the reader can resolve. | Not raised. | C2-09. No upload or push is implied. |

## Consolidated work queue

Priority: **P0** is required for acceptance by at least one reviewer (a major comment); **P1** is expected; **P2** is editorial or response work.

| ID | Priority | Workstream | Work category | Dependencies |
|---|---|---|---|---|
| C2-01 | P0 | Study target, acceptance profiles and KLS framing | Author clarification; manuscript; existing C01 records | None |
| C2-02 | P0 | Executed acquisition and attribution of the feasible-sampling advantage | Existing evaluations; manuscript | C2-01 (profile wording) |
| C2-03 | P0 | Space-filling reference from shared initial designs | Existing records | C2-02 (per-channel breakdown) |
| C2-04 | P0 | Report the completed numerical-convergence evidence | Documentation; existing record | Author supplies the record |
| C2-05 | P0 | Interpretation of surrogate predictive accuracy | Existing C11 records; optional offline refit | None |
| C2-06 | P0 | Reference-dependent statistical inference | Manuscript; optional offline reanalysis | None |
| C2-07 | P1 | MOGA-derived nominal setting as a reference point | Documentation; one authorized ASTRA run | C2-01; author authorization |
| C2-08 | P1 | Robustness interpretation refinements | Analytic estimate; existing jitter records; optional runs | C2-01 |
| C2-09 | P0 | Supplement identity and evidence map | Packaging and documentation | C2-02 to C2-08 outputs |
| C2-10 | P2 | Terminology, length, abstract and submission items | Manuscript; author input | C2-01 to C2-09 |
| C2-11 | P2 | Point-by-point responses and validation | Documentation; focused checks; PDF build | All of the above |

---

### C2-01. Make the study target and acceptance population consistent

**Sources:** Reviewer 1 M1 and minor 5 (R2-01); Reviewer 2 N1 and minor 1 (Q1, part of Q10).

- [ ] State the origin of the production limits (1 mm, 1 mrad, 1 mm, 195–205 MeV, T ≥ 0.90): an earlier design stage, a deliberately relaxed exploration profile, or a configuration default. If there is no engineering basis, say so. Replace "The TDR does not justify replacing its requirements with the production limits."
- [ ] Revise the title so it does not imply a KLS-acceptance design study, e.g. "…of a KLS-derived 200 MeV injector-linac model".
- [ ] In the abstract (no numbers), describe the contribution as a matched fixed-model comparison under a specified acceptance profile that is looser than the TDR optimization requirements.
- [ ] Replace "all archived observations" with the actual population: the 4,800 **primary** evaluations (648/251/200 production-feasible; 2/0/0 TDR-feasible).
- [ ] Add a compact table or appendix entry for the two TDR candidates, from `evidence/c01_tdr_candidates.csv`: stable candidate IDs (no raw seed numbers in the prose), objectives and signed physical margins. Note that they are marginal and come from two different matched runs.
- [ ] State that two versus zero is observed coverage, not a demonstrated method ranking under the TDR profile, and that these candidates are not the six jitter representatives.
- [ ] Discuss whether the TDR region is reachable with the six fixed-lattice controls, or needs controls held fixed here (RF amplitudes, the matching quadrupoles of the full TDR linac).
- [ ] In the conclusions, state what engineering conclusion the TDR check supports, and identify the population and profile in every feasibility and robustness claim.
- **Optional 🖥 (author authorization needed):** one or more constraint-aware campaigns under the TDR optimization constraints (Reviewer 2). Reviewer 1 does not require this for the restricted computational claim.

**Done when:** the title, abstract, section 2.2, Discussion and Conclusions consistently describe a method comparison under a stated, relaxed profile on a KLS-derived model, and the TDR candidates can be inspected.

### C2-02. Identify the executed acquisition and attribute its feasible-sampling advantage

**Sources:** Reviewer 1 M3 and minor 3 (R2-03); Reviewer 2 N2 and minor 8 (Q2, Q8).

*Method identity (manuscript):*
- [ ] Describe the comparison as three specified optimization pipelines that share the physical model, initial designs and simulation budget. They differ in target construction, model count, constraint information and Monte Carlo sample counts, not only in the acquisition formula.
- [ ] Keep the raw residual units, effective smoothing scales, unequal posterior sample counts and baseline handling in the Methods. State explicitly that τ_c = 10⁻³ eV makes the energy-band weight an effective step with vanishing gradient, alongside the existing beam-size values.
- [ ] Add a short synthesis that separates the empirical three-pipeline result from the frozen-model unit-sensitivity diagnostic. That diagnostic covers q = 1, no pruning and one run; an unchanged top probe does not show that the production q = 8 optimizer is invariant.
- [ ] Make no claim of measured efficacy for a normalized or corrected acquisition.

*Attribution (existing data only):*
- [ ] For each method and post-initialization batch, classify infeasible evaluations into exclusive categories (energy band only; transverse size or divergence only; bunch length only; combinations) and also report "any violation".
- [ ] Divide the paired feasible-fraction gap (constraint-aware minus each baseline) among those categories.
- [ ] Per batch and method, report the fraction of evaluations in the upper ACC3/4 quarter (325.5561–341.0588°).
- [ ] Report the conditional feasible fraction among evaluations that satisfy the energy band, with paired intervals.
- [ ] Add a figure or table and one Results paragraph. If the advantage comes mainly from the energy boundary, say so in the abstract, Discussion and Conclusions. Present the analysis as descriptive attribution, not a prediction for a restricted domain.

**Done when:** the abstract, Methods, Results and Conclusions identify the same executed implementation, and the manuscript states which constraints account for the gain. The script, tests and evidence files are committed (e.g. `evidence/r2_attribution_*`).

### C2-03. Report a space-filling reference from the shared initial designs

**Sources:** Reviewer 2 N3 (Q3). Reviewer 1 does not request a Sobol arm; this task uses existing data only.

- [ ] Report the feasible rate of the 160 shared Sobol initial points (5/160 = 3.1 %) with an exact Clopper–Pearson interval. Label it as initialization-only, not a matched arm.
- [ ] Using C2-02's breakdown, explain why constraint-blind acquisition already raises feasibility above this rate.
- [ ] Keep the statement that no advantage over a full Sobol search is established.
- **Optional 🖥 (author authorization needed):** a budget-matched Sobol arm, 10 seeds × 160 evaluations with the same initial designs (about 1 h of tracking per campaign).

**Done when:** Results reports the reference and its interval, and the Discussion explains the baseline feasibility gain.

### C2-04. Report the completed numerical-convergence evidence

**Sources:** Reviewer 1 M2 (R2-02); Reviewer 2 N4(b) (Q4b). **The underlying study is already complete; no new convergence calculation is requested.**

- [ ] Locate the existing convergence record from the previous study of this injector: the particle, mesh and integration settings, the source used, the solver-transition correspondence, and the residual changes in ε_n and σ_E at the adopted settings.
- [ ] Report these in section 2.1 with a citable source, and compare them with the method differences and the relevant margins. The TDR candidates' margins are about 2.47/8.93 µm in σ_x, 8.16/7.96 µm in σ_z and 0.31/0.14 MeV in lower energy; also compare with the smallest robustness margin.
- [ ] Revise the section 6.2 sentence "numerical uncertainty … is therefore unquantified" to agree.
- [ ] If the record cannot be located, state that the classifications are results at nominal resolution, and remove any implication of numerically validated engineering settings. Record in the responses which route was taken.
- [ ] Do not substitute deterministic repeats, the GP likelihood variance, the physical jitter spread or printed output precision for the tracking-discretization error.

**Done when:** sections 2.1 and 6.2 agree with each other and with the author's confirmation, and the claims match the evidence.

### C2-05. Interpret surrogate predictive accuracy

**Sources:** Reviewer 1 M5 (R2-05); Reviewer 2 N4(a) (Q4a).

- [ ] Discuss the likely causes of the 79–89 % coverage of nominal 95 % intervals: fixed near-zero noise (η = 10⁻⁶), kernel misspecification and adaptively selected test points. Explain the consequences for the constraint-feasibility weights used in acquisition.
- [ ] Explain the whole-trajectory RMSE (about 7.88 and 13.73 µm·rad for the constrained emittance channels): it mixes stages and feasible and infeasible regions. Make clear that it does not invalidate the directly tracked observations.
- [ ] Either refrain from claims of accurate local or late-stage prediction, or support them with stage-resolved and feasible/near-front summaries from the existing C11 records (counts and run-level variation).
- [ ] Keep the floored and covariance-derived interval conventions distinct. Claim no calibrated machine reliability and no loss discrimination from the constant transmission channel.
- **Optional (offline, no ASTRA):** refit the saved training sets with inferred homoscedastic noise and repeat the next-batch coverage check (Reviewer 2). Reviewer 1 does not require refitting.

**Done when:** the predictive limitations and any retained local-accuracy claim are supported at the stated scope.

### C2-06. Qualify inference that depends on a shared, data-derived reference

**Sources:** Reviewer 1 M4 (R2-04); Reviewer 2 minor 5 (Q7).

- [ ] Separate feasible-fraction inference, which uses no pooled reference and has constraint-aware ahead in all ten groups against each baseline, from the epsilon, IGD+ and HV comparisons, which use a reference estimated from the tested outcomes.
- [ ] State that 0.0234 is the smallest Holm-adjusted p-value the design allows: n = 10, exact two-sided p = 2/1024, multiplied by 12. Lead the paired-results paragraph with effect sizes and paired intervals.
- [ ] Explain why exact sign enumeration alone does not establish calibration after a shared data-derived transformation. Choose one route:
  - (a) keep the quality effects and reference sensitivities descriptive, and label the quality-test probabilities as exploratory and assumption-dependent; or
  - (b) use a justified offline procedure that rebuilds the references within run-level resampling, stating its estimand and remaining assumptions.
- [ ] Keep the unadjusted mean-effect intervals, the signed-rank hypotheses and the Holm-adjusted values distinct. Do not change endpoints to obtain a favourable ranking.

**Done when:** no quality-significance claim is stronger than its inferential construction supports, and the original tables remain preserved.

### C2-07. Reuse the MOGA-derived nominal setting as a reference point

**Sources:** [MOGA reusability assessment](moga_reuse_assessment.md), recommendations 1–5; Reviewer 2 round1 M7 context; the manuscript sections on selected settings and previous KLS studies.

**Findings carried forward:**
- No MOGA population or front exists. The NSGA-II notebook in `cmkim/moga/` failed on its first evaluation and never wrote its results.
- `beam_tracking/astra.in` is the MOGA-derived setting and is identical to `mobo-linac/astra.in`; field maps, source and ASTRA binary are byte-identical.
- It is **not** the published MOGA solution: the MOGA code used a 120 MV/m gun, different gradients, 0–360° phases and TDR-like constraints.
- Its stored ASTRA output stops at 15.727 m, so exit-plane diagnostics are missing.
- None of the 53 pooled feasible nondominated primary observations dominates its notebook objective values (3.4728, 3.2968 µm·rad; 0.39419 MeV).

Tasks:
- [ ] **Manuscript wording (no simulation):**
  - State that the nominal setting, and hence the centre of the ±50 % search domain, is a MOGA-derived setting adapted to the present field amplitudes.
  - Distinguish it from the published tracked MOGA point.
  - Correct the related statements in sections 5.7 and 6.1 ("no primary observation exactly matches the nominal input vector"; "reevaluation of its published setting").
- [ ] **🖥 Single re-evaluation (author authorization needed):** run `astra.in` once through the current pipeline, journaled like the production evaluations. Record its full exit-plane diagnostics and its feasibility under the production, TDR and NAPAC profiles in a separate evidence file.
- [ ] After the re-evaluation: show the setting as a reference marker in the primary Pareto projections and constraint-space plots. Report whether any feasible primary point dominates it, and give each method's additive epsilon to it.
- [ ] **Optional 🖥:** run 50 lattice-jitter trials of this setting under the same protocol as the six representatives, as a robustness baseline.
- [ ] Do not present it as a MOGA benchmark or use it for any claim about MOGA efficiency or coverage. A real MOGA comparison would be a new campaign (with the NSGA-II code's I/O bug and mutation typo fixed and the problem redefined) and is outside this round.

**Done when:** the manuscript identifies the nominal setting correctly and, if the run is authorized, reports it as a measured reference point with its feasibility status.

### C2-08. Refine the robustness interpretation

**Sources:** Reviewer 1 minor 5 (part of R2-01/R2-07); Reviewer 2 minors 4, 6 and 7 (Q5, Q6, Q9).

- [ ] State the robustness result as conditional on the simulated lattice-only error model. Success in all samples is not a reliability guarantee.
- [ ] Add an analytic RF-amplitude estimate: about 0.2 % amplitude jitter shifts the mean energy by roughly 0.4 MeV at 200 MeV, against the 3.11 MeV lower-energy headroom, plus an estimate of the phase-dependent contribution to σ_E. Or state why it does not apply.
- [ ] From the archived jitter samples, count perturbed samples that Pareto-dominate their nominal point, especially for the spread extreme (D = 0.988) and the centroid point (D = 0.9985). Comment on the local convergence of the selected front.
- **Optional 🖥 (author authorization needed):** 50 lattice-jitter trials for each of the two TDR candidates, about 100 runs, evaluated against the TDR profile with Clopper–Pearson bounds.

**Done when:** the robustness claims carry their error-model scope, and the RF-amplitude and dominance points are answered.

### C2-09. Make the supporting evidence identifiable from the manuscript

**Sources:** Reviewer 1 M6 (R2-06); supports Reviewer 2 minor 2 (moving detail to a supplement).

- [ ] Add one concise supplement or software reference (a versioned local package for peer review is enough) in Methods or an appendix. No Data availability section is needed.
- [ ] Map the reported results to the run-level quality and paired summaries, the TDR candidate diagnostics (C2-01), the attribution outputs (C2-02), the representative diagnostics, the prediction summaries, the MOGA-derived reference evaluation (C2-07, if run) and the production settings.
- [ ] Distinguish the production startup code from the revision-analysis code. Identify configuration and CLI overrides and any inputs that are not distributed. State that sampler base draws were not archived.
- [ ] Validate local links and completeness. Publication or deposition is a separate action; this task does not authorize an upload or a push.

**Done when:** a reader with the article and the package can locate the evidence without knowing internal task numbers.

### C2-10. Terminology, length, abstract and submission items

**Sources:** Reviewer 1 minors 1, 2, 4, 6 and 7 (R2-07); Reviewer 2 minors 1, 2, 3, 9 and 10 (Q10–Q13).

- [ ] Use "ideal-distance point" consistently instead of "knee", and explain the centroid-distance naming.
- [ ] Replace "without smoothing the data" with an accurate description of the effective fixed-noise regularization.
- [ ] Harmonize the weighting labels between section 4.4 and Table 6 (e.g. "emittance emphasis" rather than "high brightness").
- [ ] Abstract: qualify "weighted-sum optimization completes campaigns faster" as overhead of the present implementation, or remove it. Add the qualitative profile statement from C2-01.
- [ ] Move the implementation-audit detail to the supplement from C2-09: sampler counts, smoothing constants, the inclusion–exclusion description, Adam-recovery counts, effective likelihood floors and evaluation-interval unions. Keep the unit-smoothing issue and the acceptance definitions in the main text.
- [ ] State each limitation once, in section 6.2. Reduce repeated pooled counts in the Conclusions and centre them on the supported comparisons.
- [ ] Remove the revision-integration comments from `main.tex` and the `revisions/evidence/*.tex` inputs (`% C0x …`, `% Integrate before …`, the campaign-output block), and add PDF title, author and keyword metadata.
- [ ] The two reviewers differ on the table of contents: Reviewer 2 suggests removing it, while Reviewer 1 accepts it for internal review. Decide this together with the target journal.
- [ ] **Author-dependent:** confirm the target journal; supply the funding and acknowledgments; then set `\finaltrue`. Do not invent the funding text or mark it complete while it is deferred.

**Done when:** the terminology and conclusions are consistent, the source is clean, and the remaining author dependencies are explicit.

### C2-11. Responses and validation

**Sources:** Reviewer 1 R2-08; Reviewer 2 Q14.

- [ ] Write `docs/paper/reviews/reviewer1_round2_response.md` and `docs/paper/reviews/reviewer2_round2_response.md`, mapping every major and minor comment to a change, evidence or a reasoned non-adoption. Distinguish narrowed claims from newly supplied validation.
- [ ] In the Reviewer 2 response, explain the C2-07 distinction: the MOGA-derived nominal setting is reused as a reference point, and this does not reverse the round1 decision against MOGA benchmarks.
- [ ] Produce a manuscript diff against `9077875`, separating analysis code from narrative edits, and a changed-file inventory.
- [ ] Check data, table and link consistency, and run focused tests for any changed analysis code. Build the PDF and inspect the affected pages.
- [ ] List the optional simulations that were authorized and run, and those that were not.

**Done when:** every comment of both reviewers has a traceable disposition and the unresolved items remain visible.

---

## Simulations: required versus optional

None of the following is required for acceptance by either reviewer. Each needs explicit author authorization before it is run.

| Run | Size | Task | Requested by |
|---|---|---|---|
| Re-evaluation of the MOGA-derived nominal setting | 1 ASTRA run | C2-07 | MOGA reusability assessment (recommended) |
| Jitter of the MOGA-derived setting | 50 runs | C2-07 | MOGA reusability assessment (optional) |
| Jitter of the two TDR candidates | about 100 runs | C2-08 | Reviewer 2 (optional) |
| Constraint-aware campaign(s) under TDR constraints | 160 runs per seed | C2-01 | Reviewer 2 (optional) |
| Budget-matched Sobol arm | 10 × 160 runs | C2-03 | Reviewer 2 (optional) |
| Inferred-noise GP refit | offline, no ASTRA | C2-05 | Reviewer 2 (optional) |
| Run-level resampling with rebuilt references | offline, no ASTRA | C2-06 | Reviewer 1 (one optional route) |

No new convergence study, MOGA/NSGA-II campaign, corrected-acquisition campaign, RF crest scan or expanded source/alignment jitter campaign is requested in round2.

## Coverage of the source task lists

A mapping records where a request is handled; it does not mean the request is already fulfilled.

| Reviewer 1 task | Consolidated tasks |
|---|---|
| R2-01 | C2-01, C2-08 |
| R2-02 | C2-04 |
| R2-03 | C2-02 |
| R2-04 | C2-06 |
| R2-05 | C2-05 |
| R2-06 | C2-09 |
| R2-07 | C2-10, C2-08 (robustness wording) |
| R2-08 | C2-11 |

| Reviewer 2 task | Consolidated tasks |
|---|---|
| Q1 | C2-01 |
| Q2 | C2-02 |
| Q3 | C2-03 |
| Q4(a) | C2-05 |
| Q4(b) | C2-04 |
| Q5 | C2-08 |
| Q6 | C2-08 |
| Q7 | C2-06 |
| Q8 | C2-02 |
| Q9 | C2-08 (optional run) |
| Q10 | C2-10, C2-01 |
| Q11 | C2-10, C2-09 |
| Q12 | C2-10 |
| Q13 | C2-10 |
| Q14 | C2-11 |

| MOGA assessment recommendation | Consolidated tasks |
|---|---|
| 1. Re-evaluate the MOGA-derived setting once | C2-07 (authorization needed) |
| 2. Report it as a reference point | C2-07 |
| 3. Optional jitter trials | C2-07 (optional) |
| 4. Not a MOGA benchmark | C2-07, C2-11 |
| 5. A real MOGA comparison would be a new campaign | C2-07 (out of scope this round) |

## Suggested sequence

1. **Decisions and documentation:** the origin of the production limits and the title (C2-01), locating the convergence record (C2-04), authorization of any optional runs, and the MOGA-derived wording (C2-07).
2. **Existing-data analysis:** attribution (C2-02), the space-filling reference (C2-03), the predictive interpretation (C2-05), the inference route (C2-06) and the jitter dominance check (C2-08).
3. **Authorized runs, if any:** the MOGA-derived re-evaluation first (one run), then any optional jitter or campaign runs.
4. **Manuscript integration:** C2-01, C2-02, C2-07 and C2-08 text; the supplement map (C2-09); presentation (C2-10).
5. **Responses and validation:** C2-11, last.
