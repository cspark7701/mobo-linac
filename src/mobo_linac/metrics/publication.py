"""Data-driven publication statistics and report adapters, independent of ASTRA."""
from pathlib import Path
import numpy as np

from mobo_linac.io.run_data import RunData, read_comparable_runs, read_run_data
from mobo_linac.io.journal import same_evaluation
from typing import List, Optional, Sequence

from mobo_linac.display import objective_displays
from mobo_linac.metrics.latex import (RawLatex, Table, _markdown_text, _write_table, escape_latex, format_measured,
                                      format_scientific, objective_columns, verification_records, verification_table)
from mobo_linac.metrics.reporting import reporting_metadata, validate_campaign_compatibility
from mobo_linac.metrics.selection import select_representatives
from mobo_linac.result_schema import ResultSchema

def compute_target_distance(values, targets) -> float:
    """Euclidean norm of objective values relative to their configured targets."""
    values, targets = np.asarray(values, dtype=float), np.asarray(targets, dtype=float)
    if values.shape != targets.shape or not np.isfinite(targets).all() or (targets <= 0).any():
        return float("nan")
    return float(np.linalg.norm(values / targets))


def campaign_summary(run):
    """Counts use all history; extrema use feasible measurements; Pareto sets stay distinct.

    The knee target distance uses the configured objective ``target`` values (NaN when any
    objective has no target).
    """
    total = len(run.results)
    valid, feasible = run.valid_results(), run.valid_results(True)
    final = run.hypervolume.iloc[-1] if len(run.hypervolume) else {}
    extrema = {}
    for index, objective in enumerate(run.config.objectives):
        values = [r.objectives_physical[index] for r in feasible]
        extrema[objective.explicit_name] = (min(values) if objective.physical_direction == "minimize" else max(values)) if values else float("nan")
    knee = None
    distance = float("nan")
    if feasible:
        # The same knee definition used by robustness and verification.
        knee = select_representatives(feasible, run.config).roles["knee_point"]
        distance = compute_target_distance(knee.objectives_physical, [d.target for d in objective_displays(run.config)])
    return {
        "total_evaluations": total, "valid_evaluations": len(valid), "feasible_evaluations": len(feasible),
        "validity_pct": 100 * len(valid) / total if total else float("nan"),
        "feasibility_pct": 100 * len(feasible) / total if total else float("nan"),
        "feasibility_valid_pct": 100 * len(feasible) / len(valid) if valid else float("nan"),
        "failure_pct": 100 * (total - len(valid)) / total if total else float("nan"),
        "all_hv": float(final.get("all_point_hypervolume", float("nan"))),
        "feas_hv": float(final.get("feasible_hypervolume", float("nan"))),
        "pareto_size": len(run.pareto()), "feasible_pareto_size": len(run.pareto(True)),
        "objective_extrema": extrema, "knee": knee, "target_distance": distance,
    }


def _summary_rows(runs):
    summaries = [campaign_summary(run) for run in runs]
    rows = []
    for label, key in (("Total ASTRA Evaluations", "total_evaluations"), ("Valid Simulations", "valid_evaluations"),
                       ("Feasible Evaluations", "feasible_evaluations"), ("All-Valid Pareto Size", "pareto_size"),
                       ("Feasible Pareto Size", "feasible_pareto_size")):
        rows.append((label, [str(s[key]) for s in summaries]))
    for label, key, precision in (("Simulation Validity (%)", "validity_pct", 1),
                                  ("Feasibility Rate, All Evaluations (%)", "feasibility_pct", 1),
                                  ("All-Point Hypervolume", "all_hv", 6), ("Feasible Hypervolume", "feas_hv", 6)):
        rows.append((label, [format_scientific(s[key]) if key.endswith("hv") else format_measured(s[key], precision) for s in summaries]))
    for column in objective_columns(runs[0].config):
        rows.append((RawLatex("Best " + column.latex),
                     [column.format(s["objective_extrema"][column.name]) for s in summaries]))
    return rows


def generate_campaign_summary_latex_table(directories, output_path=None, phase_names=None):
    runs = read_comparable_runs(directories)
    names = phase_names or [f"Campaign {i + 1}" for i in range(len(runs))]
    if len(names) != len(runs) or not runs:
        raise ValueError("Campaign names must match a nonempty run list.")
    # Record the actual convention instead of printing an unrelated historical reference.
    caption = ("Campaign summary comparison. Extrema use feasible observations; feasibility rates use all "
               f"evaluations. Fixed model reporting reference: {runs[0].metadata['reporting_ref_point']}; "
               f"objective units: {', '.join(runs[0].metadata['objective_units'])}.")
    rows = _summary_rows(runs)
    table = Table([RawLatex("Metric"), *names], ["Metric", *names],
                  [[label, *cells] for label, cells in rows], caption, "tab:campaign_summary")
    return _write_table(table.to_latex(), output_path)


def _comparison_markdown(runs, names, title, records, wall_times, figures):
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
    for column in objective_columns(runs[0].config):
        lines.append("| Best feasible " + _markdown_text(column.text) + " | "
                     + " | ".join(column.format(s["objective_extrema"][column.name]) for s in summaries) + " |")
    lines.append("| Knee Point Solution | " + " | ".join(
        _markdown_text(str(s["knee"].objectives_physical)) if s["knee"] is not None else "--" for s in summaries) + " |")
    lines.append("| Target Distance (Knee) | " + " | ".join(format_measured(s["target_distance"]) for s in summaries) + " |")
    if wall_times:
        lines.append("| Wall-Clock Runtime [s] | " + " | ".join(format_measured(value, 2) for value in wall_times) + " |")
    if figures:
        lines += ["", "## Comparison Plots", ""]
        for caption, name in figures:
            lines += [f"![{caption}](figures/{name})", ""]
    records = verification_records(records)
    lines += [""] + verification_table(records, runs[0].config).to_markdown(
        "Independent Pareto Candidate Rerun Verification") if records else ["", "No verification records."]
    return "\n".join(lines) + "\n"


COMPARISON_FIGURES = (("Hypervolume Comparison", "hypervolume_comparison.png"),
                      ("Pareto Front Comparison", "pareto_front_comparison.png"),
                      ("Pareto Verification Comparison", "verification_rerun_comparison.png"))


def generate_comparison_report(runs: Sequence[RunData], names: Sequence[str], verification, report_path,
                               title: str = "Multi-Objective Bayesian Optimization Comparison Report",
                               wall_times: Optional[Sequence[float]] = None) -> Path:
    """Markdown comparison of any number of recorded campaigns plus the verification table.

    Figures are linked only when ``figures/<name>`` exists next to the report.
    """
    runs = list(runs)
    if not runs or len(names) != len(runs):
        raise ValueError("Comparison names must match a nonempty run list.")
    report_path = Path(report_path)
    figures = [(title_, name) for title_, name in COMPARISON_FIGURES if (report_path.parent / "figures" / name).is_file()]
    content = _comparison_markdown(runs, list(names), title, verification, wall_times, figures)
    _write_table(content, report_path)
    return report_path


def read_comparison_runs(directories, results=None) -> List[RunData]:
    """Recorded runs with matching conventions; supplied observations must equal the history."""
    runs = read_comparable_runs(directories)
    for run, supplied in zip(runs, results or []):
        if supplied is not None and (len(run.results) != len(supplied)
                                     or any(not same_evaluation(left, right) for left, right in zip(run.results, supplied))):
            raise ValueError("Supplied observations disagree with recorded history.")
    return runs


def scalarized_case_statistics(run):
    """Counts plus all-valid (Pareto) and feasible minima of every configured objective (SI)."""
    stats = campaign_summary(run)
    frame = run.pareto()
    all_valid = {}
    for objective in run.config.objectives:
        name = objective.explicit_name
        column = frame[name] if len(frame) and name in frame else None
        if column is None:
            all_valid[name] = float("nan")
        else:
            all_valid[name] = float(column.min() if objective.physical_direction == "minimize" else column.max())
    return dict(n_eval=stats["total_evaluations"], n_valid=stats["valid_evaluations"],
                n_feas=stats["feasible_evaluations"], feas_pct=stats["feasibility_pct"],
                all_valid_extrema=all_valid, feasible_extrema=stats["objective_extrema"], final_hv=stats["feas_hv"])
