# C03 — exploratory feasible-front quality and sample efficiency

## Evidence and reproducibility

Run `python scripts/analyze_revision_fronts.py` in the project environment. The script reads the 30 archived stage-04 evaluation files, checks the completed-run markers and 160 ordered unique evaluations per run, and verifies exact equality of all initial design variables, objective values and feasibility labels across each of the ten matched groups. Input SHA-256 digests are in `c03_metadata.json`; derived files are separate from immutable simulation evidence. All 4,800 evaluations are retained in the budget. Original feasibility and the original reporting reference are not modified.

The analysis follows `c03_protocol.md`. All calculations are exploratory/post hoc. The common empirical reference contains 53 unique jointly nondominated feasible objective vectors across all methods and runs. This union differs from the separately pooled per-method fronts (49,27,17): dominance is recomputed across methods. None is an estimate certified to equal the global front. The additive epsilon, IGD+ and HV numbers depend on the stated objective scaling. IGD+ also depends on the empirical reference set and is not reference-free. Attainment probabilities are empirical across the ten runs, not posterior probabilities.

## Terminal results

Numbers below are medians over the ten runs. Full per-run batch histories, interquartile ranges and ranges are in the CSV files.

| Metric | Constraint-aware MOBO | Unconstrained MOBO | Scalarized BO |
|---|---:|---:|---:|
| Additive epsilon, lower preferred | 0.333850 | 0.628000 | 0.614950 |
| IGD+, lower preferred | 0.094214 | 0.282171 | 0.229929 |
| Leave-matched-group-out IGD+ | 0.097612 | 0.285083 | 0.230408 |
| Exploratory HV, nadir +10% span | 45.985846 | 41.812306 | 40.192678 |
| Exploratory HV, nadir +25% span | 68.889609 | 63.460929 | 61.189928 |
| Exploratory HV, nadir +50% span | 121.921519 | 113.930663 | 110.808135 |
| Relaxed-target attainment fraction, delta=0.10 | 0.669811 | 0.311321 | 0.283019 |

The reference points, in (micrometre radian,micrometre radian,MeV), are respectively (7.52699,12.35676,1.445244), (8.201525,13.6494,1.59891) and (9.32575,15.8038,1.85502). They are constructed from the pooled empirical-front nadir and spans and are not physical KLS acceptance limits. The same point is held fixed over each trace and shared by all methods. Their construction is data-dependent, so these results cannot replace the predeclared primary endpoint retrospectively. The original zero-HV endpoint remains unchanged. No points on the pooled empirical reference front fall outside these references; individual-run nondominated points can do so and their counts are retained in the history CSV.

Constraint-aware MOBO has smaller median epsilon and IGD+ and larger median HV at all three references. These are descriptive rankings of the stated indicators, not a claim that one method uniformly dominates every objective. The two baselines reverse relative ordering between IGD+/epsilon and HV. This metric dependence is scientifically relevant and argues against selecting a metric after observing its ranking. Removing each matched group from the IGD+ reference preserves the ordering of method medians, although the resulting targets differ slightly between groups and remain empirical. This sensitivity does not remove all adaptive sampling/reference-set bias.

Within matched groups, median directional coverage from constraint-aware to unconstrained MOBO is 0.464286 and the reverse is 0.155556. Constraint-aware to scalarized coverage is 0.625000 and the reverse is 0.050000. Unconstrained to scalarized coverage is 0.100000 and the reverse is 0.050000. These are medians of within-group fractions, not the fraction dominated in separately pooled sets. Exact duplicate objective vectors are collapsed for these set metrics; all original observations remain archived.

`revision_front_quality.pdf` shows checkpoint medians and nearest-rank interquartile bands versus evaluations for epsilon, IGD+ and the middle HV reference. The initial 16 evaluations are included. Empty fronts score infinity for epsilon/IGD+ and zero for HV; plotting gaps mark nonfinite aggregate scores without dropping empty runs. `revision_attainment.pdf` shows the across-run probability of attaining each empirical-front target after componentwise relaxations of 0.05,0.10,0.25,0.50 normalized units. The relaxation is part of the target definition, not a feasibility change. No smooth or connected objective-space Pareto fronts are introduced.

## Validation

- Three focused metric tests cover dominance/duplicate handling, minimization direction, empty-set conventions, overlapping exact HV and reference clipping.
- Exact three-dimensional slicing agrees with BoTorch Hypervolume to 1e-12 on four independently generated synthetic cases.
- All per-run HV histories are nondecreasing and epsilon/IGD+ histories nonincreasing at recorded batch checkpoints.
- These calculations use archived outcomes only; no ASTRA simulations or changed physical validation were required.

## Integration

Use `c03_results.tex` after the primary-comparison description and include the two supporting figures where suitable. Explain the post-hoc scope and retain the compact original-endpoint disclosure. C04 supplies separate paired effect estimates and multiplicity-controlled tests; this report alone makes no significance claim.
