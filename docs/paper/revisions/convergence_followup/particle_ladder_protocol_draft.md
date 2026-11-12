# Particle-count convergence ladder — protocol draft

**Status: SUPERSEDED, not adopted (2026-11-12).** The author chose the grid × particle matrix ([rm_protocol.md](rm_protocol.md)) instead. Kept as a record of the earlier draft; it authorizes no run.

**Earlier status: DRAFT for author approval, 2026-11-12.** This is a new study after round 6, not a continuation of C6-06. The frozen round 6 protocol ([r6_protocol.md](../evidence/r6_protocol.md)) is unchanged, and its results stand as reported. The protocol becomes binding only when the author approves it and the freeze step below is committed.

## Purpose and scope

Round 6 left the emittances unconverged at the finest tested level. Fine and medium differ by a median 5.5 % (x) and 7.4 % (y), and only 3–7 % of settings meet the 1 % objective tolerance (S1.16). Separating the round 6 factors shows two contributions:

| Change (round 6, one factor at a time) | Median ε_x | Median ε_y |
|---|---|---|
| Step/grid medium → fine, 10k production source | −5.5 % | −7.4 % |
| Particles 10k → 40k at fine step/grid (source also regenerated) | −2.0 % | −2.3 % |

**Question.** At the round 6 fine step and grid, do the objectives and diagnostics converge as the macroparticle count increases?

**Author decision.** Only the particle count varies. Step size and grid stay at the round 6 fine values, and no step or grid halving is part of this study.

**What it can and cannot show.**
- It tests particle-count convergence at one fixed discretization.
- It cannot establish full numerical convergence. The step/grid contribution measured in round 6 stays unresolved.
- The manuscript's statement that the objectives are not converged stays unless the author decides otherwise after the study.

## Sample

- **Population:** the 387 settings of the frozen round 6 sample (`r6_sampling_manifest.csv`, SHA-256 `5f9d8cec…d358`).
- **Cells:** 12, crossing method (3) × production feasibility (2) × boundary class (near / interior), as defined in r6.
- **Allocation:** 5 settings per cell, 60 in total (20 per method). Cell sizes in the 387-setting sample:

| Method | Infeasible, interior | Infeasible, near | Feasible, interior | Feasible, near |
|---|---|---|---|---|
| Constraint-aware | 40 | 40 | 12 | 40 |
| Unconstrained | 40 | 40 | 9 | 40 |
| Scalarized | 40 | 40 | 6 | 40 |

- **Selection:** simple random sampling without replacement within each cell, seed `20261112`, from rows sorted by `setting_id`. Selection uses only manifest fields and no round 6 refinement outcome.
- **Inclusion probability:** the r6 inclusion probability × 5 / (cell size), recorded per setting.
- **Optional purposive set (author decision A):** the 4 settings whose classification flipped in round 6. They were chosen by outcome, so if they are added they are labelled separately and excluded from all sample summaries.

## Levels

| Level | Particles | Source file | Step and grid | Runs |
|---|---|---|---|---|
| P10 | 10,000 | `qr10k.ini` (new) | fine | 60 |
| P20 | 20,000 | `qr20k.ini` (round 6 file, `c6490201…ed65`) | fine | 60 |
| P40 | 40,000 | `qr40k.ini` (round 6 file, `a63673af…1425`) | fine | 60 |
| P80 | 80,000 | `qr80k.ini` (new) | fine | 60 |
| P160 | 160,000 | `qr160k.ini` (new) | fine | 60 |
| P320 | 320,000 | `qr320k.ini` (new) | fine | 60 |

- **Fine step and grid** are the r6 values: `h_max` 0.0025, `h_min` 0.00025, and 64 cells for `nrad`, `nlong_in`, `nxf`, `nyf` and `nzf`.
- **Other inputs:** all other inputs are the production template and field maps, with input hashes as in `r6_specification.json`.
- **Sources:**
  - Every level uses a quasi-random source from ASTRA `generator`, with the round 6 deck (`results/revision_round6/resolution/template/qr40k.gen.in`) and only `IPart` and `FNAME` changed.
  - The production file `pal_photo2.ini` is not a ladder level, so a source-file change does not confound the ladder.
  - The round 6 fixed-fine results (10k production source, same step and grid) are reported alongside P10 as context only.
  - Generated decks, files, hashes and the generator hash are recorded at the freeze.
- **Totals:** 360 attempts in all, including P40 (its rerun is described next). With purposive set A, there are 384.

## Gate and execution

1. **Reproduction gate.**
   - P40 runs first. Each run must reproduce the round 6 combined-fine diagnostics and objectives for the same setting (rtol 1e-9, atol 1e-12), because the source file, step, grid and binary are identical.
   - Any mismatch or invalid run blocks the other levels pending investigation. The failed attempt is kept.
2. **Ladder.**
   - Then P10, P20, P80, P160 and P320 run, scheduled longest-first to shorten the tail.
   - There are no automatic retries or physics changes. Invalid attempts stay in every denominator.
3. **Resources.**
   - Up to 22 evaluation workers, as in r6 amendment 01, with one thread per process.
   - Tracking timeout 24 h per attempt.
   - At least 100 GiB free disk is required at stage boundaries.
4. **Output.** New outputs go only under `results/particle_ladder/`, with an append-only journal, checksums and a completion record. Interrupted attempts are kept and accounted for before any recorded recovery.

## Endpoints and analysis

For each setting s and quantity q, the change across doubling k (N_{k−1} → N_k) is Δ_k(s,q) = q(N_k)/q(N_{k−1}) − 1.

**Primary endpoint.**
- The fraction of the 60 settings whose |Δ| for the last doubling (P160 → P320) is at most 1 % for both ε_x and ε_y.
- This is reported overall and per method, with a binomial 95 % (Wilson) interval.

**Secondary endpoints**, all predeclared:
- **Changes per doubling:** the median and interquartile range of the signed and absolute Δ_k for ε_x, ε_y and σ_E at each doubling.
- **Diagnostic tolerances:** the share of settings within the r6 diagnostic tolerances at each doubling (1 % of each transverse or bunch limit, 0.01 MeV energy, 1e-4 transmission).
- **Convergence rate:** the per-setting ratio of absolute changes in successive doublings. A ratio of √2 is consistent with N^−1/2 statistical error and 2 with N^−1 bias.
  - From the last three levels, a Richardson-type estimate of the N → ∞ value and of the remaining P320 error is made, but only where the changes are monotone. Other settings are reported as "not extrapolable".
- **Feasibility:** classification changes along the ladder, by cell. These are descriptive.

**Reporting rules.**
- **Weighting:** sample summaries are unweighted. With 60 settings no population or method-comparison estimate is made, and the r6 feasible-sampling results are not re-estimated. Inclusion probabilities are recorded for transparency.
- **Interpretation:**
  - "Particle-converged at the fine discretization" applies only to settings meeting the primary criterion.
  - A setting that fails is reported as unresolved. That is not a reason to add levels.
- **No changes after the freeze:** no level, setting or tolerance is added, dropped or changed after outcomes are seen.
- **Single source per level:** each particle count uses one source file. Variation between source files is therefore not estimated separately. The round 2 random-source replicates are context only.

## Budget and timing (planning estimate, not a deadline)

Per-run cost is extrapolated from the round 6 means at fine step and grid, measured under 22-worker load:
- 10k: 2,324 s.
- 40k: 3,468 s.
- The linear fit is T ≈ 1,943 s + 0.0381 s × N.

| Level | Est. s / run | CPU-h (60 runs) |
|---|---|---|
| P10 | 2,324 | 39 |
| P20 | 2,705 | 45 |
| P40 | 3,468 | 58 |
| P80 | 4,990 | 83 |
| P160 | 8,040 | 134 |
| P320 | 14,140 | 236 |
| **Total** | | **≈ 594 CPU-h** |

- **Duration:** about 27 h on 22 workers, plus about 3 h if the P40 gate must finish first. The planning range is 20–45 h. Cost may grow faster than linearly in N, and the timing depends on host load.
- **Disk:** about 15 MB per round 6 fine run, so at most about 25 GB in total. 741 GiB was free on 2026-11-12.
- **Purposive set A** adds about 9.9 CPU-h per setting: about 40 CPU-h, or 2 h on 22 workers, for all four.

## Implementation and freeze (after approval)

1. **Driver.** Add a driver, or a backward-compatible extension of `scripts/evaluate_revision_round6_resolution.py`, that takes a setting manifest and particle levels. Add mock tests for manifest selection, source generation and hashing, the reproduction gate, resumption and journal integrity. Keep the r6 defaults and archives unchanged.
2. **Freeze.** Generate the sample manifest and the source files, then write `pl_specification.json`: seed, cells, settings, inclusion probabilities, levels, source and input hashes, tolerances, workers and timeout. Move this document to `evidence/pl_protocol.md` marked frozen. Commit both before any physical run.
3. **Execution.** Run the gate, then the ladder. Analyze only the predeclared endpoints.
4. **Integration.**
   - The manuscript, the supplement (a new S1 item) and the response notes change only by the author's separate decision.
   - A positive result can support a statement about particle count at the fine discretization only, not about step/grid convergence.

## Decisions for the author before the freeze

- **A.** Add the 4 round 6 flipped settings as a separately labelled purposive set? (Default: no.)
- **B.** Top level 320k (default, about 27 h) or stop at 160k (about 16 h, but the primary endpoint becomes the P80 → P160 doubling).
- **C.** Confirm the 22-worker ceiling and that no other study shares the host during execution.
