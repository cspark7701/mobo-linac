"""
Unit tests for Independent Pareto Candidate Verification (Task 08).
"""

import pytest
import numpy as np
import torch

from mobo_linac.config import load_config
from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.verification.verifier import (
    compute_crowding_distances,
    compute_file_sha256,
    export_verification_latex_table,
    run_independent_verification_rerun,
    select_verification_candidates,
)


@pytest.fixture
def sample_pareto_results():
    results = []
    for i in range(1, 8):
        res = EvaluationResult(
            evaluation_id=f"eval_{i}",
            run_id="test_run",
            x_physical=[0.19 + 0.01 * i, 1.2, -2.8, 35.0, -39.0, 310.0],
            objectives_physical=[1.0e-6 * i, 2.0e-6 / i, 0.1e6 * i],
            objectives_model=[-1.0e-6 * i, -2.0e-6 / i, -0.1e6 * i],
            diagnostics={
                "sigma_x_m": 0.5e-3,
                "sigma_y_m": 0.5e-3,
                "sigma_xp_rad": 0.5e-3,
                "sigma_yp_rad": 0.5e-3,
                "sigma_z_m": 0.5e-3,
                "mean_kinetic_energy_eV": 200.0e6,
                "transmission_fraction": 1.0,
            },
            simulation_valid=True,
            physically_feasible=True,
            failure_category=FailureCategory.SUCCESS.value,
        )
        results.append(res)
    return results


def test_file_sha256_computation(tmp_path):
    """Verify SHA-256 checksum calculation for input files."""
    test_file = tmp_path / "test_input.in"
    test_file.write_text("SOLENOID: maxb(1) = 0.19477\n", encoding="utf-8")

    sha = compute_file_sha256(test_file)
    assert isinstance(sha, str)
    assert len(sha) == 64  # SHA-256 hex string length


def test_crowding_distance_calculation():
    """Verify crowding distance calculation across normalized objective points."""
    objs_norm = np.array([
        [0.0, 1.0],
        [0.5, 0.5],
        [1.0, 0.0],
    ])

    dists = compute_crowding_distances(objs_norm)
    assert len(dists) == 3
    assert np.isinf(dists[0])
    assert np.isinf(dists[2])
    assert dists[1] > 0.0


def test_select_verification_candidates(sample_pareto_results):
    """Verify selection of 7 distinct candidate roles."""
    candidates = select_verification_candidates(sample_pareto_results)

    for role in [
        "min_emit_x",
        "min_emit_y",
        "min_sigma_energy",
        "knee_point",
        "crowding_distance_max",
        "balanced_feasible",
        "robust_recommended",
    ]:
        assert role in candidates
        assert candidates[role] is not None


def test_independent_verification_rerun(sample_pareto_results, tmp_path):
    """Verify independent candidate rerun, relative error calculation, and status classification."""
    config = load_config("configs/publication_200MeV.yaml")
    candidate = sample_pareto_results[0]

    # 1. Exact match -> VERIFIED
    mock_exact = {
        "objectives_physical": candidate.objectives_physical,
        "diagnostics": candidate.diagnostics,
        "physically_feasible": True,
    }
    rec_verified = run_independent_verification_rerun(
        role="knee_point",
        candidate=candidate,
        config=config,
        output_dir=tmp_path / "verify",
        mock_rerun_data=mock_exact,
    )

    assert rec_verified["verification_status"] == "VERIFIED"
    assert rec_verified["max_diff_pct"] == pytest.approx(0.0)

    # 2. Large difference -> REJECTED
    mock_rejected = {
        "objectives_physical": [2.0e-6, 4.0e-6, 0.5e6],
        "diagnostics": candidate.diagnostics,
        "physically_feasible": True,
    }
    rec_rejected = run_independent_verification_rerun(
        role="knee_point",
        candidate=candidate,
        config=config,
        output_dir=tmp_path / "verify",
        mock_rerun_data=mock_rejected,
    )

    assert rec_rejected["verification_status"] == "REJECTED"
    assert rec_rejected["max_diff_pct"] > 1.0


def test_export_verification_latex_table(sample_pareto_results, tmp_path):
    """Verify export of LaTeX verification table."""
    config = load_config("configs/publication_200MeV.yaml")
    candidate = sample_pareto_results[0]

    rec = run_independent_verification_rerun(
        role="knee_point",
        candidate=candidate,
        config=config,
        output_dir=tmp_path / "verify",
        mock_rerun_data={"objectives_physical": candidate.objectives_physical},
    )

    tex_path = tmp_path / "verification_table.tex"
    export_verification_latex_table([rec], tex_path)

    assert tex_path.exists()
    content = tex_path.read_text(encoding="utf-8")
    assert r"\begin{table}" in content
    assert r"knee\_point" in content
    assert "VERIFIED" in content


def test_run_verification_pipeline(sample_pareto_results, tmp_path):
    """Verify full verification pipeline with mock rerun data map."""
    from mobo_linac.verification.verifier import run_verification_pipeline

    config = load_config("configs/publication_200MeV.yaml")

    def mock_eval(x, run_id, eval_id):
        return {
            "status": "success",
            "objectives": {"norm_emit_x": 1.0e-6, "norm_emit_y": 1.0e-6, "sigma_energy": 0.1e6},
            "diagnostics": {"transmission_fraction": 1.0, "sigma_x_m": 0.5e-3},
        }

    records, manifest_path, tex_path = run_verification_pipeline(
        results=sample_pareto_results,
        config=config,
        output_dir=tmp_path / "pipeline_verify",
        mock_evaluator=mock_eval,
    )

    assert len(records) == 7
    assert manifest_path.exists()
    assert tex_path.exists()
    assert (tmp_path / "pipeline_verify" / "verification_summary.csv").exists()

