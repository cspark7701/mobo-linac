# Task Completion Summary: Task 167

## Summary
After refactor tasks 15–40, the production launcher, its guide and the strategic campaign plan were brought in line with the refactored package. The launcher now uses only CLI commands and the configured scalarized cases. It resolves the ASTRA executable the way the package does, rehearses with the mock evaluator, and records its launch inputs. The guide and plan describe the current behavior and counts.

## Key Changes
- **`scripts/run_full_production.sh`**:
  - Phase 1 runs `run-scalarized-suite --cases …` over the configuration's `scalarized_cases`, replacing the hard-coded case list and `--suite option2`. `--p1-case` is validated against the configured ids.
  - The analysis steps call `mobo-linac compare` and `mobo-linac run-robustness` directly instead of the wrapper scripts. `--quiet` is forwarded to every step.
  - The executable is resolved with the package rule (`simulation.executable` → `$ASTRA_BIN` → `PATH`) during pre-output validation. The launcher no longer exports `ASTRA_BIN`/`GENERATOR_BIN` or requires an unused generator binary.
  - The reference length must match the configured objective count (no fixed "three objectives" assumption).
  - New `--mock-evaluator` option rehearses every step, including resume, without ASTRA.
  - Every non-preview launch writes `logs/launch_<timestamp>.json`: commit and dirty flag, configuration path and SHA-256, executable path and SHA-256, package and Python versions, options and reference.
- **`docs/full_production_guide.md`** was rewritten:
  - The steps table, preview/rehearsal/physical/resume usage and the options table now match the script. The stale defaults (10/4, "90% CPU workers") and the pasted chat transcript were removed.
  - The output layout and run-directory contents match measured outputs. Interpretation limits are stated (mock, lattice-only jitter).
- **`docs/strategic_simulation_campaign_plan.md`**:
  - Freezing now uses the publication installer and the automatic launch, environment and attempt records, with a clean-tree requirement and the executable resolution order.
  - Stage 0 has concrete rehearsal commands (launcher mock run and mock resume, mock benchmark).
  - The pilot is pinned to `--device cpu`. The scalarized cases are configuration-defined, with `seed_offset` seeds (0–400).
  - Verification and robustness share six representative roles, so audit cost is six reruns, not seven.
  - Per-campaign `run.log` and launch records are documented.
- **AGENTS.md**: `gp_checkpoint/` was added to the run-directory contract; it is written alongside `checkpoints/`.
- **Tests**:
  - `tests/test_production_launcher.py` adds coverage for configured case dispatch, `--mock-evaluator` forwarding to all five steps, the CLI subcommand sequence and the launch record.
  - It also covers rejecting an unresolvable executable before any output is created.

## Validation Results
- `tests/test_production_launcher.py`: 9 passed. Docs links and docs sync pass, and ruff is clean.
- End-to-end mock rehearsal of the launcher (balanced case, 4 initial + 1×2): all five steps completed, producing comparison, verification and robustness artifacts.
- Mock resume to 2 iterations: 8 evaluations per run, with phase resume, Phase 1 re-aggregation and a second launch record.
- The plan's mock benchmark and `analyze-benchmark` commands complete.
- No physical ASTRA campaign was run, and nothing was pushed.

## Status
Completed.
