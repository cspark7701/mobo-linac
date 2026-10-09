"""Configured verification service with legacy function wrappers."""
from dataclasses import asdict, replace
import math
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd
import torch

from mobo_linac.astra.workdir import file_sha256, format_eval_id, validate_component, write_once_json
from mobo_linac.diagnostics import diagnostic_observations, normalize_diagnostics
from mobo_linac.evaluation import EvaluationResult
from mobo_linac.execution.candidate_evaluator import CandidateEvaluatorBase, EvaluationTask, compute_metric_deltas
from mobo_linac.metrics.selection import select_representatives
from mobo_linac.result_schema import ResultSchema
from mobo_linac.verification.audit import audit_attempt


def compute_file_sha256(file_path):
    """Compatibility helper; missing files do not receive an invented checksum."""
    return file_sha256(file_path) if Path(file_path).is_file() else None


def select_verification_candidates(results, config):
    """Representative feasible-Pareto roles from the shared selection service."""
    return dict(select_representatives(results, config).roles)


def comparison_status(original, rerun, deltas, tol_verified, tol_conditional):
    if rerun.simulation_valid is not True:
        return 'RERUN_FAILED'
    if (not deltas['comparison_complete'] or original.simulation_valid is not True
            or diagnostic_observations(original.diagnostics) is None
            or diagnostic_observations(rerun.diagnostics) is None
            or original.physically_feasible is None or rerun.physically_feasible is None):
        return 'COMPARISON_UNKNOWN'
    if original.physically_feasible != rerun.physically_feasible:
        return 'REJECTED'
    if deltas['max_diff_pct'] < tol_verified * 100:
        return 'VERIFIED'
    if deltas['max_diff_pct'] < tol_conditional * 100:
        return 'CONDITIONALLY_VERIFIED'
    return 'REJECTED'


class ParetoVerifier(CandidateEvaluatorBase):
    def __init__(self, config, base_output_dir='results/verification', num_workers=None,
                 timeout=None, tol_verified=1e-3, tol_conditional=0.10,
                 template_dir='.', template_in='astra.in'):
        if config is None:
            raise TypeError("Verification requires the campaign MoboConfig.")
        super().__init__(config=config, base_output_dir=base_output_dir,
                         num_workers=config.execution.max_workers if num_workers is None else num_workers,
                         timeout=config.execution.timeout_sec if timeout is None else timeout,
                         template_dir=template_dir, template_in=template_in)
        self.tol_verified, self.tol_conditional = float(tol_verified), float(tol_conditional)
        if not (math.isfinite(self.tol_verified) and math.isfinite(self.tol_conditional)
                and 0 <= self.tol_verified <= self.tol_conditional):
            raise ValueError('Verification tolerances must be finite, nonnegative and ordered')
        if self.timeout <= 0 or self.num_workers <= 0:
            raise ValueError('Verification timeout and worker count must be positive')

    def generate_evaluation_plan(self, candidates, roles=None):
        if roles is not None and len(roles) != len(candidates):
            raise ValueError('roles must match candidates')
        tasks = []
        for index, candidate in enumerate(candidates):
            role = roles[index] if roles is not None else f'cand_{index+1}'
            validate_component(role)
            if len(candidate.x_physical) != len(self.config.design_variables) or not np.isfinite(candidate.x_physical).all():
                raise ValueError('Candidate parameters must be finite and match the configured layout')
            tasks.append(EvaluationTask(task_id=f'verification_{role}', role=role,
                         parameters=list(candidate.x_physical), nominal_result=candidate,
                         metadata={'role': role, 'original_run_id': candidate.run_id,
                                   'original_evaluation_id': candidate.evaluation_id,
                                   'original_attempt_id': candidate.attempt_id}))
        return tasks

    def verify_candidates(self, candidates_dict, mock_evaluator=None, mock_rerun_data_map=None,
                          request_evaluator=None):
        if not candidates_dict:
            raise ValueError('Verification requires candidate data')
        if sum(option is not None for option in (mock_evaluator, mock_rerun_data_map, request_evaluator)) > 1:
            raise ValueError('Choose one verification backend')
        tasks = self.generate_evaluation_plan(list(candidates_dict.values()), list(candidates_dict))
        session = create_verification_session(self.base_output_dir)
        mock = mock_evaluator is not None or mock_rerun_data_map is not None
        if mock_rerun_data_map is not None and set(candidates_dict) - set(mock_rerun_data_map):
            raise ValueError('Explicit mock data must cover every candidate role')
        if mock:
            def adapter(request, *, config):
                role = request.metadata['role']
                if mock_rerun_data_map is not None:
                    data = mock_rerun_data_map[role]
                    raw = {'status': 'SUCCESS' if data.get('simulation_valid', True) else 'RUN_FAILED',
                           'objectives': data.get('objectives_physical'), 'diagnostics': data.get('diagnostics', {})}
                else:
                    raw = mock_evaluator(request.parameters, run_id=f'verification_{role}', eval_id=role)
                if isinstance(raw, EvaluationResult):
                    return replace(raw, evaluation_id=request.eval_id, run_id=session.name,
                                   x_physical=list(request.parameters))
                return dict(raw, eval_id=request.eval_id, run_id=session.name,
                            parameters=list(request.parameters), execution_kind='mock')
            request_evaluator = adapter
        outcomes = self.evaluate_plan_parallel(tasks, request_evaluator=request_evaluator, run_id=session.name)
        records = [self.build_record(outcome, session, mock) for outcome in outcomes]
        manifest, table = save_verification_reports(records, session, self.base_output_dir,
                          {'config': asdict(self.config), 'timeout_sec': self.timeout, 'num_workers': self.num_workers,
                           'template_dir': str(self.template_dir.resolve()), 'template_in': self.template_in,
                           'tol_verified_relative': self.tol_verified, 'tol_conditional_relative': self.tol_conditional})
        return records, manifest, table

    def build_record(self, outcome, session, mock):
        original, rerun = outcome.task.nominal_result, outcome.evaluated_result
        schema = ResultSchema.from_config(self.config)
        deltas = compute_metric_deltas(original, rerun, self.config)
        status = comparison_status(original, rerun, deltas, self.tol_verified, self.tol_conditional)
        original_audit = audit_attempt(original, config=self.config)
        rerun_audit = audit_attempt(rerun, required=True, config=self.config) if not mock else {
            'run_id': rerun.run_id, 'evaluation_id': rerun.evaluation_id, 'attempt_id': None,
            'manifest_path': None, 'input_sha256': None, 'input_hashes': {},
            'executable_sha256': None, 'audit_status': 'MOCK', 'issues': []}
        if rerun.x_physical != outcome.task.parameters or rerun.evaluation_id not in (outcome.task.task_id, format_eval_id(outcome.task.task_id)):
            rerun_audit['issues'].append('Rerun request identity or parameters mismatch')
            rerun_audit['audit_status'] = 'FAILED'
        audited_status = status
        if mock:
            audited_status = 'MOCK_' + status
        elif status in ('VERIFIED', 'CONDITIONALLY_VERIFIED') and (rerun_audit['audit_status'] != 'VERIFIED' or original_audit['audit_status'] == 'FAILED'):
            audited_status = 'AUDIT_FAILED'
        def objective_values(result):
            values = schema.extract(result.objectives_physical)
            return dict(zip(schema.physical_columns, values)) if values is not None else {name: None for name in schema.physical_columns}
        stored, repeated = objective_values(original), objective_values(rerun)
        path = session / 'candidate_inputs' / outcome.task.role / 'verification_record.json'
        path.parent.mkdir(parents=True, exist_ok=False)
        record = {'verification_run_id': session.name, 'role': outcome.task.role,
                  'original_run_id': original.run_id, 'original_evaluation_id': original.evaluation_id,
                  'original_attempt_id': original.attempt_id, 'original_manifest_path': original.manifest_path,
                  'rerun_run_id': rerun.run_id, 'rerun_evaluation_id': rerun.evaluation_id,
                  'attempt_id': rerun.attempt_id, 'manifest_path': rerun.manifest_path, 'record_path': str(path),
                  'execution_kind': 'mock' if mock else 'astra', 'comparison_status': status,
                  'verification_status': audited_status,
                  'design_parameters': dict(zip(schema.design_columns, original.x_physical)),
                  'stored_objectives': stored, 'rerun_objectives': repeated,
                  'objective_units': {obj.explicit_name: obj.unit for obj in self.config.objectives},
                  'objective_order': list(schema.physical_columns),
                  'stored_transmission': normalize_diagnostics(original.diagnostics).get('transmission_fraction'),
                  'rerun_transmission': normalize_diagnostics(rerun.diagnostics).get('transmission_fraction'),
                  'stored_feasible': original.physically_feasible, 'rerun_feasible': rerun.physically_feasible,
                  'stored_simulation_valid': original.simulation_valid, 'rerun_simulation_valid': rerun.simulation_valid,
                  'diagnostics_complete': {'stored': diagnostic_observations(original.diagnostics) is not None,
                                           'rerun': diagnostic_observations(rerun.diagnostics) is not None},
                  'rerun_failure_category': rerun.failure_category, 'rerun_failure_reason': rerun.failure_reason,
                  'original_audit': original_audit, 'rerun_audit': rerun_audit,
                  'input_sha256': rerun_audit['input_sha256'],
                  'field_maps_sha256': {key: value for key, value in rerun_audit['input_hashes'].items() if key != 'astra.in'},
                  'executable_sha256': rerun_audit['executable_sha256'], **deltas}
        record.update(record['design_parameters'])
        for suffix, name in [('emit_x_m_rad', 'norm_emit_x_m_rad'), ('emit_y_m_rad', 'norm_emit_y_m_rad'),
                             ('sigma_energy_eV', 'sigma_energy_eV')]:
            record['stored_' + suffix] = stored.get(name) if stored.get(name) is not None else float('nan')
            record['rerun_' + suffix] = repeated.get(name) if repeated.get(name) is not None else float('nan')
        write_once_json(path, record)
        return record


def run_independent_verification_rerun(role, candidate, config, output_dir='results/verification',
        mock_rerun_data=None, mock_evaluator=None, tol_verified=1e-3, tol_conditional=0.10, **settings):
    verifier = ParetoVerifier(config=config, base_output_dir=output_dir,
                             tol_verified=tol_verified, tol_conditional=tol_conditional, **settings)
    records, _, _ = verifier.verify_candidates({role: candidate}, mock_evaluator=mock_evaluator,
                    mock_rerun_data_map={role: mock_rerun_data} if mock_rerun_data is not None else None)
    return records[0]


def run_verification_pipeline(results, config, output_dir='results/verification',
                              mock_rerun_data_map=None, mock_evaluator=None, **settings):
    verifier = ParetoVerifier(config=config, base_output_dir=output_dir, **settings)
    selection = select_representatives(results, config)
    selection.write(Path(output_dir) / "representatives.json")
    return verifier.verify_candidates(dict(selection.roles),
               mock_evaluator=mock_evaluator, mock_rerun_data_map=mock_rerun_data_map)


def create_verification_session(out_path):
    session = Path(out_path) / 'verification_runs' / ('verification_' + uuid.uuid4().hex)
    session.mkdir(parents=True, exist_ok=False)
    return session


def save_verification_reports(records, session_path, out_path, settings=None):
    rows = [{key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
             for key, value in record.items()} for record in records]
    pd.DataFrame(rows).to_csv(session_path / 'verification_summary.csv', index=False, mode='x')
    manifest = write_once_json(session_path / 'verification_manifest.json', {
        'timestamp': pd.Timestamp.now().isoformat(), 'verification_run_id': session_path.name,
        'total_candidates_verified': len(records), 'settings': settings or {}, 'records': records})
    table = export_verification_latex_table(records, session_path / 'verification_table.tex')
    for name in ('verification_summary.csv', 'verification_manifest.json', 'verification_table.tex'):
        temporary = Path(out_path) / ('.' + name + '.' + uuid.uuid4().hex)
        shutil.copyfile(session_path / name, temporary)
        os.replace(temporary, Path(out_path) / name)
    return manifest, table


def export_verification_latex_table(records, output_path='results/verification/verification_table.tex'):
    from mobo_linac.metrics.latex import generate_verification_latex_table
    path = Path(output_path)
    generate_verification_latex_table(records, output_path=path)
    return path
