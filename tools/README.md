# Maintainer tools

Repository maintenance helpers, kept apart from the scientific entry points in `scripts/`.

| Tool | Purpose |
|---|---|
| `check_github_actions.sh` | Runs the CI workflow steps locally (version, CLI, docs sync, ruff, unit tests); it never contacts GitHub. |
| `cleanup.sh` | Removes transient outputs and caches (`--dry-run` previews). Run outputs under `results/` are immutable research data; clean them deliberately. |
| `sync_site.py` | Refreshes the web bundle `docs/site/` from `docs/index.html`/`docs/style.css`; `--target-repo` deploys it to the github.io repository. |
| `resume_agy_session.sh` | Resumes an agent session for this repository. |

Repository backups (full copies of the tree) belong outside the repository directory.
