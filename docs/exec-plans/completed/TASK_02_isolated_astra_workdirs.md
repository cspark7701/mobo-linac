# Task 02 — Isolated ASTRA Working Directories

## Summary

Task 02 implemented a working directory manager to ensure every ASTRA evaluation runs inside its own isolated directory, eliminating file collisions and output corruption during parallel evaluation.

## Accomplishments

1. **Directory Isolation Manager**: Created `AstraWorkDirManager` in `src/mobo_linac/astra/workdir.py` that generates evaluation directories under `results/<run_id>/work/eval_<id>/`.
2. **Static File Linker/Copier**: Automatically copies/links required field maps (`gun.dat`, `PAL_SOL_A.dat`, `TWS_Sband.dat`) and particle distribution (`pal_photo2.ini`).
3. **Independent Input Modification**: Generates a dedicated `astra.in` for each candidate evaluation without modifying root files.
4. **Manifest Tracking**: Writes `manifest.json` per evaluation recording candidate parameters, execution timestamps, ASTRA return codes, and output file paths.
5. **ASTRA Runner Integration**: Updated `src/mobo_linac/astra/runner.py` to execute ASTRA processes with `cwd` explicitly bound to the evaluation work directory.

## Status

**Completed**. Tested via `tests/test_astra_workdirs.py`.
