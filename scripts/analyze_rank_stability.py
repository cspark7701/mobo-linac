#!/usr/bin/env python3
"""Rank stability of the round6 re-tracked objectives across numerical levels.

Absolute emittances change with resolution (round6: fine vs medium differs by a median
5.5-7.4 %). This analysis asks whether the *ordering* of settings, which is what an
optimizer acts on, is stable. It uses only the completed round6 journal; no simulation.

For each pair of levels and each objective it reports Spearman and Kendall correlations
(with a cluster bootstrap over the ten matched groups), the fraction of setting pairs
whose order is preserved, both overall and for pairs separated by more than 1/5/10 %
at the coarser level, the fraction preserved among pairs from the same campaign, and the
median signed relative shift. Summaries are unweighted descriptions of the 387 sampled
settings, not population estimates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, rankdata

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/paper/revisions/evidence'
OUTPUT = ROOT / 'docs/paper/revisions/convergence_followup'
RESULTS = ROOT / 'results/revision_round6/resolution'
QUANTITIES = ['norm_emit_x_m_rad', 'norm_emit_y_m_rad', 'sigma_energy_eV']
PAIRS = [('production', 'fixed_medium'), ('production', 'fixed_fine'), ('production', 'combined_fine'),
         ('fixed_medium', 'fixed_fine'), ('combined_medium', 'combined_fine'), ('fixed_fine', 'combined_fine')]
GAPS = [0.01, 0.05, 0.10]
SEED = 20261112
RESAMPLES = 2000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(results_dir=RESULTS, manifest=EVIDENCE / 'r6_sampling_manifest.csv'):
    """Values per setting and level from the verified journal, joined to method and group."""
    journal = results_dir / 'results.jsonl'
    complete = json.loads((results_dir / 'complete.json').read_text())
    if sha(journal) != complete['results_sha256']:
        raise ValueError('Journal does not match its completion record.')
    rows = []
    for line in journal.read_text().splitlines():
        envelope = json.loads(line)
        record = envelope['record']
        payload = json.dumps(record, sort_keys=True, allow_nan=False)
        if hashlib.sha256(payload.encode()).hexdigest() != envelope['sha256']:
            raise ValueError('Journal record checksum mismatch.')
        if not record['simulation_valid']:
            continue
        rows.append({'setting_id': record['role'], 'level': record['level'],
                     **{q: (record['objectives'] or {}).get(q) for q in QUANTITIES}})
    values = pd.DataFrame(rows)
    meta = pd.read_csv(manifest)[['setting_id', 'arm', 'seed', 'run']]
    return values.merge(meta, on='setting_id', how='left', validate='many_to_one')


def spearman(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def pair_order(a, b, groups=None, gap=0.0):
    """Fraction of setting pairs whose order agrees at both levels.

    Only pairs whose relative difference at the first level exceeds ``gap`` are counted;
    with ``groups``, only pairs from the same group (campaign) are counted.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    i, j = np.triu_indices(len(a), 1)
    keep = np.abs(a[i] - a[j]) > gap * np.minimum(np.abs(a[i]), np.abs(a[j]))
    if groups is not None:
        groups = np.asarray(groups)
        keep &= groups[i] == groups[j]
    if not keep.any():
        return np.nan, 0
    agree = np.sign(a[i] - a[j]) == np.sign(b[i] - b[j])
    return float(agree[keep].mean()), int(keep.sum())


def cluster_interval(frame, first, second, rng, resamples=RESAMPLES):
    """Percentile interval of Spearman's rho, resampling matched groups with replacement."""
    groups = frame.seed.unique()
    by_group = {g: frame[frame.seed == g] for g in groups}
    draws = []
    for _ in range(resamples):
        sample = pd.concat([by_group[g] for g in rng.choice(groups, len(groups), replace=True)])
        draws.append(spearman(sample[first], sample[second]))
    return [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]


def analyze(values, resamples=RESAMPLES, seed=SEED):
    rng = np.random.default_rng(seed)
    wide = values.pivot_table(index=['setting_id', 'arm', 'seed', 'run'], columns='level',
                              values=QUANTITIES, aggfunc='first')
    out = []
    for quantity in QUANTITIES:
        for first, second in PAIRS:
            for subset in ['all', *sorted(values.arm.unique())]:
                frame = wide[quantity][[first, second]].dropna().reset_index()
                if subset != 'all':
                    frame = frame[frame.arm == subset]
                a, b = frame[first].to_numpy(), frame[second].to_numpy()
                shift = b / a - 1
                row = {'quantity': quantity, 'first': first, 'second': second, 'subset': subset,
                       'n': len(frame), 'spearman': spearman(a, b),
                       'kendall': float(kendalltau(a, b).statistic),
                       'median_shift': float(np.median(shift)),
                       'shift_q25': float(np.percentile(shift, 25)), 'shift_q75': float(np.percentile(shift, 75))}
                row['spearman_lo'], row['spearman_hi'] = cluster_interval(frame, first, second, rng, resamples)
                row['order_all'], row['pairs_all'] = pair_order(a, b)
                for gap in GAPS:
                    key = f'gt{round(gap * 100)}pct'
                    row[f'order_{key}'], row[f'pairs_{key}'] = pair_order(a, b, gap=gap)
                row['order_same_run'], row['pairs_same_run'] = pair_order(a, b, groups=frame.run.to_numpy())
                out.append(row)
    return pd.DataFrame(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=RESULTS)
    parser.add_argument('--evidence-dir', type=Path, default=OUTPUT)
    parser.add_argument('--resamples', type=int, default=RESAMPLES)
    args = parser.parse_args(argv)
    table = analyze(load(args.results_dir), args.resamples)
    csv = args.evidence_dir / 'rs_rank_stability.csv'
    table.to_csv(csv, index=False, float_format='%.6g')
    overall = table[table.subset == 'all']
    summary = {'source_journal_sha256': sha(args.results_dir / 'results.jsonl'),
               'table_sha256': sha(csv), 'seed': SEED, 'resamples': args.resamples,
               'note': 'Unweighted description of the 387 round6 settings; not a population estimate.',
               'overall': overall[['quantity', 'first', 'second', 'n', 'spearman', 'spearman_lo', 'spearman_hi',
                                   'kendall', 'order_all', 'order_gt5pct', 'order_same_run',
                                   'median_shift']].to_dict(orient='records')}
    (args.evidence_dir / 'rs_rank_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
