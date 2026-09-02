# Task Execution Summary: TASK_93 — Standalone Scripts Execution Order & Workflow

## 1. Overview & Objectives
- **Goal**: Clarify and document the precise execution sequence for individual modular scripts in `scripts/` (outside of the automated master runner `run_full_production.sh`), including optimization phases, comparative post-processing, verification audits, robustness studies, and publication figure generation.

---

## 2. Scripts Execution Sequence

### Stage 1: Optimization Campaigns
1. `scripts/run_scalarized_bo.py` (Phase 1 Scalarized BO)
2. `scripts/run_mobo.py` (Phase 2 Unconstrained MOBO)
3. `scripts/run_constrained_mobo.py` (Phase 3 Constrained MOBO)

### Stage 2: Post-Processing & Verification
4. `scripts/run_comparison_and_verification.py` (3-Phase Comparison & Pareto Verification)
5. `scripts/run_robustness_analysis.py` (Engineering Tolerance Robustness & Sensitivity)

### Stage 3: Manuscript Figure Generation
6. `scripts/generate_paper_figures.py` (Publication Vector & PNG Figures)
7. `scripts/reproduce_paper.sh` (LaTeX PDF Compilation)

---

## 3. Key Files Updated
- `scripts/run_mobo.py`
- `scripts/run_constrained_mobo.py`
- `scripts/run_scalarized_bo.py`
