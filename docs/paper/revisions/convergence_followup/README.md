# Emittance-convergence follow-up (after round 6)

This folder holds a follow-up to round 6, made at the author's request on 2026-11-12. It is not part of the round 6 package or the supplement. The manuscript and supplement are unchanged until the author decides to integrate any of it.

| File | Content |
|---|---|
| `rs_rank_stability.csv`, `rs_rank_summary.json` | Step 1: rank stability of the round 6 re-tracked objectives (from `scripts/analyze_rank_stability.py`) |
| `rm_protocol.md`, `rm_specification.json`, `rm_settings.csv` | Step 2: grid × particle matrix protocol and its frozen inputs (added at the freeze) |
| `particle_ladder_protocol_draft.md` | Superseded particle-only draft, not adopted |

## Step 1 — rank stability from the existing round 6 runs

**Data.** 387 settings at five levels (`results/revision_round6/resolution`), checked against the journal checksums and the completion record. No simulation was run. The summaries are unweighted descriptions of the sample, with 95 % cluster-bootstrap intervals over the ten matched groups (2,000 resamples).

| Levels | Quantity | Spearman [95 %] | Pairs in same order | Same order, pairs >5 % apart | Same order, same campaign | Median shift |
|---|---|---|---|---|---|---|
| fixed medium → fixed fine | ε_x | 0.993 [0.990, 0.995] | 97.0 % | 98.1 % | 97.3 % | −5.5 % |
| | ε_y | 0.989 [0.985, 0.992] | 96.2 % | 97.6 % | 96.5 % | −7.4 % |
| production → combined fine | ε_x | 0.979 [0.969, 0.985] | 94.1 % | 95.6 % | 94.7 % | −22.9 % |
| | ε_y | 0.962 [0.950, 0.972] | 92.0 % | 93.6 % | 92.4 % | −30.6 % |
| | σ_E | 1.000 [1.000, 1.000] | 99.5 % | 100 % | 99.4 % | −0.9 % |
| fixed fine → combined fine (10k → 40k) | ε_x | 0.999 | 98.9 % | 99.7 % | 99.1 % | −2.0 % |
| | ε_y | 0.999 | 98.7 % | 99.8 % | 98.8 % | −2.3 % |

The per-method correlations for production → combined fine are close to one another: Spearman 0.973–0.978 for ε_x and 0.954–0.964 for ε_y.

**Reading.**
- **Settings mostly keep their order.** The production emittances are 23–31 % higher than at the finest level, but the shift mostly preserves the order of settings.
- **Some pairs still swap.** Between production and the finest level, 6–8 % of all setting pairs, and 4–6 % of pairs more than 5 % apart, change order (ε_y more than ε_x). The correlation also varies by setting, so the shift is not a single common factor.
- **Energy spread** is effectively resolution-independent.
- **What this supports:** an argument that the optimizer's ordering, and hence the method comparison, depends only weakly on resolution. It does not support converged absolute emittances, and it says nothing about Pareto fronts beyond the sampled settings.
