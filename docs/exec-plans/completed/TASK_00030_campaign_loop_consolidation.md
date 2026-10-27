# Task 29 Summary: Campaign Loop Consolidation (`mobo_linac.campaigns`)

## Summary

Task 29 refactored and consolidated the optimization campaign loop boilerplate across CLI commands, scripts, and production wrappers by introducing a unified manager class `MoboCampaignRunner` under `src/mobo_linac/campaigns/runner.py`.

## Accomplishments

1. **Unified Campaign Class (`MoboCampaignRunner`)**:
   - Created `MoboCampaignRunner` in `src/mobo_linac/campaigns/runner.py` encapsulating configuration loading, random seed management, Sobol initial sampling, `BatchEvaluator` parallel worker pools, iterative GP surrogate fitting, acquisition optimization, hypervolume tracking, checkpointing, dataset export, and plot generation.
   - Exported `MoboCampaignRunner` in `src/mobo_linac/campaigns/__init__.py`.
2. **Refactored CLI Commands & Wrappers**:
   - Updated `run_unconstrained` and `run_constrained` in `src/mobo_linac/cli.py` to instantiate and delegate execution to `MoboCampaignRunner`.
   - Updated `run_campaign` in `scripts/run_validation_campaign.py` to delegate campaign execution to `MoboCampaignRunner`.
   - Standardized campaign invocation across `scripts/run_mobo.py`, `scripts/run_constrained_mobo.py`, and `scripts/run_scalarized_bo.py`.
3. **Tests & Verification**:
   - Pytest suite executed successfully: **76/76 unit tests passed** in 14.12s with zero regressions.

## Status

**Completed**. Campaign loop boilerplate consolidated into `MoboCampaignRunner` and verified across unit test suite.
