import sys
from pathlib import Path
import pytest

from tests.evaluators import callable_evaluator
import pandas as pd
import numpy as np

# Ensure repo root is in sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from mobo_linac.metrics.publication import compute_target_distance
from mobo_linac.reporting.comparison import verify_pareto_candidates
from mobo_linac.io.run_data import RunData
from mobo_linac.metrics.publication import generate_comparison_report
from mobo_linac.metrics.reporting import reporting_metadata

from mobo_linac.config import load_config
from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.metrics.hypervolume import HypervolumeTracker
import torch


def test_compute_target_distance():
    """Target distance uses the configured objective targets."""
    targets = [objective.target for objective in load_config("configs/mobo_200MeV.yaml").objectives]
    assert compute_target_distance(targets, targets) == pytest.approx(np.sqrt(3.0), rel=1e-5)
    assert compute_target_distance([0.0, 0.0, 0.0], targets) == 0.0
    assert np.isnan(compute_target_distance([1.0, 1.0, 1.0], [1.0, None, 1.0]))


def test_verify_pareto_candidates_mock(tmp_path, monkeypatch):
    """Test shared Pareto selection and audited verification with an explicit mock evaluator."""
    config = load_config("configs/mobo_200MeV.yaml")

    mock_results = []
    for i in range(1, 10):
        res = EvaluationResult(
            evaluation_id=f"eval_00000{i}",
            run_id="mock_run",
            x_physical=[0.20 + 0.01 * i, 1.0, -1.0, 0.0, 0.0, 0.0],
            objectives_physical=[1e-6 * i, 1e-6 * i, 0.1e6 * i],
            objectives_model=[-1e-6 * i, -1e-6 * i, -0.1e6 * i],
            diagnostics={
                "sigma_x": 0.5e-3,
                "sigma_y": 0.5e-3,
                "sigma_xp": 0.5e-3,
                "sigma_yp": 0.5e-3,
                "sigma_z": 0.5e-3,
                "mean_kinetic_energy": 200e6,
                "transmission": 1.0,
            },
            simulation_valid=True,
            physically_feasible=True,
            failure_category=FailureCategory.SUCCESS.value,
        )
        mock_results.append(res)

    def evaluator(parameters, **kwargs):
        i = round((parameters[0] - 0.20) / 0.01)
        return mock_results[i - 1]

    records = verify_pareto_candidates(mock_results, config, tmp_path, evaluator=callable_evaluator(evaluator))

    assert len(records) == 6
    for rec in records:
        assert rec["status"] == "MOCK_VERIFIED"
        assert rec["max_diff_pct"] < 1.0e-3


def test_generate_comparison_report(tmp_path):
    """Test generating mobo_validation_report.md."""
    config = load_config("configs/mobo_200MeV.yaml")
    ref_point = torch.tensor([-5.0e-6, -5.0e-6, -2.0e6], dtype=torch.double)

    tracker_p2 = HypervolumeTracker(reporting_ref_point=ref_point, config=config)
    tracker_p3 = HypervolumeTracker(reporting_ref_point=ref_point, config=config)

    train_Y = torch.tensor([[-1.0e-6, -1.0e-6, -0.5e6]], dtype=torch.double)
    feas_mask = torch.tensor([True])

    tracker_p2.track_iteration(0, train_Y, feas_mask)
    tracker_p3.track_iteration(0, train_Y, feas_mask)

    mock_results = [
        EvaluationResult(
            evaluation_id="eval_000001",
            run_id="mock_run",
            x_physical=[0.20, 1.0, -1.0, 0.0, 0.0, 0.0],
            objectives_physical=[1.0e-6, 1.0e-6, 0.5e6],
            objectives_model=[-1.0e-6, -1.0e-6, -0.5e6],
            diagnostics={
                "sigma_x": 0.5e-3,
                "sigma_y": 0.5e-3,
                "sigma_xp": 0.5e-3,
                "sigma_yp": 0.5e-3,
                "sigma_z": 0.5e-3,
                "mean_kinetic_energy": 200e6,
                "transmission": 1.0,
            },
            simulation_valid=True,
            physically_feasible=True,
            failure_category=FailureCategory.SUCCESS.value,
        )
    ]

    verification_records = [
        {
            "role": "knee_point",
            "original_eval_id": "eval_000001",
            "stored_emit_x_m_rad": 1.0e-6,
            "rerun_emit_x_m_rad": 1.0e-6,
            "stored_emit_y_m_rad": 1.0e-6,
            "rerun_emit_y_m_rad": 1.0e-6,
            "stored_sigma_energy_eV": 0.5e6,
            "rerun_sigma_energy_eV": 0.5e6,
            "max_diff_pct": 0.0,
            "status": "VERIFIED",
        }
    ]

    report_path = tmp_path / "docs" / "results" / "mobo_validation_report.md"
    runs = [RunData(tmp_path / name, config, mock_results, reporting_metadata(config, ref_point.tolist()),
                    tracker.to_dataframe()) for name, tracker in (("run_p2", tracker_p2), ("run_p3", tracker_p3))]
    generate_comparison_report(runs, ["Phase 2 (Unconstrained MOBO)", "Phase 3 (Constrained MOBO)"],
                               verification_records, report_path,
                               title="Multi-Objective Bayesian Optimization Validation & Comparison Report",
                               wall_times=[12.34, 15.67])

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Multi-Objective Bayesian Optimization Validation & Comparison Report" in content
    assert "Phase 2 (Unconstrained MOBO)" in content
    assert "Phase 3 (Constrained MOBO)" in content
    assert "VERIFIED" in content


def test_comparison_report_is_data_driven_with_failed_evaluations(publication_runs, tmp_path):
    from mobo_linac.metrics.publication import read_comparison_runs
    p1, p2, p3, _ = publication_runs
    runs = read_comparison_runs([p2, p3])
    records = [{'role': 'failed|case', 'stored_emit_x_m_rad': 1e-6, 'rerun_emit_x_m_rad': None,
                'stored_sigma_energy_eV': .5e6, 'rerun_sigma_energy_eV': None,
                'max_diff_pct': None, 'status': 'RERUN_FAILED'}]
    path = generate_comparison_report(runs, ["Phase 2", "Phase 3"], records, tmp_path / 'report.md')
    content = path.read_text()
    assert '| Numerical Valid Simulations | 2 | 2 |' in content
    assert '| Physically Feasible Beams | 1 | 1 |' in content
    assert '33.333333' in content
    assert 'RERUN_FAILED' in content and r'failed\|case' in content
    assert 'All candidates achieved' not in content and 'zero numerical discrepancy' not in content


def test_comparison_report_links_only_existing_figures(publication_runs, tmp_path):
    from mobo_linac.metrics.publication import read_comparison_runs
    p1, p2, p3, _ = publication_runs
    runs = read_comparison_runs([p1, p2, p3])
    names = ["Phase 1", "Phase 2", "Phase 3"]
    content = generate_comparison_report(runs, names, [], tmp_path / 'report.md').read_text()
    assert 'figures/' not in content and '| Phase 1 | Phase 2 | Phase 3 |' in content
    (tmp_path / 'figures').mkdir()
    (tmp_path / 'figures' / 'pareto_front_comparison.png').write_bytes(b'png')
    content = generate_comparison_report(runs, names, [], tmp_path / 'report.md').read_text()
    assert 'figures/pareto_front_comparison.png' in content
    assert 'hypervolume_comparison.png' not in content and 'verification_rerun_comparison.png' not in content


def test_comparison_report_rejects_mismatched_references(tmp_path):
    config = load_config('configs/mobo_200MeV.yaml')
    runs = [RunData(tmp_path / name, config, [], reporting_metadata(config, ref), None)
            for name, ref in (("first", [-3e-6, -3e-6, -2e6]), ("second", [-4e-6, -3e-6, -2e6]))]
    path = tmp_path / 'new' / 'report.md'
    with pytest.raises(ValueError, match='Incompatible reporting'):
        generate_comparison_report(runs, ["first", "second"], [], path)
    assert not path.parent.exists()
