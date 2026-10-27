# Task Completion Summary: Task 166

## Summary
Implemented TASK_40 from `docs/05_refactor_tasks/`. The tracked `legacy/` tree and regenerable build clutter were removed. AGENTS.md and README now state the repository's actual facts. Overlapping guides have one home each with a documentation map, the web portal has one sync script, maintainer tooling lives in `tools/`, and a test keeps every relative documentation link valid.

## Key Changes
- **Tree hygiene**:
  - `legacy/` (nine pre-package files, not imported) was removed from the tree; git history keeps it.
  - The regenerable `build/`, `src/mobo_linac.egg-info/`, root `__pycache__/` and the empty `data/` and `mobo_results/` were removed.
  - `.gitignore` now names `backups/`, `/data/` and `/mobo_results/`. `tools/README.md` states that repository backups belong outside the tree.
- **AGENTS.md**: the duplicated GP-surrogate and Dask/multi-node bullets were removed. The Output Directory section describes the real run contract: configuration and source records, reporting metadata, journal, CSV exports, `checkpoints/`, `provenance/`, figures, `run.log` and `run_complete.json`. `tools/` was added to the tree.
- **README**:
  - The test count and the stale task-collection description were replaced by facts (04: Tasks 01–23, 05: Tasks 01–40, local and unversioned).
  - The "Phase 2 penalties" claim was corrected: unconstrained MOBO records and reports feasibility but adds no penalty.
  - The configuration list includes the perturbation specification, and `scripts/` and `tools/` are described.
  - The Python floor (3.10+) dates from TASK_37/38.
- **Guides consolidated**: `docs/README.md` maps each topic to one home.
  - `number_of_bo_iterations_and_batch_size.md` moved to `methods/budget_and_batch_size.md`.
  - `repo_review.md` moved to `architecture/`, with its links repaired and stale targets (`cli.py`, `visualizations.py`, `compute_file_sha256`) updated.
  - `architecture/current_state.md` is marked as the historical baseline.
- **One web portal source**: `docs/index.html` and `docs/style.css` are the source and `docs/site/` is the generated bundle. `tools/sync_site.py` (refresh plus optional `--target-repo` deploy) is the single sync script; `scripts/sync_site.sh` was removed and `docs/site/README.md` updated.
- **Maintainer tooling** moved to `tools/`: `check_github_actions.sh`, `cleanup.sh`, `sync_site.py` and `resume_agy_session.sh`. The local CI check now mirrors the workflow: version against the distribution metadata instead of a literal, and a ruff step. CI lint covers `tools/`.
- **Refactor-plan folders**: these stay local and unversioned (an existing deliberate ignore rule). The relative links in `docs/05_refactor_tasks/TASK_01`–`TASK_14` were fixed (`../src` → `../../src`), and links to files removed by TASK_27/37/38/39 became plain text.
- **Link checker**: `tests/test_docs_links.py` checks every relative link in README, AGENTS, INSTALL, REPRODUCIBILITY, CHANGELOG, `tools/README.md` and the versioned `docs/` Markdown. It also asserts that `legacy/` and the duplicate sync script are gone.

## Acceptance Criteria
- [x] The link checker over `docs/`, README and AGENTS.md reports no broken relative links. This includes the local refactor-plan folders when present.
- [x] No tracked file remains under `legacy/`. `git status --ignored` shows no build directories in the root.
  - Exception: `backups/` (24 MB of untracked full-repository copies). It is ignored but deliberately not deleted, because removal is irreversible user data; move it outside the repository.
- [x] README facts (Python version, test description, task collections, constraint handling) match the repository.

## Validation Results
Relevant tests pass: CLI (46), package layout (15), docs links (2), docs sync and production launcher. Ruff is clean over `src`, `scripts`, `tests` and `tools`.

## Status
Completed.
