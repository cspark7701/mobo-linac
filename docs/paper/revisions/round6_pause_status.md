# Round 6 pause and restart record

Status: **paused by the user**, 2026-11-02 07:15:48 KST (2026-11-01 22:15:48 UTC).
The revision chain, its two CPU workers and their ASTRA children have stopped.
No scaling campaign was launched. No restart, new scheduling or push is part of this pause operation.

## Preserved progress

| Work | State at pause |
| --- | --- |
| C6-01–04 editorial corrections | Completed previously |
| C6-05 adoption and A6-01 protocol | Completed; protocol remains frozen |
| C6-06 numerical validation | Paused: 387 production and 44 combined-fine results, 431 total |
| C6-07 raw/normalized comparison | Implementation prepared; 3,200 evaluations not started |
| C6-08 optional scalarized comparator | Not adopted by the author |
| C6-09 final integration and responses | Pending complete research results |

Of 1,935 numerical evaluation slots, 1,504 lack a completed record, including two
interrupted attempts. Interrupted attempts must be included in subsequent resource
accounting. Completed evaluations must not be rerun. The remaining combined study
has 4,704 incomplete slots; no completion ETA applies while execution is paused.

## Checkpoint and interrupted evidence

Checkpoint directory: `results/revision_round6/pause_checkpoints/20261101T221548Z`.
The snapshot contains `plan.json`, `pending.json`, `results.jsonl`,
`nominal_complete.json`, and `pause_manifest.json`. The manifest records process
ancestry, work directories, file hashes and pending identities. The live evidence
under `results/revision_round6/resolution/` remains intact. `results/revision_round6/PAUSED.json`
blocks the chain and both simulation entry points before output mutation.

The interrupted combined-fine identities are:

- `constrained_qlognehvi_seed_45__eval_000083__combined_fine`, attempt `attempt_fc9d3fe4bd6a48b8abbe15688da29421`.
- `constrained_qlognehvi_seed_45__eval_000137__combined_fine`, attempt `attempt_ce88313bf3e14d5eabfa24033e83f6f5`.

Their original directories remain under
`results/revision_round6/resolution/runs/round6_resolution/work/eval_<identity>/`.
ASTRA has no native restart checkpoint for these attempts: the saved checkpoint is
at the study/evaluation level, not a promise to continue an interrupted trajectory.

## Verification and scientific scope

All four copied file hashes and all 431 journal record checksums passed verification.
The nominal marker matches the first 387 journal lines. Both execution locks are free
and the original round6 processes have terminated. The previously completed validation
receipt reports 1,138 passed, two deselected and 100% package coverage; that gate
predates the pause guards, which receive separate focused checks.
Partial refinement results do not establish convergence or scaling efficacy.
The manuscript scientific conclusions are unchanged.

All eight round6 review, overview and task documents carry the dated pause status.
Historical reviews retain their recommendations. Frozen protocol, specification,
sampling manifests and previously committed completion records are intentionally
immutable; this record supersedes their earlier execution-status descriptions.

## Restart requirements — do not execute until instructed

After explicit user authorization, verify snapshot/journal hashes and inspect both
interrupted attempt manifests before choosing recovery. Preserve all original
attempts; use isolated retry evidence if re-execution is needed and account for the
additional attempts. The existing blanket `--resume` rejects unresolved pending
attempts and must not be used blindly. Reconcile the pending state only through an
audited recovery step. Archive the pause marker only after that authorization and
recovery decision. Retain the two-CPU-worker ceiling, frozen seeds, budgets,
precision and physical validation. Recheck source identities and validation receipts
before continuing numerical validation, then scaling, then scientific integration.
No recovery implementation or relaunch is part of this pause.

## Pause-specific checks

All 18 focused round6 tests passed. Ruff and shell syntax checks passed.
The chain refused startup at the pause guard before validation or simulations.

## Snapshot SHA-256

- `plan.json`: `ca4317f07d34cc4533122002abc271040a7841d7f14eb3877253e70b5982cfed`
- `pending.json`: `341db74f0d279b464fecdf192ebfceec115d78f93619f2ad5ba5a1b2e2fa28cf`
- `results.jsonl`: `b60973bc44ff1091952583c900dc2ee8f0e71ca61cdb9407bcf305db3c78541e`
- `nominal_complete.json`: `6af588d4b9f8e022ecdbb11ec632909a1edf7933c0f148940038c541370fbaaa`
