# TASK_116: Set Default Workers to 4 and Remove Automatic 90% CPU Core Selection

## 1. Requirement
Remove the dynamic 90% system CPU core allocation logic from [`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/mobo-linac/scripts/run_full_production.sh) and standardize on explicit worker specification via `-w` / `--workers`, with the default worker count set to `4`.

## 2. Changes Implemented
In [`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/mobo-linac/scripts/run_full_production.sh):
1. **Default Workers**: Initialized `NUM_WORKERS=4` (aligning with `configs/mobo_200MeV.yaml` execution settings).
2. **Removed Dynamic Allocation**: Removed the `python3 -c "import os; print(max(1, int(os.cpu_count() * 0.9)))"` evaluation block.
3. **CLI Options & Help Updated**:
   - `Usage` and `--help` text updated: `-w, --workers W (default: 4)`.
4. **Log Banner Updated**:
   - Replaced `Allocated CPU Cores: ${NUM_WORKERS} (90% capacity)` with `Parallel CPU Workers: ${NUM_WORKERS}`.

## 3. Verification
- `./scripts/run_full_production.sh --help`: Displays `-w, --workers W Number of parallel CPU worker cores (default: 4)`.
- `bash -n scripts/run_full_production.sh`: Syntax validation passed with exit code 0.
