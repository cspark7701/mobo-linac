#!/usr/bin/env python3
"""Collect the completed round6 analyses as manuscript evidence and summarize them.

``--collect`` copies the checksummed frozen-protocol analysis tables from
``results/revision_round6/analysis_*`` into the evidence directory, after verifying each
against its analysis receipt, and tabulates the recorded proposal tiers of the scaling
campaigns. Without it, only the evidence files are read: the summary JSON files and the two
LaTeX tables that the manuscript inputs are rewritten from them. No analysis choice is made
here; every number is a descriptive restatement of the frozen-protocol outputs.
"""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path
import pandas as pd
from prepare_revision_round6 import ROOT, EVIDENCE, sha

RESULTS = ROOT/'results/revision_round6'
COPIED = {'resolution': ['r6_resolution_fractions.csv', 'r6_resolution_paired.csv',
                         'r6_resolution_classification.csv', 'r6_resolution_tolerances.csv'],
          'scaling': ['r6_scaling_runs.csv', 'r6_scaling_paired.csv', 'r6_scaling_channels.csv']}
LEVELS = ['production', 'fixed_medium', 'fixed_fine', 'combined_medium', 'combined_fine']
LEVEL_NAMES = {'production': 'Production', 'fixed_medium': 'Fixed-source medium',
               'fixed_fine': 'Fixed-source fine', 'combined_medium': 'Combined medium',
               'combined_fine': 'Combined fine'}
ARMS = ['constrained_qlognehvi', 'unconstrained_qlognehvi', 'scalarized_bo']
QUANTITIES = [('norm_emit_x_m_rad', r'$\enx$'), ('norm_emit_y_m_rad', r'$\eny$'),
              ('sigma_energy_eV', r'$\sigma_E$'), ('sigma_x_m', r'$\sigma_x$'),
              ('sigma_y_m', r'$\sigma_y$'), ('sigma_xp_rad', r"$\sigma_{x'}$"),
              ('sigma_yp_rad', r"$\sigma_{y'}$"), ('sigma_z_m', r'$\sigma_z$'),
              ('mean_kinetic_energy_eV', r'$E_\mathrm{kin}$'),
              ('transmission_fraction', 'Transmission')]
CATEGORIES = ['transverse_only', 'energy_only', 'multiple_groups', 'other_only', 'feasible']


def verified_outputs(study, results=RESULTS):
    """The analysis directory of a completed study, after checking its receipt."""
    folder = results/f'analysis_{study}'
    receipt = json.loads((folder/f'r6_{study}_analysis.json').read_text())
    if receipt['spec_sha256'] != sha(EVIDENCE/'r6_specification.json'):
        raise ValueError(f'{study} analysis does not belong to the frozen specification.')
    if receipt['completion_sha256'] != sha(results/study/'complete.json'):
        raise ValueError(f'{study} analysis does not match its completion record.')
    for name, digest in receipt['outputs_sha256'].items():
        if sha(folder/name) != digest:
            raise ValueError(f'Analysis output changed: {name}')
    return folder, receipt


def proposal_tiers(scaling_dir):
    rows = []
    for path in sorted(scaling_dir.glob('*_seed_*/proposal_history.json')):
        arm, seed = path.parent.name.split('_seed_')
        methods = [b['metadata']['method'] for b in json.loads(path.read_text())]
        rows.append({'arm': arm, 'seed': int(seed), 'batches': len(methods),
                     'initial_sobol': methods.count('initial_sobol'), 'primary': methods.count('primary'),
                     'retry': methods.count('retry'),
                     'other': len(methods)-sum(methods.count(m) for m in ['initial_sobol', 'primary', 'retry'])})
    return pd.DataFrame(rows)


def collect(results=RESULTS, out=EVIDENCE):
    sources = {}
    for study, names in COPIED.items():
        folder, receipt = verified_outputs(study, results)
        for name in names:
            if name not in receipt['outputs_sha256']:
                raise ValueError(f'{name} is not a checksummed analysis output.')
            shutil.copyfile(folder/name, out/name)
            sources[name] = {'source': str((folder/name).relative_to(ROOT)) if folder.is_relative_to(ROOT) else name,
                             'sha256': receipt['outputs_sha256'][name]}
        sources[f'r6_{study}_analysis.json'] = {'completion_sha256': receipt['completion_sha256']}
    proposal_tiers(results/'scaling').to_csv(out/'r6_scaling_proposals.csv', index=False)
    (out/'r6_collection.json').write_text(json.dumps(sources, indent=2, sort_keys=True)+'\n')


def flips(classification):
    table = classification.pivot(index='setting_id', columns='level', values='feasible').astype(bool)
    meta = classification[classification.level == 'production'].set_index('setting_id')
    result = {}
    for first, second in [('production', level) for level in LEVELS[1:]] + [
            ('fixed_medium', 'fixed_fine'), ('combined_medium', 'combined_fine')]:
        changed = table.index[table[first] != table[second]]
        result[f'{second} vs {first}'] = {
            'changed': len(changed),
            'infeasible_to_feasible': int((~table[first] & table[second]).sum()),
            'feasible_to_infeasible': int((table[first] & ~table[second]).sum()),
            'arms': meta.loc[changed, 'arm'].value_counts().to_dict(),
            'nearest_channels': meta.loc[changed, 'nearest_channel'].value_counts().to_dict(),
            'largest_absolute_margin': float(meta.loc[changed, 'min_signed_margin'].abs().max()) if len(changed) else None}
    return result


def changes(classification, quantity, level, reference):
    table = classification.pivot(index='setting_id', columns='level', values=quantity)
    if quantity in ('mean_kinetic_energy_eV', 'transmission_fraction'):
        delta = table[level]-table[reference]
        scale = 1e-6 if quantity == 'mean_kinetic_energy_eV' else 1.0
        return {'unit': 'MeV' if scale == 1e-6 else 'absolute', 'median': float(delta.median()*scale),
                'min': float(delta.min()*scale), 'max': float(delta.max()*scale),
                'median_magnitude': float(delta.abs().median()*scale)}
    delta = 100*(table[level]-table[reference])/table[reference]
    return {'unit': 'percent', 'median': float(delta.median()), 'min': float(delta.min()),
            'max': float(delta.max()), 'median_magnitude': float(delta.abs().median()),
            'fraction_lower': float((delta < 0).mean())}


def summarize_resolution(evidence=EVIDENCE):
    fractions = pd.read_csv(evidence/'r6_resolution_fractions.csv')
    paired = pd.read_csv(evidence/'r6_resolution_paired.csv')
    classification = pd.read_csv(evidence/'r6_resolution_classification.csv')
    tolerances = pd.read_csv(evidence/'r6_resolution_tolerances.csv')
    production = classification[classification.level == 'production']
    weighted = {}
    for (level, arm), group in fractions.groupby(['level', 'arm']):
        weighted.setdefault(level, {})[arm] = {
            'mean': float(group.fraction.mean()), 'min': float(group.fraction.min()),
            'max': float(group.fraction.max()),
            'design_se': float(group.design_variance.sum()**.5/len(group)), 'groups': len(group)}
    within = tolerances[tolerances.comparison_valid].groupby(['comparison', 'quantity']).within_tolerance.mean()
    return {
        'settings': len(production), 'settings_by_arm': production.arm.value_counts().to_dict(),
        'boundary': production.boundary.value_counts().to_dict(),
        'attempts': len(classification), 'valid_by_level': classification.groupby('level').simulation_valid.sum().astype(int).to_dict(),
        'runtime_mean_s': classification.groupby('level').runtime_s.mean().to_dict(),
        'weighted_feasible_fraction': weighted,
        'paired': paired.to_dict(orient='records'),
        'flips': flips(classification),
        'changes': {name: {f'{level} vs {reference}': changes(classification, name, level, reference)
                           for level, reference in [('fixed_fine', 'production'), ('combined_fine', 'production'),
                                                    ('fixed_fine', 'fixed_medium'), ('combined_fine', 'combined_medium'),
                                                    ('fixed_fine', 'combined_fine')]}
                    for name, _ in QUANTITIES},
        'within_tolerance': {f'{comparison}|{quantity}': float(value) for (comparison, quantity), value in within.items()},
        'scope': 'Sampled historical primary settings re-tracked at frozen levels; weighted fractions use the '
                 'frozen inclusion probabilities. Tolerances are declared adequacy thresholds, not error bounds.'}


def summarize_scaling(evidence=EVIDENCE):
    runs = pd.read_csv(evidence/'r6_scaling_runs.csv')
    paired = pd.read_csv(evidence/'r6_scaling_paired.csv')
    channels = pd.read_csv(evidence/'r6_scaling_channels.csv')
    tiers = pd.read_csv(evidence/'r6_scaling_proposals.csv')
    wide = runs.pivot(index='seed', columns='arm', values='feasible_fraction')
    post = channels[channels.stage != 'initial'].groupby('arm')[['attempts', *CATEGORIES]].sum()
    shares = post[CATEGORIES].div(post.attempts, axis=0)
    return {
        'campaigns': len(runs), 'attempts': int(channels.attempts.sum()),
        'invalid_attempts': int(runs.invalid_attempts.sum()),
        'arms': {arm: {'feasible_fraction': {k: float(getattr(g.feasible_fraction, k)()) for k in ['mean', 'min', 'max']},
                       'post_init_feasible_fraction': {k: float(getattr(g.post_init_feasible_fraction, k)()) for k in ['mean', 'min', 'max']},
                       'elapsed_h': {k: float(getattr(g.elapsed_wall_time_s, k)()/3600) for k in ['mean', 'median', 'min', 'max']}}
                 for arm, g in runs.groupby('arm')},
        'group_differences': (wide.normalized-wide.raw).to_dict(),
        'paired': paired.to_dict(orient='records'),
        'post_init_category_shares': shares.to_dict(orient='index'),
        'post_init_share_difference_normalized_minus_raw': (shares.loc['normalized']-shares.loc['raw']).to_dict(),
        'proposal_tiers': tiers.groupby('arm')[['batches', 'initial_sobol', 'primary', 'retry', 'other']].sum().to_dict(orient='index'),
        'scope': 'Tests the frozen threshold-normalized residuals with common dimensionless temperature 0.001 '
                 'against raw residuals at temperature 0.001; physical smoothing widths differ, so no pure '
                 'normalization effect is identified. Elapsed times are descriptive on a shared host.'}


def signed(value, digits, plus=False):
    """A number for LaTeX text mode, with a typographic minus sign."""
    text = f'{value:+.{digits}f}' if plus else f'{value:.{digits}f}'
    return f'${text}$' if text[0] in '+-' else text


def interval(row):
    return (f"{signed(row['mean_difference'], 3)} [{signed(row['ci_lower_conditional'], 3)}, "
            f"{signed(row['ci_upper_conditional'], 3)}]")


def float_table(body, caption, label, size='small', column_separation=None):
    """A complete table float, set page-wide by the manuscript's ``\\inputwide``."""
    head = [r'\begin{table}[htbp]', r'\centering', rf'\caption{{{caption}}}', rf'\label{{{label}}}', rf'\{size}']
    if column_separation:
        head.append(rf'\setlength{{\tabcolsep}}{{{column_separation}}}')
    return '\n'.join(head)+'\n'+body+r'\end{table}'+'\n'


def resolution_table(summary):
    paired = pd.DataFrame(summary['paired'])
    lines = [r'\begin{tabular}{lrrrrrr}', r'\toprule',
             r'Level & Constr. & Unconstr. & Scalar. & $\Delta$ vs unconstr. & $\Delta$ vs scalar. & Flips \\', r'\midrule']
    for level in LEVELS:
        frac = summary['weighted_feasible_fraction'][level]
        rows = paired[paired.level == level].set_index('second')
        flip = '--' if level == 'production' else str(summary['flips'][f'{level} vs production']['changed'])
        constrained = frac['constrained_qlognehvi']
        lines.append(f"{LEVEL_NAMES[level]} & {constrained['mean']:.3f} ({constrained['design_se']:.3f}) & "
                     f"{frac['unconstrained_qlognehvi']['mean']:.3f} & {frac['scalarized_bo']['mean']:.3f} & "
                     f"{interval(rows.loc['unconstrained_qlognehvi'])} & {interval(rows.loc['scalarized_bo'])} & {flip} \\\\")
    lines += [r'\bottomrule', r'\end{tabular}']
    se = paired.groupby('level').design_se_conservative.max()
    caption = ('Weighted feasible fractions of the re-tracked stratified sample over all 160\n'
               'evaluations of each run, mean over ten groups. The design standard error of the constraint-aware\n'
               'fraction is in parentheses; the baseline fractions have zero design variance because none of\n'
               'their sampled classifications changed. $\\Delta$ is the paired constraint-aware difference with a\n'
               '\\SI{95}{\\percent} ten-group bootstrap interval conditional on the sampled observations; its\n'
               f"design standard error is {se['fixed_medium']:.3f} at the medium and {se['fixed_fine']:.3f} at the fine levels. Flips count changed\n"
               f"production-profile classifications among the {summary['settings']} settings relative to the production level.")
    return float_table('\n'.join(lines)+'\n', caption, 'tab:retracking', 'footnotesize', '4pt')


def change_cell(entry):
    if entry['min'] == entry['max'] == 0:
        return '0 (all settings)'
    digits = 2 if entry['unit'] == 'MeV' else (4 if entry['unit'] == 'absolute' else 1)
    return f"{signed(entry['median'], digits)} [{signed(entry['min'], digits)}, {signed(entry['max'], digits)}]"


def numerical_table(summary):
    lines = [r'\begin{tabular}{lrrrr}', r'\toprule',
             r'Quantity & Fine vs production & $|$Fine vs medium$|$ & \multicolumn{2}{c}{Within tolerance} \\',
             r' & median [range] & median & fixed & combined \\', r'\midrule']
    for name, label in QUANTITIES:
        entry = summary['changes'][name]
        tolerance = [summary['within_tolerance'][f'{kind}_fine - {kind}_medium|{name}'] for kind in ['fixed', 'combined']]
        digits = 2 if entry['fixed_fine vs fixed_medium']['unit'] == 'MeV' else (4 if entry['fixed_fine vs fixed_medium']['unit'] == 'absolute' else 1)
        magnitude = entry['fixed_fine vs fixed_medium']['median_magnitude']
        lines.append(f"{label} & {change_cell(entry['fixed_fine vs production'])} & "
                     f"{'0' if magnitude == 0 else f'{magnitude:.{digits}f}'} & "
                     f"{tolerance[0]:.3f} & {tolerance[1]:.3f} \\\\")
    lines += [r'\bottomrule', r'\end{tabular}']
    caption = (f"Changes of the exit-plane quantities of the {summary['settings']} re-tracked settings. ``Fine vs\n"
               "production'' is the signed change at the fixed-source fine level relative to production, median\n"
               "and range over settings; ``$|$Fine vs medium$|$'' is the median magnitude of the fixed-source\n"
               "fine-to-medium change. Entries are percentages, except for mean energy (\\si{\\mega\\electronvolt})\n"
               "and transmission (absolute). The last two columns give the fraction of settings whose fine-to-medium\n"
               "change meets the declared tolerance for the fixed-source and combined levels.")
    return float_table('\n'.join(lines)+'\n', caption, 'tab:retracking_values')


def scaling_table(summary):
    paired = {row['endpoint']: row for row in summary['paired']}
    shares = summary['post_init_category_shares']
    lines = [r'\begin{tabular}{lrrrrrrr}', r'\toprule',
             r'Arm & All attempts & After init. & Transverse & Energy & Multiple & $\sigma_z$ only & Time [h] \\', r'\midrule']
    for arm, name in [('raw', 'Raw'), ('normalized', 'Normalized')]:
        data = summary['arms'][arm]
        lines.append(f"{name} & {data['feasible_fraction']['mean']:.3f} & {data['post_init_feasible_fraction']['mean']:.3f} & "
                     f"{shares[arm]['transverse_only']:.3f} & {shares[arm]['energy_only']:.3f} & "
                     f"{shares[arm]['multiple_groups']:.3f} & {shares[arm]['other_only']:.3f} & {data['elapsed_h']['mean']:.2f} \\\\")
    difference = summary['post_init_share_difference_normalized_minus_raw']
    lines.append(r'\midrule')
    bounds = [f"[{signed(paired[k]['ci_lower_conditional'], 3)}, {signed(paired[k]['ci_upper_conditional'], 3)}]"
              for k in ['feasible_fraction', 'post_init_feasible_fraction']]
    lines.append(f"Difference & {signed(paired['feasible_fraction']['mean_difference'], 3)} & "
                 f"{signed(paired['post_init_feasible_fraction']['mean_difference'], 3)} & "
                 + ' & '.join(signed(difference[k], 3, True) for k in ['transverse_only', 'energy_only', 'multiple_groups', 'other_only'])
                 + f" & {signed(paired['elapsed_wall_time_s']['mean_difference']/3600, 2, True)} \\\\")
    lines.append(f"\\quad 95\\% interval & {bounds[0]} & {bounds[1]} & & & & & \\\\")
    lines += [r'\bottomrule', r'\end{tabular}']
    caption = ('Matched raw- and normalized-residual campaigns, ten groups of 160 evaluations per arm.\n'
               'Feasible fractions over all evaluations and after the 16 initial ones are means over groups; the\n'
               'category columns give the shares of post-initialization evaluations that violate only the\n'
               'transverse limits, only the energy band, more than one group, or only the bunch-length limit\n'
               '(transmission was never violated). The difference row gives normalized minus raw, with\n'
               '\\SI{95}{\\percent} paired bootstrap intervals for the feasible fractions, and the mean paired\n'
               'difference in campaign time.')
    return float_table('\n'.join(lines)+'\n', caption, 'tab:scaling', 'footnotesize', '4pt')


def write(evidence=EVIDENCE):
    resolution, scaling = summarize_resolution(evidence), summarize_scaling(evidence)
    inputs = sorted(set(sum(COPIED.values(), []))|{'r6_scaling_proposals.csv'})
    for name, data in [('r6_resolution_summary.json', resolution), ('r6_scaling_summary.json', scaling)]:
        data['inputs_sha256'] = {n: sha(evidence/n) for n in inputs if (evidence/n).exists() and n.split('_')[1] in name}
        (evidence/name).write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
    (evidence/'r6_resolution_table.tex').write_text(resolution_table(resolution))
    (evidence/'r6_numerical_table.tex').write_text(numerical_table(resolution))
    (evidence/'r6_scaling_table.tex').write_text(scaling_table(scaling))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect', action='store_true', help='copy verified analysis outputs from results/ first')
    parser.add_argument('--evidence-dir', type=Path, default=EVIDENCE)
    args = parser.parse_args(argv)
    if args.collect:
        collect(out=args.evidence_dir)
    write(args.evidence_dir)


if __name__ == '__main__':
    main()
