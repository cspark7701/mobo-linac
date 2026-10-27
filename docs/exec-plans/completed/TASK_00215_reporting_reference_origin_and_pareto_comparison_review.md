# Task Completion Summary: Task 209

## Summary
Traced the origin and role of the fixed reporting reference after the user clarified that the objective is to discover and compare the three algorithms' Pareto fronts. Pareto extraction itself needs no reference point; the selected hypervolume metric and EHVI-family acquisition functions do.

## Provenance Findings
- Commit `14d3b00` (2026-08-06, Paired Multi-Seed Benchmark Campaigns) introduced `BenchmarkConfig.reporting_ref_point` with the generic normalized default `[1.5, 1.5, 1.5]`; Task 49 documents that addition.
- The current configuration resolver still supplies `1.5` per objective when no explicit benchmark reference is provided. With reporting scales `[1e-6, 1e-6, 1e6]`, these become 1.5 micrometre-rad, 1.5 micrometre-rad, and 1.5 MeV for the current problem.
- The strategic production plan explicitly carried those physical values into the common reporting protocol in commit `41fe16a` (2026-10-09), and Task 139 records the launcher reference plumbing. The production metadata confirms those values were actually used.
- No documented experimental measurement, accelerator-physics derivation, or independent pilot-based justification for those particular values was found in the inspected source/history. They are not a BoTorch-required numerical choice or a physical feasibility constraint. The configured emittance design targets are 3.9236 micrometre-rad, separately used for target-distance reporting.

## Role and Impact
- **Pareto front:** uses nondominance among measured feasible objective vectors. A fixed reporting reference is unnecessary, and the stored feasible Pareto candidates remain available.
- **Hypervolume reporting:** needs a common reference to bound the volume. Here the reference emittances are better than the observed fronts, making the scalar endpoint zero and uninformative. The reference must not be mistaken for an emittance constraint or a universal definition of an acceptable beam.
- **MOBO acquisition:** the actual strategy independently recomputes a model-space reference from observed values and a five-percent offset each iteration. For constrained primary seed 42, the first logged reference was `[-6.362464e-5, -1.02806315e-4, -3.236386e6]` and the final was `[-7.758641e-5, -1.7883212e-4, -4.1339005e6]`; neither is the frozen reporting reference. The zero reporting metric therefore does not establish that candidate discovery failed or that the search was limited to the 1.5 emittance region.
- Carrying an unsupported default into the primary comparison, and not correcting the comparison plan when the pilot already exposed zero hypervolume, was an analysis/setup mistake. The numerical reference should have been justified and checked for an informative common comparison region before recommending the full benchmark as a primary hypervolume experiment.

## Appropriate Follow-up
Preserve the archived reporting protocol and zero values. Reassess empirical feasible fronts directly, including objective trade-offs, coverage/diversity, seed variability, and the pooled nondominated union as an empirical reference set rather than a certified global optimum. A clearly labeled supplementary hypervolume analysis can use one scientifically justified common reference for every algorithm and seed. Existing saved evaluations are sufficient for that reanalysis; changing only the reporting metric does not require ASTRA reruns. A new confirmatory claim with a newly selected primary reference requires a separately declared protocol.

## Validation Results
Inspected Git history, Task 49/125/139/176 records, the current benchmark resolver, production plan/metadata, objective targets, nondominance extraction, and actual proposal histories. Consulted the official [BoTorch reference inference implementation](https://botorch.readthedocs.io/en/stable/_modules/botorch/utils/multi_objective/hypervolume.html), which derives references from the nadir/range rather than prescribing 1.5 for accelerator objectives. No simulation, configuration, scientific endpoint, archive, or manuscript was changed. No application tests were needed for this provenance review; checked staged whitespace before the standing automatic local commit.

## Status
Completed. The unjustified reporting-reference choice is documented separately from the usable Pareto candidates and independently adaptive acquisition references. No replacement reference or new comparison was silently applied.
