#!/usr/bin/env python3
"""Post-hoc, exploratory look at which settings drive the convergence-matrix changes.

Not part of the predeclared analysis in rm_protocol.md. It uses only the completed
matrix journal and asks: are the same settings sensitive to particles, grid and step,
and do the sensitive settings share exit-plane properties or a feasibility class?
With 15 settings and several measures, the correlations generate hypotheses only;
no multiplicity correction is applied and no conclusion about the population follows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

import analyze_convergence_matrix as am
from evaluate_convergence_matrix import FOLLOWUP, OUTPUT
from prepare_revision_round6 import sha

SENSITIVITIES = ['median_all', 'max_particles', 'max_160k_640k', 'max_grid_48_64', 'max_step']


def per_setting(frame, delta):
    """Sensitivity of each setting (largest |relative change| of the two emittances) and its
    exit-plane properties at the reference level half_g64_n640k."""
    delta = delta.assign(change=delta[[f'd_{q}' for q in am.EMITTANCES]].abs().max(axis=1))
    groups = {'median_all': delta, 'max_particles': delta[delta.kind == 'particles'],
              'max_160k_640k': delta[(delta.kind == 'particles') & delta.coarse.str.endswith('n160k')],
              'max_grid_48_64': delta[(delta.kind == 'grid') & delta.coarse.str.contains('_g48_')],
              'max_step': delta[delta.kind == 'step']}
    out = pd.DataFrame({k: g.groupby('setting_id').change.agg('median' if k == 'median_all' else 'max')
                        for k, g in groups.items()})
    ref = frame[frame.level == am.REFERENCE].set_index('setting_id')
    size = ref[['sigma_x_m', 'sigma_y_m']]
    divergence = ref[['sigma_xp_rad', 'sigma_yp_rad']]
    out['feasible'] = ref.feasible.astype(bool)
    out['max_size_m'] = size.max(axis=1)
    out['size_aspect'] = size.max(axis=1) / size.min(axis=1)
    out['max_divergence_rad'] = divergence.max(axis=1)
    out['divergence_aspect'] = divergence.max(axis=1) / divergence.min(axis=1)
    out['size_times_divergence'] = out.max_size_m * out.max_divergence_rad
    out['emittance_sum_m_rad'] = ref[am.EMITTANCES].sum(axis=1)
    out['sigma_z_m'] = ref.sigma_z_m
    out['transmission_fraction'] = ref.transmission_fraction
    out['feasibility_constant_across_levels'] = frame.groupby('setting_id').feasible.nunique() == 1
    return out.sort_values('median_all', ascending=False)


def correlations(table):
    measures = ['max_size_m', 'size_aspect', 'max_divergence_rad', 'divergence_aspect',
                'size_times_divergence', 'emittance_sum_m_rad', 'sigma_z_m']
    rows = []
    for a in SENSITIVITIES:
        for b in SENSITIVITIES + measures:
            if a != b:
                r = spearmanr(table[a], table[b])
                rows.append({'sensitivity': a, 'versus': b, 'spearman': r.statistic, 'p_unadjusted': r.pvalue})
    return pd.DataFrame(rows)


def strata(delta, table):
    delta = delta.merge(table[['feasible']], left_on='setting_id', right_index=True)
    return (delta.groupby(['kind', 'coarse', 'fine', 'feasible'], sort=False)
            .agg(n=('valid', 'size'), share_emittances_within_1pct=('emittances_within', 'mean'),
                 median_norm_emit_x_m_rad=('d_norm_emit_x_m_rad', 'median'),
                 median_norm_emit_y_m_rad=('d_norm_emit_y_m_rad', 'median'))
            .reset_index())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--evidence-dir', type=Path, default=FOLLOWUP)
    args = parser.parse_args(argv)
    frame = am.load(args.output_dir)
    delta = am.changes(frame)
    table = per_setting(frame, delta)
    feasible, infeasible = table[table.feasible].median_all, table[~table.feasible].median_all
    outputs = {'rm_sensitivity_by_setting.csv': table.reset_index(),
               'rm_sensitivity_correlations.csv': correlations(table),
               'rm_sensitivity_strata.csv': strata(delta, table)}
    for file, data in outputs.items():
        data.to_csv(args.evidence_dir / file, index=False, float_format='%.6g')
    summary = {'exploratory': True, 'results_sha256': sha(args.output_dir / 'results.jsonl'),
               'settings': len(table), 'feasible': int(table.feasible.sum()),
               'median_all_feasible': float(feasible.median()), 'median_all_infeasible': float(infeasible.median()),
               'mann_whitney_p_unadjusted': float(mannwhitneyu(feasible, infeasible).pvalue)
               if len(feasible) and len(infeasible) else np.nan,
               'outputs': {f: sha(args.evidence_dir / f) for f in outputs}}
    (args.evidence_dir / 'rm_sensitivity_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
