"""
Unit tests for Centralized LaTeX Table Generators (Refactor C).
"""

from pathlib import Path
import pytest
import pandas as pd

from mobo_linac.metrics.latex import (
    generate_verification_latex_table,
    generate_robustness_summary_latex_table,
)
from mobo_linac.config import load_config


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
    content = generate_verification_latex_table(records, config=load_config("configs/mobo_200MeV.yaml"))
    assert '100000.0000' in content  # 0.1 m*rad shown in the configured μm*rad display unit
    assert '10.0000' not in content
    assert generate_verification_latex_table(records).count(' 0.1 ') == 2  # without configuration: SI values


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


def test_verification_table_includes_every_configured_objective():
    config = load_config("configs/mobo_200MeV.yaml")
    records = [{'role': 'knee_point', 'stored_objectives': {'norm_emit_x_m_rad': 1e-6, 'norm_emit_y_m_rad': 2e-6,
                'sigma_energy_eV': 5e5}, 'rerun_objectives': {'norm_emit_x_m_rad': 1e-6, 'norm_emit_y_m_rad': 2e-6,
                'sigma_energy_eV': 5e5}, 'objective_order': ['norm_emit_x_m_rad', 'norm_emit_y_m_rad', 'sigma_energy_eV'],
                'objective_units': {'norm_emit_x_m_rad': 'm*rad', 'norm_emit_y_m_rad': 'm*rad', 'sigma_energy_eV': 'eV'},
                'max_diff_pct': 0.0, 'verification_status': 'VERIFIED'}]
    content = generate_verification_latex_table(records, config=config)
    assert r'Stored $\varepsilon_{n,y}$ [$\mu$m$\cdot$rad]' in content
    assert '2.0000' in content and '0.5000' in content
    archived = [{'role': 'old', 'stored_emit_x_m_rad': 1e-6, 'rerun_emit_x_m_rad': 1e-6, 'stored_emit_y_m_rad': 2e-6,
                 'rerun_emit_y_m_rad': 2e-6, 'stored_sigma_energy_eV': 5e5, 'rerun_sigma_energy_eV': 5e5,
                 'max_diff_percent': 0.0, 'status': 'VERIFIED'}]
    assert generate_verification_latex_table(archived, config=config).count('2.0000') == 2  # ε_y no longer dropped


def test_reporting_modules_hold_no_objective_names_or_phase_counts():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src" / "mobo_linac" / "metrics"
    text = (root / "publication.py").read_text()
    for literal in ("norm_emit", "sigma_energy", "emit_x", "Phase 2", "Phase 3", "3.9236"):
        assert literal not in text, literal
