"""Data-driven publication statistics and report adapters, independent of ASTRA."""
from pathlib import Path
import numpy as np

from mobo_linac.io.run_data import RunData, read_comparable_runs, read_run_data
from mobo_linac.io.journal import same_evaluation
from mobo_linac.metrics.latex import escape_latex, format_measured, format_scientific, measured, verification_records, _write_table
from mobo_linac.metrics.reporting import reporting_metadata, validate_campaign_compatibility
from mobo_linac.metrics.selection import select_representatives
from mobo_linac.result_schema import ResultSchema

TARGET_EMIT_X_M_RAD = 3.9236e-6
TARGET_EMIT_Y_M_RAD = 3.9236e-6
TARGET_SIGMA_E_EV = 1e6


def compute_target_distance(emit_x, emit_y, sigma_e):
    return float(np.linalg.norm(np.asarray([emit_x, emit_y, sigma_e]) /
                               [TARGET_EMIT_X_M_RAD, TARGET_EMIT_Y_M_RAD, TARGET_SIGMA_E_EV]))


def campaign_summary(run):
    """Counts use all history; extrema use feasible measurements; Pareto sets stay distinct."""
    schema = ResultSchema.from_config(run.config)
    total = len(run.results)
    valid, feasible = run.valid_results(), run.valid_results(True)
    final = run.hypervolume.iloc[-1] if len(run.hypervolume) else {}
    extrema = {}
    for index, objective in enumerate(run.config.objectives):
        values = [r.objectives_physical[index] for r in feasible]
        extrema[objective.explicit_name] = (min(values) if objective.physical_direction == "minimize" else max(values)) if values else float("nan")
    knee = None
    distance = float("nan")
    canonical_units = dict(zip(schema.physical_columns, [obj.unit for obj in run.config.objectives]))
    if feasible:
        # The same knee definition used by robustness and verification.
        knee = select_representatives(feasible, run.config).roles["knee_point"]
        if (canonical_units == {"norm_emit_x_m_rad": "m*rad", "norm_emit_y_m_rad": "m*rad", "sigma_energy_eV": "eV"}
                and list(schema.physical_columns) == ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
                and all(sign == -1 for sign in schema.signs)):
            distance = compute_target_distance(*knee.objectives_physical)
    summary = {
        "total_evaluations": total, "valid_evaluations": len(valid), "feasible_evaluations": len(feasible),
        "validity_pct": 100 * len(valid) / total if total else float("nan"),
        "feasibility_pct": 100 * len(feasible) / total if total else float("nan"),
        "feasibility_valid_pct": 100 * len(feasible) / len(valid) if valid else float("nan"),
        "failure_pct": 100 * (total - len(valid)) / total if total else float("nan"),
        "all_hv": float(final.get("all_point_hypervolume", float("nan"))),
        "feas_hv": float(final.get("feasible_hypervolume", float("nan"))),
        "pareto_size": len(run.pareto()), "feasible_pareto_size": len(run.pareto(True)),
        "objective_extrema": extrema, "knee": knee, "target_distance": distance,
        "min_emit_x_um": extrema.get("norm_emit_x_m_rad", float("nan")) * 1e6 if canonical_units.get("norm_emit_x_m_rad") == "m*rad" else float("nan"),
        "min_emit_y_um": extrema.get("norm_emit_y_m_rad", float("nan")) * 1e6 if canonical_units.get("norm_emit_y_m_rad") == "m*rad" else float("nan"),
        "min_sigma_e_mev": extrema.get("sigma_energy_eV", float("nan")) * 1e-6 if canonical_units.get("sigma_energy_eV") == "eV" else float("nan"),
    }
    return summary


def _summary_rows(runs):
    summaries = [campaign_summary(run) for run in runs]
    rows = []
    for label, key in (("Total ASTRA Evaluations", "total_evaluations"), ("Valid Simulations", "valid_evaluations"),
                       ("Feasible Evaluations", "feasible_evaluations"), ("All-Valid Pareto Size", "pareto_size"),
                       ("Feasible Pareto Size", "feasible_pareto_size")):
        rows.append((label, [str(s[key]) for s in summaries]))
    for label, key, precision in ((r"Simulation Validity (\%)", "validity_pct", 1),
                                  (r"Feasibility Rate, All Evaluations (\%)", "feasibility_pct", 1),
                                  ("All-Point Hypervolume", "all_hv", 6), ("Feasible Hypervolume", "feas_hv", 6)):
        rows.append((label, [format_scientific(s[key]) if key.endswith("hv") else format_measured(s[key], precision) for s in summaries]))
    canonical = {"norm_emit_x_m_rad": (r"Best $\varepsilon_{n,x}$ [$\mu$m$\cdot$rad]", 1e6),
                 "norm_emit_y_m_rad": (r"Best $\varepsilon_{n,y}$ [$\mu$m$\cdot$rad]", 1e6),
                 "sigma_energy_eV": (r"Best $\sigma_E$ [MeV]", 1e-6)}
    for objective in runs[0].config.objectives:
        known_unit = "eV" if objective.explicit_name == "sigma_energy_eV" else "m*rad"
        label, factor = (canonical if objective.unit == known_unit else {}).get(objective.explicit_name, (
            f"Best {escape_latex(objective.explicit_name)} ({escape_latex(objective.unit)})", 1))
        rows.append((label, [format_measured(s["objective_extrema"][objective.explicit_name] * factor) for s in summaries]))
    return rows


def generate_campaign_summary_latex_table(directories, output_path=None, phase_names=None):
    runs = read_comparable_runs(directories)
    names = phase_names or [f"Campaign {i + 1}" for i in range(len(runs))]
    if len(names) != len(runs) or not runs:
        raise ValueError("Campaign names must match a nonempty run list.")
    # Record the actual convention instead of printing an unrelated historical reference.
    reference = escape_latex(str(runs[0].metadata["reporting_ref_point"]))
    units = escape_latex(", ".join(runs[0].metadata["objective_units"]))
    lines = [r"\begin{table}[htbp]", r"\centering",
             r"\caption{Campaign summary comparison. Extrema use feasible observations; feasibility rates use all evaluations. "
             + f"Fixed model reporting reference: {reference}; objective units: {units}.}}",
             r"\label{tab:campaign_summary}", r"\resizebox{\textwidth}{!}{%",
             r"\begin{tabular}{l" + "c" * len(runs) + "}", r"\toprule",
             "Metric & " + " & ".join(escape_latex(name) for name in names) + r" \\", r"\midrule"]
    lines += [label + " & " + " & ".join(cells) + r" \\" for label, cells in _summary_rows(runs)]
    lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
    return _write_table("\n".join(lines) + "\n", output_path)


def _markdown_text(value):
    return str(value).replace("|", r"\|").replace("\n", " ").replace("\r", " ")


def _verification_markdown(records):
    records = verification_records(records)
    columns = records[0].get("objective_order", list(records[0].get("stored_objectives", {}))) if records else []
    units = records[0].get("objective_units", {}) if records else {}
    legacy = ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
    dynamic = bool(columns and (columns != legacy or (units and units != dict(zip(legacy, ["m*rad", "m*rad", "eV"])))))
    if dynamic:
        headers = ["Candidate Role"] + [f"{prefix} {_markdown_text(name)} [{_markdown_text(units.get(name, 'unknown'))}]"
                   for name in columns for prefix in ("Stored", "Rerun")] + ["Max Relative Error [%]", "Status"]
    else:
        headers = ["Candidate Role", "Stored emittance x [um rad]", "Rerun emittance x [um rad]",
                   "Stored spread [MeV]", "Rerun spread [MeV]", "Max Relative Error [%]", "Status"]
    lines = ["## Independent Pareto Candidate Rerun Verification", "",
             f"Recorded candidates: {len(records)}. Statuses are reported as recorded; missing measurements are shown as --.", "",
             "| " + " | ".join(headers) + " |", "| " + " | ".join(":---" for _ in headers) + " |"]
    for record in records:
        cells = [_markdown_text(record.get("role", record.get("candidate_role", "candidate")))]
        if dynamic:
            for name in columns:
                for group in ("stored_objectives", "rerun_objectives"):
                    value = measured(record.get(group, {}).get(name))
                    cells.append(f"{value:.6g}" if np.isfinite(value) else "--")
        else:
            for name, factor in (("stored_emit_x_m_rad", 1e6), ("rerun_emit_x_m_rad", 1e6),
                                 ("stored_sigma_energy_eV", 1e-6), ("rerun_sigma_energy_eV", 1e-6)):
                cells.append(format_measured(measured(record.get(name)) * factor))
        cells += [format_measured(record.get("max_diff_pct", record.get("max_diff_percent")), 8),
                  _markdown_text(record.get("verification_status", "COMPARISON_UNKNOWN"))]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _comparison_markdown(runs, names, title, records, wall_times=None):
    for run in runs[1:]:
        validate_campaign_compatibility(runs[0].metadata, run.metadata)
    lines = [f"# {title}", "", "## Executive Summary", "",
             "This report compares recorded campaign observations under matching reporting conventions. "
             "Invalid simulations remain in evaluation counts; objective extrema use feasible observations.", "",
             "## Campaign Protocol & Methods", "",
             f"- Fixed model reporting reference: {runs[0].metadata['reporting_ref_point']}",
             f"- Objective units: {runs[0].metadata['objective_units']}", "",
             "## Performance Comparison Matrix", "",
             "| Metric | " + " | ".join(names) + " |", "| :--- | " + " :--- |" * len(names)]
    summaries = [campaign_summary(run) for run in runs]
    for label, key in (("Total Evaluation Budget", "total_evaluations"), ("Numerical Valid Simulations", "valid_evaluations"),
                       ("Physically Feasible Beams", "feasible_evaluations"), ("All-Valid Pareto Size", "pareto_size"),
                       ("Feasible Pareto Size", "feasible_pareto_size")):
        lines.append("| " + label + " | " + " | ".join(str(s[key]) for s in summaries) + " |")
    for label, key in (("Simulation Validity [%]", "validity_pct"), ("Feasibility Rate [%]", "feasibility_pct"),
                       ("ASTRA Failure Rate [%]", "failure_pct"), ("All-Point Hypervolume", "all_hv"), ("Feasible Hypervolume", "feas_hv")):
        lines.append("| " + label + " | " + " | ".join(format_scientific(s[key]) if key.endswith("hv") else format_measured(s[key], 6) for s in summaries) + " |")
    for objective in runs[0].config.objectives:
        lines.append("| Best feasible " + _markdown_text(objective.explicit_name) + " [" + _markdown_text(objective.unit) + "] | "
                     + " | ".join(f"{s['objective_extrema'][objective.explicit_name]:.6g}" if np.isfinite(s['objective_extrema'][objective.explicit_name]) else "--" for s in summaries) + " |")
    lines.append("| Knee Point Solution | " + " | ".join(
        _markdown_text(str(s["knee"].objectives_physical)) if s["knee"] is not None else "--" for s in summaries) + " |")
    lines.append("| Target Distance (Knee) | " + " | ".join(format_measured(s["target_distance"]) for s in summaries) + " |")
    if wall_times:
        lines.append("| Wall-Clock Runtime [s] | " + " | ".join(format_measured(value, 2) for value in wall_times) + " |")
    lines += ["", "## Comparison Plots", "", "![Hypervolume Comparison](figures/hypervolume_comparison.png)", "",
              "![Pareto Front Comparison](figures/pareto_front_comparison.png)", "",
              "![Pareto Verification Comparison](figures/verification_rerun_comparison.png)", ""]
    lines += _verification_markdown(records)
    return "\n".join(lines) + "\n"


def generate_comparison_report(run_dir_p2, results_p2, tracker_p2, wall_sec_p2,
                               run_dir_p3, results_p3, tracker_p3, wall_sec_p3,
                               verification_records, report_path):
    runs = []
    for directory, results, tracker in ((run_dir_p2, results_p2, tracker_p2), (run_dir_p3, results_p3, tracker_p3)):
        config = tracker.config
        meta = reporting_metadata(config, tracker.reporting_ref_point.tolist())
        if (Path(directory) / "reporting_metadata.json").exists():
            saved = read_run_data(directory, config)
            validate_campaign_compatibility(meta, saved.metadata)
            if len(results) != len(saved.results) or any(not same_evaluation(left, right) for left, right in zip(results, saved.results)):
                raise ValueError("Supplied observations disagree with recorded history.")
        runs.append(RunData(Path(directory), config, results, meta, tracker.to_dataframe()))
    content = _comparison_markdown(runs, ["Phase 2 (Unconstrained MOBO)", "Phase 3 (Constrained MOBO)"],
                                  "Multi-Objective Bayesian Optimization Validation & Comparison Report",
                                  verification_records, [wall_sec_p2, wall_sec_p3])
    return _write_table(content, report_path)


def generate_three_phase_report(p1_dir, res_p1, p2_dir, res_p2, p3_dir, res_p3, verification_records, output_dir):
    runs = read_comparable_runs([p1_dir, p2_dir, p3_dir])
    for run, supplied in zip(runs, (res_p1, res_p2, res_p3)):
        if len(run.results) != len(supplied) or any(not same_evaluation(left, right) for left, right in zip(run.results, supplied)):
            raise ValueError("Supplied observations disagree with recorded history.")
    content = _comparison_markdown(runs, ["Phase 1 (Scalarized BO)", "Phase 2 (Unconstrained MOBO)", "Phase 3 (Constrained MOBO)"],
                                  "Multi-Phase Linac Bayesian Optimization Comparative Analysis & Verification Report", verification_records)
    path = Path(output_dir) / "comparison_report.md"
    _write_table(content, path)
    return path


def scalarized_case_statistics(run):
    """Legacy case columns with explicit all-valid and feasible extrema, shared counts."""
    stats = campaign_summary(run)
    frame = run.pareto()
    values = {}
    units = {obj.explicit_name: obj.unit for obj in run.config.objectives}
    for field, factor in (("norm_emit_x_m_rad", 1e6), ("norm_emit_y_m_rad", 1e6), ("sigma_energy_eV", 1e-6)):
        required_unit = "eV" if field == "sigma_energy_eV" else "m*rad"
        values[field] = float(frame[field].min()) * factor if len(frame) and field in frame and units.get(field) == required_unit else float("nan")
    return dict(n_eval=stats['total_evaluations'], n_valid=stats['valid_evaluations'],
                n_feas=stats['feasible_evaluations'], feas_pct=stats['feasibility_pct'],
                min_ex_um=values['norm_emit_x_m_rad'], min_ey_um=values['norm_emit_y_m_rad'], min_se_mev=values['sigma_energy_eV'],
                min_ex_feas_um=stats['min_emit_x_um'], min_ey_feas_um=stats['min_emit_y_um'], min_se_feas_mev=stats['min_sigma_e_mev'],
                final_hv=stats['feas_hv'])
