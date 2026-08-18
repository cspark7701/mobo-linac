"""
Centralized LaTeX Reporting Module for mobo_linac.

Provides standard publication-grade LaTeX table generators for:
  - Pareto Candidate Verification (stored vs rerun consistency, checksums, error %)
  - Campaign Performance Comparison (Unconstrained Phase 2 vs Constrained Phase 3)
  - Robustness and Sensitivity Summary (Feasibility probability, robust scores)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd


def generate_verification_latex_table(
    records: Union[List[Dict[str, Any]], pd.DataFrame, str, Path],
    output_path: Optional[Union[str, Path]] = None,
    caption: str = "Independent Verification Results of Representative Pareto Candidates",
    label: str = "tab:pareto_verification",
) -> str:
    """
    Generates publication-ready LaTeX verification table comparing stored vs rerun metrics.

    Args:
        records: List of record dictionaries, DataFrame, or path to verification_summary.csv.
        output_path: Optional path to write output .tex file.
        caption: Table caption.
        label: LaTeX label for cross-referencing.

    Returns:
        String containing complete LaTeX table block.
    """
    if isinstance(records, (str, Path)):
        df = pd.read_csv(records)
        record_list = df.to_dict(orient="records")
    elif isinstance(records, pd.DataFrame):
        record_list = records.to_dict(orient="records")
    else:
        record_list = records

    tex = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        r"\begin{tabular}{lcccccc}",
        r"\hline\hline",
        r"Candidate Role & Stored $\varepsilon_{n,x}$ ($\mu$m) & Rerun $\varepsilon_{n,x}$ ($\mu$m) & Stored $\sigma_E$ (MeV) & Rerun $\sigma_E$ (MeV) & Max Error (\%) & Status \\",
        r"\hline",
    ]

    for rec in record_list:
        role_raw = rec.get("role", rec.get("candidate_role", "candidate"))
        role = str(role_raw).replace("_", r"\_")

        # Stored / rerun emittance
        s_ex = rec.get("stored_emit_x_m_rad", rec.get("stored_norm_emit_x", 0.0))
        r_ex = rec.get("rerun_emit_x_m_rad", rec.get("rerun_norm_emit_x", s_ex))
        if s_ex < 1e-2:  # in m*rad -> scale to um
            s_ex *= 1e6
            r_ex *= 1e6

        # Stored / rerun energy spread
        s_se = rec.get("stored_sigma_energy_eV", rec.get("stored_sigma_e", 0.0))
        r_se = rec.get("rerun_sigma_energy_eV", rec.get("rerun_sigma_e", s_se))
        if s_se > 1e2:  # in eV -> scale to MeV
            s_se *= 1e-6
            r_se *= 1e-6

        err = rec.get("max_diff_pct", rec.get("max_diff_percent", 0.0))
        status = str(rec.get("verification_status", "VERIFIED"))

        tex.append(f"{role} & {s_ex:.4f} & {r_ex:.4f} & {s_se:.4f} & {r_se:.4f} & {err:.4f} & {status} \\\\")

    tex.extend([
        r"\hline\hline",
        r"\end{tabular}",
        r"\end{table}",
    ])

    content = "\n".join(tex) + "\n"

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    return content


def generate_results_summary_latex_table(
    p2_metrics: Dict[str, Any],
    p3_metrics: Dict[str, Any],
    output_path: Optional[Union[str, Path]] = None,
    caption: str = "Performance Comparison: Unconstrained (Phase 2) vs. Constrained (Phase 3) MOBO",
    label: str = "tab:results_summary",
) -> str:
    """
    Generates a campaign summary LaTeX table comparing Phase 2 vs Phase 3 performance metrics.

    Args:
        p2_metrics: Dictionary of Phase 2 campaign summary statistics.
        p3_metrics: Dictionary of Phase 3 campaign summary statistics.
        output_path: Optional path to write output .tex file.
        caption: Table caption.
        label: LaTeX label for cross-referencing.

    Returns:
        String containing complete LaTeX table block.
    """
    tex = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        r"\begin{tabular}{lcc}",
        r"\hline\hline",
        r"Metric & Phase 2 (Unconstrained) & Phase 3 (Constrained) \\",
        r"\hline",
        f"Total Evaluations & {p2_metrics.get('total_evaluations', 'N/A')} & {p3_metrics.get('total_evaluations', 'N/A')} \\\\",
        f"Valid Simulations & {p2_metrics.get('valid_evaluations', 'N/A')} & {p3_metrics.get('valid_evaluations', 'N/A')} \\\\",
        f"Feasible Simulations & {p2_metrics.get('feasible_evaluations', 'N/A')} & {p3_metrics.get('feasible_evaluations', 'N/A')} \\\\",
        f"Feasibility Rate (\\%) & {p2_metrics.get('feasibility_pct', 0.0):.1f}\\% & {p3_metrics.get('feasibility_pct', 0.0):.1f}\\% \\\\",
        f"All-Point Hypervolume & {p2_metrics.get('all_hv', 0.0):.4e} & {p3_metrics.get('all_hv', 0.0):.4e} \\\\",
        f"Feasible Hypervolume & {p2_metrics.get('feas_hv', 0.0):.4e} & {p3_metrics.get('feas_hv', 0.0):.4e} \\\\",
        f"Pareto Set Size & {p2_metrics.get('pareto_size', 'N/A')} & {p3_metrics.get('pareto_size', 'N/A')} \\\\",
        f"Best $\\varepsilon_{{n,x}}$ ($\\mu$m) & {p2_metrics.get('min_emit_x_um', 0.0):.4f} & {p3_metrics.get('min_emit_x_um', 0.0):.4f} \\\\",
        f"Best $\\varepsilon_{{n,y}}$ ($\\mu$m) & {p2_metrics.get('min_emit_y_um', 0.0):.4f} & {p3_metrics.get('min_emit_y_um', 0.0):.4f} \\\\",
        f"Best $\\sigma_E$ (MeV) & {p2_metrics.get('min_sigma_e_mev', 0.0):.4f} & {p3_metrics.get('min_sigma_e_mev', 0.0):.4f} \\\\",
        r"\hline\hline",
        r"\end{tabular}",
        r"\end{table}",
    ]

    content = "\n".join(tex) + "\n"

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    return content


def generate_robustness_summary_latex_table(
    robustness_data: Union[List[Dict[str, Any]], pd.DataFrame, str, Path],
    output_path: Optional[Union[str, Path]] = None,
    caption: str = "Machine Tolerance and Perturbation Robustness Summary",
    label: str = "tab:robustness_summary",
) -> str:
    """
    Generates LaTeX table summarizing engineering tolerance and perturbation robustness.

    Args:
        robustness_data: List of robustness summaries, DataFrame, or path to robustness_summary.csv.
        output_path: Optional path to write output .tex file.
        caption: Table caption.
        label: LaTeX label.

    Returns:
        String containing complete LaTeX table block.
    """
    if isinstance(robustness_data, (str, Path)):
        df = pd.read_csv(robustness_data)
        record_list = df.to_dict(orient="records")
    elif isinstance(robustness_data, pd.DataFrame):
        record_list = robustness_data.to_dict(orient="records")
    else:
        record_list = robustness_data

    tex = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        r"\begin{tabular}{lcccc}",
        r"\hline\hline",
        r"Candidate Role & Nominal $\varepsilon_{n,x}$ ($\mu$m) & Nominal $\sigma_E$ (MeV) & Feasibility $P_{\mathrm{feas}}$ & Robust Score \\",
        r"\hline",
    ]

    for rec in record_list:
        role_raw = rec.get("role", rec.get("candidate_role", "candidate"))
        role = str(role_raw).replace("_", r"\_")

        # Nominal objectives
        nom_ex = rec.get("nominal_emit_x_m_rad", rec.get("emit_x", 0.0))
        if nom_ex < 1e-2:
            nom_ex *= 1e6
        nom_se = rec.get("nominal_sigma_energy_eV", rec.get("sigma_energy", 0.0))
        if nom_se > 1e2:
            nom_se *= 1e-6

        p_feas = rec.get("probability_of_feasibility", rec.get("p_feas", 1.0))
        score = rec.get("robust_score", rec.get("score", 1.0))

        tex.append(f"{role} & {nom_ex:.4f} & {nom_se:.4f} & {p_feas:.2f} & {score:.4f} \\\\")

    tex.extend([
        r"\hline\hline",
        r"\end{tabular}",
        r"\end{table}",
    ])

    content = "\n".join(tex) + "\n"

    if output_path is not None:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    return content
