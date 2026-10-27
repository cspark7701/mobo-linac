# Task Completion Summary: Task 196

## Summary
Checked readiness to restart `scripts/production/04_primary.sh` on GPU following the completed saved-proposal benchmark and authorized cleanup.

## Key Findings
- Both benchmark workers completed successfully. Acquisition construction plus proposal optimization measured a 95.85× CPU/GPU speedup for the saved late-stage workload; this does not predict an equal end-to-end simulation speedup.
- The comparison records `primary_removed: true`; the old primary directory and stage-04 status markers are absent. Stages 01–03 remain complete.
- The GPU changes are committed locally as `8ad6c2c4ef30d8c310eca5c1d9f663e9a47d1f52`. The tracked working tree was clean at inspection. Remote push remains pending the previously requested precise approval and does not block local execution.
- No primary campaign or proposal benchmark was running. The RTX A5000 had approximately 24 GB VRAM with only approximately 252 MiB in use at inspection.
- The primary script defaults to `cuda:0` and checks the device before optimization. Recommend eight global ASTRA workers, one concurrent GPU campaign, and one PyTorch controller thread initially. All 30 campaigns, seeds, 160-evaluation budgets, batch size eight, and physical validation remain unchanged.

## Validation Results
Read comparison/publication status artifacts and the current primary script; checked Git state, completion markers, output-directory absence, local processes, GPU availability, and free disk space. Did not launch production or query remote workflows.

## Status
Completed. The user can launch the GPU primary experiment from the activated `linac-opt` environment.
