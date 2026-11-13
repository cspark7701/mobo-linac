# Step 3a — step size and space-charge update test — protocol

**Status: FROZEN at the commit that adds this file together with `rq_specification.json` (2026-11-13).**
- **Author decisions** (2026-11-13): use the recommended options (rotated quasi-random replicates, all 15 settings as the primary sample, eighth step kept), run the pre-freeze probe, then freeze.
- **Not yet authorized:** launching the 120 attempts needs a separate go-ahead.
- **Code:** the runner `scripts/evaluate_convergence_step_test.py` and the analysis `scripts/analyze_convergence_step_test.py` are committed with the freeze.
- **Manuscript and supplement:** not modified.

## Why this study

- **Step 2 result.** The matrix ([rm_protocol.md](rm_protocol.md), README step 2) found no 1 %-adequate half-step point. At 64 cells, going from half to quarter step lowered both emittances by a median 3–3.5 %, at 40k and at 640k particles, and 0 of 15 settings stayed within 1 %.
- **Exploratory follow-up** (`rm_sensitivity_*`, README):
  - The same settings are sensitive to particles, grid and step (Spearman 0.65–0.81 between their changes).
  - The six settings that are infeasible at the reference level (all with a transverse rms size above 1 mm) change more (median 4.9 % against 1.4 %, unadjusted p = 0.012).
  - The step change is not confined to them. The nine feasible settings still drop by a median 2.1–2.4 % (ε_x) and 3.0–3.2 % (ε_y), with 0 of 9 within 1 %.
- **Two candidate mechanisms.** The template reuses the space-charge field for up to `Max_count=10` steps while the beam scales by less than `Max_scale=0.01`. Halving `H_max` therefore also halves the distance between space-charge updates, so the step change can come from either source:
  - the **space-charge update interval**;
  - the **integration step** itself.
- **Why the order matters.** Half and quarter alone cannot give the order of convergence:
  - first order would need about 1/16 step to reach 1 %, roughly 8× the half-step cost;
  - second order would make an eighth step sufficient.

**Questions.** At 64 cells and 160k particles:
1. Is the half → quarter change mainly from the space-charge update interval or from the integration step?
2. What is the observed order of step convergence, and which step (or update setting) brings the remaining change within 1 %?
3. How large is the per-setting change caused only by drawing a new particle sample?

## Sample

- **Settings:** the same 15 settings as step 2. `rm_settings.csv` is reused unchanged and checked by hash, so every comparison is paired with the step 2 records.
- **Not a population sample.** The settings were chosen for coverage, not to represent the 387.
- **Strata:**
  - Results are reported for all 15, and separately for feasible (9) and infeasible (6) at `half_g64_n640k`. Feasibility is constant across all step 2 levels.
  - These strata were chosen after seeing the step 2 results. They are fixed before this study runs.

## Levels (grid 64, 160k particles; 8 per setting, 120 attempts)

| Level | `H_max` / `H_min` | `Max_count` | Source | Purpose |
|---|---|---|---|---|
| `half_mc10` (gate) | 5 / 0.5 mm | 10 | `qr160k.ini` (step 2) | Rerun of `half_g64_n160k`; must reproduce step 2 (rtol 1e-9, atol 1e-12) |
| `half_mc1` | 5 / 0.5 mm | 1 | `qr160k.ini` | space charge updated every step |
| `quarter_mc10` | 2.5 / 0.25 mm | 10 | `qr160k.ini` | step only |
| `quarter_mc1` | 2.5 / 0.25 mm | 1 | `qr160k.ini` | step at full update cadence |
| `eighth_mc10` | 1.25 / 0.125 mm | 10 | `qr160k.ini` | third step point for the order |
| `half_mc10_rot{1,2,3}` | 5 / 0.5 mm | 10 | `qr160k` rotated about z | sample-noise replicates |

- **Other inputs.** Everything else is unchanged from step 2: template, field maps, binary, grid 64 (`nrad = nlong_in = nxf = nyf = nzf = 64`), and `Max_scale=0.01`.
- **Why 160k particles.** From 160k to 640k, the median emittance change was at most 0.1 %, and 8 of 9 feasible settings stayed within 1 % at 64 cells. 640k would cost about 3.3× more per run.

### Pre-freeze checks (done 2026-11-13; not outcomes)

1. **`Max_count` semantics.**
   - **Probe:** 3 cm, 64 cells, 160k, using the step 2 template's default settings rather than a study setting; no physics output is used.
   - **Variants:** `Max_count` 10 and 1 at half step, with the 2D solver and with `z_trans=0.01` to exercise the 3D solver; plus eighth step with `Max_count=10` in 3D.
   - **Parsed:** ASTRA's echoed input shows `MAX_COUNT = 1` and `Z_TRANS = 0.01`.
   - **Effect:** `Max_count=1` changed the 3 cm emittances (by 0.005 % in 2D and 0.02 % in 3D) and raised the CPU time by 18 % (2D) and 24 % (3D). That fits extra space-charge solves, so the fallback to `Max_scale=0` is not needed.
   - **Not used for cost:** the first 3 cm is dominated by emission control (`Zemit`): every variant wrote 2,499 emittance lines, and the eighth step even ran faster than the half step. Eighth-step cost is therefore scaled from step 2, not from this probe.
2. **Rotated sources.**
   - The cathode source is round (`sig_x = sig_y`, both `2DGaussian`), so rotating each ordinary particle's (x, y) and (px, py) about z by a fixed angle gives a new sample with the same distribution and the same quasi-random noise character.
   - **Angles:** 40°, 80° and 160°. The reference particle, the six probe particles and every longitudinal column are unchanged.
   - **Precision:** the files are written with 11 significant digits. The source file stores only 4, so its moments cannot be matched to 1e-12.
   - **Check instead:** each rotated file must differ from the original and keep the rotation invariants to 1e-9 relative: ⟨x² + y²⟩, ⟨px² + py²⟩, ⟨x·px + y·py⟩, ⟨x·py − y·px⟩, total charge, and the z, pz and clock sums. The two correlation invariants are compared on the scale √(⟨r²⟩⟨p²⟩).
   - **Result:** all three files pass. σ_x and σ_y stay within 1e-4 relative of each other, as expected for a round source. Their hashes and invariants are in `rq_specification.json`.
   - Pseudo-random sources were considered and set aside: they are noisier than quasi-random ones, so a noise band from them would be too wide.

## Execution

These steps are the same as step 2:
- **Gate first:** `half_mc10` must reproduce step 2 for all 15 settings. A mismatch blocks the rest of the study.
- **Then the rest:** the remaining runs go longest first, with no retries. Invalid attempts stay in every denominator.
- **Resources:** 22 workers, one thread per process, and a 24 h timeout per attempt.
- **Records:** an append-only checksummed journal, a pending list and a completion record.
- **Freeze:** the runner refuses to start unless the freeze is committed.

Outputs go to `results/convergence_step_test/`. **Disk:** step 2 used about 290 MB per run (47 GB total). The plan allows up to 60 GB, and at least 100 GiB must be free at stage boundaries.

## Endpoints (predeclared at the freeze)

For each setting and emittance, compute the paired relative change between levels at the same source. The pairings are:
- **`half_mc10 → quarter_mc10`:** the step 2 change, at 160k.
- **`quarter_mc10 → eighth_mc10`:** the next halving of the step.
- **`half_mc10 → half_mc1`:** the effect of the update interval alone.
- **`half_mc1 → quarter_mc1`:** the effect of the step at full update cadence.

**Sample-noise band.** Per setting and emittance, the band is twice the standard deviation of the four `half_mc10` sources (the original plus three rotations).

**Primary 1 — mechanism.** Per setting, compute the ratio R = (half_mc1 − half_mc10) / (quarter_mc10 − half_mc10), and take its median over the 15 settings.

| Outcome | Condition |
|---|---|
| Update-interval dominated | median R ≥ 0.7 **and** the median \|half_mc1 → quarter_mc1\| ≤ 1 % for both emittances |
| Step dominated | median R ≤ 0.3 |
| Mixed | otherwise |

Settings where the denominator is below 0.1 % are excluded from R and counted.

**Primary 2 — order and adequacy of the step.**
- **Observed order:** p = log₂(median Δ(half→quarter) / median Δ(quarter→eighth)) per emittance, computed only when both medians have the same sign. Per-setting orders are also reported.
- **Extrapolated remainders:** Richardson-extrapolated values at quarter and eighth step.
- **Adequacy rule.** A step level is 1 %-adequate if, for its next halving, both of the following hold:
  - **systematic:** for both emittances, the median change is within ±1 %, and its 95 % bootstrap interval over settings (2,000 resamples, seed 20261113) lies within ±2 %;
  - **per setting:** at least 80 % of settings (12 of 15) change both emittances by at most max(1 %, that setting's noise band).
- **Which levels can be assessed:** quarter is assessed against eighth. Eighth has no finer level, so it is reported through the extrapolated remainder only.

**Secondary:**
- feasible / infeasible strata, for all of the above;
- σ_E, the diagnostic tolerances from round 6, and feasibility changes;
- Spearman correlation with `eighth_mc10`;
- cost per level.

## Interpretation rules (fixed at the freeze)

| Outcome | Next step proposed (each needs separate authorization) |
|---|---|
| Update-interval dominated | Step 3b at half step with the converging space-charge update setting: grid 64 → 80 → 96, with particles scaled to keep the particles per cell constant |
| Step dominated, quarter adequate | Step 3b at quarter step: the same grid ladder |
| Step dominated, only eighth adequate by extrapolation | Report the cost: about 2.6× half per run. Eighth step is then judged impractical for 387 settings |
| Mixed, or no adequacy | Absolute emittance convergence stays unresolved. Results are reported, and levels are not added after the outcomes are seen |

- **Scope:** the conclusions cover these 15 settings at 64 cells and 160k. Grid convergence at the chosen step is not assessed here (step 2 showed −0.5 to −1 % for 48 → 64).
- **Manuscript:** it changes only by the author's separate decision.

## Budget (planning estimate)

Costs are scaled from step 2 runs at 64 cells and 160k (half step: 1.27 h each under 22-worker load):
- quarter ≈ 1.6× half, as measured at 640k;
- `Max_count=1` ≈ 1.25×, from the probe, allowing up to 2× for the 3D section after 5.25 m.

| Levels | Runs | CPU-h |
|---|---|---|
| `half_mc10` gate + 3 replicates | 60 | ~76 |
| `quarter_mc10` | 15 | ~31 |
| `eighth_mc10` (≈ 2.6–3.3× half) | 15 | ~50–63 |
| `half_mc1`, `quarter_mc1` | 30 | ~63–100 |
| **Total** | **120** | **~220–270 CPU-h, about 11–15 h on 22 workers** |

Disk: up to about 35 GB at about 290 MB per run.
