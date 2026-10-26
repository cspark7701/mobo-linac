# October 2026 production manuscript

The figures, tables, and primary endpoint summary in this directory use the completed
`results/paper_production/04_primary` through `07_paper_outputs` stages. Raw simulations,
model checkpoints, and full journals remain in the local results tree and are not part
of the paper update. `main.pdf` and LaTeX build products are regenerated locally.

## Evidence and interpretation

- Primary simulation comparison: 30 campaigns, ten paired seeds per algorithm, 160 evaluations
  each; all 4,800 evaluations valid and 1,099 feasible.
- Survey: five scalarized cases and two MOBO campaigns, 176 evaluations each;
  all 1,232 valid and 194 feasible. Fixed seed numbers and the actual run identities
  are retained in the campaign metadata.
- Primary and survey audits: six distinct representatives per audit, all independently
  verified at recorded output precision. All 600 lattice-jitter simulations were valid
  and feasible. Charge, laser-size, and laser-duration jitter were not physically applied.
- Every primary hypervolume is zero against the fixed predeclared reference. The paper
  does not change that reference, assign a signed-rank p-value to all-zero differences,
  or infer a hypervolume ranking. One discussion paragraph retains the original endpoint
  limitation; uninformative hypervolume plots and table rows are omitted from the paper.
  Feasibility and physical trade-offs are presented descriptively.
- `primary_results.json` retains per-seed aggregate endpoints and reproducible percentile
  bootstrap summaries (1,000 resamples with a fixed seed number). Its feasible Pareto sizes count the actual
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

# Final manuscript presentation (run after the generic reproduction/copy steps).
python scripts/prepare_paper_presentation.py
python scripts/compare_pareto_fronts.py --two-d \
  --output-dir results/paper_production/pareto_points_NEW_DIRECTORY \
  --paper-dir docs/paper/figures

python scripts/compare_constraint_spaces.py \
  --output-dir results/paper_production/constraint_spaces_NEW_DIRECTORY \
  --paper-dir docs/paper/figures

latexmk -cd -pdf -interaction=nonstopmode -halt-on-error docs/paper/main.tex
```

Do not edit generated tables to change observations. The main text still requires author
completion of funding and acknowledgments before submission.

## Journal and figure presentation

The manuscript uses the official JINST `jinstpub.sty` package and `JHEP.bst`,
vendored unchanged from the publisher for reproducible builds:
https://jinst.sissa.it/jinst/help/JINST_TeXclass.jsp
The style files retain their upstream licensing headers.

The primary and survey Pareto panels are scatter-only and keep every measured feasible
three-objective nondominated observation. No connecting lines, interpolation, or fitted
curves are drawn. Pooling the ten primary
runs yields 49, 27, and 17 points for constrained MOBO, unconstrained MOBO, and
scalarized BO; the pooled survey yields 14, 6, and 14, with unequal survey budgets.
Point counts alone do not rank physical trade-off quality.

`prepare_paper_presentation.py` draws the beamline component order from `astra.in`
and regenerates audit tables in configured display units without explicit seed
values in captions. It also replaces the generic survey-table caption with the
manuscript convention and removes the uninformative hypervolume rows from that display
only. Run it after the generic reproduction steps above.
`generate_primary_paper_table.py` retains timing and seed data in its JSON evidence
but omits explicit timing from the manuscript table. The manuscript describes only
the observed computational ordering.

## Internal nominal-verification artifacts

The nominal rerun tables and stored-versus-rerun figure remain available as internal
validation evidence and reproduction outputs. They are excluded from the manuscript,
along with the Independent verification subsection. The paper retains the lattice-jitter
robustness analysis and its representative-selection and perturbation methods.

## KLS context and comparison sources

The manuscript identifies this reference injector model with KLS, formerly Korea-4GSR,
and cites the official project overview and the prior injector studies:

- KLS project overview: https://kls.kbsi.re.kr/sub0201
- MOGA design study, JINST (2024): https://doi.org/10.1088/1748-0221/19/01/P01023
- Error analysis, JKPS (2025): https://doi.org/10.1007/s40042-024-01232-2
  (author-institution copy: https://kuacc.korea.ac.kr/bbs/kuacc/993/174430/download.do)

The JINST numerical comparison distinguishes its abstract summary from the tracked setting in
section 4.3 and compares the latter with the present primary knee representative. The JKPS comparison distinguishes
geometric and normalized emittance, different feasibility limits, perturbation channels and
sample sizes. No matched MOGA benchmark or superior robustness under the JKPS error model
is claimed. The abstract is qualitative without numerical values; limitations are discussed
in Discussion. The Data availability statement is removed from the manuscript, while these
local regeneration instructions and the underlying evidence remain available.

The manuscript Pareto panels (Figures 2 and 5) retain scatter-only points and use visible
major grid lines on both axes. Regeneration uses `paper_comparison` in the comparison script.

## Constraint-space plots

Generate all primary runs and survey cases from authoritative campaign histories:

```bash
python scripts/compare_constraint_spaces.py \
  --output-dir results/paper_production/constraint_spaces_NEW_DIRECTORY \
  --paper-dir docs/paper/figures
```

The output contains an individual PNG and PDF page for every campaign, a comparison
PDF for all paired runs and survey weight cases, pooled primary/survey figures,
measured diagnostic CSVs, per-channel pass counts and source/configuration metadata.
Shading indicates the allowed region in the displayed coordinates only. Filled
markers satisfy all constraints; open markers fail at least one. Invalid simulations
remain counted without invented coordinates. All thresholds and scales come from
recorded configurations, and joint feasibility is checked against the recorded flags.
The paper includes the pooled primary and survey panels; the complete companion PDFs
retain every individual case. Figures 2 and 5 remain scatter-only Pareto views.

## Round1 evidence and paired analyses

The consolidated revision list records completion of C01, C03, C04, C05 and C12, plus the specific
author-closed C02 phase-calibration limitation and remaining C09 source-evidence gap. The original
production labels and outputs remain authoritative. New profile filters and quality metrics
are post hoc, with source hashes, protocols and limitations under `revisions/evidence/`.

Run from the repository root using the production Python environment:

```bash
python scripts/analyze_revision_acceptance.py
python docs/paper/revisions/evidence/c02_audit.py
python docs/paper/revisions/evidence/c05_audit.py
python scripts/analyze_revision_fronts.py
python scripts/analyze_revision_pairs.py
python scripts/generate_primary_paper_table.py --benchmark-dir results/paper_production/04_primary/benchmark
latexmk -cd -pdf -interaction=nonstopmode -halt-on-error docs/paper/main.tex
```

C03 must precede C04. The paired analysis checks the C03 source hashes, resamples entire
matched groups and applies Holm correction to one family of twelve comparisons. Its pointwise
bootstrap intervals condition on the empirical reference and are not simultaneous intervals.
The first-feasible table row is omitted because it mixes shared initialization with acquisition.
The underlying first-feasible records are retained in the JSON and initialization audit.

The new appendix contains metric histories and target-attainment heatmaps. Objective-space
Pareto plots remain scatter-only. Manuscript source, compact derived analyses and figures are
versioned; raw simulations, model artifacts and generated LaTeX build products are not added.

C01 now uses the official October 2025 KLS TDR (4GSR-I-DE-TDR-001), Tables 2.1.4.4 and
2.1.4.6. Its optimization limits admit two constraint-aware observations and none from the
baselines; both also meet the separate relative-spread specification. These post-hoc checks
preserve the production labels and do not certify full machine acceptance. Exact source pages,
PDF hash, profile definitions and candidate identities are recorded in the C01 evidence files.
