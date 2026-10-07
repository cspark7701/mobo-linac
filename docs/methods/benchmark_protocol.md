# Statistically Rigorous Benchmark Campaign Protocol

## 1. Executive Summary

This document establishes the experimental design, seed pairing rules, statistical aggregation methodology, and baseline algorithms for benchmarking Multi-Objective Bayesian Optimization (MOBO) performance on the 200 MeV electron injector linac.

---

## 2. Benchmark Algorithms & Baselines

The benchmark dispatcher currently executes four optimization methods:

1. **Constrained qLogNEHVI**: Primary proposed method (logarithmic noisy expected hypervolume improvement with feasibility constraints).
2. **Unconstrained qLogNEHVI**: MOBO baseline without physical beam constraints.
3. **qLogEHVI**: Exact logarithmic expected hypervolume improvement baseline for deterministic simulations.
4. **Scalarized BO**: Scalarized Bayesian Optimization using the runner's default equal weights and qLogNEI. Use the separate scalarized suite for a weight sweep.

MOGA / NSGA-II and Sobol-only sampling remain planned baselines. Requests for `nsga2` or `sobol` fail before creating output directories because no benchmark executor exists. They are never substituted with MOBO. `--algorithms` accepts the implemented names `constrained_qlognehvi`, `unconstrained_qlognehvi`, `qlogehvi`, and `scalarized_bo`. `--num-workers` is forwarded to each campaign.

---

## 3. Fair-Comparison & Pairing Protocol

Within each random seed ($s \in \{42, 43, \dots, 51\}$), all algorithms adhere to identical experimental conditions:

- **Seed-Paired Initial Sobol Design**: Generated using a deterministic scrambled Sobol sequence (`SobolEngine(dimension=6, scramble=True, seed=s)`). Initial candidates are identical across algorithms for seed $s$.
- **Identical ASTRA Model Files**: Standard `astra.in`, field maps, and particle distribution.
- **Identical Search Bounds**: 6D bounds specified in `configs/publication_200MeV.yaml`.
- **Equal Simulation Budget**: Identical total candidate-evaluation budget ($N = 40, 100, 200, 400$), including initialization and failed evaluations. A smaller final batch consumes any remainder, so requested and effective budgets agree. ASTRA retries remain attempts within a candidate evaluation, not separate budget entries.
- **Identical Reporting Reference Point**: Benchmark metrics use the negative of `BenchmarkConfig.reporting_ref_point`, a positive physical reference in normalized objective space (default `[1.5, 1.5, 1.5]`, model-space `[-1.5, -1.5, -1.5]`). This explicit benchmark setting is distinct from the reporting helper's default `[-10, -10, -10]` and the runner's data-derived acquisition/reporting references. Settings are saved in `benchmark_state.json`; incompatible reporting settings cannot be aggregated together. Archived outputs are not rewritten.
- **Identical Objective Normalization**: Fixed engineering scale factors ($1\ \mu\text{m}\cdot\text{rad}, 1\ \mu\text{m}\cdot\text{rad}, 1\text{ MeV}$).

---

## 4. Statistical Aggregation & Bootstrap Confidence Intervals

1. **Median Hypervolume Trajectory**:
   Hypervolume histories across 10 random seeds are aggregated using element-wise median trajectories:
   $$\text{Median\_HV}(t) = \text{median}_{s=1 \dots S} \{ \text{HV}_s(t) \}$$

2. **95% Bootstrap Confidence Intervals**:
   Uncertainty bands around median trajectories are computed via $B = 1000$ bootstrap resamples across seeds. The 2.5th and 97.5th percentiles of bootstrap medians define the 95% confidence interval $[CI_{\text{lower}}(t), CI_{\text{upper}}(t)]$.

3. **Empirical Attainment Probability**:
   The fraction of seeds attaining hypervolume threshold $V_{\text{target}}$ at step $t$:
   $$P_{\text{attain}}(t) = \frac{1}{S} \sum_{s=1}^S \mathbb{I}(\text{HV}_s(t) \ge V_{\text{target}})$$

---

## 5. Output Hierarchy & Campaign Reproducibility

Campaign outputs are structured under `results/publication_benchmark/`:

```text
results/publication_benchmark/
├── campaign_manifest.csv
├── aggregate_metrics.csv
├── per_seed/
│   ├── constrained_qlognehvi_seed_42/
│   ├── unconstrained_qlognehvi_seed_42/
│   └── ...
├── figures/
└── tables/
    └── benchmark_summary_table.csv
```

Single command regeneration:
```bash
mobo-linac analyze-benchmark --output-dir results/publication_benchmark
```

## 6. Completion and interrupted runs

Each run writes `benchmark_state.json` with its algorithm, seed, evaluation kind (ASTRA or mock), configuration signature, requested/effective budget, evaluation count, reporting scales/reference, and execution status. Completion is recorded atomically after the runner returns the exact budget and metric export succeeds. A completed state is accepted only when candidate IDs are unique and both history and metrics contain the expected number of evaluations. `candidate_history.csv` alone is insufficient evidence of completion.

Incomplete, legacy unmarked, or incompatible outputs are preserved and execution fails with an explicit instruction to choose a new output directory. Automatic checkpoint/journal recovery belongs to the subsequent resume-state tasks. `analyze-benchmark` reads algorithm/seed pairs from the persisted manifest, including custom seeds and budgets, and aggregates only completed runs with consistent reporting settings and evaluation kind. Production execution cannot reuse a completed mock run.
