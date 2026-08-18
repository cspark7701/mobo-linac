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
