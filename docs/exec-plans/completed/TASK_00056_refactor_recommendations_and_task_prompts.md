# TASK_55: Codebase & Physics Refactor Recommendations & Task Prompt Generation

**Date**: 2026-08-14  
**Author**: Chong Shik Park  
**Status**: COMPLETED  

---

## 1. Overview & Objectives

Conducted an in-depth repository review covering accelerator beam dynamics, Gaussian Process surrogate modeling with BoTorch, ASTRA simulation runners, campaign orchestration loops, Pareto diversity metrics, and robustness analysis. Generated an 8-task modular refactoring suite saved in `docs/04_refactor_tasks/`.

---

## 2. Refactoring Task Suite in `docs/04_refactor_tasks/`

| Task | Title | Priority | Target Scope |
| :--- | :--- | :--- | :--- |
| **TASK_01** | `TASK_01_relative_noise_variance_gp.md` | P1 (Physics) | Scaled observation noise for multi-scale objectives ($\mu\text{m}\cdot\text{rad}$ vs $\text{MeV}$) |
| **TASK_02** | `TASK_02_dynamic_parameter_mapping.md` | P1 (Physics) | Config-driven ASTRA namelist mapping & decoupled lattice parameters |
| **TASK_03** | `TASK_03_exit_plane_loss_detection.md` | P1 (Physics) | Exit-plane tracking verification & premature loss / core collimation trapping |
| **TASK_04** | `TASK_04_unify_execution_loops.md` | P2 (Architecture) | Single unified campaign loop in `MoboCampaignRunner` across CLI & scripts |
| **TASK_05** | `TASK_05_deduplicate_pareto_metrics.md` | P2 (Code Quality) | Deduplication of `compute_crowding_distances` & CLI cleanup |
| **TASK_06** | `TASK_06_photocathode_laser_robustness.md` | P3 (Physics) | Full-stack photocathode, laser, and bunch charge jitter modeling |
| **TASK_07** | `TASK_07_type_safe_checkpoint_schema.md` | P3 (Architecture) | Typed `CheckpointState` dataclass & serialization validation |
| **TASK_08** | `TASK_08_configurable_acquisition_optimization.md` | P3 (Performance) | User-configurable multi-restart optimization budget for acquisition functions |

---

## 3. Package Structure Created

- [`docs/04_refactor_tasks/README.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/README.md)
- [`docs/04_refactor_tasks/TASK_ORDER.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/TASK_ORDER.md)
- [`docs/04_refactor_tasks/Antigravity_MASTER_PROMPT.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/Antigravity_MASTER_PROMPT.md)
- [`docs/04_refactor_tasks/TASK_01_relative_noise_variance_gp.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/TASK_01_relative_noise_variance_gp.md)
- [`docs/04_refactor_tasks/TASK_02_dynamic_parameter_mapping.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/TASK_02_dynamic_parameter_mapping.md)
- [`docs/04_refactor_tasks/TASK_03_exit_plane_loss_detection.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/TASK_03_exit_plane_loss_detection.md)
- [`docs/04_refactor_tasks/TASK_04_unify_execution_loops.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/TASK_04_unify_execution_loops.md)
- [`docs/04_refactor_tasks/TASK_05_deduplicate_pareto_metrics.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/TASK_05_deduplicate_pareto_metrics.md)
- [`docs/04_refactor_tasks/TASK_06_photocathode_laser_robustness.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/TASK_06_photocathode_laser_robustness.md)
- [`docs/04_refactor_tasks/TASK_07_type_safe_checkpoint_schema.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/TASK_07_type_safe_checkpoint_schema.md)
- [`docs/04_refactor_tasks/TASK_08_configurable_acquisition_optimization.md`](file:///home/cspark/Work/projects/mobo_linac/docs/04_refactor_tasks/TASK_08_configurable_acquisition_optimization.md)

---

## 4. Verification

All task prompts were verified for format compliance, clear acceptance criteria, actionable test commands, and alignment with repository physics and code rules.
