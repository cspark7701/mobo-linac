"""Convergence-matrix checks use the tracked round6 evidence and synthetic results only."""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import evaluate_convergence_matrix as cm  # noqa: E402
import analyze_convergence_matrix as am  # noqa: E402
from prepare_revision_round6 import EVIDENCE, ROOT  # noqa: E402

MANIFEST = EVIDENCE / 'r6_sampling_manifest.csv'


def test_levels_and_gate_match_round6():
    levels = cm.levels()
    assert len(levels) == 11
    r6 = json.loads(cm.R6_SPEC.read_text())
    assert levels[cm.GATE] == r6['levels'][cm.R6_GATE_LEVEL]
    assert {v['newrun:h_max'] for k, v in levels.items() if k.startswith('half')} == {0.005}
    assert levels['quarter_g64_n640k']['newrun:distribution'] == 'qr640k.ini'


def test_selection_is_deterministic_and_covers_every_cell():
    frame = pd.read_csv(MANIFEST)
    first, second = cm.select(frame), cm.select(frame.sample(frac=1, random_state=3))
    assert first.setting_id.tolist() == second.setting_id.tolist()
    assert len(first) == 15 and first.setting_id.is_unique
    for arm, rows in first.groupby('arm'):
        assert len(rows) == 5 and rows[rows.role == 'cell'].cell.nunique() == 4
    assert (first.inclusion_probability > 0).all() and (first.inclusion_probability <= 1).all()
    with pytest.raises(ValueError, match='four nonempty cells'):
        cm.select(frame[frame.boundary == 'near'])


def test_tasks_run_longest_first_with_identical_controls():
    settings = cm.select(pd.read_csv(MANIFEST)).head(2)
    tasks = cm.make_tasks(settings, {'levels': cm.levels()})
    assert len(tasks) == 22 and tasks[0].metadata['level'] == 'quarter_g64_n640k'
    assert tasks[-1].metadata['level'] == 'half_g32_n40k'
    by_setting = {}
    for task in tasks:
        by_setting.setdefault(task.role, set()).add(tuple(task.parameters))
    assert all(len(v) == 1 for v in by_setting.values())


def test_gate_requires_exact_reproduction():
    settings = cm.select(pd.read_csv(MANIFEST)).head(1)
    sid = settings.setting_id.iloc[0]
    values = {k: 1.0 + i for i, k in enumerate(cm.QUANTITIES)}
    old = {f'{sid}__{cm.R6_GATE_LEVEL}': {'simulation_valid': True, 'objectives': values, 'diagnostics': {}}}
    new = {f'{sid}__{cm.GATE}': {'simulation_valid': True, 'objectives': dict(values), 'diagnostics': {}}}
    spec = {'gate_rtol': 1e-9, 'gate_atol': 1e-12}
    cm.check_gate(settings, new, old, spec)
    new[f'{sid}__{cm.GATE}']['objectives'][cm.QUANTITIES[0]] *= 1 + 1e-6
    with pytest.raises(ValueError, match='Gate reproduction mismatch'):
        cm.check_gate(settings, new, old, spec)
    with pytest.raises(ValueError, match='Invalid gate'):
        cm.check_gate(settings, {}, old, spec)


def test_mock_prepare_run_resume_and_analysis(tmp_path):
    r6 = tmp_path / 'r6'
    (r6 / 'template').mkdir(parents=True)
    for name in ['qr40k.ini', 'qr40k.gen.in']:
        shutil.copy2(ROOT / 'pal_photo2.ini', r6 / 'template' / name)
    (r6 / 'results.jsonl').write_text('')
    out, spec_path, settings_path = tmp_path / 'out', tmp_path / 'spec.json', tmp_path / 'settings.csv'
    frame = pd.read_csv(MANIFEST)
    spec = cm.prepare(out, spec_path, settings_path, mock=True, frame=frame, r6_results=r6)
    assert spec['tracking_attempts'] == 165 and spec['template_sha256']['qr40k.ini'] == spec['r6_qr40k_sha256']
    with pytest.raises(ValueError, match='Output exists'):
        cm.prepare(out, spec_path, settings_path, mock=True, frame=frame, r6_results=r6)
    with pytest.raises(ValueError, match='Freeze not committed'):
        cm.execute(out, spec_path, settings_path, mock=False, r6_results=r6)
    cm.execute(out, spec_path, settings_path, mock=True, r6_results=r6)
    records = cm.read_records(out / 'results.jsonl')
    assert len(records) == 165
    before = (out / 'results.jsonl').read_bytes()
    cm.execute(out, spec_path, settings_path, mock=True, resume=True, r6_results=r6)
    assert (out / 'results.jsonl').read_bytes() == before
    with pytest.raises(ValueError, match='require --resume'):
        cm.execute(out, spec_path, settings_path, mock=True, r6_results=r6)
    (out / 'pending.json').write_text(json.dumps(['unrecorded']))
    with pytest.raises(ValueError, match='Interrupted'):
        cm.execute(out, spec_path, settings_path, mock=True, resume=True, r6_results=r6)
    (out / 'pending.json').unlink()
    (out / 'template' / 'qr640k.ini').write_text('changed')
    with pytest.raises(ValueError, match='Template checksum'):
        cm.execute(out, spec_path, settings_path, mock=True, resume=True, r6_results=r6)
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    assert am.main(['--output-dir', str(out), '--evidence-dir', str(evidence), '--spec', str(spec_path),
                    '--settings', str(settings_path)]) == 0
    assert len(pd.read_csv(evidence / 'rm_changes.csv')) == 15 * len(am.refinements())
    receipt = json.loads((evidence / 'rm_analysis_receipt.json').read_text())
    assert set(receipt['outputs']) >= {'rm_adequacy.csv', 'rm_refinements.csv'}


def test_real_mode_requires_committed_freeze(tmp_path):
    spec = tmp_path / 'spec.json'
    spec.write_text('{}')
    with pytest.raises(ValueError, match='Freeze not committed'):
        cm.require_committed([spec])


def _synthetic(settings=15, particle=0.02, grid=0.0, step=0.0, bad=()):
    """Emittance = 1 + particle*(40/N)**0.5 + grid*(32/G)**2 + step for quarter steps."""
    rows = []
    for s in range(settings):
        for level in cm.levels():
            step_name, g, n = level.split('_')
            g, n = int(g[1:]), int(n[1:-1])
            value = (1 + s / 10) * (1 + particle * (40 / n) ** 0.5 + grid * (32 / g) ** 2
                                    + (step if step_name == 'quarter' else 0))
            rows.append({'setting_id': f's{s:02d}', 'level': level, 'valid': not (s, level) in bad,
                         'feasible': True, 'norm_emit_x_m_rad': value, 'norm_emit_y_m_rad': value,
                         'sigma_energy_eV': 1.0, **{k: 0.0 for k in am.DIAGNOSTIC_TOLERANCE}})
    return pd.DataFrame(rows)


def test_adequacy_follows_the_declared_rule():
    converged = am.adequacy(am.summarize(am.changes(_synthetic(particle=0.001))), 0.8)
    assert set(converged.status) == {'adequate', 'terminal (step check met)'}
    assert converged.set_index('point').loc['half_g64_n640k', 'status'].startswith('terminal')
    grid_limited = am.adequacy(am.summarize(am.changes(_synthetic(particle=0.001, grid=0.2))), 0.8)
    status = grid_limited.set_index('point').status
    assert status['half_g32_n40k'] == 'not adequate' and status['half_g48_n40k'] == 'not adequate'
    step_limited = am.adequacy(am.summarize(am.changes(_synthetic(particle=0.001, step=0.05))), 0.8)
    assert step_limited.set_index('point').status['half_g64_n40k'] == 'not adequate'


def test_invalid_runs_count_against_adequacy_and_extrapolation_is_geometric():
    frame = _synthetic(particle=0.001, bad={(s, 'half_g32_n160k') for s in range(4)})
    delta = am.changes(frame)
    assert not delta[(delta.setting_id == 's00') & (delta.fine == 'half_g32_n160k')].valid.any()
    status = am.adequacy(am.summarize(delta), 0.8).set_index('point').status
    assert status['half_g32_n40k'] == 'not adequate'
    extrapolation = am.particle_extrapolation(_synthetic(particle=0.04))
    assert np.allclose(extrapolation.ratio, 0.5)
    # Geometric tail 0.04*(40/640)**0.5 = 0.01 remaining relative to 1 + 0.01.
    assert np.allclose(extrapolation.remaining_at_640k, -0.01 / 1.01, rtol=1e-6)
    ranks = am.rank_agreement(_synthetic())
    assert np.allclose(ranks.spearman_vs_reference, 1)


def test_sensitivity_exploration_ranks_settings_and_splits_feasibility():
    import explore_convergence_sensitivity as ex
    frame = _synthetic(particle=0.04)
    frame[['sigma_x_m', 'sigma_y_m', 'sigma_xp_rad', 'sigma_yp_rad', 'sigma_z_m']] = 1e-3
    frame['feasible'] = frame.setting_id < 's05'
    # Make one setting step-sensitive only.
    step = (frame.setting_id == 's14') & frame.level.str.startswith('quarter')
    frame.loc[step, am.EMITTANCES] *= 1.2
    table = ex.per_setting(frame, am.changes(frame))
    assert table.index[0] == 's14' and np.isclose(table.loc['s14', 'max_step'], 0.2)
    assert table.feasible.sum() == 5 and table.feasibility_constant_across_levels.all()
    strata = ex.strata(am.changes(frame), table)
    assert set(strata.feasible) == {True, False} and strata.n.sum() == 15 * len(am.refinements())
    assert not ex.correlations(table).empty


def test_analysis_rejects_incomplete_or_tampered_results(tmp_path):
    (tmp_path / 'results.jsonl').write_text('')
    (tmp_path / 'complete.json').write_text(json.dumps({'results_sha256': 'x'}))
    with pytest.raises(ValueError, match='completion record'):
        am.load(tmp_path)
