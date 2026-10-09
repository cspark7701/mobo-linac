"""Publication readers preserve measured identity and explicit reporting conventions."""
import json
from pathlib import Path
import pytest

from mobo_linac.io.run_data import read_run_data, read_comparable_runs, load_candidates, discover_candidate_source
from mobo_linac.metrics.publication import campaign_summary, generate_campaign_summary_latex_table


def test_history_reconstructs_distinct_pareto_sets(publication_runs):
    directory = publication_runs[0]
    run = read_run_data(directory)
    assert run.pareto().evaluation_id.tolist() == ['eval_000002']
    assert run.pareto(True).evaluation_id.tolist() == ['eval_000001']
    summary = campaign_summary(run)
    assert summary['total_evaluations'] == 3
    assert summary['valid_evaluations'] == 2
    assert summary['feasible_evaluations'] == 1
    assert summary['feasibility_pct'] == pytest.approx(100 / 3)
    assert summary['feasibility_valid_pct'] == 50
    assert summary['min_emit_x_um'] == 1
    # Status-free derived CSVs are joined to the observed candidate identities.
    records = load_candidates(directory / 'pareto.csv', run.config)
    assert records[0].evaluation_id == 'eval_000002'
    assert records[0].physically_feasible is False
    assert load_candidates(directory / 'pareto_feasible.csv', run.config)[0].physically_feasible is True


@pytest.mark.parametrize('field', ['objective_units', 'objective_signs', 'objective_scales', 'reporting_ref_point', 'constraint_profile'])
def test_comparisons_reject_incompatible_metadata_before_writes(publication_runs, tmp_path, field):
    first, second = publication_runs[:2]
    path = second / 'reporting_metadata.json'
    meta = json.loads(path.read_text())
    if field == 'constraint_profile':
        meta[field]['max_sigma_x_m'] *= 2
    else:
        meta[field][0] = 'unknown' if field == 'objective_units' else meta[field][0] * 2
    path.write_text(json.dumps(meta))
    output = tmp_path / 'output' / 'table.tex'
    with pytest.raises(ValueError):
        generate_campaign_summary_latex_table([first, second], output)
    assert not output.parent.exists()


def test_reader_requires_explicit_legacy_convention(publication_runs):
    directory = publication_runs[0]
    path = directory / 'reporting_metadata.json'
    meta = json.loads(path.read_text())
    path.unlink()
    with pytest.raises(ValueError, match='Explicit reporting metadata'):
        read_run_data(directory)
    assert read_run_data(directory, legacy_reporting_metadata=meta).metadata == meta


def test_history_identity_and_metric_count_conflicts_fail(publication_runs):
    directory = publication_runs[0]
    path = directory / 'candidate_history.json'
    original = path.read_text()
    records = json.loads(original)
    records[1]['evaluation_id'] = records[0]['evaluation_id']
    path.write_text(json.dumps(records))
    with pytest.raises(ValueError, match='Duplicate candidate identity'):
        read_run_data(directory)
    records = json.loads(original)
    records[0]['physically_feasible'] = False
    path.write_text(json.dumps(records))
    with pytest.raises(ValueError, match='counts disagree'):
        read_run_data(directory)


def test_candidate_discovery_rejects_explicit_missing_inputs(publication_runs, tmp_path):
    directory = publication_runs[0]
    assert discover_candidate_source(directory) == directory / 'candidate_history.json'
    with pytest.raises(FileNotFoundError):
        discover_candidate_source(tmp_path / 'absent')
    bare = tmp_path / 'bare'
    bare.mkdir()
    (bare / 'pareto.csv').write_bytes((directory / 'pareto.csv').read_bytes())
    assert discover_candidate_source(root=bare) is None
    record = load_candidates(bare / 'pareto.csv', read_run_data(directory).config)[0]
    assert record.simulation_valid is None and record.physically_feasible is None


def test_empty_campaign_has_unknown_rates_and_extrema(tmp_path):
    from mobo_linac.config import load_config
    from mobo_linac.io.artifacts import RunArtifactWriter
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    config = load_config('configs/mobo_200MeV.yaml')
    config.save_json(tmp_path / 'config.json')
    writer = RunArtifactWriter(tmp_path, config)
    writer.write([], HypervolumeTracker([-3e-6, -3e-6, -2e6], config))
    content = generate_campaign_summary_latex_table([tmp_path])
    assert '--' in content
    assert 'Feasible Pareto Size & 0' in content


def test_reader_checks_existing_completion_marker(publication_runs):
    from mobo_linac.io.artifacts import RunArtifactWriter
    from mobo_linac.io.results import get_train_tensors
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    directory = publication_runs[0]
    run = read_run_data(directory)
    tracker = HypervolumeTracker(run.metadata['reporting_ref_point'], run.config)
    _, y, feasible = get_train_tensors(run.results, config=run.config)
    tracker.track_iteration(0, y, feasible)
    writer = RunArtifactWriter(directory, run.config)
    writer.write(run.results, tracker)
    writer.complete(3, None)
    assert len(read_run_data(directory).results) == 3
    with (directory / 'candidate_history.json').open('a') as stream:
        stream.write(' ')
    with pytest.raises(ValueError, match='completion marker conflicts'):
        read_run_data(directory)
