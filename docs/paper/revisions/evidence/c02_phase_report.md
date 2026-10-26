# C02 — Archived phase-domain audit

## Status
Closed by explicit author instruction on 2026-10-26, with the unresolved scientific limitations retained. The author closes C02 with the historical absolute-phase domain retained. No calibrated crest, engineering tolerance or alternative-domain ranking is claimed. Closure is administrative scope disposition, not new validation evidence.

## Reproduction and evidence
Run `/home/cspark/Work/simulation_codes-working/miniforge3/envs/linac-opt/bin/python docs/paper/revisions/evidence/c02_audit.py` from any directory. The script reads all 30 primary campaign configurations, 4,800 evaluation records and their archived pre-execution ASTRA input decks. Derived results are in [c02_phase_audit.json](c02_phase_audit.json); source paths and configuration SHA-256 values are recorded there. It reads one initial-distribution copy per campaign and the selected audit representatives. It does not mutate production files.

All 4,800 decks have `auto_phase=False`; every deck assigns equal phases within ACC1/ACC2 and within ACC3/ACC4. This implements two common controls and a six-variable comparison. It does not establish that the paired phases are independently optimal or correspond to equal off-crest phases.

The authoritative [ASTRA manual, section 4.8](https://www.desy.de/~mpyflo/Astra_manual/Astra-Manual_V3.2.pdf) distinguishes absolute wave phase at tracking start from phase relative to maximum energy gain. The production decks use the former. Their phase origin must not be relabelled as a measured crest. The first particle's initial timestamp, field maps, frequencies and transit through upstream structures matter to physical phase interpretation.

## Verified angular intervals

| Control | Nominal / degree | Lower / degree | Upper / degree | Half-width / degree |
|---|---:|---:|---:|---:|
| Gun | 35.62497684 | 32.062479156 | 39.187474524 | 3.562497684 |
| ACC1/ACC2 | -39.50903029 | -43.459933319 | -35.558127261 | 3.950903029 |
| ACC3/ACC4 | 310.0534192 | 279.04807728 | 341.05876112 | 31.00534192 |

The ACC3/ACC4 nominal is equivalently -49.9465808 degrees modulo 360 degrees; its interval can be written [-80.95192272, -18.94123888] degrees. This is a coordinate re-expression, not an off-crest calibration. Its width is about 7.85 times that of ACC1/ACC2. The bounds originated in percentage offsets of stored nominal coordinates, not a documented engineering tolerance. The manuscript should report the actual angular intervals and acknowledge this origin rather than assert physical invariance.

The JSON lists the six selected representatives' absolute phases and offsets from nominal. Those offsets are explicitly **not** off-crest angles. Representative identity includes run and evaluation identifiers for reproducibility; manuscript tables need not expose explicit seed values.

## Observed ACC3/ACC4 coverage
Eight equal-width bins partition the recorded interval. All observations in the two highest bins, [325.55609016, 341.05876112] degrees, violate the mean-energy band: 259 constraint-aware, 345 unconstrained and 394 scalarized observations. These bins contain no feasible observation. All sampled feasible points therefore lie below this upper-quarter interval. This is a descriptive association in adaptively sampled multivariable histories; it does not identify a causal phase threshold or prove how the algorithms would rank in a restricted search domain. Upstream variables also vary, and the bins were defined post hoc.

## Published phase convention
The earlier JINST study, [section 4.3 and table 6](https://doi.org/10.1088/1748-0221/19/01/P01023), explicitly gives phases relative to maximum energy gain. This is a different convention from the current absolute ASTRA inputs. Its selected controls and trajectory differ from the present nominal and representatives, so its tabulated phases cannot calibrate current off-crest values by subtraction. The prior paper's paired phase variables support continuity of the chosen control architecture; they do not physically justify the present unequal angular widths.

## Evidence needed for stronger future claims
1. Supply the archived nominal/reference phase-scan calibration, or separately plan a physical scan with the full tracking model and fixed upstream conditions. Identify whether the reference maximizes energy or minimizes energy spread and how paired cavities are treated.
2. Justify chosen angular widths in terms of that calibration and accepted beam transport. This is presently absent from the inspected records.
3. If narrower bounds are adopted, define matched reruns before execution. Filtering the current data cannot substitute for new adaptive searches in that domain.

The manuscript-ready [c02_phase.tex](c02_phase.tex) corrects the phase interpretation and reports the verified domain. It does not claim the unresolved scientific justification is complete. These stronger claims are outside the closed revision scope.
