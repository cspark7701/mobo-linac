"""Round6 evidence collection and summary tables from synthetic frozen-protocol outputs."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import summarize_revision_round6 as summary  # noqa: E402
from prepare_revision_round6 import sha  # noqa: E402

LEVELS = summary.LEVELS
QUANTITIES = [name for name, _ in summary.QUANTITIES]


def classification():
    rows = []
    for setting, arm, feasible in [('a', 'constrained_qlognehvi', [False, True, True, True, True]),
                                   ('b', 'unconstrained_qlognehvi', [True]*5),
                                   ('c', 'scalarized_bo', [False]*5)]:
        for index, level in enumerate(LEVELS):
            values = {q: 1.0 for q in QUANTITIES}
            values['norm_emit_x_m_rad'] = 1.0-0.1*index
            values['mean_kinetic_energy_eV'] = 2e8+1e4*index
            rows.append({'setting_id': setting, 'level': level, 'simulation_valid': True, 'feasible': feasible[index],
                         'runtime_s': 10.0*(index+1), 'arm': arm, 'nearest_channel': 'sigma_z_m',
                         'min_signed_margin': -0.002, 'boundary': 'near', **values})
    return pd.DataFrame(rows)


def write_evidence(folder):
    classification().to_csv(folder/'r6_resolution_classification.csv', index=False)
    pd.DataFrame([{'arm': arm, 'seed': seed, 'level': level, 'fraction': 0.4 if arm.startswith('c') else 0.1,
                   'design_variance': 0.0004, 'physical_upper_if_invalid_pass': 0.4, 'unknown_fraction': 0.0,
                   'population': 160, 'sample': 4}
                  for arm in summary.ARMS for seed in (42, 43) for level in LEVELS]).to_csv(
        folder/'r6_resolution_fractions.csv', index=False)
    pd.DataFrame([{'level': level, 'first': 'constrained_qlognehvi', 'second': second, 'groups': 2,
                   'mean_difference': 0.3, 'ci_lower_conditional': -0.25, 'ci_upper_conditional': 0.35,
                   'minimum_difference': 0.2, 'positive_groups': 2, 'design_se_conservative': 0.02}
                  for level in LEVELS for second in summary.ARMS[1:]]).to_csv(folder/'r6_resolution_paired.csv', index=False)
    pd.DataFrame([{'setting_id': 'a', 'comparison': f'{kind}_fine - {kind}_medium', 'quantity': q, 'delta': 0.0,
                   'tolerance': 1.0, 'comparison_valid': True, 'within_tolerance': q != 'norm_emit_x_m_rad'}
                  for kind in ['fixed', 'combined'] for q in QUANTITIES]).to_csv(folder/'r6_resolution_tolerances.csv', index=False)
    pd.DataFrame([{'arm': arm, 'seed': seed, 'feasible_fraction': fraction, 'post_init_feasible_fraction': fraction+0.02,
                   'invalid_attempts': 0, 'elapsed_wall_time_s': 7200.0 if arm == 'raw' else 3600.0}
                  for seed in (42, 43) for arm, fraction in [('raw', 0.4), ('normalized', 0.3)]]).to_csv(
        folder/'r6_scaling_runs.csv', index=False)
    pd.DataFrame([{'endpoint': endpoint, 'first': 'normalized', 'second': 'raw', 'groups': 2, 'mean_difference': value,
                   'ci_lower_conditional': value-0.01, 'ci_upper_conditional': value+0.01, 'minimum_difference': value,
                   'positive_groups': 0}
                  for endpoint, value in [('feasible_fraction', -0.1), ('post_init_feasible_fraction', -0.12),
                                          ('elapsed_wall_time_s', -3600.0)]]).to_csv(folder/'r6_scaling_paired.csv', index=False)
    pd.DataFrame([{'arm': arm, 'seed': seed, 'stage': stage, 'attempts': 10, 'invalid': 0, 'transverse_only': t,
                   'energy_only': 0, 'multiple_groups': 2, 'other_only': 1, 'feasible': 10-t-3}
                  for arm, t in [('raw', 1), ('normalized', 3)] for seed in (42, 43)
                  for stage in ['initial', 'early_post', 'late']]).to_csv(folder/'r6_scaling_channels.csv', index=False)
    pd.DataFrame([{'arm': arm, 'seed': 42, 'batches': 19, 'initial_sobol': 1, 'primary': 18, 'retry': 0, 'other': 0}
                  for arm in ['raw', 'normalized']]).to_csv(folder/'r6_scaling_proposals.csv', index=False)


def test_summaries_and_tables(tmp_path):
    write_evidence(tmp_path)
    summary.write(tmp_path)
    resolution = json.loads((tmp_path/'r6_resolution_summary.json').read_text())
    flips = resolution['flips']['fixed_fine vs production']
    assert flips['changed'] == 1 and flips['infeasible_to_feasible'] == 1 and flips['feasible_to_infeasible'] == 0
    assert flips['arms'] == {'constrained_qlognehvi': 1}
    assert resolution['flips']['fixed_fine vs fixed_medium']['largest_absolute_margin'] is None
    change = resolution['changes']['norm_emit_x_m_rad']['fixed_fine vs production']
    assert change['median'] == pytest.approx(-20.0) and change['fraction_lower'] == 1.0
    assert resolution['changes']['mean_kinetic_energy_eV']['fixed_fine vs production']['median'] == pytest.approx(0.02)
    assert resolution['weighted_feasible_fraction']['production']['constrained_qlognehvi']['design_se'] == pytest.approx(0.0008**.5/2)
    assert resolution['within_tolerance']['fixed_fine - fixed_medium|norm_emit_x_m_rad'] == 0.0
    assert resolution['inputs_sha256']['r6_resolution_paired.csv'] == sha(tmp_path/'r6_resolution_paired.csv')
    scaling = json.loads((tmp_path/'r6_scaling_summary.json').read_text())
    assert scaling['group_differences'] == {'42': pytest.approx(-0.1), '43': pytest.approx(-0.1)}
    assert scaling['post_init_share_difference_normalized_minus_raw']['transverse_only'] == pytest.approx(0.2)
    assert scaling['arms']['raw']['elapsed_h']['mean'] == pytest.approx(2.0)
    assert 'r6_scaling_proposals.csv' in scaling['inputs_sha256'] and 'r6_resolution_paired.csv' not in scaling['inputs_sha256']
    table = (tmp_path/'r6_resolution_table.tex').read_text()
    assert 'Fixed-source fine & 0.400 (0.014)' in table and '[$-0.250$, 0.350]' in table
    numerical = (tmp_path/'r6_numerical_table.tex').read_text()
    assert '$-20.0$ [$-20.0$, $-20.0$]' in numerical
    assert 'Transmission & 0 (all settings) & 0 &' in numerical
    assert 'Difference & $-0.100$ & $-0.120$' in (tmp_path/'r6_scaling_table.tex').read_text()
    assert '95\\% interval & [$-0.110$, $-0.090$]' in (tmp_path/'r6_scaling_table.tex').read_text()
    assert '$+0.200$' in (tmp_path/'r6_scaling_table.tex').read_text()


def test_signed_number_format():
    assert summary.signed(0.25, 2) == '0.25'
    assert summary.signed(-0.25, 2) == '$-0.25$'
    assert summary.signed(0.25, 1, plus=True) == '$+0.2$'


def receipt_results(tmp_path):
    results = tmp_path/'results'
    for study, names in summary.COPIED.items():
        folder = results/f'analysis_{study}'
        folder.mkdir(parents=True)
        (results/study).mkdir()
        (results/study/'complete.json').write_text('{}\n')
        for name in names:
            (folder/name).write_text(f'{name}\n')
        (folder/f'r6_{study}_analysis.json').write_text(json.dumps({
            'spec_sha256': sha(summary.EVIDENCE/'r6_specification.json'),
            'completion_sha256': sha(results/study/'complete.json'),
            'outputs_sha256': {name: sha(folder/name) for name in names}}))
    campaign = results/'scaling'/'raw_seed_42'
    campaign.mkdir()
    (campaign/'proposal_history.json').write_text(json.dumps(
        [{'metadata': {'method': m}} for m in ['initial_sobol', 'primary', 'retry', 'sobol_fallback']]))
    return results


def test_collect_copies_only_verified_outputs(tmp_path):
    results, out = receipt_results(tmp_path), tmp_path/'evidence'
    out.mkdir()
    summary.collect(results, out)
    assert (out/'r6_scaling_runs.csv').read_text() == 'r6_scaling_runs.csv\n'
    tiers = pd.read_csv(out/'r6_scaling_proposals.csv').iloc[0]
    assert (tiers.primary, tiers.retry, tiers.other, tiers.batches) == (1, 1, 1, 4)
    collection = json.loads((out/'r6_collection.json').read_text())
    assert collection['r6_scaling_runs.csv']['sha256'] == sha(out/'r6_scaling_runs.csv')
    (results/'analysis_scaling'/'r6_scaling_runs.csv').write_text('changed\n')
    with pytest.raises(ValueError, match='Analysis output changed'):
        summary.collect(results, out)


@pytest.mark.parametrize('field, message', [('spec_sha256', 'frozen specification'),
                                            ('completion_sha256', 'completion record')])
def test_collect_rejects_foreign_receipts(tmp_path, field, message):
    results = receipt_results(tmp_path)
    receipt = results/'analysis_resolution'/'r6_resolution_analysis.json'
    data = json.loads(receipt.read_text())
    data[field] = '0'*64
    receipt.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=message):
        summary.verified_outputs('resolution', results)


def test_collect_requires_listed_outputs(tmp_path):
    results = receipt_results(tmp_path)
    receipt = results/'analysis_scaling'/'r6_scaling_analysis.json'
    data = json.loads(receipt.read_text())
    del data['outputs_sha256']['r6_scaling_runs.csv']
    receipt.write_text(json.dumps(data))
    (tmp_path/'evidence').mkdir()
    with pytest.raises(ValueError, match='not a checksummed'):
        summary.collect(results, tmp_path/'evidence')


def test_main_rewrites_from_evidence(tmp_path):
    write_evidence(tmp_path)
    summary.main(['--evidence-dir', str(tmp_path)])
    assert (tmp_path/'r6_scaling_table.tex').exists()
