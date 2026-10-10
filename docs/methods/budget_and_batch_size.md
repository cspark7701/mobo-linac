# Number of BO Iterations & Batch Size

## 1. Problem Formulation & Budget Equation

In Bayesian Optimization for accelerator beam dynamics (6 design variables, 3 objectives, 7 constraints), the total evaluation budget is governed by:

$$\text{Total ASTRA Evaluations} = N_{\text{initial}} + \left(N_{\text{iterations}} \times q\right)$$

where:
- $N_{\text{initial}}$ is the initial quasi-random Sobol design (typically $2D$ to $3D$, i.e., $12\text{--}18$ samples in 6D).
- $N_{\text{iterations}}$ is the number of sequential Bayesian active-learning cycles (`num_batches`).
- $q$ is the parallel batch size (`batch_size`), representing candidate points evaluated simultaneously per iteration.

---

## 2. Is It Helpful to Increase the Number of BO Iterations?

**Yes, significantly.**

- **Why 10 Iterations is a Minimal Baseline**:
  With 10 iterations at $q=4$, only 40 candidates are proposed by the acquisition function ($N_{\text{total}} \approx 56$). In a 6-dimensional parameter space with 7 beam quality constraints, the surrogate Gaussian Process (GP) spends the first 4–6 iterations primarily discovering the feasible operational island.
- **Key Benefits of Increasing Iterations**:
  1. **Tighter Pareto Front**: Additional iterations allow `qLogNEHVI` to exploit high-hypervolume regions, pushing the trade-off surface towards fundamental space-charge limits.
  2. **Surrogate Uncertainty Reduction**: Epistemic uncertainty $\sigma(x)$ drops substantially around feasible boundaries, improving the accuracy of constraint boundary modeling.
  3. **Stabilization of Critical Candidate Roles**: Distinct Pareto solutions (such as the balanced knee point, minimum emittance $\varepsilon_{n,x}/\varepsilon_{n,y}$, and minimum energy spread $\sigma_E$) stabilize with higher iteration counts.

---

## 3. What is the Optimal Number of Iterations?

For our 6D linac problem, recommended iteration budgets across research tiers are:

| Tier | BO Iterations ($N_{\text{iter}}$) | Batch Size ($q$) | Initial ($N_{\text{init}}$) | Total Evaluations ($N_{\text{total}}$) | Use Case |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Exploratory / Quick Test** | $10\text{--}15$ | $4$ | $12\text{--}16$ | $50\text{--}75$ | Algorithm debugging, dry runs, quick verification |
| **Standard Production (Recommended)** | **$25\text{--}35$** | **$4$** | **$16$** | **$120\text{--}160$** | **Optimal balance of hypervolume convergence & compute time** |
| **Publication / High-Fidelity Pareto** | $50\text{--}70$ | $4$ | $16\text{--}20$ | $220\text{--}300$ | Dense 3D Pareto front mapping, robust sensitivity analysis |

> [!TIP]
> **Diminishing Returns Threshold**: Beyond $\sim 40\text{--}50$ iterations ($N_{\text{total}} > 200$), the hypervolume indicator typically plateaus ($\Delta \text{HV} < 0.1\%$ per batch). In addition, standard GP exact inference exhibits $\mathcal{O}(N^3)$ computational scaling, making 25–35 iterations the optimal efficiency sweet spot on modern multi-core workstations.

---

## 4. Batch Size ($q$) Trade-Offs

The choice of batch size balances **sample efficiency** (algorithmic intelligence per point) against **wall-clock efficiency** (parallel throughput):

### A. Sample Efficiency ($q=1$ vs. $q > 1$)
- **Strictly Sequential ($q = 1$)**: Algorithmically optimal because every single simulation result immediately updates the GP surrogate before picking the next candidate.
- **Parallel Batches ($q = 4$ or $q = 8$)**: `qLogNEHVI` evaluates joint candidate sets by modeling the joint predictive covariance across all $q$ points simultaneously using Monte Carlo sampling.

### B. Wall-Clock Efficiency (Hardware Utilization)
- If your system has 4–8 CPU cores, running $q=4$ evaluates 4 ASTRA simulations concurrently via `ProcessPoolExecutor`.
- Running 30 iterations at $q=4$ takes roughly the **same wall-clock time** as 30 iterations at $q=1$, but provides **$4\times$ more data** ($120$ vs $30$ points).

### Recommended Batch Size Guidelines
- **$q = 4$ (Standard Recommended)**: Ideal for 4–8 core CPUs. Provides high parallel throughput with minimal information redundancy between batch points.
- **$q = 8$**: Excellent on high-core workstations ($\ge 8$ cores).
- **$q \ge 16$**: Not recommended for a single 6D BO run; candidate points in very large batches tend to cluster or explore low-value marginal regions. (If you have 16+ cores, running 4 independent random seeds with $q=4$ in parallel is far more effective than 1 run with $q=16$).

---

## 5. Recommended Production CLI Commands

### Constrained MOBO (Phase 3 Production)
```bash
mobo-linac run-constrained \
  --config configs/publication_200MeV.yaml \
  --num-initial-samples 16 \
  --n-iterations 30 \
  --batch-size 4 \
  --num-workers 4 \
  --acquisition qLogNEHVI
```

### Scalarized BO Benchmark Comparison
```bash
mobo-linac run-scalarized \
  --config configs/publication_200MeV.yaml \
  --num-initial-samples 16 \
  --n-iterations 30 \
  --batch-size 4 \
  --num-workers 4
```
