# Reviewer 1 revision tasks — round3

**Source:** [Reviewer 1 round3 report](../reviews/reviewer1_round3_report.md)

**Reviewed revision:** `00190d83b2026b1764af01b1a51bbb0eb10e95d1`.

**Recommendation:** Major revision; not acceptable in its current form.

**Status:** Proposed actions only. No manuscript revision, new simulation or publication action is authorized by this task list.

## Sequence and simulation scope

Execute scope decision **R3-01 first**, then R3-02–R3-05 (independent analyses/documentation), R3-06 and R3-07. Preserve all historical simulations, labels and numerical settings. Use separate derived records for corrected analysis.

| Task | Priority | Deliverable | New ASTRA simulations? |
|---|---|---|---|
| R3-01 | P1 | Align the scientific claim with measured numerical sensitivity | Not for restricted model-benchmark route; conditional for physically resolved claims, separately approved |
| R3-02 | P1 | Correct Sobol and adaptive-sample uncertainty | No; existing ten-run records |
| R3-03 | P1 | Restrict domain and causal interpretations | No; existing diagnostics and control vectors |
| R3-04 | P1 | Bound the scope of the RF-amplitude estimate | No if unsupported extrapolation is removed |
| R3-05 | P1 | Correct the supplement input/dependency inventory | No; local documentation and reproduction checks |
| R3-06 | P2 | Correct dominance, predictive-cause and precision wording | No; optional offline fallback sensitivity |
| R3-07 | P2 | Point-by-point response and final consistency check | No; focused validation |

No new MOGA search, constrained-scalarized arm, crest scan or blanket campaign rerun is part of this list.

## R3-01 — Make numerical resolution part of the central result

**Report:** M1; minor 3.

- [ ] Choose explicitly between a benchmark of the nominal numerical model and a physically resolved injector-optimization comparison; align title/abstract/results/conclusions with that choice.
- [ ] Add a compact table or figure of production, medium/fine and fixed-source step/grid changes for the ten tested settings, including classification changes.
- [ ] State that all 150 checks concern ten selected settings, mostly from constrained searches; stable production feasibility there does not establish stable classification of the primary datasets, baseline rejected points or jittered neighbors.
- [ ] Separate source/particle sensitivity from fixed-source numerical changes. Do not label medium/fine differences as a proven discretization-error bound.
- [ ] For the existing-data route, keep Pareto and algorithm comparisons explicitly within the nominal numerical model and remove physical rank-stability implications.
- [ ] If stronger claims are retained, propose a tolerance-based, method-balanced validation design including relevant rejected/boundary points; identify what it can and cannot establish. Obtain separate approval before new tracking. Full campaign replication is not automatically the first step.

**Done when:** Every numerical-stability statement names its tested population, and no unvalidated physical ranking or engineering certification is inferred. A reporting closure must not be labelled convergence.

## R3-02 — Use the correct independent units for Sobol uncertainty

**Report:** M2.

- [ ] Remove or replace the pooled “exact binomial” interval for 41/1,440 scrambled-Sobol outcomes.
- [ ] Report the ten run-level estimates and their dispersion; if an interval is used, justify its independent-scramble/run-level construction and small-sample limitations.
- [ ] Audit `analyze_revision_space_filling.py` and its outputs for analogous pooled binomial intervals on initial Sobol and adaptive BO points; correct affected derived evidence.
- [ ] Retain paired complete-group analysis for BO-minus-Sobol effects; do not resample individual adaptive evaluations as independent trials.
- [ ] Preserve the executed sequences, 160-point budgets and 144-point post-initialization comparison; update prose/table values consistently.
- [ ] Keep legitimate per-design independent-jitter binomial intervals separate from this correction.

**Done when:** The observed counts remain unchanged and every interval states an appropriate sampling unit. No new simulations.

## R3-03 — Separate observed coverage from domain geometry and causation

**Report:** M3.

- [ ] Replace unsupported “edge of the explored domain” assertions with measured scarcity and small diagnostic margins, or define the term explicitly as a diagnostic boundary rather than a control-space boundary.
- [ ] If control-space location is discussed, use normalized actual controls; include the interior coordinates of candidate A and the near-upper gun phase of B without generalizing to the entire feasible region.
- [ ] Present three TDR campaigns as finite-budget, nominal-resolution observations, not proof of inaccessible acceptance or necessity of extra controls.
- [ ] Describe exclusive violation categories as an accounting decomposition of observed gaps, not causal identification of acquisition terms.
- [ ] Keep comparisons separate: transverse-only contribution dominates against unconstrained MOBO, while energy-involving categories account for the larger share against scalarized BO.
- [ ] Qualify conditioning on energy acceptance as comparing method-selected populations; do not infer an isolated energy-independent mechanism.

**Done when:** Abstract, attribution, TDR discussion and conclusions make the same observational claims. No domain change or new campaign.

## R3-04 — Restrict the RF-amplitude extrapolation

**Report:** M4.

- [ ] Name the reference setting, gain-scaling approximation and assumed correlations used for the 0.28/0.40 MeV RMS estimates.
- [ ] Replace “bounds their effect” with conditional linearized estimation unless a mathematical bound is actually supplied.
- [ ] Remove the inference that a large lower-energy headroom establishes preservation of every representative's full feasibility.
- [ ] Explain or remove the equal-relative-scaling assumption for projected energy spread; it is not established by mean-energy scaling alone.
- [ ] Retain the tracked lattice-only findings as their own evidence, without extending them to omitted amplitude/alignment channels.

**Done when:** Every conclusion is limited to the quantity actually estimated. No new error campaign is needed for this route.

## R3-05 — Make reproduction dependencies accurate

**Report:** M5.

- [ ] Correct the blanket claim that evaluation/configuration/completion ledgers alone regenerate every evidence file.
- [ ] Map S1 items to required raw inputs: GP checkpoints, retained tracking outputs, convergence result/plan/source records, and ledgers as applicable.
- [ ] Distinguish regenerating displayed assets from supplied derived tables, regenerating the underlying analyses, and replaying the original simulations/proposals.
- [ ] Identify the exact local manuscript/analysis snapshot and which inputs accompany the review package versus require a separate author-supplied archive.
- [ ] Test representative local regeneration paths with the claimed input set, or clearly label an inventory-only validation. Do not let a successful map/label checker stand in for an unperformed regeneration test.

**Done when:** A reader can identify the inputs needed for each claimed reproduction level. Local packaging only; no remote upload or push.

## R3-06 — Resolve the remaining interpretation and presentation details

**Report:** Minor 1–4.

- [ ] Replace broad statements that no pipeline “exceeded” or “improved on” the nominal reference with the measured absence of a Pareto-dominating primary observation at nominal resolution; retain genuine single-objective improvements.
- [ ] Label kernel/adaptive-selection explanations of undercoverage as hypotheses. If causal interpretation of noise refits is retained, distinguish fit-fallback cases using existing refit records; otherwise report the sensitivity descriptively.
- [ ] Label Pareto figures and key tables as nominal-resolution outputs and avoid confusing archived precision with physical accuracy.
- [ ] Make the resolution finding visible alongside the optimization interpretation, while moving secondary implementation detail to the identified supplement where useful.
- [ ] Preserve the current one-column review layout, scatter-only Pareto projections, grids and shaded constraint regions.

**Done when:** No unsupported dominance, causal or accuracy claim remains in the edited passages. No new tracking or model architecture study.

## R3-07 — Respond and check the final revision

- [ ] Create `docs/paper/reviews/reviewer1_round3_response.md`, mapping each major/minor comment to changes, evidence or reasoned non-adoption.
- [ ] Distinguish narrower claims from new scientific validation; do not equate task closure with reviewer agreement or journal acceptance.
- [ ] Validate changed analysis values, links and supplement dependencies. Run focused tests only for affected computation.
- [ ] Build the manuscript and inspect the changed tables/figures and their nominal-resolution captions; confirm the abstract remains qualitative.
- [ ] Record remaining scientific limitations and the review baseline; save the next numbered completion summary and commit related files locally under repository rules.

**Done when:** All comments have traceable dispositions, retained claims match evidence, and validation status is honest. No push is included.
