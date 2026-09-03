"""
Unit tests for Result Serialization, DataFrame Conversions, and Checkpoint Management (Task 05).
"""

from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.io.results import (
    CheckpointState,
    load_evaluation_results,
    load_run_checkpoint,
    results_to_dataframe,
    save_evaluation_results,
    save_run_checkpoint,
)
import torch


@pytest.fixture
def sample_results():
    res1 = EvaluationResult(
        evaluation_id="eval_000001",
        run_id="run_001",
        x_physical=[0.20, 1.2, -1.2, 0.0, 0.0, 0.0],
        objectives_physical=[1.2e-6, 1.2e-6, 5.0e4],
        objectives_model=[-1.2e-6, -1.2e-6, -5.0e4],
        diagnostics={"sigma_x": 0.8e-3, "mean_kinetic_energy": 200.0e6},
        simulation_valid=True,
        physically_feasible=True,
        failure_category=FailureCategory.SUCCESS.value,
        runtime_s=2.5,
        work_dir="/tmp/work/eval_1",
    )
    res2 = EvaluationResult(
        evaluation_id="eval_000002",
        run_id="run_001",
        x_physical=[0.25, 1.5, -1.5, 5.0, 2.0, 2.0],
        objectives_physical=[2.5e-6, 2.5e-6, 6.0e4],
        objectives_model=[-2.5e-6, -2.5e-6, -6.0e4],
        diagnostics={"sigma_x": 1.2e-3, "mean_kinetic_energy": 200.0e6},
        simulation_valid=True,
        physically_feasible=False,
        failure_category=FailureCategory.INFEASIBLE_BEAM.value,
        failure_reason="Beam diagnostics violated constraint thresholds",
        runtime_s=2.7,
        work_dir="/tmp/work/eval_2",
    )
    return [res1, res2]


def test_results_to_dataframe(sample_results):
    """Test converting EvaluationResult list to Pandas DataFrame."""
    df = results_to_dataframe(sample_results)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "evaluation_id" in df.columns
    assert "simulation_valid" in df.columns
    assert "physically_feasible" in df.columns
    assert df.loc[0, "simulation_valid"] == True
    assert df.loc[0, "physically_feasible"] == True
    assert df.loc[1, "physically_feasible"] == False


def test_save_and_load_evaluation_results(sample_results, tmp_path):
    """Test saving and restoring evaluation results to/from JSON and CSV."""
    paths = save_evaluation_results(sample_results, tmp_path)
    assert paths["json"].exists()
    assert paths["csv"].exists()

    loaded_json = load_evaluation_results(paths["json"])
    assert len(loaded_json) == 2
    assert loaded_json[0].evaluation_id == "eval_000001"
    assert loaded_json[0].simulation_valid is True
    assert loaded_json[1].physically_feasible is False

    loaded_csv = load_evaluation_results(paths["csv"])
    assert len(loaded_csv) == 2
    assert loaded_csv[0].evaluation_id == "eval_000001"
    assert loaded_csv[0].simulation_valid is True


def test_save_and_load_checkpoint(sample_results, tmp_path):
    """Test saving and loading optimization checkpoints."""
    ckpt_path = tmp_path / "checkpoint.pt"
    hypervolumes = [0.0, 1.5e-10, 2.1e-10]

    save_run_checkpoint(
        iteration=5,
        results=sample_results,
        hypervolumes=hypervolumes,
        checkpoint_path=ckpt_path,
        acquisition_mode="qLogNEHVI",
    )

    assert ckpt_path.exists()

    ckpt = load_run_checkpoint(ckpt_path)
    assert isinstance(ckpt, CheckpointState)
    assert ckpt.iteration == 5
    assert ckpt["iteration"] == 5
    assert ckpt.hypervolumes == hypervolumes
    assert len(ckpt.results) == 2
    assert ckpt.results[0].evaluation_id == "eval_000001"
    assert ckpt.results[0].simulation_valid is True
    assert ckpt.torch_rng_state is not None
    assert ckpt.numpy_rng_state is not None


def test_checkpoint_state_schema_validation(sample_results):
    """Verify CheckpointState schema validation and error handling."""
    state = CheckpointState(
        iteration=3,
        results=sample_results,
        hypervolumes=[0.1, 0.2],
        acquisition_mode="qLogEHVI",
        seed=42,
    )
    d = state.to_dict()
    assert d["iteration"] == 3
    assert len(d["results_serialized"]) == 2

    # Reconstruction from dict
    restored = CheckpointState.from_dict(d)
    assert restored.iteration == 3
    assert restored.acquisition_mode == "qLogEHVI"
    assert len(restored.results) == 2
    assert restored.seed == 42

    # Invalid structures raise ValueError
    with pytest.raises(ValueError, match="must be a dictionary"):
        CheckpointState.from_dict("not_a_dict")  # type: ignore

    with pytest.raises(ValueError, match="missing required 'iteration' field"):
        CheckpointState.from_dict({"hypervolumes": [0.1]})


def test_atomic_checkpoint_save(sample_results, tmp_path):
    """Verify atomic checkpoint writes leave no leftover temporary files and ensure target integrity."""
    ckpt_path = tmp_path / "checkpoints" / "checkpoint_iter_02.pt"
    hypervolumes = [0.0, 1.2e-10]

    saved_path = save_run_checkpoint(
        iteration=2,
        results=sample_results,
        hypervolumes=hypervolumes,
        checkpoint_path=ckpt_path,
        acquisition_mode="qLogNEHVI",
    )

    assert saved_path.exists()
    latest_path = tmp_path / "checkpoints" / "checkpoint.pt"
    assert latest_path.exists()

    # Verify no .tmp files left behind
    tmp_files = list(tmp_path.glob("**/*.tmp*"))
    assert len(tmp_files) == 0

    # Verify loaded content from both iteration checkpoint and latest checkpoint
    loaded_iter = load_run_checkpoint(saved_path)
    loaded_latest = load_run_checkpoint(latest_path)

    assert loaded_iter.iteration == 2
    assert loaded_latest.iteration == 2
    assert len(loaded_latest.results) == 2


def test_dynamic_config_column_binding(tmp_path):
    """Verify dynamic column header binding from custom MoboConfig."""
    from mobo_linac.config import ConstraintsConfig, DesignVariableConfig, MoboConfig, ObjectiveConfig

    dvs = [
        DesignVariableConfig("var_a", "key_a", "T", 1.0, 0.1, 0.5, 1.5),
        DesignVariableConfig("var_b", "key_b", "T", 2.0, 0.1, 1.0, 3.0),
        DesignVariableConfig("var_c", "key_c", "T", 3.0, 0.1, 2.0, 4.0),
        DesignVariableConfig("var_d", "key_d", "T", 4.0, 0.1, 3.0, 5.0),
    ]
    objs = [
        ObjectiveConfig("custom_emit", "custom_emit_m", "m", "minimize", -1),
        ObjectiveConfig("custom_energy", "custom_energy_eV", "eV", "minimize", -1),
    ]
    custom_cfg = MoboConfig(
        version="2.0",
        description="Custom 4D 2-Obj Config",
        design_variables=dvs,
        objectives=objs,
        constraints=ConstraintsConfig(),
    )

    custom_res = [
        EvaluationResult(
            evaluation_id="eval_000001",
            run_id="custom_run",
            x_physical=[1.1, 2.2, 3.3, 4.4],
            objectives_physical=[1.0e-6, 2.0e5],
            objectives_model=[-1.0e-6, -2.0e5],
            diagnostics={"sigma_x_m": 0.5e-3, "mean_kinetic_energy_eV": 200.0e6, "transmission_fraction": 1.0},
            simulation_valid=True,
            physically_feasible=True,
        )
    ]

    df = results_to_dataframe(custom_res, config=custom_cfg)
    assert "var_a" in df.columns
    assert "var_d" in df.columns
    assert "custom_emit_m" in df.columns
    assert "model_custom_emit_neg" in df.columns
    assert df.loc[0, "var_a"] == 1.1
    assert df.loc[0, "var_d"] == 4.4

    paths = save_evaluation_results(custom_res, tmp_path / "custom_run", config=custom_cfg)
    loaded_csv = load_evaluation_results(paths["csv"], config=custom_cfg)

    assert len(loaded_csv) == 1
    assert loaded_csv[0].x_physical == [1.1, 2.2, 3.3, 4.4]
    assert loaded_csv[0].objectives_physical == [1.0e-6, 2.0e5]
    assert loaded_csv[0].objectives_model == [-1.0e-6, -2.0e5]



