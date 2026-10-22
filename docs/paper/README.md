# October 2026 production manuscript

The figures, tables, and primary endpoint summary in this directory use the completed
`results/paper_production/04_primary` through `07_paper_outputs` stages. Raw simulations,
model checkpoints, and full journals remain in the local results tree and are not part
of the paper update. `main.pdf` and LaTeX build products are regenerated locally.

## Evidence and interpretation

- Primary experiment: 30 campaigns, ten paired seeds per algorithm, 160 evaluations
  each; all 4,800 evaluations valid and 1,099 feasible.
- Survey: five scalarized cases and two MOBO campaigns, 176 evaluations each;
  all 1,232 valid and 194 feasible. The scalarized suite uses case seeds
  42, 142, 242, 342, and 442; both MOBO survey runs use seed 42.
- Primary and survey audits: six distinct representatives per audit, all independently
  verified at recorded output precision. All 600 lattice-jitter simulations were valid
  and feasible. Charge, laser-size, and laser-duration jitter were not physically applied.
- Every primary hypervolume is zero against the fixed predeclared reference. The paper
  does not change that reference, assign a signed-rank p-value to all-zero differences,
  or infer a hypervolume ranking. Feasibility results are descriptive secondary endpoints.
- `primary_results.json` retains per-seed aggregate endpoints and reproducible percentile
  bootstrap summaries (1,000 resamples, seed 42). Its feasible Pareto sizes count the actual
  feasible nondominated observations; historical hypervolume-history counts only include
  points that dominate the reference and are zero here.
- `benchmark_summary_table.csv` is the unchanged stage-07 copy of the primary summary.
  Its mean reference-dominating Pareto count is distinct from the actual feasible Pareto
  cardinality reported in `primary_results_table.tex`. No archived result was rewritten.

The final review independently validated all 55 inventoried run-completion records,
1,850 attempt audits, and 16,650 retained output hashes with no issues. That inventory
includes preflight/pilot/screening provenance; those runs do not enter the primary
comparison or the survey endpoints. Detailed validation records remain under
`results/paper_production/monitor/`.

## Regeneration

Activate `linac-opt` and run from the repository root:

```bash
python scripts/generate_primary_paper_table.py \
  --benchmark-dir results/paper_production/04_primary/benchmark \
  --output-dir docs/paper

bash scripts/reproduce_paper.sh \
  --phase1-dir results/paper_production/05_operating_points/campaign/phase1_scalarized \
  --phase2-dir results/paper_production/05_operating_points/campaign/phase2_unconstrained \
  --phase3-dir results/paper_production/05_operating_points/campaign/phase3_constrained \
  --verification-csv results/paper_production/05_operating_points/campaign/analysis/verification/verification_summary.csv

cp results/paper_production/07_paper_outputs/figures/benchmark_*.pdf docs/paper/figures/
cp results/paper_production/07_paper_outputs/tables/{audit_verification_table,robustness_table}.tex docs/paper/
cp results/paper_production/07_paper_outputs/tables/benchmark_summary_table.csv docs/paper/

latexmk -cd -pdf -interaction=nonstopmode -halt-on-error docs/paper/main.tex
```

Do not edit generated tables to change observations. The main text still requires author
completion of public archive identifiers, funding, and acknowledgments before submission.
