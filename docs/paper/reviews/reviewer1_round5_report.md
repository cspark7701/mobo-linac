# Reviewer 1 report — round5

**Manuscript:** Multi-objective Bayesian optimization of a 200 MeV injector-linac model derived from the Korea Light Source design

**Date:** 30 October 2026

**Reviewed revision:** `c1e9d21088d1830a2736487533d01993eeaf8472`; 57-page one-column REVTeX review copy.

**Review status:** Internal scientific pre-submission assessment as Reviewer 1. This is not a journal decision.

## Recommendation

**Accept on scientific grounds for the stated nominal-model computational study. No further mandatory scientific revision or new simulations are requested.** The three corrections required in my round4 report have been made, and the required corrections from Reviewer 2 are also present. I do not recommend another revision cycle merely to restate limitations that the manuscript now makes explicit.

The contribution is an application study of specified optimization pipelines, rather than a new acquisition method or a physically converged optimization of the KLS injector. Within that scope, the matched comparison, observed feasible nondominated sets, constraint-specific accounting, numerical-sensitivity evidence and lattice-only robustness assessment form a defensible scientific contribution. The main result is the higher feasible sampling fraction of the recorded constraint-aware pipeline under the computational acceptance profile. The evidence does not establish uniform Pareto superiority, optimal machine settings or a general advantage of all constrained BO formulations.

This recommendation is consistent with my round4 conditional acceptance: the required conditions have now been met. Journal fit and significance remain editorial judgments. The optional editorial suggestions below are not acceptance conditions.

## Review of the responses across rounds 1–4

I assessed the response history as cumulative, with later corrections superseding earlier assertions. In particular, the original absence of a matched Sobol arm and a resolution study was addressed in round2; the resulting evidence exposed nonconvergence rather than confirming the earlier convergence assurance. The author subsequently adopted the nominal-model scope. The round4 responses explicitly correct inaccurate locations and overstatements in earlier responses instead of treating those historical statements as current evidence.

| Concern from the review history | Round5 disposition |
|---|---|
| Fair comparison and missing controls | Resolved for the stated pipelines. Shared initial designs and equal evaluation budgets support paired comparisons; different model counts, acquisition sampling and computational costs are disclosed. The Sobol arm is now included. No efficacy relative to an unrun constrained-scalarized or corrected constraint method is claimed. |
| Pareto quality versus feasible counts | Resolved within the nominal model. Joint three-objective nondominance, pooled versus per-run populations, empirical indicators and conditional uncertainty are distinguished. Cardinality is no longer presented as resolution-independent evidence. |
| Failed original hypervolume endpoint | Transparently retained as a failed endpoint; replacement analyses remain post hoc. No inference that zero hypervolume means no feasible observations is made. |
| Numerical fidelity and acceptance margins | Resolved by the explicitly restricted claim, not by demonstrated convergence. The refinement study and selected population are stated; physical Pareto ranks and micrometre-scale TDR margins are not certified. |
| Physical acceptance and phase domain | Computational constraints are separated from TDR requirements; uncalibrated inherited phase windows remain a limitation. The paper does not infer inaccessible domain geometry from a few observations. |
| Raw-unit constraint smoothing | Actual implementation and unit dependence are disclosed. Frozen-model sensitivity is not represented as validation of a corrected campaign. |
| Statistical inference | Matched groups are the sampling units. Small-sample uncertainty, post-hoc quality indicators, fitted-reference dependence and approximate Sobol uncertainty are explicit. |
| Attribution and surrogate calibration | Baseline-specific violation accounting is distinguished from causal identification. Undercoverage and non-equivalent fallback refits are disclosed; feasibility probabilities are not machine-reliability estimates. |
| Robustness and published KLS studies | Lattice-only trial outcomes are separated from omitted errors and the earlier broader error study. The nominal reference is not treated as a new MOGA benchmark or a global optimum. |
| Reproduction | Inputs and reproduction levels are identified. Representative regeneration is distinguished from complete replay; missing base draws and additional archive requirements are stated. |

These are dispositions against the actual claims of the revised paper. They do not turn missing convergence, crest calibration, broader error studies or additional optimization controls into completed validation.

## Closure of round4 comments

### Reviewer 1 C1 — Scenario sensitivity versus numerical-error bounds: resolved

The abstract now says “persists in the tested diagnostic-shift scenarios.” The primary-comparison section specifies the common transformation applied to every evaluation and method, acknowledges omitted upward changes, and explicitly excludes re-tracking, a per-setting refinement model and a worst-case error bound. The Discussion and Conclusions use scenario language consistently.

The new upward and differential checks requested by Reviewer 2 strengthen the description within the tested transformations. They do not bound arbitrary channel- or setting-dependent refinement errors, and the manuscript says so. Retaining historical `r3_resolution_bounds_*` filenames and metadata is acceptable because the current interpretation is corrected explicitly and the original evidence remains traceable.

### Reviewer 1 C2 — RF-amplitude implication: resolved

The TDR-candidate paragraph identifies the energy-gain estimate as belonging to the MOGA-derived nominal reference, not to tracked amplitude responses of candidates A and B. It now states a conditional risk and infers no additional failure count or probability. The measured lattice-only trial results remain separate. No amplitude simulation is necessary to support this wording.

### Reviewer 1 C3 — Table I units: resolved

The rendered table separates relative changes in percent from absolute energy changes in MeV. Its caption defines signed production-relative changes, the medium denominator for fine-versus-medium differences, absolute magnitudes and source standard deviations. The filled step-only energy cell is identified in the response as a value from existing evidence. The earlier header ambiguity is removed.

### Reviewer 2 required and recommended items

All four required items are addressed: contribution 3 distinguishes the two TDR candidates' refinement outcomes; the Conclusions limit the regeneration claim; the Limitations identify the selected refinement population; and Pareto-set size is grouped with nominal-resolution objective-quality evidence.

The recommended upward and differential analyses are supplied as separate evidence. The comparison with Kim et al. now conditions the emittance differences on resolution, while not claiming an algorithmic explanation for the energy-spread difference. The two appendix fallback statements are reconciled. The alternative abstract wording requested by Reviewer 1 is scientifically preferable to the earlier proposed “bounding shifts” wording. Declining optional moves to appendices is not an unresolved scientific defect; manuscript length remains an editorial consideration.

## Independent checks in this round

- Read the current abstract, scope, methods, inference, affected result/discussion passages and reproduction statements against both round4 responses and the earlier response dispositions. Reviewed the round4 manuscript diff and scenario-analysis implementation.
- Ran `scripts/analyze_revision_shift_scenarios.py --output-dir /tmp/reviewer1_round5_scenarios`. All four outputs, including metadata, match the committed evidence byte for byte.
- The upward scale is 1.012. The nominal post-initialization mean differences are 0.2792 against unconstrained MOBO and 0.3111 against scalarized BO; their ranges over the additional shifts are 0.2458–0.2951 and 0.2799–0.3292.
- The differential case gives means 0.1660 and 0.2111, with minimum group differences 0.0625 and 0.1319; all ten groups are positive. These reproduce the rounded manuscript statements and remain scenario-specific descriptive evidence.
- Ran `tests/test_revision_shift_scenarios.py`: **3 passed**. The test includes a constructed differential case that need not remain positive, so positivity is not imposed by the implementation.
- Ran the supplement manifest checker successfully. This checks package consistency; it is not a new validation of all raw simulations or every reproduction level.
- Confirmed the revised passages in the compiled 57-page PDF and visually inspected Table I on page 8. Its unit blocks and caption are readable.

No ASTRA simulations, GP refits, manuscript edits or full-suite rerun were performed for this review. I did not independently reverify the external literature in this round or repeat the round4 scratch-tree check of the older generators. Prior reported checks are distinguished from the new checks above.

## Optional editorial suggestions

**E1 — Clarify what may be quoted.** The Conclusions say that “absolute emittances should not be quoted without a converged calculation,” although the manuscript appropriately quotes nominal-model emittances with qualifications. Consider “absolute emittances should not be interpreted as numerically converged physical predictions.” The existing scope already prevents a material scientific misreading; this is a wording improvement, not a new convergence requirement.

**E2 — Name the added scenario families precisely.** “Two further post-hoc scenarios” introduces an upward family with nine bunch-length/energy combinations and a differential construction. “Two further post-hoc sensitivity checks” would avoid confusing the number of constructions with the number of transformations. No analysis needs changing.

Neither suggestion requires a new response round. A task list is supplied at the author's request, with optional polish and conditional final checks clearly distinguished from mandatory revision.

## Review snapshot

| File | SHA-256 |
|---|---|
| `docs/paper/main.tex` | `0b19581d07335973601550f031429f4dbf8296d3a87f9b1f91c9dc8a04d93b67` |
| `docs/paper/main.pdf` | `653713ba1dead00c95b8fa59231838f682d36ef59bbe535ea05599c8151954be` |
| `docs/paper/reviews/reviewer1_round4_response.md` | `7b37598b5e18150d472a942a1eeebae6d6d2c5e1d37bbd9bbb912cb34f53701e` |
| `docs/paper/reviews/reviewer2_round4_response.md` | `9cf252ad5f699581eb829e233e2ef772d949bd3974359d4cf87a260a600cb4d9` |
| `docs/paper/revisions/evidence/r4_shift_scenarios_metadata.json` | `7fb40bc649ba7caa184f133bae201fcf5186cc4fdbf3ce464b9a96f6125b2114` |

See the [Reviewer 1 round5 task list](../revisions/reviewer1_round5_revision_tasks.md). **There are no outstanding required scientific tasks from Reviewer 1.**
