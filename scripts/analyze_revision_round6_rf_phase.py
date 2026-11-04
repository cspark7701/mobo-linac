#!/usr/bin/env python3
"""C6-10: the RF phase reference and the bunch-length change in the tracked linac.

Reads the retained production-resolution tracking outputs of the round6 sample. For each
travelling-wave structure it fits the tracked energy gain to A cos(phi - crest), where phi is
the absolute input phase, and it reports the RMS bunch length through the structures. No
simulation is run. The fit describes this model's gain maximum; it is not an RF calibration.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from prepare_revision_round6 import EVIDENCE, ROOT

WORK = ROOT/'results/revision_round6/resolution/runs/round6_resolution/work'
STRUCTURES = {'ACC1': 'phi(2)', 'ACC2': 'phi(3)', 'ACC3': 'phi(4)', 'ACC4': 'phi(5)'}
EXIT_M = 16.2


def deck_value(deck, name):
    return float(re.search(re.escape(name)+r'\s*=\s*([-+\d.eE]+)', deck, re.I).group(1))


def setting_row(attempt):
    """Phases, and energy and bunch length at the structure edges, for one tracked setting."""
    deck = (attempt/'astra.in').read_text()
    # Zemit columns: z (m), t (ns), kinetic energy (MeV), RMS bunch length (mm), ...
    z = np.loadtxt(attempt/'astra.Zemit.001')
    starts = [deck_value(deck, f'C_pos({k})') for k in range(2, 6)]
    edges = [*starts, EXIT_M]
    energy = np.interp(edges, z[:, 0], z[:, 2])
    length = np.interp(edges, z[:, 0], z[:, 3])
    row = {'injection_energy_MeV': energy[0], 'exit_energy_MeV': energy[-1]}
    for k, (name, phase) in enumerate(STRUCTURES.items()):
        row[f'{name}_phase_deg'] = deck_value(deck, phase)
        row[f'{name}_gain_MeV'] = energy[k+1]-energy[k]
        row[f'{name}_end_length_mm'] = length[k+1]
    row['entry_length_mm'] = length[0]
    return row


def fit_crest(phase_deg, gain):
    """Least-squares A cos(phi - crest); there is no offset because a structure gains nothing at A = 0."""
    x = np.radians(phase_deg)
    design = np.c_[np.cos(x), np.sin(x)]
    coefficient = np.linalg.lstsq(design, gain, rcond=None)[0]
    residual = gain-design@coefficient
    return {'amplitude_MeV': float(np.hypot(*coefficient)),
            'crest_deg': float(np.degrees(np.arctan2(coefficient[1], coefficient[0]))),
            'residual_rms_MeV': float(np.sqrt(np.mean(residual**2)))}


def spread(series):
    return {'min': float(series.min()), 'median': float(series.median()), 'max': float(series.max())}


def analyze(frame, nominal):
    result = {'settings': len(frame), 'structures': {},
              'injection_energy_MeV': spread(frame.injection_energy_MeV),
              'entry_length_mm': spread(frame.entry_length_mm)}
    for name in STRUCTURES:
        fit = fit_crest(frame[f'{name}_phase_deg'].to_numpy(), frame[f'{name}_gain_MeV'].to_numpy())
        offset = (nominal[name]-fit['crest_deg']+180) % 360-180
        result['structures'][name] = {**fit, 'nominal_phase_deg': nominal[name],
                                      'nominal_minus_crest_deg': float(offset)}
    entry = frame.entry_length_mm
    result['length_ratio_to_entry'] = {f'{name}_end': spread(frame[f'{name}_end_length_mm']/entry)
                                       for name in STRUCTURES}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=WORK)
    parser.add_argument('--output', type=Path, default=EVIDENCE/'r6_rf_phase_fit.json')
    args = parser.parse_args(argv)
    attempts = [sorted(d.glob('attempt_*'))[-1] for d in sorted(args.work_dir.glob('eval_*__production'))]
    frame = pd.DataFrame([setting_row(a) for a in attempts])
    deck = (ROOT/'astra.in').read_text()
    nominal = {name: deck_value(deck, phase) for name, phase in STRUCTURES.items()}
    result = {'note': 'Fit of tracked gain in this model; not an RF calibration.', **analyze(frame, nominal)}
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
