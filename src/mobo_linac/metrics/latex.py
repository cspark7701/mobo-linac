"""
Centralized LaTeX Reporting Module for mobo_linac.

Provides standard publication-grade LaTeX table generators for:
  - Pareto Candidate Verification (stored vs rerun consistency, checksums, error %)
  - Campaign Performance Comparison (Unconstrained Phase 2 vs Constrained Phase 3)
  - Robustness and Sensitivity Summary (Feasibility probability, robust scores)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd


class RawLatex(str):
    """Explicit trusted markup for captions; dynamic data is always escaped."""


def escape_latex(value):
    if isinstance(value, RawLatex):
        return str(value)
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(character, character) for character in str(value))


def measured(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def format_measured(value, precision=4):
    value = measured(value)
    return f"{value:.{precision}f}" if np.isfinite(value) else "--"



def format_scientific(value):
    value = measured(value)
    return f"{value:.4e}" if np.isfinite(value) else "--"

def verification_records(records):
    """Copy records and decode explicit nested CSV fields without changing source data."""
    import json
    if isinstance(records, (str, Path)):
        records = pd.read_csv(records).to_dict(orient="records")
    elif isinstance(records, pd.DataFrame):
        records = records.to_dict(orient="records")
    records = [dict(record) for record in records]
    for record in records:
        for key in ("stored_objectives", "rerun_objectives", "objective_units", "objective_order"):
            if isinstance(record.get(key), str):
                record[key] = json.loads(record[key])
        for group, prefix in (("stored_objectives", "stored"), ("rerun_objectives", "rerun")):
            for name, alias in (("norm_emit_x_m_rad", "emit_x_m_rad"), ("norm_emit_y_m_rad", "emit_y_m_rad"),
                                ("sigma_energy_eV", "sigma_energy_eV")):
                if name in record.get(group, {}):
                    record.setdefault(f"{prefix}_{alias}", record[group][name])
        record.setdefault("verification_status", record.get("status", "COMPARISON_UNKNOWN"))
    if records:
        columns = records[0].get("objective_order", list(records[0].get("stored_objectives", {})))
        units = records[0].get("objective_units", {})
        for record in records[1:]:
            if (record.get("objective_order", list(record.get("stored_objectives", {}))) != columns
                    or record.get("objective_units", {}) != units):
                raise ValueError("Verification objective order/units disagree across records.")
    return records


def _write_table(content, output_path):
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return content


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
    record_list = verification_records(records)
    escape = escape_latex
    columns = record_list[0].get("objective_order", list(record_list[0].get("stored_objectives", {}))) if record_list else []
    legacy_columns = ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
    units = record_list[0].get("objective_units", {}) if record_list else {}
    legacy_units = {"norm_emit_x_m_rad": "m*rad", "norm_emit_y_m_rad": "m*rad", "sigma_energy_eV": "eV"}
    if columns and (columns != legacy_columns or (units and units != legacy_units)):
        units = record_list[0].get("objective_units", {})
        headers = ["Candidate Role"] + [f"{prefix} {escape(name)} ({escape(units.get(name, 'unknown'))})"
                   for name in columns for prefix in ("Stored", "Rerun")] + [r"Max Error (\%)", "Status"]
        tex = [r"\begin{table}[htbp]", r"\centering", f"\\caption{{{escape_latex(caption)}}}", f"\\label{{{label}}}",
               r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{l" + "c" * (2 * len(columns) + 2) + "}",
               r"\toprule", " & ".join(headers) + r" \\", r"\midrule"]
        for record in record_list:
            cells = [escape(record.get("role", "candidate"))]
            for name in columns:
                for group in ("stored_objectives", "rerun_objectives"):
                    value = measured(record.get(group, {}).get(name))
                    cells.append(f"{value:.6g}" if np.isfinite(value) else "--")
            error = measured(record.get("max_diff_pct"))
            cells.extend([f"{error:.4f}" if np.isfinite(error) else "--",
                          escape(record.get("verification_status", "COMPARISON_UNKNOWN"))])
            tex.append(" & ".join(cells) + r" \\")
        tex.extend([r"\bottomrule", r"\end{tabular}}", r"\end{table}"])
        content = "\n".join(tex) + "\n"
        if output_path is not None:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return content

    tex = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{escape_latex(caption)}}}",
        f"\\label{{{label}}}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        r"Candidate Role & Stored $\varepsilon_{n,x}$ ($\mu$m) & Rerun $\varepsilon_{n,x}$ ($\mu$m) & Stored $\sigma_E$ (MeV) & Rerun $\sigma_E$ (MeV) & Max Error (\%) & Status \\",
        r"\midrule",
    ]

    for rec in record_list:
        role_raw = rec.get("role", rec.get("candidate_role", "candidate"))
        role = escape_latex(role_raw)

        # Stored / rerun emittance
        s_ex = measured(rec.get("stored_emit_x_m_rad", rec.get("stored_norm_emit_x")))
        r_ex = measured(rec.get("rerun_emit_x_m_rad", rec.get("rerun_norm_emit_x")))
        s_ex *= 1e6
        r_ex *= 1e6

        # Stored / rerun energy spread
        s_se = measured(rec.get("stored_sigma_energy_eV", rec.get("stored_sigma_e")))
        r_se = measured(rec.get("rerun_sigma_energy_eV", rec.get("rerun_sigma_e")))
        s_se *= 1e-6
        r_se *= 1e-6

        err = measured(rec.get("max_diff_pct", rec.get("max_diff_percent")))
        status = escape(rec.get("verification_status", "COMPARISON_UNKNOWN"))

        tex.append(f"{role} & {format_measured(s_ex)} & {format_measured(r_ex)} & {format_measured(s_se)} & {format_measured(r_se)} & {format_measured(err)} & {status} \\\\")

    tex.extend([
        r"\bottomrule",
        r"\end{tabular}}",
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
        f"\\caption{{{escape_latex(caption)}}}",
        f"\\label{{{label}}}",
        r"\begin{tabular}{lcc}",
        r"\hline\hline",
        r"Metric & Phase 2 (Unconstrained) & Phase 3 (Constrained) \\",
        r"\hline",
        f"Total Evaluations & {p2_metrics.get('total_evaluations', 'N/A')} & {p3_metrics.get('total_evaluations', 'N/A')} \\\\",
        f"Valid Simulations & {p2_metrics.get('valid_evaluations', 'N/A')} & {p3_metrics.get('valid_evaluations', 'N/A')} \\\\",
        f"Feasible Simulations & {p2_metrics.get('feasible_evaluations', 'N/A')} & {p3_metrics.get('feasible_evaluations', 'N/A')} \\\\",
        f"Feasibility Rate (\\%) & {format_measured(p2_metrics.get('feasibility_pct'), 1)}\\% & {format_measured(p3_metrics.get('feasibility_pct'), 1)}\\% \\\\",
        f"All-Point Hypervolume & {format_scientific(p2_metrics.get('all_hv'))} & {format_scientific(p3_metrics.get('all_hv'))} \\\\",
        f"Feasible Hypervolume & {format_scientific(p2_metrics.get('feas_hv'))} & {format_scientific(p3_metrics.get('feas_hv'))} \\\\",
        f"Pareto Set Size & {p2_metrics.get('pareto_size', 'N/A')} & {p3_metrics.get('pareto_size', 'N/A')} \\\\",
        f"Best $\\varepsilon_{{n,x}}$ ($\\mu$m) & {format_measured(p2_metrics.get('min_emit_x_um'), 4)} & {format_measured(p3_metrics.get('min_emit_x_um'), 4)} \\\\",
        f"Best $\\varepsilon_{{n,y}}$ ($\\mu$m) & {format_measured(p2_metrics.get('min_emit_y_um'), 4)} & {format_measured(p3_metrics.get('min_emit_y_um'), 4)} \\\\",
        f"Best $\\sigma_E$ (MeV) & {format_measured(p2_metrics.get('min_sigma_e_mev'), 4)} & {format_measured(p3_metrics.get('min_sigma_e_mev'), 4)} \\\\",
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
    import json
    record_list = [{key: json.loads(value) if key in ("objective_order", "objective_units") and isinstance(value, str) else value
                    for key, value in record.items()} for record in record_list]
    if record_list and "objective_order" in record_list[0]:
        # Configured objectives, recorded per summary, in physical units.
        columns = record_list[0]["objective_order"]
        units = record_list[0].get("objective_units", {})
        headers = ["Candidate Role"] + [f"Nominal {escape_latex(name)} ({escape_latex(units.get(name, 'unknown'))})" for name in columns] \
            + [r"Feasibility $P_{\mathrm{feas}}$", "Robust Score"]
        tex = [r"\begin{table}[htbp]", r"\centering", f"\\caption{{{escape_latex(caption)}}}", f"\\label{{{label}}}",
               r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{l" + "c" * (len(columns) + 2) + "}", r"\toprule",
               " & ".join(headers) + r" \\", r"\midrule"]
        for rec in record_list:
            cells = [escape_latex(rec.get("role", rec.get("candidate_label", "candidate")))]
            cells += [format_scientific(rec.get(f"nominal_{name}")) for name in columns]
            cells += [format_measured(rec.get("probability_of_feasibility"), 2), format_measured(rec.get("robust_score"))]
            tex.append(" & ".join(cells) + r" \\")
        tex += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
        return _write_table("\n".join(tex) + "\n", output_path)

    tex = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{escape_latex(caption)}}}",
        f"\\label{{{label}}}",
        r"\begin{tabular}{lcccc}",
        r"\hline\hline",
        r"Candidate Role & Nominal $\varepsilon_{n,x}$ ($\mu$m) & Nominal $\sigma_E$ (MeV) & Feasibility $P_{\mathrm{feas}}$ & Robust Score \\",
        r"\hline",
    ]

    for rec in record_list:
        role_raw = rec.get("role", rec.get("candidate_role", "candidate"))
        role = escape_latex(role_raw)

        # Named SI fields and documented legacy SI aliases; never guess from magnitudes.
        nom_ex = measured(rec.get("nominal_emit_x_m_rad", rec.get("emit_x"))) * 1e6
        nom_se = measured(rec.get("nominal_sigma_energy_eV", rec.get("sigma_energy"))) * 1e-6
        p_feas = measured(rec.get("probability_of_feasibility", rec.get("p_feas")))
        score = measured(rec.get("robust_score", rec.get("score")))
        tex.append(f"{role} & {format_measured(nom_ex)} & {format_measured(nom_se)} & {format_measured(p_feas, 2)} & {format_measured(score)} " + r"\\")

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


def generate_phase1_cases_latex_table(
    cases_summary_path: Union[str, Path],
    output_path: Union[str, Path],
) -> str:
    """
    Exports publication-grade LaTeX table of Phase 1 Option 2 cases.
    """
    summary_path = Path(cases_summary_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not summary_path.exists():
        raise FileNotFoundError(summary_path)

    df = pd.read_csv(summary_path)

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Phase 1 Scalarized BO multi-case campaign summary across representative operational linac archetypes (Option 2). Feasibility uses all evaluations; minima use all-valid observations. The shared fixed reporting reference point and objective units are recorded in reporting metadata.}",
        r"\label{tab:phase1_cases}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llcccccc}",
        r"\toprule",
        r"\textbf{Case} & \textbf{Operating Mode} & $\mathbf{w} = [w_x, w_y, w_E]$ & \textbf{Evals} & \textbf{Feas. (\%)} & \textbf{Min} $\varepsilon_{n,x}$ [$\mu$m] & \textbf{Min} $\varepsilon_{n,y}$ [$\mu$m] & \textbf{Min} $\sigma_E$ [MeV] \\",
        r"\midrule",
    ]

    for _, row in df.iterrows():
        case_id = str(row["case_id"])
        case_id_tex = escape_latex(case_id)
        name = escape_latex(row["name"])
        if "weights" in row and isinstance(row["weights"], str):
            weights = [float(w) for w in json.loads(row["weights"])]  # recorded per case
        else:
            weights = [float(row[name]) for name in ("w_emit_x", "w_emit_y", "w_energy_spread")]  # archived summaries
        w_str = "$[" + ", ".join(f"{w:.2f}" for w in weights) + "]$"
        n_eval = int(row["num_evaluations"])
        feas_str = f"{int(row['num_feasible'])} ({float(row['feasible_fraction_pct']):.1f}\\%)"
        min_ex = f"{float(row['min_norm_emit_x_um']):.4f}" if pd.notna(row['min_norm_emit_x_um']) else "-"
        min_ey = f"{float(row['min_norm_emit_y_um']):.4f}" if pd.notna(row['min_norm_emit_y_um']) else "-"
        min_se = f"{float(row['min_sigma_energy_MeV']):.4f}" if pd.notna(row['min_sigma_energy_MeV']) else "-"

        lines.append(
            f"\\texttt{{{case_id_tex}}} & {name} & {w_str} & {n_eval} & {feas_str} & {min_ex} & {min_ey} & {min_se} \\\\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}}",
        r"\end{table}",
    ])

    return _write_table("\n".join(lines) + "\n", out_path)
