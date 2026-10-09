"""
Publication tables built from one table model with LaTeX and Markdown renderers.

Objective columns come from the configuration (configured label, display unit and scale)
or, without a configuration, from the objective names and units recorded with the data.
Archived records using the earlier 200 MeV column aliases are decoded on read only.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd

# Archived verification/robustness/case files named the three 200 MeV objectives by alias.
_LEGACY_ORDER = ["norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]
_LEGACY_UNITS = {"norm_emit_x_m_rad": "m*rad", "norm_emit_y_m_rad": "m*rad", "sigma_energy_eV": "eV"}
_LEGACY_VERIFICATION_ALIASES = {"norm_emit_x_m_rad": "emit_x_m_rad", "norm_emit_y_m_rad": "emit_y_m_rad",
                                "sigma_energy_eV": "sigma_energy_eV"}


class RawLatex(str):
    """Explicit trusted markup for captions and headers; dynamic data is always escaped."""


def escape_latex(value):
    if isinstance(value, RawLatex):
        return str(value)
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                    "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                    "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(character, character) for character in str(value))


def latex_unit(unit: str) -> str:
    """Display unit as LaTeX text (Unicode micro sign and middle dot become math symbols)."""
    return "".join({"μ": r"$\mu$", "µ": r"$\mu$", "·": r"$\cdot$"}.get(c, escape_latex(c)) for c in str(unit))


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


def _markdown_text(value):
    return str(value).replace("|", r"\|").replace("\n", " ").replace("\r", " ")


@dataclass(frozen=True)
class ReportColumn:
    """One objective column: LaTeX header text, plain header text and the display divisor."""

    name: str
    latex: str
    text: str
    scale: float = 1.0
    precision: Optional[int] = None  # None: 6 significant digits (physical units)

    def format(self, value) -> str:
        value = measured(value) / self.scale
        if not np.isfinite(value):
            return "--"
        return f"{value:.{self.precision}f}" if self.precision is not None else f"{value:.6g}"


def objective_columns(config=None, names: Optional[Sequence[str]] = None,
                      units: Optional[Dict[str, str]] = None) -> List[ReportColumn]:
    """Configured display columns, or recorded names/units shown in physical units."""
    if config is not None:
        from mobo_linac.display import objective_displays
        displays = {d.column: d for d in objective_displays(config)}
        # Configured labels are LaTeX; an unlabelled objective shows its escaped column name.
        latex_labels = {obj.explicit_name: obj.label or escape_latex(obj.explicit_name) for obj in config.objectives}
        selected = list(names) if names is not None else list(displays)
        missing = [name for name in selected if name not in displays]
        if missing:
            raise ValueError(f"Recorded objectives {missing} are not configured.")
        return [ReportColumn(name, f"{latex_labels[name]} [{latex_unit(displays[name].unit)}]",
                             f"{name} [{displays[name].unit}]", displays[name].scale, 4) for name in selected]
    units = units or {}
    return [ReportColumn(name, f"{escape_latex(name)} ({escape_latex(units.get(name, 'unknown'))})",
                         f"{name} [{units.get(name, 'unknown')}]") for name in names or []]


@dataclass
class Table:
    """Header cells (``RawLatex`` for markup) and preformatted plain-text rows."""

    latex_headers: List[str]
    text_headers: List[str]
    rows: List[List[str]]
    caption: str
    label: str
    notes: List[str] = field(default_factory=list)

    def to_latex(self) -> str:
        lines = [r"\begin{table}[htbp]", r"\centering", f"\\caption{{{escape_latex(self.caption)}}}",
                 f"\\label{{{self.label}}}", r"\resizebox{\textwidth}{!}{%",
                 r"\begin{tabular}{l" + "c" * (len(self.latex_headers) - 1) + "}", r"\toprule",
                 " & ".join(escape_latex(cell) for cell in self.latex_headers) + r" \\", r"\midrule"]
        lines += [" & ".join(escape_latex(cell) for cell in row) + r" \\" for row in self.rows]
        lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
        return "\n".join(lines) + "\n"

    def to_markdown(self, title: Optional[str] = None) -> List[str]:
        lines = ([f"## {title}", ""] if title else []) + [*self.notes, *([""] if self.notes else [])]
        lines += ["| " + " | ".join(_markdown_text(h) for h in self.text_headers) + " |",
                  "| " + " | ".join(":---" for _ in self.text_headers) + " |"]
        lines += ["| " + " | ".join(_markdown_text(cell) for cell in row) + " |" for row in self.rows]
        return lines


def _write_table(content, output_path):
    if output_path is not None:
        from mobo_linac.io.durable import atomic_write_text
        atomic_write_text(output_path, content)
    return content


def _records(data) -> List[Dict[str, Any]]:
    if isinstance(data, (str, Path)):
        return pd.read_csv(data).to_dict(orient="records")
    if isinstance(data, pd.DataFrame):
        return data.to_dict(orient="records")
    return [dict(record) for record in data]


def verification_records(records):
    """Copy records, decode nested CSV fields and archived aliases; source data is unchanged."""
    records = _records(records)
    for record in records:
        for key in ("stored_objectives", "rerun_objectives", "objective_units", "objective_order"):
            if isinstance(record.get(key), str):
                record[key] = json.loads(record[key])
        if "stored_objectives" not in record:  # archived alias-only records
            for group, prefix in (("stored_objectives", "stored"), ("rerun_objectives", "rerun")):
                record[group] = {name: record.get(f"{prefix}_{alias}") for name, alias in _LEGACY_VERIFICATION_ALIASES.items()
                                 if f"{prefix}_{alias}" in record}
            record.setdefault("objective_order", [n for n in _LEGACY_ORDER if n in record["stored_objectives"]])
            record.setdefault("objective_units", {n: _LEGACY_UNITS[n] for n in record["objective_order"]})
        record.setdefault("role", record.get("candidate_role", "candidate"))
        record.setdefault("max_diff_pct", record.get("max_diff_percent"))
        record.setdefault("verification_status", record.get("status", "COMPARISON_UNKNOWN"))
    if records:
        columns = records[0].get("objective_order", list(records[0].get("stored_objectives", {})))
        units = records[0].get("objective_units", {})
        for record in records[1:]:
            if (record.get("objective_order", list(record.get("stored_objectives", {}))) != columns
                    or record.get("objective_units", {}) != units):
                raise ValueError("Verification objective order/units disagree across records.")
    return records


def verification_table(records, config=None,
                       caption: str = "Independent Verification Results of Representative Pareto Candidates",
                       label: str = "tab:pareto_verification") -> Table:
    """Stored and rerun value of every recorded objective per verified role."""
    records = verification_records(records)
    names = records[0].get("objective_order", list(records[0].get("stored_objectives", {}))) if records else []
    columns = objective_columns(config, names, records[0].get("objective_units", {}) if records else {})
    latex = [RawLatex("Candidate Role")]
    text = ["Candidate Role"]
    for column in columns:
        for prefix in ("Stored", "Rerun"):
            latex.append(RawLatex(f"{prefix} {column.latex}"))
            text.append(f"{prefix} {column.text}")
    latex += [RawLatex(r"Max Error (\%)"), RawLatex("Status")]
    text += ["Max Relative Error [%]", "Status"]
    rows = []
    for record in records:
        row = [str(record.get("role"))]
        for column in columns:
            row += [column.format(record.get(group, {}).get(column.name)) for group in ("stored_objectives", "rerun_objectives")]
        row += [format_measured(record.get("max_diff_pct")), str(record.get("verification_status"))]
        rows.append(row)
    return Table(latex, text, rows, caption, label)


def generate_verification_latex_table(
    records: Union[List[Dict[str, Any]], pd.DataFrame, str, Path],
    output_path: Optional[Union[str, Path]] = None,
    caption: str = "Independent Verification Results of Representative Pareto Candidates",
    label: str = "tab:pareto_verification",
    config=None,
) -> str:
    """LaTeX verification table (configured labels/units when ``config`` is given)."""
    return _write_table(verification_table(records, config, caption, label).to_latex(), output_path)


def robustness_records(data) -> List[Dict[str, Any]]:
    records = _records(data)
    for record in records:
        for key in ("objective_order", "objective_units"):
            if isinstance(record.get(key), str):
                record[key] = json.loads(record[key])
        if "objective_order" not in record:  # archived summaries named nominal values by alias
            for name, alias in (("norm_emit_x_m_rad", "emit_x"), ("sigma_energy_eV", "sigma_energy")):
                record.setdefault(f"nominal_{name}", record.get(alias))
            record["objective_order"] = [n for n in _LEGACY_ORDER if f"nominal_{n}" in record]
            record["objective_units"] = {n: _LEGACY_UNITS[n] for n in record["objective_order"]}
        record.setdefault("role", record.get("candidate_label", record.get("candidate_role", "candidate")))
        record.setdefault("probability_of_feasibility", record.get("p_feas"))
        record.setdefault("robust_score", record.get("score"))
    return records


def generate_robustness_summary_latex_table(
    robustness_data: Union[List[Dict[str, Any]], pd.DataFrame, str, Path],
    output_path: Optional[Union[str, Path]] = None,
    caption: str = "Machine Tolerance and Perturbation Robustness Summary",
    label: str = "tab:robustness_summary",
    config=None,
) -> str:
    """Nominal objectives, probability of feasibility and robust score per candidate role."""
    records = robustness_records(robustness_data)
    names = records[0]["objective_order"] if records else []
    columns = objective_columns(config, names, records[0].get("objective_units", {}) if records else {})
    latex = [RawLatex("Candidate Role"), *(RawLatex(f"Nominal {c.latex}") for c in columns),
             RawLatex(r"Feasibility $P_{\mathrm{feas}}$"), RawLatex("Robust Score")]
    text = ["Candidate Role", *(f"Nominal {c.text}" for c in columns), "Feasibility P_feas", "Robust Score"]
    rows = [[str(record["role"]), *(c.format(record.get(f"nominal_{c.name}")) for c in columns),
             format_measured(record.get("probability_of_feasibility"), 2), format_measured(record.get("robust_score"))]
            for record in records]
    return _write_table(Table(latex, text, rows, caption, label).to_latex(), output_path)


def case_summary_records(path) -> List[Dict[str, Any]]:
    """Scalarized case rows with SI objective minima (archived μm/MeV columns are converted)."""
    records = _records(path)
    archived = {"norm_emit_x_m_rad": ("min_norm_emit_x_um", 1e-6), "norm_emit_y_m_rad": ("min_norm_emit_y_um", 1e-6),
                "sigma_energy_eV": ("min_sigma_energy_MeV", 1e6)}
    for record in records:
        for key in ("weights", "objective_order", "objective_units"):
            if isinstance(record.get(key), str):
                record[key] = json.loads(record[key])
        if "objective_order" not in record:
            record["objective_order"] = [n for n, (column, _) in archived.items() if column in record]
            record["objective_units"] = {n: _LEGACY_UNITS[n] for n in record["objective_order"]}
            for name in record["objective_order"]:
                column, factor = archived[name]
                record[f"min_{name}"] = measured(record[column]) * factor
        if "weights" not in record:
            record["weights"] = [float(record[name]) for name in ("w_emit_x", "w_emit_y", "w_energy_spread")]
    return records


def generate_phase1_cases_latex_table(
    cases_summary_path: Union[str, Path],
    output_path: Union[str, Path],
    config=None,
) -> str:
    """Scalarized case summary: weights, evaluations, feasibility and all-valid objective minima."""
    summary_path = Path(cases_summary_path)
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    records = case_summary_records(summary_path)
    names = records[0]["objective_order"] if records else []
    columns = objective_columns(config, names, records[0].get("objective_units", {}) if records else {})
    latex = [RawLatex(r"\textbf{Case}"), RawLatex(r"\textbf{Operating Mode}"), RawLatex(r"$\mathbf{w}$"),
             RawLatex(r"\textbf{Evals}"), RawLatex(r"\textbf{Feas. (\%)}"),
             *(RawLatex(r"\textbf{Min} " + c.latex) for c in columns)]
    text = ["Case", "Operating Mode", "w", "Evals", "Feas. (%)", *(f"Min {c.text}" for c in columns)]
    rows = [[RawLatex(f"\\texttt{{{escape_latex(r['case_id'])}}}"), str(r["name"]), "[" + ", ".join(f"{float(w):.2f}" for w in r["weights"]) + "]",
             str(int(r["num_evaluations"])), f"{int(r['num_feasible'])} ({float(r['feasible_fraction_pct']):.1f}%)",
             *(c.format(r.get(f"min_{c.name}")) for c in columns)] for r in records]
    caption = ("Phase 1 Scalarized BO multi-case campaign summary across representative operational linac "
               "archetypes. Feasibility uses all evaluations; minima use all-valid observations. The shared "
               "fixed reporting reference point and objective units are recorded in reporting metadata.")
    return _write_table(Table(latex, text, rows, caption, "tab:phase1_cases").to_latex(), output_path)
