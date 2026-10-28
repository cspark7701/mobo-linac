# Consolidated revision tasks — round2

**Reviewers:** Reviewer 1 and Reviewer 2

**Recommendation shared by both:** Major revision. The manuscript reviewed at `9077875` is not acceptable in its present form, but both reviewers describe a route to acceptance that needs **no mandatory new optimization campaigns**.

**Purpose:** A single working queue that merges the two round2 task lists and the MOGA-data reusability assessment. Overlapping requests are merged, each reviewer's specific concerns are kept, and the dispositions are explicit. The individual reviewer documents remain the source records. This document does not itself authorize simulations. **On 2026-10-27 the author authorized all optional runs listed below, with three seeds for the TDR-constrained campaigns.**

## Status (2026-10-28)

| ID | Status | Commit(s) | Remaining |
|---|---|---|---|
| C2-01 | Done (required part) | `26cdea3` | The optional TDR campaigns moved to C2-13 |
| C2-02 | Done | `4aa2795` | — |
| C2-03 | Done (required part) | `1e9bebf` | The optional Sobol arm moved to C2-14 |
| C2-04 | Done by the fallback route (record not found) | `6dddfd4` | Superseded in part by C2-12 if the convergence check is run |
| C2-05 | Done, including the optional refit | `771957d` | — |
| C2-06 | Done, routes (a) and (b) | `0e60cfc` | — |
| C2-07 | Done, including the run and jitter | `7416fb5` | — |
| C2-08 | Done, including the optional jitter runs | `245162b` | — |
| C2-09 | Done | `c7fbbc0` | Rebuild `ledger_manifest.json` after the remaining runs complete |
| C2-10 | Editorial work done; Data availability statement added; **open until the reviewers accept** | `559f460` | Statement of contributions in the Introduction; target journal (PRAB recommended), table of contents, funding and acknowledgments, `\finaltrue` |
| C2-11 | Drafts written, not committed; **open until the reviewers accept** | — | Fill the C2-12/13/14 results and page count; diff and inventory; validation; commit |
| C2-12 | Authorized 2026-10-28; prepared, starts when C2-14 finishes | — | Numerical-resolution check of ten reported settings (about 8 h); analysis and manuscript text |
| C2-13 | Done | see C2-13 | No TDR-feasible setting in 480 evaluations; closest miss 0.4 % |
| C2-14 | New; running | — | 10-seed Sobol arm, expected to finish about 20:30–21:00 on 2026-10-28; analysis and manuscript text |
| C2-15 | New; optional; not started | — | Zenodo deposition; needs the author's go-ahead before any upload |

All work is committed locally only; nothing has been pushed.

**Closure rule for C2-10 and C2-11 (author decision, 2026-10-28):** these two tasks are closed only when both reviewers judge the revised manuscript acceptable. Finishing their checklists does not close them.

**Runs:**
- **TDR-constrained campaigns (C2-13):** complete at 12:05 on 2026-10-28. None of the three campaigns has a TDR-feasible observation.
- **Sobol arm (C2-14):** starts automatically after the TDR stage (`scripts/run_revision_round2_simulations.sh`).
- **Run speed:** an unrelated WarpX job occupies most of the 24 cores, roughly halving simulation throughput.

## Sources

- [Reviewer 1 round2 report](../reviews/reviewer1_round2_report.md) and [its revision tasks](reviewer1_round2_revision_tasks.md) (R2-01 to R2-08).
- [Reviewer 2 round2 report](../reviews/reviewer2_round2_report.md) and [its revision tasks](reviewer2_round2_revision_tasks.md) (Q1 to Q14).
- [MOGA data reusability assessment](moga_reuse_assessment.md) (recommendations 1–5).
- Background: [consolidated round1 tasks](consolidated_round1_revision_tasks.md), [round1 revision overview](round1_revision_overview.md), and the round1 responses in `../reviews/`.

## Ground rules carried into round2

- Keep the production campaigns, provenance, feasibility labels, seeds and acquisition definitions unchanged. New classifications and analyses go in separate derived evidence files, labelled post hoc where applicable.
- **The numerical convergence study is already done** (author confirmation recorded in [Task 00226](../../exec-plans/completed/TASK_00226_withdraw_convergence_review_comment.md) and [Task 00227](../../exec-plans/completed/TASK_00227_record_completed_convergence_study.md); round1 C09). Neither reviewer asks for a new convergence campaign. Round2 only asks for the existing result to be reported, or, if the record cannot be found, for the claims to be restricted. *Outcome (C2-04): no quantitative record was found, so the restricted route was taken.*
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
| C2-12 | P1 | Numerical-resolution (convergence) record for the reported settings | ASTRA refinement runs; manuscript | Authorized 2026-10-28; after C2-14; supersedes the C2-04 fallback |
| C2-13 | P1 | TDR-constrained campaigns (optional run of C2-01) | Authorized ASTRA campaigns; analysis; manuscript | C2-01 |
| C2-14 | P1 | Budget-matched Sobol arm (optional run of C2-03) | Authorized ASTRA runs; analysis; manuscript | C2-03; starts after C2-13 |
| C2-15 | P2 | Data deposition on Zenodo (optional) | Packaging; upload by the author | C2-09, C2-12 to C2-14; author decision before any upload |

---

### C2-01. Make the study target and acceptance population consistent

**Sources:** Reviewer 1 M1 and minor 5 (R2-01); Reviewer 2 N1 and minor 1 (Q1, part of Q10).

- [x] State the origin of the production limits (1 mm, 1 mrad, 1 mm, 195–205 MeV, T ≥ 0.90): an earlier design stage, a deliberately relaxed exploration profile, or a configuration default. If there is no engineering basis, say so. Replace "The TDR does not justify replacing its requirements with the production limits."
- [x] Revise the title so it does not imply a KLS-acceptance design study, e.g. "…of a KLS-derived 200 MeV injector-linac model".
- [x] In the abstract (no numbers), describe the contribution as a matched fixed-model comparison under a specified acceptance profile that is looser than the TDR optimization requirements.
- [x] Replace "all archived observations" with the actual population: the 4,800 **primary** evaluations (648/251/200 production-feasible; 2/0/0 TDR-feasible).
- [x] Add a compact table or appendix entry for the two TDR candidates, from `evidence/c01_tdr_candidates.csv`: stable candidate IDs (no raw seed numbers in the prose), objectives and signed physical margins. Note that they are marginal and come from two different matched runs.
- [x] State that two versus zero is observed coverage, not a demonstrated method ranking under the TDR profile, and that these candidates are not the six jitter representatives.
- [x] Discuss whether the TDR region is reachable with the six fixed-lattice controls, or needs controls held fixed here (RF amplitudes, the matching quadrupoles of the full TDR linac).
- [x] In the conclusions, state what engineering conclusion the TDR check supports, and identify the population and profile in every feasibility and robustness claim.
- **Optional 🖥:** constraint-aware campaigns under the TDR optimization constraints (Reviewer 2). **Moved to C2-13.**

**Done when:** the title, abstract, section 2.2, Discussion and Conclusions consistently describe a method comparison under a stated, relaxed profile on a KLS-derived model, and the TDR candidates can be inspected.

**Done in `26cdea3`:**
- The limits are traced to `docs/physics/constraint_rationale.md`, frozen on 2026-07-24.
- New title, abstract framing and the 4,800-evaluation population wording.
- Table `tab:tdr_candidates` (candidates A and B).
- New subsection `sec:tdr_reach` and revised Conclusions.

### C2-02. Identify the executed acquisition and attribute its feasible-sampling advantage

**Sources:** Reviewer 1 M3 and minor 3 (R2-03); Reviewer 2 N2 and minor 8 (Q2, Q8).

*Method identity (manuscript):*
- [x] Describe the comparison as three specified optimization pipelines that share the physical model, initial designs and simulation budget. They differ in target construction, model count, constraint information and Monte Carlo sample counts, not only in the acquisition formula.
- [x] Keep the raw residual units, effective smoothing scales, unequal posterior sample counts and baseline handling in the Methods. State explicitly that τ_c = 10⁻³ eV makes the energy-band weight an effective step with vanishing gradient, alongside the existing beam-size values.
- [x] Add a short synthesis that separates the empirical three-pipeline result from the frozen-model unit-sensitivity diagnostic. That diagnostic covers q = 1, no pruning and one run; an unchanged top probe does not show that the production q = 8 optimizer is invariant.
- [x] Make no claim of measured efficacy for a normalized or corrected acquisition.

*Attribution (existing data only):*
- [x] For each method and post-initialization batch, classify infeasible evaluations into exclusive categories (energy band only; transverse size or divergence only; bunch length only; combinations) and also report "any violation".
- [x] Divide the paired feasible-fraction gap (constraint-aware minus each baseline) among those categories.
- [x] Per batch and method, report the fraction of evaluations in the upper ACC3/4 quarter (325.5561–341.0588°).
- [x] Report the conditional feasible fraction among evaluations that satisfy the energy band, with paired intervals.
- [x] Add a figure or table and one Results paragraph. If the advantage comes mainly from the energy boundary, say so in the abstract, Discussion and Conclusions. Present the analysis as descriptive attribution, not a prediction for a restricted domain.

**Done when:** the abstract, Methods, Results and Conclusions identify the same executed implementation, and the manuscript states which constraints account for the gain. The script, tests and evidence files are committed (e.g. `evidence/r2_attribution_*`).

**Done in `4aa2795`:**
- The gain is not mainly the energy boundary. Against unconstrained MOBO, 62 % of the gap is transverse-only and 34 % energy-related. Against scalarized BO, 63 % is energy-related and 31 % transverse-only.
- The feasible fraction conditional on the energy band is 0.578, against 0.254 and 0.231.
- New subsection `sec:attribution` and `figures/revision_attribution.pdf`.

### C2-03. Report a space-filling reference from the shared initial designs

**Sources:** Reviewer 2 N3 (Q3). Reviewer 1 does not request a Sobol arm; this task uses existing data only.

- [x] Report the feasible rate of the 160 shared Sobol initial points (5/160 = 3.1 %) with an exact Clopper–Pearson interval. Label it as initialization-only, not a matched arm.
- [x] Using C2-02's breakdown, explain why constraint-blind acquisition already raises feasibility above this rate.
- [x] Keep the statement that no advantage over a full Sobol search is established.
- **Optional 🖥:** a budget-matched Sobol arm. **Moved to C2-14.**

**Done when:** Results reports the reference and its interval, and the Discussion explains the baseline feasibility gain.

**Done in `1e9bebf`:** 5/160 = 3.1 % (exact 95 % interval 1.0–7.1 %). Evidence: `evidence/r2_space_filling_initial.csv`. The Sobol-arm part of the script is in place.

### C2-04. Report the completed numerical-convergence evidence

**Sources:** Reviewer 1 M2 (R2-02); Reviewer 2 N4(b) (Q4b). **The underlying study is already complete; no new convergence calculation is requested.**

- [ ] ~~Locate the existing convergence record~~ *Not found* (search recorded in `evidence/r2_numerical_disposition.md`). The original task: from the previous study of this injector: the particle, mesh and integration settings, the source used, the solver-transition correspondence, and the residual changes in ε_n and σ_E at the adopted settings.
- [ ] *Not possible without the record.* Report these in section 2.1 with a citable source, and compare them with the method differences and the relevant margins. The TDR candidates' margins are about 2.47/8.93 µm in σ_x, 8.16/7.96 µm in σ_z and 0.31/0.14 MeV in lower energy; also compare with the smallest robustness margin.
- [x] Revise the section 6.2 sentence "numerical uncertainty … is therefore unquantified" to agree.
- [x] If the record cannot be located, state that the classifications are results at nominal resolution, and remove any implication of numerically validated engineering settings. Record in the responses which route was taken.
- [x] Do not substitute deterministic repeats, the GP likelihood variance, the physical jitter spread or printed output precision for the tracking-discretization error.

**Done when:** sections 2.1 and 6.2 agree with each other and with the author's confirmation, and the claims match the evidence.

**Done in `6dddfd4`, by the fallback route** (C2-12 can replace it with a measured record):
- Section 2.1 gives the settings correspondence with the previous study and states that no residual is reproduced.
- All values are labelled nominal-resolution results.
- The Limitations, now section 6.3, do not treat small margins as resolved.

### C2-05. Interpret surrogate predictive accuracy

**Sources:** Reviewer 1 M5 (R2-05); Reviewer 2 N4(a) (Q4a).

- [x] Discuss the likely causes of the 79–89 % coverage of nominal 95 % intervals: fixed near-zero noise (η = 10⁻⁶), kernel misspecification and adaptively selected test points. Explain the consequences for the constraint-feasibility weights used in acquisition.
- [x] Explain the whole-trajectory RMSE (about 7.88 and 13.73 µm·rad for the constrained emittance channels): it mixes stages and feasible and infeasible regions. Make clear that it does not invalidate the directly tracked observations.
- [x] Either refrain from claims of accurate local or late-stage prediction, or support them with stage-resolved and feasible/near-front summaries from the existing C11 records (counts and run-level variation).
- [x] Keep the floored and covariance-derived interval conventions distinct. Claim no calibrated machine reliability and no loss discrimination from the constant transmission channel.
- **Optional (offline, no ASTRA; done):** refit the saved training sets with inferred homoscedastic noise and repeat the next-batch coverage check (Reviewer 2). Reviewer 1 does not require refitting.

**Done when:** the predictive limitations and any retained local-accuracy claim are supported at the stated scope.

**Done in `771957d`:**
- Undercoverage is concentrated in the infeasible region: constraint-aware ε_x coverage is 89.9 % for feasible observations and 69.5 % for infeasible ones.
- Inferred noise raises coverage, for example to 83.4/86.6/92.7 % for the objectives, but not to nominal.
- Evidence: `evidence/r2_calibration_*`.

### C2-06. Qualify inference that depends on a shared, data-derived reference

**Sources:** Reviewer 1 M4 (R2-04); Reviewer 2 minor 5 (Q7).

- [x] Separate feasible-fraction inference, which uses no pooled reference and has constraint-aware ahead in all ten groups against each baseline, from the epsilon, IGD+ and HV comparisons, which use a reference estimated from the tested outcomes.
- [x] State that 0.0234 is the smallest Holm-adjusted p-value the design allows: n = 10, exact two-sided p = 2/1024, multiplied by 12. Lead the paired-results paragraph with effect sizes and paired intervals.
- [x] Explain why exact sign enumeration alone does not establish calibration after a shared data-derived transformation. Choose one route:
  - (a) keep the quality effects and reference sensitivities descriptive, and label the quality-test probabilities as exploratory and assumption-dependent; or
  - (b) use a justified offline procedure that rebuilds the references within run-level resampling, stating its estimand and remaining assumptions.
- [x] Keep the unadjusted mean-effect intervals, the signed-rank hypotheses and the Holm-adjusted values distinct. Do not change endpoints to obtain a favourable ranking.

**Done when:** no quality-significance claim is stronger than its inferential construction supports, and the original tables remain preserved.

**Done in `0e60cfc`:**
- Route (a): the quality-indicator p-values are labelled exploratory.
- Route (b): 2,000 resamples with the reference rebuilt each time. Every constraint-aware interval excludes zero.
- Evidence: `evidence/r2_rebuilt_reference_*`.

### C2-07. Reuse the MOGA-derived nominal setting as a reference point

**Sources:** [MOGA reusability assessment](moga_reuse_assessment.md), recommendations 1–5; Reviewer 2 round1 M7 context; the manuscript sections on selected settings and previous KLS studies.

**Findings carried forward:**
- No MOGA population or front exists. The NSGA-II notebook in `cmkim/moga/` failed on its first evaluation and never wrote its results.
- `beam_tracking/astra.in` is the MOGA-derived setting and is identical to `mobo-linac/astra.in`; field maps, source and ASTRA binary are byte-identical.
- It is **not** the published MOGA solution: the MOGA code used a 120 MV/m gun, different gradients, 0–360° phases and TDR-like constraints.
- Its stored ASTRA output stops at 15.727 m, so exit-plane diagnostics are missing.
- None of the 53 pooled feasible nondominated primary observations dominates its notebook objective values (3.4728, 3.2968 µm·rad; 0.39419 MeV).

Tasks:
- [x] **Manuscript wording (no simulation):**
  - State that the nominal setting, and hence the centre of the ±50 % search domain, is a MOGA-derived setting adapted to the present field amplitudes.
  - Distinguish it from the published tracked MOGA point.
  - Correct the related statements in sections 5.7 and 6.1 ("no primary observation exactly matches the nominal input vector"; "reevaluation of its published setting").
- [x] **🖥 Single re-evaluation (author authorization needed):** run `astra.in` once through the current pipeline, journaled like the production evaluations. Record its full exit-plane diagnostics and its feasibility under the production, TDR and NAPAC profiles in a separate evidence file.
- [x] After the re-evaluation: show the setting as a reference marker in the primary Pareto projections and constraint-space plots. Report whether any feasible primary point dominates it, and give each method's additive epsilon to it.
- [x] **Optional 🖥:** run 50 lattice-jitter trials of this setting under the same protocol as the six representatives, as a robustness baseline.
- [x] Do not present it as a MOGA benchmark or use it for any claim about MOGA efficiency or coverage. A real MOGA comparison would be a new campaign (with the NSGA-II code's I/O bug and mutation typo fixed and the problem redefined) and is outside this round.

**Done when:** the manuscript identifies the nominal setting correctly and, if the run is authorized, reports it as a measured reference point with its feasibility status.

**Done in `7416fb5`:**
- The re-evaluation reproduced the notebook values exactly.
- The setting is feasible under the production and NAPAC profiles, and fails the TDR only in σ_y′ (0.2690 against 0.2663 mrad).
- No feasible primary point dominates it.
- Jitter: 50/50 trials production-feasible and 12/50 TDR-feasible.
- The outcome is also recorded in `moga_reuse_assessment.md`.

### C2-08. Refine the robustness interpretation

**Sources:** Reviewer 1 minor 5 (part of R2-01/R2-07); Reviewer 2 minors 4, 6 and 7 (Q5, Q6, Q9).

- [x] State the robustness result as conditional on the simulated lattice-only error model. Success in all samples is not a reliability guarantee.
- [x] Add an analytic RF-amplitude estimate: about 0.2 % amplitude jitter shifts the mean energy by roughly 0.4 MeV at 200 MeV, against the 3.11 MeV lower-energy headroom, plus an estimate of the phase-dependent contribution to σ_E. Or state why it does not apply.
- [x] From the archived jitter samples, count perturbed samples that Pareto-dominate their nominal point, especially for the spread extreme (D = 0.988) and the centroid point (D = 0.9985). Comment on the local convergence of the selected front.
- **Optional 🖥 (authorized; done):** 50 lattice-jitter trials for each of the two TDR candidates, about 100 runs, evaluated against the TDR profile with Clopper–Pearson bounds.

**Done when:** the robustness claims carry their error-model scope, and the RF-amplitude and dominance points are answered.

**Done in `245162b`:**
- RF amplitude: 0.28–0.40 MeV mean-energy shift against 3.11 MeV of headroom.
- Dominance: 14 and 8 of 50 perturbed settings dominate the spread-extreme and centroid-distance nominals.
- TDR candidates under jitter: 36/50 and 44/50 TDR-feasible.

### C2-09. Make the supporting evidence identifiable from the manuscript

**Sources:** Reviewer 1 M6 (R2-06); supports Reviewer 2 minor 2 (moving detail to a supplement).

- [x] Add one concise supplement or software reference (a versioned local package for peer review is enough) in Methods or an appendix. *(Neither reviewer asked for a Data availability section. The author decided on 2026-10-28 to add one anyway; see C2-10.)*
- [x] Map the reported results to the run-level quality and paired summaries, the TDR candidate diagnostics (C2-01), the attribution outputs (C2-02), the representative diagnostics, the prediction summaries, the MOGA-derived reference evaluation (C2-07, if run) and the production settings.
- [x] Distinguish the production startup code from the revision-analysis code. Identify configuration and CLI overrides and any inputs that are not distributed. State that sampler base draws were not archived.
- [x] Validate local links and completeness. Publication or deposition is a separate action; this task does not authorize an upload or a push.

**Done when:** a reader with the article and the package can locate the evidence without knowing internal task numbers.

**Done in `c7fbbc0`:**
- Supplement S1 (`docs/paper/supplement/`): README with items S1.1–S1.15, `evidence_map.csv` and `ledger_manifest.json`.
- Checker: `scripts/build_supplement_manifest.py`.
- Appendix A has a "Supporting package" paragraph.
- To finish: rebuild the manifest and add the C2-12, C2-13 and C2-14 evidence to the map once those runs are analyzed.

### C2-10. Terminology, length, abstract and submission items

**Sources:** Reviewer 1 minors 1, 2, 4, 6 and 7 (R2-07); Reviewer 2 minors 1, 2, 3, 9 and 10 (Q10–Q13).

- [x] Use "ideal-distance point" consistently instead of "knee", and explain the centroid-distance naming.
- [x] Replace "without smoothing the data" with an accurate description of the effective fixed-noise regularization.
- [x] Harmonize the weighting labels between section 4.4 and Table 6 (e.g. "emittance emphasis" rather than "high brightness").
- [x] Abstract: qualify "weighted-sum optimization completes campaigns faster" as overhead of the present implementation, or remove it. Add the qualitative profile statement from C2-01.
- [x] Move the implementation-audit detail to the supplement from C2-09: sampler counts, smoothing constants, the inclusion–exclusion description, Adam-recovery counts, effective likelihood floors and evaluation-interval unions. Keep the unit-smoothing issue and the acceptance definitions in the main text.
- [x] State each limitation once, in section 6.2. Reduce repeated pooled counts in the Conclusions and centre them on the supported comparisons.
- [x] Remove the revision-integration comments from `main.tex` and the `revisions/evidence/*.tex` inputs (`% C0x …`, `% Integrate before …`, the campaign-output block), and add PDF title, author and keyword metadata.
- [ ] The two reviewers differ on the table of contents: Reviewer 2 suggests removing it, while Reviewer 1 accepts it for internal review. Decide this together with the target journal.
- [ ] **Author-dependent:** confirm the target journal; supply the funding and acknowledgments; then set `\finaltrue`. Do not invent the funding text or mark it complete while it is deferred.
  - **Recommendation (2026-10-28):** Physical Review Accelerators and Beams (PRAB), with Nuclear Instruments and Methods A as the fallback. PRAB has no strict length limit and does not use a table of contents, which would settle the table-of-contents item above. Check the chosen journal's current length, data-availability and reference-style requirements before converting the front matter.
- [ ] **State the contributions explicitly in the Introduction.** Referees at PRAB in particular will ask what is new compared with existing accelerator MOBO papers (for example, Roussel et al.'s online-tuning work), so the Introduction should end with an explicit, numbered list of contributions:
  1. a constraint-aware comparison against two baselines (unconstrained MOBO and equal-weight scalarized BO) under matched budgets and shared initial designs, in ten paired runs with failure-inclusive accounting;
  2. the attribution of where the feasibility gain comes from, by violated channel group, conditional on the energy band, and from the upper ACC3/ACC4 phase quarter (C2-02);
  3. the quantified reach of the TDR acceptance region: reclassification of the primary evaluations, the two marginal candidates and their jitter, the MOGA-derived reference, and the TDR-constrained campaigns (C2-01, C2-07, C2-08, C2-13);
  4. the space-filling reference: the shared initial designs and the budget-matched Sobol arm (C2-03, C2-14).

  Each item must point to the section that supports it and must not claim more than that section shows: no unit-invariant or corrected acquisition, no global optimality, no engineering acceptance. Position the items against prior accelerator-MOBO work in the related-work paragraph, and keep the Conclusions consistent with the list. The abstract stays without numbers. Fill items 3 and 4 only after C2-13 and C2-14 are integrated; C2-12 may add a fifth item if it yields a measured resolution record.
- [x] **Add a Data availability statement (author decision, 2026-10-28).** Added as an unnumbered section after the Acknowledgments. It states that the data supporting the findings are available from the corresponding author upon reasonable request: the evaluation ledgers and run records, the complete run directories, the configuration files and the analysis scripts, each identified through Supplement S1. It names no GitHub page and claims no public deposition, DOI or URL. In the Reviewer 1 response (M6), replace "no Data availability section was added" accordingly. If the data are deposited on Zenodo (C2-15), the statement is revised to cite the record.

**Done when:** the terminology and conclusions are consistent, the Introduction states the contributions explicitly and supportably, a Data availability statement is present, the source is clean, and the remaining author dependencies are explicit. **Closed only when the reviewers judge the revised manuscript acceptable.**

**Done in `559f460`:**
- The audit detail moved to a new Appendix A, `app:implementation`. It is identified through S1.7 and not removed from the record.
- The Limitations subsection is now section 6.3, after the new `sec:tdr_reach`.
- **Open, author decisions:** the target journal with the table of contents (PRAB recommended), funding and acknowledgments, and `\finaltrue`.
- **Open, editorial (added 2026-10-28):** the statement of contributions in the Introduction. The Data availability statement is in place.

### C2-11. Responses and validation

**Sources:** Reviewer 1 R2-08; Reviewer 2 Q14.

- [ ] *(Drafted; TDR, Sobol and page-count placeholders remain.)* Write `docs/paper/reviews/reviewer1_round2_response.md` and `docs/paper/reviews/reviewer2_round2_response.md`, mapping every major and minor comment to a change, evidence or a reasoned non-adoption. Distinguish narrowed claims from newly supplied validation.
- [x] *(In the draft.)* In the Reviewer 2 response, explain the C2-07 distinction: the MOGA-derived nominal setting is reused as a reference point, and this does not reverse the round1 decision against MOGA benchmarks.
- [ ] Produce a manuscript diff against `9077875`, separating analysis code from narrative edits, and a changed-file inventory.
- [ ] Check data, table and link consistency, and run focused tests for any changed analysis code. Build the PDF and inspect the affected pages.
- [ ] List the optional simulations that were authorized and run, and those that were not.

**Done when:** every comment of both reviewers has a traceable disposition and the unresolved items remain visible. **Closed only when the reviewers judge the revised manuscript acceptable.**

### C2-12. Measure the numerical resolution of the reported settings

**Sources:** Reviewer 1 M2 (R2-02); Reviewer 2 N4(b) (Q4b); the C2-04 outcome. Neither reviewer requires a new study. The task is author-initiated, because the previous study's convergence record could not be located (`evidence/r2_numerical_disposition.md`) and C2-04 therefore fell back to nominal-resolution wording.

**Status:** authorized by the author on 2026-10-28, to run when the Sobol arm (C2-14) finishes. Prepared in `scripts/evaluate_revision_convergence.py` and stage `convergence` of `scripts/run_revision_round2_simulations.sh`.
- **Source reconstruction.** The production `pal_photo2.ini` is reproduced with ASTRA's `generator`: quasi-random mode, 2D Gaussian with σ = 1.118 mm cut at 1.0 mm, 2.553 ps Gaussian emission cut at 4σ, isotropic 0.6 eV emission, 1 nC. Its time, radius and momentum marginals agree with the file to print precision; only the pairing of coordinates differs. Refined and regenerated sources come from the same input.
- **Plumbing test (scratch only).** A fine-level run over the first 0.3 m confirmed that the source, step and grid overrides reach `astra.in`.

**Settings (10):**
- the MOGA-derived nominal;
- TDR candidates A and B;
- the closest observation of the TDR-constrained campaigns (C2-13), which misses by 0.4 %;
- the six selected constraint-aware representatives.

These are the settings whose margins and objective digits the manuscript reports.

**Resolution levels** (production: 10,000 macroparticles, 32×32 cylindrical grid and 32³ 3D grid, H_max = 0.01, H_min = 0.001):

| Factor | Levels | Relative cost per run |
|---|---|---|
| Source sampling noise | 1 regenerated quasi-random and 5 pseudo-random 10k distributions (`bin/generator`; its random mode is clock-seeded, so each file's SHA-256 is recorded) | 1× each |
| Macroparticles | 20k, 40k | 2×, 4× |
| Space-charge grid | 48, 64 per dimension (cylindrical and 3D) | about 3×, about 6× |
| Integration step | H_max/2, H_max/4 (with H_min scaled alike) | 2×, 4× |
| Combined | medium (20k, 48, H/2); fine (40k, 64, H/4) | about 12×, about 96× |

- [ ] Time the levels. The fine runs are submitted first, so their runtimes replace the assumed cost factors early in the run.
- [ ] Run all 15 levels (the production level, 6 source levels, 6 single-factor levels and 2 combined levels) for the ten settings through the production pipeline: 150 runs with outputs in `results/revision_round2/convergence/`. The production runs stay unchanged. The production-level rerun is checked against each archived value.
- [ ] Report, for each setting, the change in ε_n,x, ε_n,y, σ_E and each constraint diagnostic between the production and the fine levels, and the spread across regenerated sources.
- [ ] Compare these residuals with the method differences, the TDR-candidate margins (about 2.5/8.9 µm in σ_x, 8.2/8.0 µm in σ_z, 0.31/0.14 MeV in energy) and the smallest robustness margin. State whether each TDR or production classification survives refinement.
- [ ] Replace the nominal-resolution wording in section 2.1 and the Limitations (section 6.3) with the measured residuals. Update S1.13 and both responses (M2 and N4(b)).
- [ ] Add the evidence `evidence/r2_convergence_*`. The analysis script `scripts/analyze_revision_convergence.py` and its tests are prepared.

**Estimated runtime:**
- Per setting: about 136 baseline-run units (1 + 6 source + 2 + 4 + 3 + 6 + 2 + 4 single-factor + 12 + 96 combined). At about 145 s per unit unloaded, that is about 5.5 CPU-hours.
- Ten settings: about 55 CPU-hours. The machine is no longer shared with the WarpX job, so the stage uses 16 workers: the ten fine runs start together, and the other 140 runs (about 16 CPU-hours) share the remaining six workers.
- Wall clock: bounded by the fine runs, **about 4–8 h**, depending on how far the fine level departs from the assumed 96× cost.
- Analysis and manuscript work: about 2–3 h.

**Done when:** sections 2.1 and 6.3 report measured residuals at the reported margins, or state that particular classifications are not resolved.

### C2-13. TDR-constrained campaigns (optional run of C2-01)

**Sources:** Reviewer 2 N1 (strongly encouraged, not required). Reviewer 1 does not require it.

**Status:** authorized on 2026-10-27 for three seeds; done.
- Configuration: `configs/revision_tdr_200MeV.yaml`, the production configuration with only the TDR constraints changed.
- Protocol: as in the primary comparison (160 evaluations, 16 shared Sobol points, batch 8).
- Output: `results/revision_round2/tdr_benchmark/`.

- [x] Run seeds 42 and 43 (complete).
- [x] Run seed 44 (complete 2026-10-28, 12:05; recorded labels agree with the TDR mask in 160/160 evaluations of every campaign).
- [x] Run `scripts/analyze_revision_tdr_campaigns.py`. It reports per campaign:
  - TDR, production and NAPAC feasibility counts;
  - the closest observation and its binding constraint;
  - the violated-channel shares;
  - TDR-feasible nondominated points and whether any dominates candidates A/B or the MOGA-derived reference.

  It compares these descriptively with the TDR-reclassified primary runs of the same seeds. With three groups no test is made.
- [x] Update the "Reach of the TDR acceptance region" subsection, the TDR sentences in the abstract (qualitative) and the Conclusions. Add the evidence to S1.4 and the result to both responses.

**Result (`evidence/r2_tdr_campaign_*`):**
- TDR-feasible observations: 0, 0 and 0 of 160. Production-feasible: 58, 52 and 55; NAPAC-feasible: 4, 2 and 1.
- Closest observations: −4.2 % in σ_y′ (seed 42); −0.42 % in σ_x and −0.41 % in σ_y′, about 1.3 µm and 1.1 µrad (seed 43); −3.6 % in σ_x (seed 44).
- The same seeds' primary constraint-aware runs, reclassified: candidate A (seed 44), otherwise −9.4 % and −2.3 % in σ_y′. Targeting the TDR inequalities did not raise TDR coverage at this budget.
- Worst-margin channel after initialization: σ_x in 62 %, σ_y′ in 24 % and σ_y in 14 % of evaluations.
- No point dominates the MOGA-derived reference, which itself misses by −1.0 % in σ_y′.
- The seed-43 closest observation is added to the C2-12 settings, because a 0.4 % miss needs a resolution check before it is called infeasible.

**Runtime:**
- Measured: seed 42 took 9.7 h (it shared the GPU with the C2-05 refit), seed 43 took 4.5 h and seed 44 about 8 h, under the shared-machine load. For comparison, a primary constraint-aware campaign took 3.6 h unloaded.
- Analysis and manuscript work: about 1 h.

**Done when:** the manuscript states whether the method reaches the TDR region within the six-control domain at this budget.

### C2-14. Budget-matched Sobol arm (optional run of C2-03)

**Sources:** Reviewer 2 N3 (strongly encouraged, not required). Reviewer 1 does not request a Sobol arm.

**Status:** authorized on 2026-10-27. It starts automatically after C2-13 (`scripts/run_revision_round2_simulations.sh`, stage `sobol`). Run parameters:
- 10 seeds (42–51), each 160 scrambled-Sobol points with no acquisition;
- `run-unconstrained --num-initial-samples 160 --n-iterations 0`;
- output in `results/revision_round2/sobol/`.

- [ ] Run the 10 campaigns.
- [ ] Run `scripts/analyze_revision_space_filling.py --part sobol`. It verifies that each seed's first 16 points equal the shared initial design, and gives post-initialization feasible fractions, channel shares and paired differences against each pipeline with bootstrap intervals.
- [ ] If feasible, add the front-quality indicators (epsilon and IGD+ against the same empirical reference) for the Sobol arm. Label them post hoc.
- [ ] Update the Results paragraph on the space-filling reference, the scope statement in section 4.2 and the Limitations. Add the evidence to S1.6 and the result to the Reviewer 2 response (N3).

**Estimated runtime:**
- Tracking only, with no surrogate fitting or acquisition. At 160 evaluations with 8 workers:
  - about 0.8 h per seed unloaded (145 s per evaluation), **about 8 h for 10 seeds**;
  - about 2 h per seed under the current load (about 360 s per evaluation), **about 20 h**.
- Expected completion: around the morning of 2026-10-29.
- Analysis and manuscript work: about 2 h.

**Done when:** the paper states, with paired intervals, whether each pipeline raises the feasible fraction above budget-matched space-filling sampling.

### C2-15. Deposit the data on Zenodo (optional)

**Sources:** author decision, 2026-10-28. Neither reviewer requires a public deposition. The Data availability statement (C2-10) currently offers the data on request; a Zenodo record is the alternative if a journal or the author wants public access. No GitHub page is cited.

**Status:** not started. Uploading is an outward-facing action. It needs the author's explicit go-ahead and is done by the author or with the author's Zenodo credentials. Nothing is uploaded automatically.

- [ ] Decide whether to deposit, which journal requirements apply, and the licence (for example CC BY 4.0 for data and the repository's licence for code).
- [ ] Assemble the deposition package after C2-12 to C2-14 are integrated:
  - Supplement S1 (`docs/paper/supplement/`), the evidence files in `docs/paper/revisions/evidence/` and the manuscript's figure sources;
  - the run ledgers listed in `ledger_manifest.json` (`evaluations.csv`, `config.json`, `run_complete.json` for every campaign; about 10 MB) and the production step records;
  - the configurations, field maps, source distribution and the `mobo_linac` 1.0.0 source at the release commit;
  - optionally a compressed archive of the complete run directories (about 46 GB). Check it against Zenodo's per-record size limit, and split it or leave it on request if it does not fit.
- [ ] Verify the package: every file in `ledger_manifest.json` is present with a matching SHA-256, `scripts/build_supplement_manifest.py` passes on the unpacked package, and nothing outside the listed paths, such as credentials, local paths or the other user's data, is included.
- [ ] Prepare the Zenodo metadata: title, author and affiliation, ORCID, description, keywords, related identifiers (the manuscript, once it has a DOI) and version.
- [ ] Reserve or obtain the DOI. Then revise the Data availability statement to cite the record, update the supplement README ("What is and is not distributed"), and keep the "on request" wording only for anything not deposited.

**Estimated effort:** about 2–3 h to assemble and verify the core package, plus upload time for the optional full archive.

**Done when:** a Zenodo record with a DOI holds the verified package and the manuscript cites it, or the author decides to keep the data on request only.

---

## Simulations: required versus optional

None of the following is required for acceptance by either reviewer. The author authorized the first seven on 2026-10-27 and the C2-12 resolution check on 2026-10-28.

| Run | Size | Task | Requested by | Status (2026-10-28) |
|---|---|---|---|---|
| Re-evaluation of the MOGA-derived nominal setting | 1 ASTRA run | C2-07 | MOGA reusability assessment (recommended) | Done (`7416fb5`) |
| Jitter of the MOGA-derived setting | 50 runs | C2-07 | MOGA reusability assessment (optional) | Done (`7416fb5`) |
| Jitter of the two TDR candidates | about 100 runs | C2-08 | Reviewer 2 (optional) | Done (`245162b`) |
| Constraint-aware campaign(s) under TDR constraints | 160 runs per seed | C2-13 | Reviewer 2 (optional) | Done (3 seeds, about 22 h under load); no TDR-feasible setting |
| Budget-matched Sobol arm | 10 × 160 runs | C2-14 | Reviewer 2 (optional) | Authorized; queued after the TDR stage; about 20 h under load (about 8 h unloaded) |
| Numerical-resolution check of 10 reported settings | 150 runs, about 1,360 run units (about 55 CPU-h) | C2-12 | Author-initiated (neither reviewer requires it) | Authorized 2026-10-28; starts after the Sobol arm; about 4–8 h |
| Inferred-noise GP refit | offline, no ASTRA | C2-05 | Reviewer 2 (optional) | Done (`771957d`) |
| Run-level resampling with rebuilt references | offline, no ASTRA | C2-06 | Reviewer 1 (one optional route) | Done (`0e60cfc`) |

All revision runs use the driver `scripts/run_revision_round2_simulations.sh` from commit `bfb0be0`, and their stages are logged in `results/revision_round2/run_record.jsonl`.

Apart from the author-initiated C2-12 check, no new convergence study, MOGA/NSGA-II campaign, corrected-acquisition campaign, RF crest scan or expanded source/alignment jitter campaign is requested in round2.

## Coverage of the source task lists

A mapping records where a request is handled; it does not mean the request is already fulfilled.

| Reviewer 1 task | Consolidated tasks |
|---|---|
| R2-01 | C2-01, C2-08 |
| R2-02 | C2-04, C2-12 |
| R2-03 | C2-02 |
| R2-04 | C2-06 |
| R2-05 | C2-05 |
| R2-06 | C2-09 |
| R2-07 | C2-10, C2-08 (robustness wording) |
| R2-08 | C2-11 |

| Reviewer 2 task | Consolidated tasks |
|---|---|
| Q1 | C2-01, C2-13 |
| Q2 | C2-02 |
| Q3 | C2-03, C2-14 |
| Q4(a) | C2-05 |
| Q4(b) | C2-04, C2-12 |
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
5. **Further runs and their integration:** C2-13, then C2-14, which is queued behind it. C2-12 starts when C2-14 finishes (author decision, 2026-10-28), and the manuscript and this list are updated after it.
6. **Responses and validation:** C2-11, last. C2-10 and C2-11 close only when the reviewers accept the revised manuscript.
