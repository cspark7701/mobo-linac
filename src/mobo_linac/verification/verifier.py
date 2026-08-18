import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from mobo_linac.config import MoboConfig, load_config
from mobo_linac.evaluation import EvaluationResult, create_evaluation_result
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
    work_path = out_path / "candidate_inputs" / role
    work_path.mkdir(parents=True, exist_ok=True)

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

        eval_dir = Path(raw_res.get("eval_dir", work_path))
        input_file = eval_dir / "astra.in"
        input_sha256 = compute_file_sha256(input_file)
        field_files = ["gun.dat", "PAL_SOL_A.dat", "TWS_Sband.dat", "pal_photo2.ini"]
        field_maps_sha256 = {f: compute_file_sha256(eval_dir / f) for f in field_files if (eval_dir / f).exists()}
        astra_bin = os.environ.get("ASTRA_BIN", "bin/astra")
        executable_sha256 = compute_file_sha256(astra_bin)

    if not rerun_valid:
        status = "RERUN_FAILED"
        diff_ex_pct = float("nan")
        diff_ey_pct = float("nan")
        diff_se_pct = float("nan")
        diff_trans_pct = float("nan")
        max_diff_pct = float("nan")
    else:
        diff_ex_pct = abs(rerun_objs[0] - orig_objs[0]) / orig_objs[0] * 100.0 if orig_objs[0] > 0 else 0.0
        diff_ey_pct = abs(rerun_objs[1] - orig_objs[1]) / orig_objs[1] * 100.0 if orig_objs[1] > 0 else 0.0
        diff_se_pct = abs(rerun_objs[2] - orig_objs[2]) / orig_objs[2] * 100.0 if orig_objs[2] > 0 else 0.0

        orig_trans = orig_diags.get("transmission_fraction", orig_diags.get("transmission", 1.0))
        rerun_trans = rerun_diags.get("transmission_fraction", rerun_diags.get("transmission", 1.0))
        diff_trans_pct = abs(rerun_trans - orig_trans) / orig_trans * 100.0 if orig_trans > 0 else 0.0

        max_diff_pct = max(diff_ex_pct, diff_ey_pct, diff_se_pct, diff_trans_pct)

        if max_diff_pct < tol_verified * 100.0:
            status = "VERIFIED"
        elif max_diff_pct < tol_conditional * 100.0 and rerun_feas == orig_feas:
            status = "CONDITIONALLY_VERIFIED"
        else:
            status = "REJECTED"

    record = {
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

    candidates = select_verification_candidates(results)
    records = []

    print(f"=== Starting Independent Pareto Verification ({len(candidates)} candidates) ===")

    for role, candidate in candidates.items():
        mock_data = mock_rerun_data_map.get(role) if mock_rerun_data_map else None
        rec = run_independent_verification_rerun(
            role=role,
            candidate=candidate,
            config=config,
            output_dir=out_path,
            mock_rerun_data=mock_data,
            mock_evaluator=mock_evaluator,
        )
        records.append(rec)
        print(
            f"Candidate [{role:<20}]: Stored ex={rec['stored_emit_x_m_rad']*1e6:.4f} μm | "
            f"Rerun ex={rec['rerun_emit_x_m_rad']*1e6:.4f} μm | "
            f"Max Diff={rec['max_diff_pct']:.6f}% | Status: {rec['verification_status']}"
        )

    # Save DataFrame / CSV
    df = pd.DataFrame(records)
    csv_path = out_path / "verification_summary.csv"
    df.to_csv(csv_path, index=False)

    # Save JSON manifest
    manifest_path = out_path / "verification_manifest.json"
    manifest_data = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "total_candidates_verified": len(records),
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # Save LaTeX table
    tex_path = export_verification_latex_table(records, out_path / "verification_table.tex")

    print(f"Pareto verification complete! Artifacts in: {out_path.resolve()}")
    return records, manifest_path, tex_path


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


