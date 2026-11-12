import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import analyze_rank_stability as rs  # noqa: E402


def test_pair_order_counts_agreement_gap_and_groups():
    a = np.array([1.0, 2.0, 3.0, 3.01])
    assert rs.pair_order(a, a)[0] == 1.0
    assert rs.pair_order(a, -a)[0] == 0.0
    b = np.array([1.0, 2.0, 3.02, 3.0])  # only the near-tie swaps
    frac, n = rs.pair_order(a, b)
    assert n == 6 and frac == pytest.approx(5 / 6)
    assert rs.pair_order(a, b, gap=0.05) == (1.0, 5)
    assert rs.pair_order(a, b, groups=['r', 'r', 's', 's']) == (0.5, 2)
    assert np.isnan(rs.pair_order(a, b, gap=10)[0])


def _synthetic(tmp_path, flip=False):
    rng = np.random.default_rng(0)
    meta, lines = [], []
    levels = sorted({lv for pair in rs.PAIRS for lv in pair})
    for k in range(40):
        sid = f's{k}'
        meta.append({'setting_id': sid, 'arm': ['m1', 'm2'][k % 2], 'seed': k % 5, 'run': f'r{k % 10}'})
        base = 1 + rng.random()
        for i, level in enumerate(levels):
            value = base * (0.9 ** i) if not (flip and level == 'combined_fine') else 3 - base
            record = {'role': sid, 'level': level, 'simulation_valid': k != 0 or level != 'fixed_fine',
                      'objectives': {q: value for q in rs.QUANTITIES}}
            payload = json.dumps(record, sort_keys=True)
            lines.append(json.dumps({'record': record, 'sha256': hashlib.sha256(payload.encode()).hexdigest()}))
    (tmp_path / 'results.jsonl').write_text('\n'.join(lines) + '\n')
    (tmp_path / 'complete.json').write_text(json.dumps({'results_sha256': rs.sha(tmp_path / 'results.jsonl')}))
    pd.DataFrame(meta).to_csv(tmp_path / 'manifest.csv', index=False)
    return rs.load(tmp_path, tmp_path / 'manifest.csv')


def test_scaled_levels_have_perfect_rank_stability(tmp_path):
    table = rs.analyze(_synthetic(tmp_path), resamples=20)
    overall = table[table.subset == 'all']
    assert set(table.subset) == {'all', 'm1', 'm2'}
    assert np.allclose(overall.spearman, 1) and np.allclose(overall.order_all, 1)
    row = overall[(overall['first'] == 'production') & (overall['second'] == 'fixed_medium')].iloc[0]
    # Fixture levels are scaled by 0.9**i in alphabetical order: production i=4, fixed_medium i=3.
    assert row.median_shift == pytest.approx(0.9 ** 3 / 0.9 ** 4 - 1)
    assert overall[overall['second'] == 'fixed_fine'].n.eq(39).all()  # invalid attempt excluded


def test_reversed_level_is_detected(tmp_path):
    table = rs.analyze(_synthetic(tmp_path, flip=True), resamples=20)
    row = table[(table.subset == 'all') & (table['second'] == 'combined_fine') & (table['first'] == 'production')]
    assert row.spearman.iloc[0] == pytest.approx(-1) and row.order_all.iloc[0] == 0
    assert row.spearman_hi.iloc[0] < 0


def test_tampered_journal_is_rejected(tmp_path):
    _synthetic(tmp_path)
    (tmp_path / 'results.jsonl').write_text((tmp_path / 'results.jsonl').read_text().replace('s1"', 's9"', 1))
    with pytest.raises(ValueError, match='completion record'):
        rs.load(tmp_path, tmp_path / 'manifest.csv')
    (tmp_path / 'complete.json').write_text(json.dumps({'results_sha256': rs.sha(tmp_path / 'results.jsonl')}))
    with pytest.raises(ValueError, match='checksum'):
        rs.load(tmp_path, tmp_path / 'manifest.csv')


def test_main_writes_evidence(tmp_path):
    _synthetic(tmp_path)
    manifest = tmp_path / 'manifest.csv'
    original = rs.load.__defaults__
    rs.load.__defaults__ = (rs.RESULTS, manifest)
    try:
        assert rs.main(['--results-dir', str(tmp_path), '--evidence-dir', str(tmp_path), '--resamples', '5']) == 0
    finally:
        rs.load.__defaults__ = original
    summary = json.loads((tmp_path / 'rs_rank_summary.json').read_text())
    assert summary['table_sha256'] == rs.sha(tmp_path / 'rs_rank_stability.csv')
    assert len(summary['overall']) == len(rs.QUANTITIES) * len(rs.PAIRS)
