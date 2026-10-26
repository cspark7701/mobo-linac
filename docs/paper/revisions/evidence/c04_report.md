# C04 — paired effects, uncertainty and initialization

## Reproducibility and inferential scope

Run `python scripts/analyze_revision_pairs.py` after the C03 analysis. This uses all ten matched groups, resampling complete group identities jointly across methods and endpoints. The twelve-test family and handling of zeros/ties are fixed in `c04_protocol.md`. No evaluation-level resampling or unpaired test is used. The exact signed-rank test conditions on absolute ranks and enumerates every sign assignment; tied magnitudes receive midranks, exact zero differences are excluded, and all-zero differences have p=1. It assumes independent matched groups and sign symmetry of differences under the null. The methods were not randomly relabeled, and ten groups do not establish that assumption empirically.

Paired mean differences have pointwise 95% percentile-bootstrap intervals from 10,000 complete-group resamples. These estimate variation conditional on the archived profile, the chosen scales and the fixed empirical reference; they do not propagate uncertainty from constructing the reference front or post-hoc metric selection. They are not simultaneous intervals. Holm-adjusted probabilities use all twelve comparisons (three method pairs times feasible fraction, epsilon, IGD+ and HV25). Original all-zero HV is not tested. Results remain exploratory despite multiplicity correction.

## Results

Differences below are constraint-aware minus comparator. Negative values favor constraint-aware MOBO for epsilon and IGD+; positive values favor it for feasible fraction and HV25.

| Endpoint | Comparator | Mean difference | Pointwise 95% bootstrap interval | Exact p | Holm p, 12 tests |
|---|---|---:|---|---:|---:|
| Feasible fraction | Unconstrained | 0.248125 | [0.205625,0.292500] | 0.001953 | 0.023438 |
| Feasible fraction | Scalarized | 0.280000 | [0.249375,0.313125] | 0.001953 | 0.023438 |
| Additive epsilon | Unconstrained | -0.326910 | [-0.496491,-0.165402] | 0.009766 | 0.058594 |
| Additive epsilon | Scalarized | -0.320290 | [-0.470194,-0.187697] | 0.001953 | 0.023438 |
| IGD+ | Unconstrained | -0.192338 | [-0.313299,-0.070612] | 0.019531 | 0.097656 |
| IGD+ | Scalarized | -0.155212 | [-0.246015,-0.072938] | 0.005859 | 0.041016 |
| HV25 | Unconstrained | 5.201752 | [3.061748,7.440674] | 0.003906 | 0.031250 |
| HV25 | Scalarized | 7.104015 | [5.132368,9.314836] | 0.001953 | 0.023438 |

The eight rows shown belong to the same twelve-test family as the four baseline-to-baseline comparisons; all twelve rows and full-precision values are in `c04_paired_effects.csv`. For unconstrained minus scalarized BO, adjusted p-values are 0.097656 (feasible fraction), 1.0 (epsilon), 1.0 (IGD+) and 0.966797 (HV25). No baseline-to-baseline comparison passes 0.05 after correction.

Constraint-aware MOBO has a larger feasible fraction than either comparator in every matched group. Its epsilon and IGD+ advantages over unconstrained MOBO do not pass the specified Holm threshold even though their pointwise mean-effect intervals exclude zero. This difference is expected: the bootstrap intervals and exact signed-rank tests answer related but different questions, and the intervals are unadjusted. Do not imply that all objective-quality endpoints establish superiority over unconstrained MOBO. The selected HV reference favors constraint-aware MOBO after correction, but remains post hoc and reference-dependent. Epsilon and IGD+ comparisons with scalarized BO pass the specified corrected threshold.

## Initialization

Five of the ten shared initial designs already contain a feasible evaluation. Shared-initialization counts, first-feasible evaluation and post-initialization fractions are in `c04_initialization.csv`. Exact equality of the initial six-dimensional inputs, objectives and feasibility labels is checked across all three methods by the C03 loader. A first-feasible point within the initial sixteen cannot be attributed to acquisition. Remove the unqualified first-feasible row from the primary manuscript table, or explicitly label it as initialization-inclusive and omit any acquisition advantage claim.

Across all ten groups, median fractions among evaluations 17–160 are 0.451389 (constraint-aware), 0.163194 (unconstrained) and 0.131944 (scalarized). This descriptive post-initialization summary retains groups with initially feasible points; it does not select a favorable subgroup. It introduces no additional significance tests. Pooled coverage and a typical per-run outcome remain different quantities.

## Validation and integration

Two focused tests check exact signed-rank results, sign symmetry, tied ranks, zeros, invalid inputs and known Holm adjustments. Integrate `c04_results.tex` following the C03 analysis, qualify the primary comparison/abstract/conclusion consistently, and remove or qualify the initialization-inclusive first-feasible row. No ASTRA run was needed, and archived data are unchanged.
