# TASK_115: Align Step Numbering (7 Steps) and Add Leading Blank Lines in run_full_production.sh

## 1. Context & Identified Discrepancy
In [`scripts/run_full_production.sh`](file:///home/cspark/Work/projects/mobo-linac/scripts/run_full_production.sh):
- Pre-execution worker calculation was labeled `# Step 1: Calculate Available CPU Cores for Parallel Simulation`, while the first execution log printed `[Step 1/8] Verifying environment & executable permissions...`.
- The remaining steps sequentially called `[Step 2/8]` through `[Step 6/8]`, and then jumped directly to `[Step 8/8] Pipeline Execution Finished Successfully!`, leaving no step 7.
- Consecutive step logging lacked visual spacing between large blocks of simulation and optimization output.

## 2. Actual Total Step Count
There are **7 execution steps in total**:
- **Step 1/7**: Environment & Binary Verification
- **Step 2/7**: Phase 1 Scalarized BO Production Simulation
- **Step 3/7**: Phase 2 Unconstrained MOBO Production Simulation
- **Step 4/7**: Phase 3 Constraint-Aware MOBO Production Simulation
- **Step 5/7**: 3-Phase Comparative Analysis & Independent Rerun Audit
- **Step 6/7**: Engineering Tolerance Robustness Analysis
- **Step 7/7**: Final Summary & Verification Report Generation

## 3. Changes Implemented
1. Re-titled the pre-execution worker allocation comment block to `# Parallel Worker Allocation (90% System CPU Cores)` so it is clearly distinct from the numbered execution pipeline.
2. Synchronized all section header comments (`# Step 1` to `# Step 7`) and console log messages (`[Step 1/7]` to `[Step 7/7]`).
3. Added two blank lines (`\n\n`) preceding every step title printed to stdout to ensure clear visual separation.

## 4. Verification
- `bash -n scripts/run_full_production.sh`: Syntax check passed.
- `grep -E '(\[Step|# Step)' scripts/run_full_production.sh`: Verified continuous, consistent 1/7 through 7/7 sequence.
