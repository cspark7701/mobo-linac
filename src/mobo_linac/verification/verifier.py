import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from mobo_linac.astra.workdir import read_evaluation_manifest, validate_component, write_once_json
from mobo_linac.config import MoboConfig, load_config
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
from mobo_linac.execution.candidate_evaluator import (
    CandidateEvaluatorBase,
    EvaluationOutcome,
    EvaluationTask,
    compute_metric_deltas,
)
from mobo_linac.io.results import DESIGN_VAR_COLUMNS
from mobo_linac.metrics.pareto import (
    compute_crowding_distances,
    select_representative_pareto_candidates,
)


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """Computes SHA-256 hash checksum for a file."""
    path = Path(file_path)
    if not path.exists():
        return "FILE_NOT_FOUND"

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def select_verification_candidates(
    results: List[EvaluationResult],
) -> Dict[str, EvaluationResult]:
    """
    Selects representative Pareto candidates for verification strictly from the feasible Pareto set.

    Args:
        results: List of EvaluationResult records.

    Returns:
        Dict mapping candidate role -> EvaluationResult.
    """
    cands = select_representative_pareto_candidates(results)
    candidates = {
        "min_emit_x": cands["min_emit_x"],
        "min_emit_y": cands["min_emit_y"],
        "min_sigma_energy": cands["min_sigma_energy"],
        "knee_point": cands["knee_point"],
        "crowding_distance_max": cands["crowding_distance_max"],
        "balanced_feasible": cands["balanced"],
        "robust_recommended": cands["knee_point"],
    }
    return candidates



def run_independent_verification_rerun(
    role: str,
    candidate: EvaluationResult,
    config: MoboConfig,
    output_dir: Union[str, Path] = "results/verification",
    mock_rerun_data: Optional[Dict[str, Any]] = None,
    mock_evaluator: Optional[Any] = None,
    tol_verified: float = 1.0e-3,
    tol_conditional: float = 0.10,
) -> Dict[str, Any]:
    """
    Executes an independent rerun for a Pareto candidate in a fresh workdir,
    computing file checksums, relative differences, and verification status.

    Args:
        role: Candidate role name (e.g. 'knee_point').
        candidate: Original EvaluationResult object.
        config: MoboConfig instance.
        output_dir: Output verification directory.
        mock_rerun_data: Optional mock rerun dictionary for unit testing.
        mock_evaluator: Optional callable for mock batch evaluations in unit testing.
        tol_verified: Tolerance threshold for VERIFIED status (default 1e-3 i.e. 0.1%).
        tol_conditional: Tolerance threshold for CONDITIONALLY_VERIFIED status (default 0.10 i.e. 10%).

    Returns:
        Verification result record dictionary.
    """
    out_path = Path(output_dir)
    validate_component(role)
    verification_run_id = "rerun_" + uuid.uuid4().hex
    work_path = out_path / "candidate_inputs" / role / verification_run_id
    work_path.mkdir(parents=True, exist_ok=False)
    raw_res = {}

    x_phys = candidate.x_physical
    orig_objs = candidate.objectives_physical or [1.0e-6, 1.0e-6, 1.0e6]
    orig_diags = candidate.diagnostics or {}
    orig_feas = candidate.physically_feasible

    input_sha256 = "UNKNOWN"
    field_maps_sha256 = {}
    executable_sha256 = "UNKNOWN"

    if mock_rerun_data is not None:
        rerun_objs = mock_rerun_data.get("objectives_physical", orig_objs)
        rerun_diags = mock_rerun_data.get("diagnostics", orig_diags)
        rerun_feas = mock_rerun_data.get("physically_feasible", True)
        rerun_valid = mock_rerun_data.get("simulation_valid", True)
        input_sha256 = mock_rerun_data.get("input_sha256", "3a7b9f8e02d1c4b...")
        field_maps_sha256 = mock_rerun_data.get("field_maps_sha256", {})
        executable_sha256 = mock_rerun_data.get("executable_sha256", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    elif mock_evaluator is not None:
        raw_res = mock_evaluator(x_phys, run_id=f"verification_{role}", eval_id=role)
        eval_res = create_evaluation_result(raw_res, config)
        rerun_objs = eval_res.objectives_physical or orig_objs
        rerun_diags = eval_res.diagnostics or orig_diags
        rerun_feas = eval_res.physically_feasible
        rerun_valid = eval_res.simulation_valid
    else:
        from mobo_linac.astra.runner import run_astra_eval

        raw_res = run_astra_eval(
            parameters=x_phys,
            run_id=f"verification_{role}",
            eval_id=role,
            base_results_dir=work_path,
            template_dir=".",
            clean_on_success=False,
        )
        eval_res = create_evaluation_result(raw_res, config)
        rerun_objs = eval_res.objectives_physical or [1.0e-6, 1.0e-6, 1.0e6]
        rerun_diags = eval_res.diagnostics or {}
        rerun_feas = eval_res.physically_feasible
        rerun_valid = eval_res.simulation_valid

        manifest = read_evaluation_manifest(raw_res["manifest_path"])
        hashes = manifest.get("input_hashes", {})
        input_sha256 = hashes.get("astra.in", "UNKNOWN")
        field_maps_sha256 = {name: digest for name, digest in hashes.items() if name != "astra.in"}
        executable_sha256 = manifest.get("executable", {}).get("sha256") or "UNKNOWN"

    if not rerun_valid:
        status = "RERUN_FAILED"
        diff_ex_pct = float("nan")
        diff_ey_pct = float("nan")
        diff_se_pct = float("nan")
        diff_trans_pct = float("nan")
        max_diff_pct = float("nan")
    else:
        eval_res_tmp = EvaluationResult(
            evaluation_id=f"rerun_{role}",
            run_id=f"verification_{role}",
            x_physical=x_phys,
            objectives_physical=rerun_objs,
            diagnostics=rerun_diags,
            simulation_valid=rerun_valid,
            physically_feasible=rerun_feas,
        )
        deltas = compute_metric_deltas(candidate, eval_res_tmp)
        diff_ex_pct = deltas["diff_emit_x_pct"]
        diff_ey_pct = deltas["diff_emit_y_pct"]
        diff_se_pct = deltas["diff_sigma_energy_pct"]
        diff_trans_pct = deltas["diff_transmission_pct"]
        max_diff_pct = deltas["max_diff_pct"]

        if max_diff_pct < tol_verified * 100.0:
            status = "VERIFIED"
        elif max_diff_pct < tol_conditional * 100.0 and rerun_feas == orig_feas:
            status = "CONDITIONALLY_VERIFIED"
        else:
            status = "REJECTED"

    record_path = work_path / "verification_record.json"
    record = {
        "verification_run_id": verification_run_id,
        "attempt_id": raw_res.get("attempt_id"),
        "manifest_path": raw_res.get("manifest_path"),
        "record_path": str(record_path),
        "role": role,
        "original_evaluation_id": candidate.evaluation_id,
        "solenoid_field_T": x_phys[0],
        "quad_1_gradient_T_m": x_phys[1],
        "quad_2_gradient_T_m": x_phys[2],
        "gun_phase_deg": x_phys[3],
        "acc1_acc2_phase_deg": x_phys[4],
        "acc3_acc4_phase_deg": x_phys[5],
        "stored_emit_x_m_rad": orig_objs[0],
        "rerun_emit_x_m_rad": rerun_objs[0],
        "stored_emit_y_m_rad": orig_objs[1],
        "rerun_emit_y_m_rad": rerun_objs[1],
        "stored_sigma_energy_eV": orig_objs[2],
        "rerun_sigma_energy_eV": rerun_objs[2],
        "stored_transmission": orig_diags.get("transmission_fraction", 1.0),
        "rerun_transmission": rerun_diags.get("transmission_fraction", 1.0),
        "stored_feasible": orig_feas,
        "rerun_feasible": rerun_feas if rerun_valid else False,
        "diff_emit_x_pct": diff_ex_pct,
        "diff_emit_y_pct": diff_ey_pct,
        "diff_sigma_energy_pct": diff_se_pct,
        "diff_transmission_pct": diff_trans_pct,
        "max_diff_pct": max_diff_pct,
        "verification_status": status,
        "input_sha256": input_sha256,
        "field_maps_sha256": field_maps_sha256,
        "executable_sha256": executable_sha256,
    }

    write_once_json(record_path, record)
    return record


def run_verification_pipeline(
    results: List[EvaluationResult],
    config: Optional[MoboConfig] = None,
    output_dir: Union[str, Path] = "results/verification",
    mock_rerun_data_map: Optional[Dict[str, Dict[str, Any]]] = None,
    mock_evaluator: Optional[Any] = None,
) -> Tuple[List[Dict[str, Any]], Path, Path]:
    """
    Executes independent Pareto verification pipeline across representative candidates,
    running fresh ASTRA evaluations, computing checksums, and exporting results.

    Args:
        results: List of EvaluationResult records.
        config: MoboConfig instance.
        output_dir: Target verification directory.
        mock_rerun_data_map: Optional dict mapping role -> mock_rerun_data for testing.
        mock_evaluator: Optional mock evaluator function.

    Returns:
        Tuple of (records, json_manifest_path, latex_table_path).
    """
    if config is None:
        config = load_config()

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    session_path = create_verification_session(out_path)
    candidates = select_verification_candidates(results)
    records = []

    print(f"=== Starting Independent Pareto Verification ({len(candidates)} candidates) ===")

    for role, candidate in candidates.items():
        mock_data = mock_rerun_data_map.get(role) if mock_rerun_data_map else None
        rec = run_independent_verification_rerun(
            role=role,
            candidate=candidate,
            config=config,
            output_dir=session_path,
            mock_rerun_data=mock_data,
            mock_evaluator=mock_evaluator,
        )
        records.append(rec)
        print(
            f"Candidate [{role:<20}]: Stored ex={rec['stored_emit_x_m_rad']*1e6:.4f} μm | "
            f"Rerun ex={rec['rerun_emit_x_m_rad']*1e6:.4f} μm | "
            f"Max Diff={rec['max_diff_pct']:.6f}% | Status: {rec['verification_status']}"
        )

    manifest_path, tex_path = save_verification_reports(records, session_path, out_path)
    print(f"Pareto verification complete! Artifacts in: {session_path.resolve()}")
    return records, manifest_path, tex_path


def create_verification_session(out_path):
    session = Path(out_path) / "verification_runs" / ("verification_" + uuid.uuid4().hex)
    session.mkdir(parents=True, exist_ok=False)
    return session


def save_verification_reports(records, session_path, out_path):
    """Archive reports once; root reports are compatibility views of the latest run."""
    pd.DataFrame(records).to_csv(session_path / "verification_summary.csv", index=False, mode="x")
    manifest_path = write_once_json(session_path / "verification_manifest.json", {
        "timestamp": pd.Timestamp.now().isoformat(),
        "verification_run_id": session_path.name,
        "total_candidates_verified": len(records),
        "records": records,
    })
    tex_path = export_verification_latex_table(records, session_path / "verification_table.tex")
    for name in ("verification_summary.csv", "verification_manifest.json", "verification_table.tex"):
        temporary = Path(out_path) / ("." + name + "." + uuid.uuid4().hex)
        shutil.copyfile(session_path / name, temporary)
        os.replace(temporary, Path(out_path) / name)
    return manifest_path, tex_path


def export_verification_latex_table(
    records: List[Dict[str, Any]],
    output_path: Union[str, Path] = "results/verification/verification_table.tex",
) -> Path:
    """
    Generates publication-ready LaTeX verification table.

    Args:
        records: List of verification record dictionaries.
        output_path: Path to output .tex file.

    Returns:
        Path object of created .tex file.
    """
    from mobo_linac.metrics.latex import generate_verification_latex_table
    path = Path(output_path)
    generate_verification_latex_table(records, output_path=path)
    return path


class ParetoVerifier(CandidateEvaluatorBase):
    """
    Independent Pareto candidate verification engine.
    Executes fresh rerun simulations in isolated directories and checks reproducibility.
    """

    def __init__(
        self,
        config: Optional[MoboConfig] = None,
        base_output_dir: Union[str, Path] = "results/verification",
        num_workers: int = 1,
        timeout: int = 30,
        tol_verified: float = 1.0e-3,
        tol_conditional: float = 0.10,
    ):
        super().__init__(
            config=config,
            base_output_dir=base_output_dir,
            num_workers=num_workers,
            timeout=timeout,
        )
        self.tol_verified = float(tol_verified)
        self.tol_conditional = float(tol_conditional)

    def generate_evaluation_plan(
        self,
        candidates: Sequence[EvaluationResult],
        roles: Optional[Sequence[str]] = None,
    ) -> List[EvaluationTask]:
        """Generates independent rerun evaluation tasks."""
        tasks: List[EvaluationTask] = []
        for idx, cand in enumerate(candidates):
            role_name = roles[idx] if roles and idx < len(roles) else f"cand_{idx+1}"
            task = EvaluationTask(
                task_id=f"verification_{role_name}",
                role=role_name,
                parameters=cand.x_physical,
                nominal_result=cand,
                metadata={"role": role_name},
            )
            tasks.append(task)
        return tasks

    def verify_candidates(
        self,
        candidates_dict: Dict[str, EvaluationResult],
        mock_evaluator: Optional[Any] = None,
    ) -> Tuple[List[Dict[str, Any]], Path, Path]:
        """
        Runs verification pipeline on candidate dictionary and outputs artifacts.
        """
        out_path = self.base_output_dir
        out_path.mkdir(parents=True, exist_ok=True)

        session_path = create_verification_session(out_path)
        records: List[Dict[str, Any]] = []
        for role, cand in candidates_dict.items():
            rec = run_independent_verification_rerun(
                role=role,
                candidate=cand,
                config=self.config,
                output_dir=session_path,
                mock_evaluator=mock_evaluator,
                tol_verified=self.tol_verified,
                tol_conditional=self.tol_conditional,
            )
            records.append(rec)

        manifest_path, tex_path = save_verification_reports(records, session_path, out_path)
        return records, manifest_path, tex_path
