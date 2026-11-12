#!/usr/bin/env python3
"""Predeclared analysis of the grid x particle convergence matrix (rm_protocol.md).

Per setting it computes the relative change of each objective for every refinement in
the matrix: particles x4 at a fixed grid (half step), the next grid at fixed particles
(half step), and half -> quarter step at 64 cells (40k and 640k). A half-step point is
1 %-adequate if, for every refinement available from it, at least the declared share of
settings changes both emittances by at most 1 %. Diagnostics are compared with the
round6 tolerances. All summaries describe the 15 settings; none is a population estimate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from evaluate_convergence_matrix import FOLLOWUP, GRIDS, OUTPUT, PARTICLES, SETTINGS, SPEC
from evaluate_revision_round6_resolution import read_records
from prepare_revision_round6 import sha

OBJECTIVES = ['norm_emit_x_m_rad', 'norm_emit_y_m_rad', 'sigma_energy_eV']
EMITTANCES = OBJECTIVES[:2]
# Round6 refinement tolerances (r6_specification.json): 1 % of the 1 mm / 1 mrad limits,
# 10 keV energy, 1e-4 transmission.
DIAGNOSTIC_TOLERANCE = {'sigma_x_m': 1e-5, 'sigma_y_m': 1e-5, 'sigma_xp_rad': 1e-5, 'sigma_yp_rad': 1e-5,
                        'sigma_z_m': 1e-5, 'mean_kinetic_energy_eV': 1e4, 'transmission_fraction': 1e-4}
REFERENCE = 'half_g64_n640k'


def name(grid, particles, step='half'):
    return f'{step}_g{grid}_n{particles}k'


def refinements():
    """(kind, coarse level, fine level) for every refinement in the matrix."""
    out = [('particles', name(g, a), name(g, b)) for g in GRIDS for a, b in zip(PARTICLES, PARTICLES[1:])]
    out += [('grid', name(a, n), name(b, n)) for n in PARTICLES for a, b in zip(GRIDS, GRIDS[1:])]
    out += [('step', name(64, n), name(64, n, 'quarter')) for n in (40, 640)]
    return out


def load(out=OUTPUT):
    journal = out / 'results.jsonl'
    complete = json.loads((out / 'complete.json').read_text())
    if sha(journal) != complete['results_sha256']:
        raise ValueError('Journal does not match its completion record.')
    rows = []
    for record in read_records(journal).values():
        values = {**(record.get('objectives') or {}), **(record.get('diagnostics') or {})}
        rows.append({'setting_id': record['role'], 'level': record['level'], 'valid': record['simulation_valid'],
                     'feasible': record.get('physically_feasible'),
                     **{k: values.get(k) for k in [*OBJECTIVES, *DIAGNOSTIC_TOLERANCE]}})
    frame = pd.DataFrame(rows)
    numeric = [*OBJECTIVES, *DIAGNOSTIC_TOLERANCE]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors='coerce')
    return frame


def changes(frame):
    """One row per setting and refinement: relative objective changes and diagnostic checks."""
    table = frame.set_index(['setting_id', 'level'])
    rows = []
    for setting in sorted(frame.setting_id.unique()):
        for kind, coarse, fine in refinements():
            a, b = table.loc[(setting, coarse)], table.loc[(setting, fine)]
            present = all(pd.notna(x[k]) for x in (a, b) for k in [*OBJECTIVES, *DIAGNOSTIC_TOLERANCE])
            row = {'setting_id': setting, 'kind': kind, 'coarse': coarse, 'fine': fine,
                   'valid': bool(a.valid and b.valid and present)}
            for q in OBJECTIVES:
                row[f'd_{q}'] = float(b[q] / a[q] - 1) if row['valid'] else np.nan
            row['emittances_within'] = row['valid'] and all(abs(row[f'd_{q}']) <= 0.01 for q in EMITTANCES)
            row['diagnostics_within'] = row['valid'] and all(abs(b[k] - a[k]) <= t
                                                             for k, t in DIAGNOSTIC_TOLERANCE.items())
            row['feasibility_changed'] = row['valid'] and bool(a.feasible) != bool(b.feasible)
            rows.append(row)
    return pd.DataFrame(rows)


def summarize(delta):
    rows = []
    for (kind, coarse, fine), group in delta.groupby(['kind', 'coarse', 'fine'], sort=False):
        row = {'kind': kind, 'coarse': coarse, 'fine': fine, 'n': len(group), 'valid': int(group.valid.sum()),
               'share_emittances_within_1pct': float(group.emittances_within.mean()),
               'share_diagnostics_within': float(group.diagnostics_within.mean()),
               'feasibility_changes': int(group.feasibility_changed.sum())}
        for q in OBJECTIVES:
            values = group[f'd_{q}'].dropna()
            row[f'median_{q}'] = float(values.median()) if len(values) else np.nan
            row[f'median_abs_{q}'] = float(values.abs().median()) if len(values) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def adequacy(summary, share):
    """Half-step points whose every available refinement meets the declared share."""
    by_coarse = summary.groupby('coarse')
    rows = []
    for grid in GRIDS:
        for particles in PARTICLES:
            point = name(grid, particles)
            group = by_coarse.get_group(point)
            met = group.share_emittances_within_1pct >= share
            row = {'point': point, 'refinements': ';'.join(group.kind),
                   'min_share': float(group.share_emittances_within_1pct.min())}
            if not {'particles', 'grid'} & set(group.kind):
                # The finest point has only the step check; grid and particles cannot be assessed.
                row['status'] = 'terminal (step check ' + ('met)' if met.all() else 'not met)')
            else:
                row['status'] = 'adequate' if met.all() else 'not adequate'
            rows.append(row)
    return pd.DataFrame(rows)


def particle_extrapolation(frame):
    """Per grid and emittance: ratio of successive x4 changes, and the geometric-extrapolated
    remaining change at 640k, only where both changes have the same sign."""
    table = frame.set_index(['setting_id', 'level'])
    rows = []
    for setting in sorted(frame.setting_id.unique()):
        for grid in GRIDS:
            q40, q160, q640 = (table.loc[(setting, name(grid, n))] for n in PARTICLES)
            for q in EMITTANCES:
                d1, d2 = q160[q] - q40[q], q640[q] - q160[q]
                ratio = d2 / d1 if d1 else np.nan
                residual = (d2 * ratio / (1 - ratio)) / q640[q] if 0 < ratio < 1 else np.nan
                rows.append({'setting_id': setting, 'grid': grid, 'quantity': q, 'ratio': ratio,
                             'remaining_at_640k': residual})
    return pd.DataFrame(rows)


def rank_agreement(frame):
    """Spearman correlation of each level with the half-step 64-cell 640k level."""
    out = []
    for q in EMITTANCES:
        wide = frame.pivot(index='setting_id', columns='level', values=q)
        for level in wide.columns:
            pair = wide[[level, REFERENCE]].dropna()
            rho = np.corrcoef(rankdata(pair[level]), rankdata(pair[REFERENCE]))[0, 1]
            out.append({'quantity': q, 'level': level, 'n': len(pair), 'spearman_vs_reference': float(rho)})
    return pd.DataFrame(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--evidence-dir', type=Path, default=FOLLOWUP)
    parser.add_argument('--spec', type=Path, default=SPEC)
    parser.add_argument('--settings', type=Path, default=SETTINGS)
    args = parser.parse_args(argv)
    spec = json.loads(args.spec.read_text())
    frame = load(args.output_dir)
    expected = set(pd.read_csv(args.settings).setting_id)
    if set(frame.setting_id) != expected or len(frame) != spec['tracking_attempts']:
        raise ValueError('Results do not cover the frozen plan.')
    delta = changes(frame)
    summary = summarize(delta)
    outputs = {'rm_changes.csv': delta, 'rm_refinements.csv': summary,
               'rm_adequacy.csv': adequacy(summary, spec['adequacy_share']),
               'rm_particle_extrapolation.csv': particle_extrapolation(frame),
               'rm_rank_agreement.csv': rank_agreement(frame)}
    for file, table in outputs.items():
        table.to_csv(args.evidence_dir / file, index=False, float_format='%.6g')
    receipt = {'results_sha256': sha(args.output_dir / 'results.jsonl'), 'spec_sha256': sha(args.spec),
               'outputs': {f: sha(args.evidence_dir / f) for f in outputs}}
    (args.evidence_dir / 'rm_analysis_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
