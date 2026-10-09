"""
Unit tests for Centralized LaTeX Table Generators (Refactor C).
"""

from pathlib import Path
import pytest
import pandas as pd

from mobo_linac.metrics.latex import (
    generate_verification_latex_table,
    generate_results_summary_latex_table,
    generate_robustness_summary_latex_table,
)


@pytest.fixture
def sample_verification_records():
    return [
        {
            "role": "knee_point",
            "stored_emit_x_m_rad": 1.25e-6,
            "rerun_emit_x_m_rad": 1.25e-6,
            "stored_sigma_energy_eV": 4.5e4,
            "rerun_sigma_energy_eV": 4.5e4,
            "max_diff_pct": 0.0001,
            "verification_status": "VERIFIED",
        },
        {
            "role": "min_emit_x",
            "stored_emit_x_m_rad": 0.85e-6,
            "rerun_emit_x_m_rad": 0.85e-6,
            "stored_sigma_energy_eV": 8.0e4,
            "rerun_sigma_energy_eV": 8.0e4,
            "max_diff_pct": 0.0002,
            "verification_status": "VERIFIED",
        },
    ]


@pytest.fixture
def sample_robustness_records():
    return [
        {
            "role": "knee_point",
            "nominal_emit_x_m_rad": 1.25e-6,
            "nominal_sigma_energy_eV": 4.5e4,
            "probability_of_feasibility": 0.95,
            "robust_score": 0.92,
        },
        {
            "role": "balanced_feasible",
            "nominal_emit_x_m_rad": 1.10e-6,
            "nominal_sigma_energy_eV": 5.0e4,
            "probability_of_feasibility": 0.90,
            "robust_score": 0.88,
        },
    ]


def test_generate_verification_latex_table(sample_verification_records, tmp_path):
    """Test generating LaTeX verification table from list and writing to file."""
    tex_path = tmp_path / "verification_table.tex"
    tex_content = generate_verification_latex_table(sample_verification_records, output_path=tex_path)

    assert r"\begin{table}" in tex_content
    assert r"\end{table}" in tex_content
    assert r"\label{tab:pareto_verification}" in tex_content
    assert r"knee\_point" in tex_content
    assert r"min\_emit\_x" in tex_content
    assert r"VERIFIED" in tex_content
    assert tex_path.exists()

    # Test reading directly from DataFrame
    df = pd.DataFrame(sample_verification_records)
    tex_from_df = generate_verification_latex_table(df)
    assert r"knee\_point" in tex_from_df


def test_generate_results_summary_latex_table(tmp_path):
    """Test generating Phase 2 vs Phase 3 campaign summary table."""
    p2 = {
        "total_evaluations": 136,
        "valid_evaluations": 130,
        "feasible_evaluations": 75,
        "feasibility_pct": 55.1,
        "all_hv": 1.85e-9,
        "feas_hv": 1.20e-9,
        "pareto_size": 18,
        "min_emit_x_um": 0.82,
        "min_emit_y_um": 0.84,
        "min_sigma_e_mev": 0.045,
    }
    p3 = {
        "total_evaluations": 136,
        "valid_evaluations": 136,
        "feasible_evaluations": 110,
        "feasibility_pct": 80.9,
        "all_hv": 1.95e-9,
        "feas_hv": 1.75e-9,
        "pareto_size": 24,
        "min_emit_x_um": 0.80,
        "min_emit_y_um": 0.81,
        "min_sigma_e_mev": 0.042,
    }

    tex_path = tmp_path / "results_table.tex"
    tex_content = generate_results_summary_latex_table(p2, p3, output_path=tex_path)

    assert r"\begin{table}" in tex_content
    assert r"\label{tab:results_summary}" in tex_content
    assert "Phase 2 (Unconstrained)" in tex_content
    assert "Phase 3 (Constrained)" in tex_content
    assert "55.1\\%" in tex_content
    assert "80.9\\%" in tex_content
    assert tex_path.exists()


def test_generate_robustness_summary_latex_table(sample_robustness_records, tmp_path):
    """Test generating robustness summary LaTeX table."""
    tex_path = tmp_path / "robustness_table.tex"
    tex_content = generate_robustness_summary_latex_table(sample_robustness_records, output_path=tex_path)

    assert r"\begin{table}" in tex_content
    assert r"\label{tab:robustness_summary}" in tex_content
    assert r"knee\_point" in tex_content
    assert r"0.95" in tex_content
    assert r"0.9200" in tex_content
    assert tex_path.exists()


def test_script_and_package_verification_exports_agree_with_failed_reruns(tmp_path):
    import copy
    from scripts.generate_paper_figures import export_verification_latex_table
    from mobo_linac.metrics.latex import escape_latex, RawLatex
    role = r'case_50% & #1 {a} $b$ ~ ^ \path'
    records = [{'role': role, 'stored_emit_x_m_rad': 1e-6, 'rerun_emit_x_m_rad': None,
                'stored_sigma_energy_eV': .5e6, 'rerun_sigma_energy_eV': None,
                'max_diff_pct': None, 'verification_status': 'RERUN_FAILED'}]
    before = copy.deepcopy(records)
    source = tmp_path / 'verification.csv'
    pd.DataFrame(records).to_csv(source, index=False)
    output = tmp_path / 'table.tex'
    assert export_verification_latex_table(source, output) == generate_verification_latex_table(records)
    content = output.read_text()
    assert escape_latex(role) in content
    assert r'RERUN\_FAILED' in content
    assert 'nan' not in content and '--' in content
    assert records == before
    content = generate_verification_latex_table(records, caption=RawLatex(r'Test $\sigma_E$ \& text'))
    assert r'\caption{Test $\sigma_E$ \& text}' in content
    assert r'\caption{Test \$x\$ \& text}' in generate_verification_latex_table(records, caption='Test $x$ & text')


def test_custom_objective_units_and_order_are_consistent(tmp_path):
    import json
    records = [{'role': 'unusual&role', 'stored_objectives': {'cost_1': 2.}, 'rerun_objectives': {'cost_1': None},
                'objective_order': ['cost_1'], 'objective_units': {'cost_1': 'J/s & unit'},
                'max_diff_pct': None, 'verification_status': 'COMPARISON_UNKNOWN'}]
    direct = generate_verification_latex_table(records)
    csv_records = [{key: json.dumps(value) if isinstance(value, (dict, list)) else value
                    for key, value in record.items()} for record in records]
    path = tmp_path / 'nested.csv'
    pd.DataFrame(csv_records).to_csv(path, index=False)
    assert generate_verification_latex_table(path) == direct
    assert r'cost\_1' in direct and r'J/s \& unit' in direct
    bad = dict(records[0], objective_units={'cost_1': 'eV'})
    with pytest.raises(ValueError, match='order/units disagree'):
        generate_verification_latex_table([*records, bad])


def test_small_energy_spread_uses_explicit_si_units():
    records = [{'role': 'small', 'stored_emit_x_m_rad': .1, 'rerun_emit_x_m_rad': .1,
                'stored_sigma_energy_eV': 10., 'rerun_sigma_energy_eV': 10.,
                'max_diff_pct': 0., 'verification_status': 'VERIFIED'}]
    content = generate_verification_latex_table(records)
    assert '100000.0000' in content
    assert '10.0000' not in content


def test_unusual_names_compile_as_latex(tmp_path):
    import shutil
    import subprocess
    compiler = shutil.which('pdflatex')
    if compiler is None:
        pytest.skip('pdflatex unavailable')
    records = [{'role': r'case_50% & #1 {a} $b$ ~ ^ \path', 'stored_emit_x_m_rad': 1e-6,
                'rerun_emit_x_m_rad': None, 'stored_sigma_energy_eV': .5e6,
                'rerun_sigma_energy_eV': None, 'max_diff_pct': None, 'verification_status': 'RERUN_FAILED'}]
    content = generate_verification_latex_table(records)
    source = tmp_path / 'table.tex'
    source.write_text(r'\documentclass{article}\usepackage{booktabs,graphicx}\begin{document}' + content + r'\end{document}')
    result = subprocess.run([compiler, '-interaction=nonstopmode', '-halt-on-error', source.name],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-4000:]
    assert (tmp_path / 'table.pdf').exists()
