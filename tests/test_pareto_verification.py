"""
Unit tests for Independent Pareto Candidate Verification (Task 08).
"""

import pytest

from mobo_linac.astra.workdir import read_evaluation_manifest
from mobo_linac.execution import FunctionEvaluator
from tests.evaluators import callable_evaluator, mock_data_evaluator
import numpy as np
import torch

from mobo_linac.config import load_config
from mobo_linac.evaluation import EvaluationResult, FailureCategory
from mobo_linac.metrics.selection import compute_crowding_distances
from mobo_linac.verification.verifier import (
    compute_file_sha256,
    export_verification_latex_table,
    run_independent_verification_rerun,
    select_verification_candidates,
)

from mobo_linac.config import load_config as _load_test_config
TEST_CONFIG = _load_test_config("configs/mobo_200MeV.yaml")


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
    """Verify the shared representative roles."""
    candidates = select_verification_candidates(sample_pareto_results, TEST_CONFIG)

    assert set(candidates) == {"min_emit_x", "min_emit_y", "min_sigma_energy",
                               "knee_point", "crowding_distance_max", "balanced"}
    assert all(candidate is not None for candidate in candidates.values())


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
        evaluator=mock_data_evaluator(mock_exact),
    )

    assert rec_verified["verification_status"] == "MOCK_VERIFIED"
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
        evaluator=mock_data_evaluator(mock_rejected),
    )

    assert rec_rejected["verification_status"] == "MOCK_REJECTED"
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
        evaluator=mock_data_evaluator({"objectives_physical": candidate.objectives_physical, "diagnostics": candidate.diagnostics}),
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
        evaluator=callable_evaluator(mock_eval),
    )

    assert len(records) == 6
    assert manifest_path.exists()
    assert tex_path.exists()
    assert (tmp_path / "pipeline_verify" / "verification_summary.csv").exists()



def test_repeated_verification_retains_records_and_reports(sample_pareto_results, tmp_path):
    import json
    from pathlib import Path
    from mobo_linac.verification.verifier import run_verification_pipeline

    candidate = sample_pareto_results[0]
    config = load_config()
    mock = {'objectives_physical': candidate.objectives_physical,
            'diagnostics': candidate.diagnostics}
    first = run_independent_verification_rerun('knee', candidate, config, tmp_path, mock_data_evaluator(mock))
    first_bytes = Path(first['record_path']).read_bytes()
    second = run_independent_verification_rerun('knee', candidate, config, tmp_path, mock_data_evaluator(mock))
    assert first['record_path'] != second['record_path']
    assert Path(first['record_path']).read_bytes() == first_bytes
    assert json.loads(Path(second['record_path']).read_text())['verification_run_id'] == second['verification_run_id']
    roles = select_verification_candidates([candidate], config)
    mocks = mock_data_evaluator(mock)
    _, first_manifest, first_tex = run_verification_pipeline([candidate], config, tmp_path, mocks)
    saved = first_manifest.read_bytes()
    _, second_manifest, second_tex = run_verification_pipeline([candidate], config, tmp_path, mocks)
    assert first_manifest != second_manifest
    assert first_tex.exists() and second_tex.exists()
    assert first_manifest.read_bytes() == saved
    assert (tmp_path / 'verification_manifest.json').read_bytes() == second_manifest.read_bytes()
    assert len(list((tmp_path / 'verification_runs').iterdir())) == 4


@pytest.mark.parametrize('workers', [1, 2])
def test_configured_real_reruns_and_audit(sample_pareto_results, recording_astra_project, tmp_path, workers):
    import json
    import os
    from pathlib import Path
    from dataclasses import replace
    from mobo_linac.config import ObjectiveConfig, DesignVariableConfig
    from mobo_linac.verification.verifier import ParetoVerifier
    from mobo_linac.astra.workdir import file_sha256

    project, config = recording_astra_project
    config.objectives = [ObjectiveConfig('mean_kinetic_energy', 'energy_eV', 'eV', 'maximize', 1,
                                        reporting_scale=200e6), config.objectives[0]]
    config.design_variables.append(DesignVariableConfig('grid_count', 'charge:nrad', 'count', 32, 0.1, 30, 34))
    config.execution.timeout_sec = 17
    config.execution.max_workers = workers
    candidate = replace(sample_pareto_results[0], x_physical=[dv.nominal_value for dv in config.design_variables],
                        objectives_physical=[200e6, 1e-6], objectives_model=[200e6, -1e-6])
    verifier = ParetoVerifier(config, tmp_path / 'verification', template_dir=project)
    records, manifest, table = verifier.verify_candidates({'first': candidate, 'second': candidate})
    assert len(records) == 2
    settings = json.loads(manifest.read_text())['settings']
    assert settings['num_workers'] == workers
    assert settings['timeout_sec'] == 17
    for record in records:
        assert record['verification_status'] == 'VERIFIED', record['rerun_audit']
        assert record['comparison_status'] == 'VERIFIED'
        assert set(record['objective_deltas_pct']) == {'energy_eV', 'norm_emit_x_m_rad'}
        assert record['rerun_objectives'] == {'energy_eV': 200e6, 'norm_emit_x_m_rad': 1e-6}
        assert record['design_parameters']['grid_count'] == 32
        assert record['original_run_id'] == candidate.run_id
        assert record['original_audit']['audit_status'] == 'UNKNOWN'
        assert record['original_audit']['input_sha256'] is None
        archive = Path(record['manifest_path']).parent
        inputs = archive / 'inputs' / 'astra.in'
        execution = json.loads(inputs.read_text().splitlines()[-1])
        assignments = json.loads(inputs.read_text().splitlines()[-2])
        assert execution['timeout_sec'] == 17
        assert execution['pid'] != os.getpid()  # every worker count runs process-isolated
        assert assignments['solenoid:maxb(2)'] == candidate.x_physical[0]
        assert assignments['charge:nrad'] == 32
        assert record['input_sha256'] == file_sha256(inputs)
        assert record['executable_sha256'] == file_sha256(project / 'stub_astra')
        assert record['rerun_audit']['attempt_id'] == record['attempt_id']
        assert record['rerun_audit']['evaluation_id'] == record['rerun_evaluation_id']
    assert 'energy\\_eV' in table.read_text()
    assert '200000000' not in table.read_text() or 'eV' in table.read_text()


@pytest.mark.parametrize('mutation,issue', [('missing_objective', 'norm_emit_x_m_rad'),
                                           ('zero_objective', 'norm_emit_x_m_rad'),
                                           ('nonfinite_objective', 'norm_emit_x_m_rad'),
                                           ('missing_transmission', 'transmission_fraction'),
                                           ('zero_transmission', 'transmission_fraction')])
def test_unknown_comparisons_never_agree(sample_pareto_results, tmp_path, mutation, issue):
    from copy import deepcopy
    from mobo_linac.execution.candidate_evaluator import compute_metric_deltas

    config = load_config()
    original = deepcopy(sample_pareto_results[0])
    rerun = deepcopy(original)
    if mutation == 'missing_objective':
        original.objectives_physical = None
    elif mutation == 'zero_objective':
        original.objectives_physical[0] = 0.0
        rerun.objectives_physical[0] = 0.0
    elif mutation == 'nonfinite_objective':
        original.objectives_physical[0] = float('nan')
    elif mutation == 'missing_transmission':
        original.diagnostics.pop('transmission_fraction')
    else:
        original.diagnostics['transmission_fraction'] = 0.0
    deltas = compute_metric_deltas(original, rerun, config)
    assert deltas['comparison_complete'] is False
    assert issue in deltas['comparison_issues']
    record = run_independent_verification_rerun('knee', original, config, tmp_path,
               evaluator=mock_data_evaluator({'objectives_physical': rerun.objectives_physical, 'diagnostics': rerun.diagnostics}))
    assert record['comparison_status'] == 'COMPARISON_UNKNOWN'
    assert record['verification_status'] == 'MOCK_COMPARISON_UNKNOWN'
    assert record['input_sha256'] is None and record['executable_sha256'] is None


def test_missing_rerun_metrics_and_feasibility_change(sample_pareto_results, tmp_path):
    config = load_config()
    original = sample_pareto_results[0]
    missing = run_independent_verification_rerun('missing', original, config, tmp_path,
                evaluator=mock_data_evaluator({'diagnostics': original.diagnostics}))
    assert missing['verification_status'] == 'MOCK_RERUN_FAILED'
    assert all(value is None for value in missing['rerun_objectives'].values())
    diagnostics = dict(original.diagnostics, sigma_x_m=2e-3)
    changed = run_independent_verification_rerun('changed', original, config, tmp_path,
                evaluator=mock_data_evaluator({'objectives_physical': original.objectives_physical, 'diagnostics': diagnostics}))
    assert changed['max_diff_pct'] == 0.0
    assert changed['comparison_status'] == 'REJECTED'


def test_tampered_provenance_cannot_verify(sample_pareto_results, recording_astra_project, tmp_path):
    from dataclasses import replace
    from pathlib import Path
    from mobo_linac.astra.runner import run_astra_eval
    from mobo_linac.verification.verifier import ParetoVerifier

    project, config = recording_astra_project
    candidate = replace(sample_pareto_results[0], objectives_physical=[1e-6, 1e-6, 0.5e6])
    def backend(request, run_id):
        result = run_astra_eval(request.parameters, 'captured', request.eval_id, config=config,
                               template_dir=project, base_results_dir=tmp_path / 'work')
        (Path(result['manifest_path']).parent / 'inputs' / 'astra.in').write_text('tampered')
        return result
    records, _, _ = ParetoVerifier(config, tmp_path / 'reports').verify_candidates({'knee': candidate}, evaluator=FunctionEvaluator(backend))
    assert records[0]['comparison_status'] == 'VERIFIED'
    assert records[0]['verification_status'] == 'AUDIT_FAILED'
    assert any('checksum mismatch' in issue for issue in records[0]['rerun_audit']['issues'])


def test_function_class_and_cli_equivalent(sample_pareto_results, recording_astra_project, tmp_path):
    import argparse
    import json
    import yaml
    from dataclasses import asdict, replace
    from mobo_linac.cli.commands.audit import run_verification
    from mobo_linac.verification.verifier import ParetoVerifier, run_verification_pipeline

    project, config = recording_astra_project
    candidate = replace(sample_pareto_results[0], objectives_physical=[1e-6, 1e-6, 0.5e6])
    candidates = select_verification_candidates([candidate], config)
    first, _, _ = run_verification_pipeline([candidate], config, tmp_path / 'function', num_workers=1, template_dir=project, timeout=13)
    second, _, _ = ParetoVerifier(config, tmp_path / 'class', num_workers=1, template_dir=project, timeout=13).verify_candidates(candidates)
    history = tmp_path / 'candidate_history.json'
    history.write_text(json.dumps([candidate.to_dict()]))
    cfg = tmp_path / 'config.yaml'
    cfg.write_text(yaml.safe_dump(asdict(config)))
    run_verification(argparse.Namespace(config=str(cfg), input=str(history), output_dir=str(tmp_path / 'cli'),
                      num_workers=1, timeout=13, template_dir=str(project), dry_run=False, mock_evaluator=False))
    third = json.loads((tmp_path / 'cli' / 'verification_manifest.json').read_text())['records']
    for records in (first, second, third):
        assert [record['verification_status'] for record in records] == ['VERIFIED'] * len(candidates)
        assert [record['max_diff_pct'] for record in records] == [0.0] * len(candidates)
        assert [record['role'] for record in records] == list(candidates)
        assert [record['rerun_objectives'] for record in records] == [first[0]['rerun_objectives']] * len(candidates)


def test_transmission_participates_in_error_threshold(sample_pareto_results, tmp_path):
    original = sample_pareto_results[0]
    record = run_independent_verification_rerun('knee', original, load_config(), tmp_path,
                 evaluator=mock_data_evaluator({'objectives_physical': original.objectives_physical,
                                  'diagnostics': dict(original.diagnostics, transmission_fraction=0.99)}))
    assert record['max_diff_pct'] == pytest.approx(1.0)
    assert record['comparison_status'] == 'CONDITIONALLY_VERIFIED'
    assert record['verification_status'] == 'MOCK_CONDITIONALLY_VERIFIED'


def test_original_and_rerun_audits_link_exact_attempts(recording_astra_project, tmp_path):
    from pathlib import Path
    from mobo_linac.astra.runner import run_astra_eval
    from mobo_linac.evaluation import create_evaluation_result
    from mobo_linac.verification.verifier import ParetoVerifier

    project, config = recording_astra_project
    raw = run_astra_eval([variable.nominal_value for variable in config.design_variables], 'nominal', 1,
                         config=config, template_dir=project, base_results_dir=tmp_path / 'nominal',
                         clean_on_success=True)
    original = create_evaluation_result(raw, config)
    assert original.simulation_valid is True
    verifier = ParetoVerifier(config, tmp_path / 'reports', num_workers=1, template_dir=project)
    first, first_manifest, _ = verifier.verify_candidates({'knee': original})
    record = first[0]
    assert record['verification_status'] == 'VERIFIED'
    assert record['original_audit']['audit_status'] == 'VERIFIED'
    assert record['original_audit']['input_sha256'] == read_evaluation_manifest(raw['manifest_path'])['input_hashes']['astra.in']
    assert record['original_attempt_id'] == raw['attempt_id']
    assert record['original_manifest_path'] == raw['manifest_path']
    assert record['attempt_id'] != record['original_attempt_id']
    saved = first_manifest.read_bytes()
    (Path(raw['manifest_path']).parent / 'inputs' / 'astra.in').write_text('changed original snapshot')
    second, _, _ = verifier.verify_candidates({'knee': original})
    assert second[0]['comparison_status'] == 'VERIFIED'
    assert second[0]['original_audit']['audit_status'] == 'FAILED'
    assert second[0]['verification_status'] == 'AUDIT_FAILED'
    assert first_manifest.read_bytes() == saved
