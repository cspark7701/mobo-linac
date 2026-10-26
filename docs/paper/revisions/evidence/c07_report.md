# C07 — Comparison matrix and author scope disposition

## Status
Closed for the author's explicit existing-simulation scope (26 October 2026). The comparison matrix and claim limitations are complete. New constrained-scalarized and Sobol arms are **not performed**, so their original reviewer request is not represented as scientifically fulfilled. No MOGA arm or published-MOGA-setting reevaluation is adopted.

## Author decision
The author chose: “Retain existing simulations; complete offline sensitivity and document non-adoption of new controls.” This governs C06/C07. The new controls would have required matched physical evaluations; offline predictions, a subset of initial Sobol points and the unequal-budget multiweight survey cannot substitute for them.

## Existing matched comparison
c07_comparison_matrix.csv distinguishes the three measured primary methods, the descriptive survey, and the unrun additions. The existing primary arms share the six-variable domain, fixed source, tracking resolution, physical validation, paired 16-point initial designs, 160-evaluation total budgets, eight-point adaptive batches and ten repetitions. C04 verified initialization alignment; C05/C13 document actual implementation, precision, fitting/acquisition settings and devices. Raw seed identities remain in the recorded manifests.

The scalarized arm uses equal weights on the three scale-normalized objectives. It is not representative evidence for every scalarization or a budget-matched multiweight strategy. The survey has five separate 176-evaluation scalarized cases (880 total), independently initialized, compared descriptively with single 176-evaluation MOBO runs. Pooling these cases does not create a 160-evaluation control or a continuous 880-point search.

## Scientific boundaries and non-adoption response
The constrained/unconstrained vector comparison tests the recorded constraint-handling implementation within this problem. The absence of constrained scalarized BO means the comparison cannot establish that vector acquisition is uniquely responsible for gains over an equally constraint-aware scalar strategy. The absence of a full-budget Sobol arm means no BO-over-space-filling efficiency claim is established. Initial Sobol observations alone cannot measure 160-point Sobol performance. C06's normalized feasibility factors are sensitivity probes, not corrected-method physical results.

MOGA/NSGA-II runs, including low-budget controls or re-tracking a published MOGA solution, are excluded by the author's MOBO scope. Prior JINST/JKPS publications remain cited context, not a matched ranking. The response does not presume reviewer acceptance of these decisions.

## Compatibility rule
All retained primary arms preserve the original domain, broad production acceptance profile, source, resolution and budgets. No revised physics/domain/constraint arm is silently paired with these histories by seed label. If a future study changes one of these definitions, it must either rerun every comparator under the same definition or report separate non-paired studies. Acceptance reclassification and fixed-model acquisition sensitivity are labelled post hoc and do not replace actual adaptive searches under changed definitions.
