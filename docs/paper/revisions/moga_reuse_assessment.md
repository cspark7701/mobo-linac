# Reusability of the previous MOGA data — round2

**Date:** 2026-10-27
**Examined (read-only):** `/home/cspark/Work/projects/linac/beam_tracking/`, and the sibling
`/home/cspark/Work/projects/linac/cmkim/` (MOGA code by C. Kim)
**Question:** Can the earlier MOGA results be reused for the MOBO comparison requested in
Reviewer 2's round 1 M7 and round 2 N1, or for the MOGA context in section 6.1?

## Verdict

| What | Reusable? | Why |
|---|---|---|
| MOGA population or Pareto front | **No: does not exist on disk** | The only NSGA-II code (`cmkim/moga/linac_opt_moga.ipynb`) failed on its first evaluation, and no `result.csv` or history file exists anywhere under `~/Work`. |
| A matched MOGA-vs-MOBO efficiency comparison | **No** | No MOGA population is available, and the MOGA problem is defined differently (see below). |
| The MOGA-derived operating setting (`beam_tracking/astra.in`) | **Yes, as one reference point** | It is identical to the `mobo-linac` nominal setting, and the field maps, source file and ASTRA binary are byte-identical. |
| The stored ASTRA output for that setting (`beam_tracking/astra.*.001`) | **No: incomplete** | The run stops at z = 15.727 m, short of the 16.2 m exit plane. A fresh evaluation is needed. |

## Evidence

### 1. There are no MOGA result files
- `beam_tracking/` contains scikit-optimize scalarized-BO runs over nine weightings
  (`data/gp_minimize_result_*.pkl`, `data/optimization_results_*.csv`,
  `results/output_*.pkl`) and early MOBO notebooks (`mobo*.ipynb`, `bo_results*.json`). None
  of them is MOGA output. Keyword matches for "moga" or "genetic" inside the notebooks are
  embedded image data, except for the cells described in section 2.
- `cmkim/moga/linac_opt_moga.ipynb` defines a pymoo NSGA-II run with population 500, 250
  offspring and 300 generations, i.e. about 75,000 evaluations if completed. Its run cell ends
  in `FileNotFoundError: 'linac.Xemit.001'`: it writes `astra.in` but reads `linac.*` outputs.
  It also contains the typo `mmutation=PM(eta=20)`, so the intended mutation operator was
  never applied. Its output, `result.csv`, does not exist.
- A search of `~/Work` for `*moga*`, `*nsga*` and `result.csv` finds only an unrelated project
  (`nkm-injection`, a transport-line study).

### 2. The `mobo-linac` nominal setting is the MOGA-derived setting
- `beam_tracking/linac_optimization-parallel2.ipynb` loads `astra.in` and labels its controls
  "linac input variables from MOGA simulations". It then searches ±50 % around them, which is
  exactly how the present paper's domain was built (round 1 M2).
- `diff -w` of `mobo-linac/astra.in` against `beam_tracking/astra.in` (blank lines ignored)
  shows no differences. The settings are:
  - B_sol 0.1947739 T; G_q1 1.28652859 T/m; G_q2 −2.88668503 T/m;
  - φ_gun 35.62497684°, φ_acc1/2 −39.50903029°, φ_acc3/4 310.0534192°;
  - MaxE 100 / 22.264 / 24.4672 MV/m.
- SHA-256 prefixes are identical for `gun.dat` (`8d90dcfdab0d`), `PAL_SOL_A.dat`
  (`437908a008fc`), `TWS_Sband.dat` (`83268709c363`) and `pal_photo2.ini` (`0084449f4750`)
  across `mobo-linac`, `beam_tracking` and `cmkim/moga`.
- `mobo-linac/bin/astra` and `lume-astra/bin/astra`, the binary the notebooks used, have the
  same SHA-256 (`bf62ae2e…`). `beam_tracking/Astra.exe` is a Windows build and is not
  relevant.

### 3. It is MOGA-derived, not the published MOGA solution
The MOGA code and the published study (Kim et al., JINST 2024) solve a different problem:

| Item | MOGA code | Present study |
|---|---|---|
| Phase bounds | 0–360° for all phases | inherited ±10 % windows |
| Gun peak field | 120 MV/m | 100 MV/m |
| ACC1/2 peak field | 22.0284 MV/m | 22.264 MV/m |
| ACC3/4 peak field | 24.3672 MV/m | 24.4672 MV/m |
| Solenoid, quadrupole bounds | 0.1–0.3 T; 0–10 and −10–0 T/m | ±50 % of nominal |
| Constraints | σ_x,y < 0.2 mm; σ_x′,y′ < 0.2663 mrad; σ_z < 0.9 mm; no particle loss; E ≥ 200 MeV | production profile (1 mm, 1 mrad, 1 mm, T ≥ 0.90, 195–205 MeV) |

The published tracked setting gives (3.9586, 3.9424) µm·rad and 0.333 MeV. The notebook's
rerun of `astra.in` gives (3.4728, 3.2968) µm·rad and 0.39419 MeV at 200.19 MeV. These are
different points. The paper should therefore call it a MOGA-derived reference setting adapted
to the present field amplitudes, not "the published MOGA solution".

### 4. The stored output is incomplete
The deck echoed in `astra.Log.001` matches `astra.in` (ZSTOP = 16.2 m), but the last rows of
`astra.Xemit/Yemit/Zemit.001` are at z = 15.727 m, at 194.02 MeV with no losses. The run
evidently stopped before the exit plane, so these files cannot supply exit-plane diagnostics.
The only complete values are the four printed in the notebook (ε_n,x, ε_n,y, σ_E and E_kin).
The constraint diagnostics (σ_x, σ_y, σ_x′, σ_y′, σ_z, transmission) are missing.

### 5. A first comparison with the archived MOBO data
Using the notebook's objective values (3.4728, 3.2968, 0.39419), **none of the 53 pooled
feasible nondominated primary observations** (`evidence/c03_empirical_reference.csv`)
Pareto-dominates the MOGA-derived setting. Because the pooled set is nondominated, no feasible
primary observation dominates it at all. The present searches started around this setting and
found trade-offs with lower ε_n,x (e.g. the knee at 2.9983 µm·rad), but none improved all three
objectives at once. This is an objective-space comparison only, because the feasibility of the
MOGA-derived setting under either profile is not yet known.

## Recommended use
1. **Re-evaluate the MOGA-derived setting once** with the current pipeline: one ASTRA run of
   `astra.in`, journaled like the production evaluations. This gives full exit-plane
   diagnostics and its feasibility under the production, TDR and NAPAC profiles. It replaces
   the claim that "no primary observation matches the nominal input vector" with a measured
   reference point.
2. **Report it in the results** as a reference marker in the Pareto projections and the
   constraint-space plots. State whether any feasible MOBO or BO point dominates it (currently
   none in objective space) and how far each method's front lies from it, e.g. additive epsilon
   to the reference point.
3. **Optionally add 50 lattice-jitter trials** for this setting, under the same protocol as the
   six representatives, as a baseline for the robustness table.
4. **Do not present it as a MOGA benchmark.** It is a single setting from a differently posed
   optimization (different fields, bounds and constraints). It gives no information about MOGA
   sample efficiency or front coverage.
5. If a real MOGA comparison is wanted later, the NSGA-II code would first need its I/O bug
   and mutation typo fixed, and its problem redefined to match the present domain, fields and
   constraints. That would be a new campaign, not reuse.

## Outcome of the authorized re-evaluation (2026-10-27, task C2-07)
- **Single re-evaluation** (`results/revision_round2/references/moga_nominal/`, production pipeline):
  - reproduced the notebook values exactly: (3.4728, 3.2968) µm·rad, 0.39419 MeV, 200.19 MeV, transmission 1;
  - the stored output that stopped at 15.727 m is now superseded by a complete exit-plane evaluation.
- **Feasibility of the nominal setting:**
  - feasible under the production and NAPAC profiles;
  - fails the TDR optimization requirements only in vertical divergence (0.2690 against 0.2663 mrad).
- **Comparison with the primary runs:** no feasible observation of any primary run dominates the setting. The median additive epsilon to it is 0.039 (constraint-aware), 0.195 (unconstrained) and 0.134 (scalarized). Evidence: `evidence/r2_moga_reference_comparison.csv`.
- **Lattice jitter** (50 trials, common seed 42):
  - all 50 trials are production-feasible, with D = 1.030;
  - 12 of 50 meet the TDR inequalities.
  - Evidence: `evidence/r2_moga_jitter_summary.csv` and `evidence/r2_moga_jitter_trials.csv`.
