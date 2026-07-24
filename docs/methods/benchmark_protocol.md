# Statistically Rigorous Benchmark Campaign Protocol

## 1. Executive Summary

This document establishes the experimental design, seed pairing rules, statistical aggregation methodology, and baseline algorithms for benchmarking Multi-Objective Bayesian Optimization (MOBO) performance on the 200 MeV electron injector linac.

---

## 2. Benchmark Algorithms & Baselines

The benchmark campaign compares six optimization methods:

1. **Constrained qLogNEHVI**: Primary proposed method (logarithmic noisy expected hypervolume improvement with feasibility constraints).
2. **Unconstrained qLogNEHVI**: MOBO baseline without physical beam constraints.
3. **qLogEHVI**: Exact logarithmic expected hypervolume improvement baseline for deterministic simulations.
4. **Scalarized BO**: Scalarized Bayesian Optimization weight sweep baseline.
5. **MOGA / NSGA-II**: Multi-Objective Genetic Algorithm baseline.
6. **Sobol Quasi-Random Sampling**: Space-filling quasi-random baseline.

---

## 3. Fair-Comparison & Pairing Protocol

Within each random seed ($s \in \{42, 43, \dots, 51\}$), all algorithms adhere to identical experimental conditions:

- **Seed-Paired Initial Sobol Design**: Generated using a deterministic scrambled Sobol sequence (`SobolEngine(dimension=6, scramble=True, seed=s)`). Initial candidates are identical across algorithms for seed $s$.
- **Identical ASTRA Model Files**: Standard `astra.in`, field maps, and particle distribution.
- **Identical Search Bounds**: 6D bounds specified in `configs/publication_200mev.yaml`.
- **Equal Simulation Budget**: Identical total evaluation budget ($N = 40, 100, 200, 400$).
- **Identical Reporting Reference Point**: Fixed $R_{\text{model, norm}} = [-10.0, -10.0, -10.0]$ in normalized model space.
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
