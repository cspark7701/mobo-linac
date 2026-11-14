"""Step 3a checks use the tracked step 2 settings, the production source and synthetic results only."""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import evaluate_convergence_matrix as cm  # noqa: E402
import evaluate_convergence_step_test as st  # noqa: E402
import analyze_convergence_step_test as sa  # noqa: E402
from prepare_revision_round6 import EVIDENCE, ROOT  # noqa: E402


def test_levels_extend_step2_with_only_step_update_and_source_changes():
    levels = st.levels()
    assert len(levels) == 8 and set(levels) == {st.GATE, *st.ORDER}
    assert levels[st.GATE] == cm.levels()[st.RM_GATE_LEVEL]
    base = cm.levels()[st.RM_GATE_LEVEL]
    for name, value in levels.items():
        changed = {k for k in set(base) | set(value) if base.get(k) != value.get(k)}
        assert changed <= {'newrun:h_max', 'newrun:h_min', 'charge:max_count', 'newrun:distribution'}, name
    assert levels['half_mc1']['charge:max_count'] == 1 and 'charge:max_count' not in levels['quarter_mc10']
    assert levels['eighth_mc10']['newrun:h_max'] == 0.00125
    assert levels['half_mc10_rot2']['newrun:distribution'] == 'qr160k_rot2.ini'


def test_rotation_keeps_invariants_and_fixed_particles(tmp_path):
    source = tmp_path / 'source.ini'
    shutil.copy2(ROOT / 'pal_photo2.ini', source)
    invariants = st.rotate_source(source, tmp_path / 'rot.ini', 40.0)
    assert invariants['angle_deg'] == 40.0
    a, b = np.loadtxt(source), np.loadtxt(tmp_path / 'rot.ini')
    assert np.array_equal(a[0], b[0]) and not np.array_equal(a[:, :2], b[:, :2])
    assert np.allclose((a[1:, :2] ** 2).sum(axis=1), (b[1:, :2] ** 2).sum(axis=1), rtol=1e-9, atol=1e-20)
    with pytest.raises(ValueError, match='distinct'):
        st.check_rotation(source, source, 0.0)
    ordinary = int(np.flatnonzero(b[1:, 9] != -3)[0]) + 1
    b[ordinary, 2] += 1e-3
    np.savetxt(tmp_path / 'bad.ini', b)
    with pytest.raises(ValueError, match='Longitudinal'):
        st.check_rotation(source, tmp_path / 'bad.ini', 40.0)


def _mock_step2(tmp_path):
    r6 = tmp_path / 'r6'
    (r6 / 'template').mkdir(parents=True)
    for name in ['qr40k.ini', 'qr40k.gen.in']:
        shutil.copy2(ROOT / 'pal_photo2.ini', r6 / 'template' / name)
    (r6 / 'results.jsonl').write_text('')
    out, spec, settings = tmp_path / 'rm', tmp_path / 'rm_spec.json', tmp_path / 'rm_settings.csv'
    cm.prepare(out, spec, settings, mock=True, frame=pd.read_csv(EVIDENCE / 'r6_sampling_manifest.csv'),
               r6_results=r6)
    shutil.copy2(ROOT / 'pal_photo2.ini', out / 'template' / 'qr160k.gen.in')  # mock deck placeholder
    rm = json.loads(spec.read_text())
    rm['template_sha256']['qr160k.gen.in'] = cm.sha(out / 'template' / 'qr160k.gen.in')
    rm['minimum_free_disk_GiB'] = 0  # CI runners have far less than the production floor of free disk
    spec.write_text(json.dumps(rm, indent=2, sort_keys=True) + '\n')
    cm.execute(out, spec, settings, mock=True, r6_results=r6)
    return out, spec, settings


def test_mock_prepare_run_resume_and_analysis(tmp_path):
    rm_out, rm_spec, settings = _mock_step2(tmp_path)
    out, spec_path = tmp_path / 'rq', tmp_path / 'rq_spec.json'
    spec = st.prepare(out, spec_path, settings, rm_spec=rm_spec, rm_results=rm_out, mock=True)
    rq = json.loads(spec_path.read_text())
    rq['minimum_free_disk_GiB'] = 0
    spec_path.write_text(json.dumps(rq, indent=2, sort_keys=True) + '\n')
    assert spec['tracking_attempts'] == 120 and len(spec['feasible_at_reference']) == 15
    assert {f'qr160k_{k}.ini' for k in st.ANGLES} <= set(spec['template_sha256'])
    with pytest.raises(ValueError, match='Output exists'):
        st.prepare(out, spec_path, settings, rm_spec=rm_spec, rm_results=rm_out, mock=True)
    with pytest.raises(ValueError, match='Freeze not committed'):
        st.execute(out, spec_path, settings, rm_results=rm_out, mock=False)
    st.execute(out, spec_path, settings, rm_results=rm_out, mock=True)
    journal = out / 'results.jsonl'
    assert len(cm.read_records(journal)) == 120
    before = journal.read_bytes()
    st.execute(out, spec_path, settings, rm_results=rm_out, mock=True, resume=True)
    assert journal.read_bytes() == before
    with pytest.raises(ValueError, match='require --resume'):
        st.execute(out, spec_path, settings, rm_results=rm_out, mock=True)
    (out / 'template' / 'qr160k_rot1.ini').write_text('changed')
    with pytest.raises(ValueError, match='Template checksum'):
        st.execute(out, spec_path, settings, rm_results=rm_out, mock=True, resume=True)
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    assert sa.main(['--output-dir', str(out), '--evidence-dir', str(evidence), '--spec', str(spec_path),
                    '--settings', str(settings)]) == 0
    assert len(pd.read_csv(evidence / 'rq_changes.csv')) == 15 * len(sa.PAIRS)
    assert set(json.loads((evidence / 'rq_analysis_receipt.json').read_text())['outputs']) >= {
        'rq_adequacy.csv', 'rq_mechanism.csv', 'rq_order.csv'}


def test_gate_requires_exact_reproduction_of_step2():
    settings = pd.read_csv(cm.SETTINGS).head(1)
    sid = settings.setting_id.iloc[0]
    values = {k: 1.0 + i for i, k in enumerate(cm.QUANTITIES)}
    old = {f'{sid}__{st.RM_GATE_LEVEL}': {'simulation_valid': True, 'objectives': values, 'diagnostics': {}}}
    new = {f'{sid}__{st.GATE}': {'simulation_valid': True, 'objectives': dict(values), 'diagnostics': {}}}
    spec = {'gate_rtol': 1e-9, 'gate_atol': 1e-12}
    st.check_gate(settings, new, old, spec)
    new[f'{sid}__{st.GATE}']['objectives'][cm.QUANTITIES[0]] *= 1 + 1e-6
    with pytest.raises(ValueError, match='Gate reproduction mismatch'):
        st.check_gate(settings, new, old, spec)


H = {'half': 1.0, 'quarter': 0.5, 'eighth': 0.25}


def _synthetic(step=0.0, update=0.0, order=2, noise=0.0, settings=15, bad=()):
    """E = base * (1 + step*h^order + update*h [Max_count=10 only]) + replicate noise."""
    rng = np.random.default_rng(1)
    rows = []
    for s in range(settings):
        base = 1 + s / 10
        for level in st.levels():
            name = level.split('_')
            h = H[name[0]]
            value = base * (1 + step * h ** order + (update * h if name[1] == 'mc10' else 0))
            if len(name) == 3:
                value *= 1 + noise * rng.standard_normal()
            rows.append({'setting_id': f's{s:02d}', 'level': level, 'valid': (s, level) not in bad,
                         'feasible': s < 9, 'runtime_s': 1.0, 'norm_emit_x_m_rad': value, 'norm_emit_y_m_rad': value,
                         'sigma_energy_eV': 1.0, **{k: 0.0 for k in sa.am.DIAGNOSTIC_TOLERANCE}})
    return pd.DataFrame(rows)


SPEC = {'feasible_at_reference': {f's{s:02d}': s < 9 for s in range(15)}, 'bootstrap_resamples': 200,
        'bootstrap_seed': 1, 'objective_tolerance_relative': 0.01, 'systematic_interval_limit_relative': 0.02,
        'adequacy_share': 0.8, 'mechanism_update_threshold': 0.7, 'mechanism_step_threshold': 0.3,
        'mechanism_min_denominator_relative': 0.001}


def _analyze(frame, multiple=2.0):
    band = sa.noise_band(frame, multiple)
    delta = sa.changes(frame, band)
    summary = sa.summarize(delta, SPEC)
    return delta, summary


def test_mechanism_classifies_update_and_step_dominated_cases():
    delta, _ = _analyze(_synthetic(update=0.04))
    mech = sa.mechanism(delta, SPEC)[0].set_index('stratum')
    assert mech.loc['all', 'class'] == 'update-interval dominated'
    delta, _ = _analyze(_synthetic(step=0.04))
    assert sa.mechanism(delta, SPEC)[0].set_index('stratum').loc['all', 'class'] == 'step dominated'


def test_order_and_adequacy_follow_the_declared_rules():
    frame = _synthetic(step=0.04, order=2)
    delta, summary = _analyze(frame)
    orders = sa.order(frame, summary, SPEC).set_index(['stratum', 'quantity'])
    assert np.isclose(orders.loc[('all', 'norm_emit_x_m_rad'), 'order_from_medians'], 2, rtol=0.05)
    assert abs(orders.loc[('all', 'norm_emit_x_m_rad'), 'median_remainder_eighth']) < 0.01
    status = sa.adequacy(summary, SPEC).set_index(['stratum', 'step']).status
    # Half -> quarter changes 3 %, quarter -> eighth about 0.75 %.
    assert status[('all', 'half')] == 'not adequate' and status[('all', 'quarter')] == 'adequate'
    linear = _synthetic(step=0.04, order=1)
    first = sa.order(linear, _analyze(linear)[1], SPEC).set_index(['stratum', 'quantity'])
    assert np.isclose(first.loc[('all', 'norm_emit_y_m_rad'), 'order_from_medians'], 1, rtol=0.1)


def test_noise_band_widens_the_per_setting_rule_and_invalid_runs_count_against():
    frame = _synthetic(step=0.12, order=2, noise=0.02)
    band = sa.noise_band(frame, 2.0)
    assert (band.filter(like='band_') > 0.01).all().all()
    delta = sa.changes(frame, band)
    pair = delta[delta.pair == 'step_quarter_eighth']
    assert pair.within_noise_aware.mean() > pair.within_1pct.mean()
    bad = _synthetic(step=0.04, bad={(s, 'eighth_mc10') for s in range(4)})
    delta, summary = _analyze(bad)
    row = summary[(summary.stratum == 'all') & (summary.pair == 'step_quarter_eighth')].iloc[0]
    assert row.valid == 11 and row.share_within_noise_aware <= 11 / 15
    assert sa.adequacy(summary, SPEC).set_index(['stratum', 'step']).status[('all', 'quarter')] == 'not adequate'
