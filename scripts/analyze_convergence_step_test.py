#!/usr/bin/env python3
"""Predeclared analysis of step 3a (rq_protocol.md): step size versus space-charge update.

Per setting and emittance it computes paired relative changes between levels at the same
source, a sample-noise band from the four half-step sources, the mechanism ratio, the
observed order of step convergence with Richardson remainders, and the 1 %-adequacy of
the half and quarter steps. All summaries describe the 15 settings (and the feasible /
infeasible strata fixed in the specification); none is a population estimate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_convergence_matrix as am
from evaluate_convergence_step_test import FOLLOWUP, OUTPUT, SETTINGS, SPEC, ANGLES, GATE
from prepare_revision_round6 import sha

EMITTANCES = am.EMITTANCES
OBJECTIVES = am.OBJECTIVES
PAIRS = {'step_half_quarter': ('half_mc10', 'quarter_mc10'), 'step_quarter_eighth': ('quarter_mc10', 'eighth_mc10'),
         'update_half': ('half_mc10', 'half_mc1'), 'step_half_quarter_mc1': ('half_mc1', 'quarter_mc1')}
REPLICATES = [GATE, *(f'half_mc10_{k}' for k in ANGLES)]
REFERENCE = 'eighth_mc10'
STRATA = {'all': None, 'feasible': True, 'infeasible': False}


def load(out=OUTPUT):
    journal = out / 'results.jsonl'
    complete = json.loads((out / 'complete.json').read_text())
    if sha(journal) != complete['results_sha256']:
        raise ValueError('Journal does not match its completion record.')
    rows = []
    for record in am.read_records(journal).values():
        values = {**(record.get('objectives') or {}), **(record.get('diagnostics') or {})}
        rows.append({'setting_id': record['role'], 'level': record['level'], 'valid': record['simulation_valid'],
                     'feasible': record.get('physically_feasible'), 'runtime_s': record.get('runtime_s'),
                     **{k: values.get(k) for k in [*OBJECTIVES, *am.DIAGNOSTIC_TOLERANCE]}})
    frame = pd.DataFrame(rows)
    numeric = [*OBJECTIVES, *am.DIAGNOSTIC_TOLERANCE, 'runtime_s']
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors='coerce')
    return frame


def noise_band(frame, multiple):
    """Per setting and emittance: multiple x the relative SD of the four half-step sources.
    NaN when any replicate is invalid or missing."""
    rows = []
    for setting, group in frame[frame.level.isin(REPLICATES)].groupby('setting_id'):
        ok = len(group) == len(REPLICATES) and group.valid.all()
        row = {'setting_id': setting, 'replicates_valid': bool(ok)}
        for q in EMITTANCES:
            values = group[q]
            row[f'band_{q}'] = float(multiple * values.std(ddof=1) / values.mean()) if ok and values.notna().all() \
                else np.nan
        rows.append(row)
    return pd.DataFrame(rows).set_index('setting_id')


def changes(frame, band):
    table = frame.set_index(['setting_id', 'level'])
    rows = []
    for setting in sorted(frame.setting_id.unique()):
        for pair, (coarse, fine) in PAIRS.items():
            a, b = table.loc[(setting, coarse)], table.loc[(setting, fine)]
            present = all(pd.notna(x[k]) for x in (a, b) for k in [*OBJECTIVES, *am.DIAGNOSTIC_TOLERANCE])
            valid = bool(a.valid and b.valid and present)
            row = {'setting_id': setting, 'pair': pair, 'coarse': coarse, 'fine': fine, 'valid': valid}
            for q in OBJECTIVES:
                row[f'd_{q}'] = float(b[q] / a[q] - 1) if valid else np.nan
            row['within_1pct'] = valid and all(abs(row[f'd_{q}']) <= 0.01 for q in EMITTANCES)
            limits = [max(0.01, band.loc[setting, f'band_{q}']) if pd.notna(band.loc[setting, f'band_{q}'])
                      else 0.01 for q in EMITTANCES]
            row['within_noise_aware'] = valid and all(abs(row[f'd_{q}']) <= t for q, t in zip(EMITTANCES, limits))
            row['diagnostics_within'] = valid and all(abs(b[k] - a[k]) <= t
                                                      for k, t in am.DIAGNOSTIC_TOLERANCE.items())
            row['feasibility_changed'] = valid and bool(a.feasible) != bool(b.feasible)
            rows.append(row)
    return pd.DataFrame(rows)


def bootstrap_median(values, resamples, seed):
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if not len(values):
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    medians = np.median(values[rng.integers(len(values), size=(resamples, len(values)))], axis=1)
    return tuple(float(v) for v in np.quantile(medians, [0.025, 0.975]))


def present(spec):
    """Strata with at least one setting."""
    flags = set(spec['feasible_at_reference'].values())
    return [k for k, flag in STRATA.items() if flag is None or flag in flags]


def subset(delta, stratum, feasible_map):
    flag = STRATA[stratum]
    return delta if flag is None else delta[delta.setting_id.map(feasible_map) == flag]


def summarize(delta, spec):
    rows = []
    for stratum in present(spec):
        part = subset(delta, stratum, spec['feasible_at_reference'])
        for pair, group in part.groupby('pair', sort=False):
            row = {'stratum': stratum, 'pair': pair, 'n': len(group), 'valid': int(group.valid.sum()),
                   'share_within_1pct': float(group.within_1pct.mean()),
                   'share_within_noise_aware': float(group.within_noise_aware.mean()),
                   'share_diagnostics_within': float(group.diagnostics_within.mean()),
                   'feasibility_changes': int(group.feasibility_changed.sum())}
            for q in OBJECTIVES:
                values = group[f'd_{q}'].dropna()
                row[f'median_{q}'] = float(values.median()) if len(values) else np.nan
                lo, hi = bootstrap_median(values, spec['bootstrap_resamples'], spec['bootstrap_seed'])
                row[f'median_lo_{q}'], row[f'median_hi_{q}'] = lo, hi
            rows.append(row)
    return pd.DataFrame(rows)


def adequacy(summary, spec):
    """Half is assessed against quarter, quarter against eighth (Max_count=10)."""
    tol, limit, share = (spec['objective_tolerance_relative'], spec['systematic_interval_limit_relative'],
                         spec['adequacy_share'])
    rows = []
    for stratum in present(spec):
        for step, pair in [('half', 'step_half_quarter'), ('quarter', 'step_quarter_eighth')]:
            s = summary[(summary.stratum == stratum) & (summary.pair == pair)].iloc[0]
            systematic = all(abs(s[f'median_{q}']) <= tol and abs(s[f'median_lo_{q}']) <= limit
                             and abs(s[f'median_hi_{q}']) <= limit for q in EMITTANCES)
            per_setting = s.share_within_noise_aware >= share
            rows.append({'stratum': stratum, 'step': step, 'pair': pair, 'systematic_met': bool(systematic),
                         'per_setting_share': float(s.share_within_noise_aware), 'per_setting_met': bool(per_setting),
                         'status': 'adequate' if systematic and per_setting else 'not adequate'})
    return pd.DataFrame(rows)


def mechanism(delta, spec):
    """R = (half_mc1 - half_mc10) / (quarter_mc10 - half_mc10), per setting and emittance."""
    wide = delta.pivot(index='setting_id', columns='pair')
    rows, per_setting = [], []
    for stratum in present(spec):
        ids = [s for s in wide.index if STRATA[stratum] is None or spec['feasible_at_reference'][s] == STRATA[stratum]]
        classes = []
        row = {'stratum': stratum}
        for q in EMITTANCES:
            num, den = wide.loc[ids, (f'd_{q}', 'update_half')], wide.loc[ids, (f'd_{q}', 'step_half_quarter')]
            keep = den.abs() >= spec['mechanism_min_denominator_relative']
            ratio = (num / den)[keep].dropna()
            # Relative changes from the same coarse level, so their ratio is the ratio of differences.
            after = wide.loc[ids, (f'd_{q}', 'step_half_quarter_mc1')].abs().median()
            median_r = float(ratio.median()) if len(ratio) else np.nan
            if pd.notna(median_r) and median_r >= spec['mechanism_update_threshold'] and after <= 0.01:
                cls = 'update-interval dominated'
            elif pd.notna(median_r) and median_r <= spec['mechanism_step_threshold']:
                cls = 'step dominated'
            else:
                cls = 'mixed'
            classes.append(cls)
            row.update({f'median_R_{q}': median_r, f'n_R_{q}': int(len(ratio)),
                        f'excluded_small_denominator_{q}': int((~keep).sum()),
                        f'median_abs_step_at_mc1_{q}': float(after), f'class_{q}': cls})
            if stratum == 'all':
                per_setting += [{'setting_id': s, 'quantity': q, 'R': float(num[s] / den[s]) if keep[s] else np.nan}
                                for s in ids]
        row['class'] = classes[0] if len(set(classes)) == 1 else 'mixed'
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(per_setting)


def order(frame, summary, spec):
    """Observed order from the medians and per setting; Richardson remainders at quarter and eighth."""
    table = frame.set_index(['setting_id', 'level'])
    rows = []
    for stratum in present(spec):
        s = summary[summary.stratum == stratum].set_index('pair')
        ids = [x for x in sorted(frame.setting_id.unique())
               if STRATA[stratum] is None or spec['feasible_at_reference'][x] == STRATA[stratum]]
        for q in EMITTANCES:
            a, b = s.loc['step_half_quarter', f'median_{q}'], s.loc['step_quarter_eighth', f'median_{q}']
            p = float(np.log2(a / b)) if a * b > 0 else np.nan
            per, rem_q, rem_e = [], [], []
            for x in ids:
                h, qt, e = (table.loc[(x, lv)] for lv in ('half_mc10', 'quarter_mc10', 'eighth_mc10'))
                if not (h.valid and qt.valid and e.valid):
                    continue
                d1, d2 = qt[q] - h[q], e[q] - qt[q]
                per.append(np.log2(d1 / d2) if d1 * d2 > 0 else np.nan)
                if np.isfinite(p) and p > 0:
                    limit = e[q] + (e[q] - qt[q]) / (2 ** p - 1)
                    rem_q.append(qt[q] / limit - 1)
                    rem_e.append(e[q] / limit - 1)
            per = np.array(per, dtype=float)
            rows.append({'stratum': stratum, 'quantity': q, 'order_from_medians': p,
                         'per_setting_order_median': float(np.nanmedian(per)) if np.isfinite(per).any() else np.nan,
                         'per_setting_order_defined': int(np.isfinite(per).sum()), 'settings': len(ids),
                         'median_remainder_quarter': float(np.median(rem_q)) if rem_q else np.nan,
                         'median_remainder_eighth': float(np.median(rem_e)) if rem_e else np.nan})
    return pd.DataFrame(rows)


def ranks_and_cost(frame):
    rows = []
    for q in EMITTANCES:
        wide = frame.pivot(index='setting_id', columns='level', values=q)
        for level in wide.columns:
            pair = wide[[level, REFERENCE]].dropna()
            rho = am.rank_correlation(pair[level], pair[REFERENCE])
            rows.append({'quantity': q, 'level': level, 'n': len(pair), 'spearman_vs_eighth': rho})
    cost = frame.groupby('level').runtime_s.agg(['count', 'mean', 'max']).reset_index()
    return pd.DataFrame(rows), cost


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--evidence-dir', type=Path, default=FOLLOWUP)
    parser.add_argument('--spec', type=Path, default=SPEC)
    parser.add_argument('--settings', type=Path, default=SETTINGS)
    args = parser.parse_args(argv)
    spec = json.loads(args.spec.read_text())
    frame = load(args.output_dir)
    if set(frame.setting_id) != set(pd.read_csv(args.settings).setting_id) or len(frame) != spec['tracking_attempts']:
        raise ValueError('Results do not cover the frozen plan.')
    band = noise_band(frame, spec['noise_band_sd_multiple'])
    delta = changes(frame, band)
    summary = summarize(delta, spec)
    mech, mech_settings = mechanism(delta, spec)
    ranks, cost = ranks_and_cost(frame)
    outputs = {'rq_changes.csv': delta, 'rq_noise_band.csv': band.reset_index(), 'rq_pairs.csv': summary,
               'rq_adequacy.csv': adequacy(summary, spec), 'rq_mechanism.csv': mech,
               'rq_mechanism_by_setting.csv': mech_settings, 'rq_order.csv': order(frame, summary, spec),
               'rq_rank_agreement.csv': ranks, 'rq_cost.csv': cost}
    for file, table in outputs.items():
        table.to_csv(args.evidence_dir / file, index=False, float_format='%.6g')
    receipt = {'results_sha256': sha(args.output_dir / 'results.jsonl'), 'spec_sha256': sha(args.spec),
               'outputs': {f: sha(args.evidence_dir / f) for f in outputs}}
    (args.evidence_dir / 'rq_analysis_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
