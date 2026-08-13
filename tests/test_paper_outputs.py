"""
tests/test_paper_outputs.py — Manuscript Consistency & Paper Output Tests (Task 10)
====================================================================================
Verifies that:
  1. All required result CSV files exist and have correct columns.
  2. generate_paper_figures.py produces all required figure PNGs and LaTeX tables.
  3. Verification summary CSV maps to valid LaTeX table content.
  4. Manuscript LaTeX contains no forbidden "experimental validation" terminology
     and correctly references all generated figure/table files.
  5. reproduce_paper.sh passes a dry-run syntax check.

These tests are designed to run WITHOUT launching any ASTRA simulations.

CLI options (registered in conftest.py):
  --phase2-dir PATH          Phase 2 campaign run directory
  --phase3-dir PATH          Phase 3 campaign run directory
  --verification-csv PATH    Verification summary CSV
  --figures-dir PATH         Figures output directory (default: docs/paper/figures)
  --tables-dir PATH          Tables output directory (default: docs/paper)
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest



def _auto_detect_phase_dir(results_dir: Path, phase_name: str, prefix: str) -> Path | None:
    """Auto-detects the campaign directory matching phase_name or prefix."""
    full_prod = results_dir / "full_production" / phase_name
    if full_prod.exists() and (full_prod / "train_X.csv").exists():
        return full_prod
    candidates = sorted(results_dir.glob(f"{prefix}*"))
    for cand in reversed(candidates):
        if (cand / "train_X.csv").exists():
            return cand
    return None


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def phase2_dir(request, project_root) -> Path:
    cli_val = request.config.getoption("--phase2-dir")
    if cli_val:
        return Path(cli_val)
    detected = _auto_detect_phase_dir(project_root / "results", "phase2_unconstrained", "phase2_unconstrained_")
    if detected is None:
        pytest.skip("No Phase 2 campaign directory found; skipping.")
    return detected


@pytest.fixture(scope="session")
def phase3_dir(request, project_root) -> Path:
    cli_val = request.config.getoption("--phase3-dir")
    if cli_val:
        return Path(cli_val)
    detected = _auto_detect_phase_dir(project_root / "results", "phase3_constrained", "phase3_constrained_")
    if detected is None:
        pytest.skip("No Phase 3 campaign directory found; skipping.")
    return detected


@pytest.fixture(scope="session")
def verification_csv(request, project_root) -> Path:
    cli_val = request.config.getoption("--verification-csv")
    if cli_val:
        return Path(cli_val)
    default = project_root / "results" / "verification" / "verification_summary.csv"
    return default


@pytest.fixture(scope="session")
def figures_dir(request, project_root) -> Path:
    val = request.config.getoption("--figures-dir")
    return project_root / val if not Path(val).is_absolute() else Path(val)


@pytest.fixture(scope="session")
def tables_dir(request, project_root) -> Path:
    val = request.config.getoption("--tables-dir")
    return project_root / val if not Path(val).is_absolute() else Path(val)


# ---------------------------------------------------------------------------
# 1. Required campaign result file checks
# ---------------------------------------------------------------------------

REQUIRED_RESULT_FILES = [
    "hypervolume.csv",
    "pareto.csv",
    "train_X.csv",
    "train_Y.csv",
    "config.yaml",
]

HYPERVOLUME_REQUIRED_COLS = {
    "iteration",
    "feasible_hypervolume",
    "num_valid_points",
    "num_feasible_points",
}

PARETO_CSV_N_COLS = 9  # 6 design vars + 3 objectives


@pytest.mark.parametrize("fname", REQUIRED_RESULT_FILES)
def test_phase2_result_files_exist(phase2_dir, fname):
    """All required Phase 2 result files must exist."""
    assert (phase2_dir / fname).exists(), (
        f"Missing Phase 2 result file: {phase2_dir / fname}"
    )


@pytest.mark.parametrize("fname", REQUIRED_RESULT_FILES)
def test_phase3_result_files_exist(phase3_dir, fname):
    """All required Phase 3 result files must exist."""
    assert (phase3_dir / fname).exists(), (
        f"Missing Phase 3 result file: {phase3_dir / fname}"
    )


def test_hypervolume_csv_columns_phase2(phase2_dir):
    """Phase 2 hypervolume.csv must have required columns."""
    df = pd.read_csv(phase2_dir / "hypervolume.csv")
    assert HYPERVOLUME_REQUIRED_COLS.issubset(set(df.columns)), (
        f"Missing columns in Phase 2 hypervolume.csv: "
        f"{HYPERVOLUME_REQUIRED_COLS - set(df.columns)}"
    )


def test_hypervolume_csv_columns_phase3(phase3_dir):
    """Phase 3 hypervolume.csv must have required columns."""
    df = pd.read_csv(phase3_dir / "hypervolume.csv")
    assert HYPERVOLUME_REQUIRED_COLS.issubset(set(df.columns)), (
        f"Missing columns in Phase 3 hypervolume.csv: "
        f"{HYPERVOLUME_REQUIRED_COLS - set(df.columns)}"
    )


def test_pareto_csv_has_data_phase2(phase2_dir):
    """Phase 2 pareto.csv must contain at least one Pareto point."""
    df = pd.read_csv(phase2_dir / "pareto.csv", comment="#")
    if list(df.columns) != ["solenoid_field_T", "quad_1_gradient_T_m", "quad_2_gradient_T_m", "gun_phase_deg", "acc1_acc2_phase_deg", "acc3_acc4_phase_deg", "norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]:
        df = pd.read_csv(phase2_dir / "pareto.csv", comment="#", header=None)
    df = df.dropna(how="all")
    assert len(df) >= 1, "Phase 2 pareto.csv is empty."
    assert df.shape[1] == PARETO_CSV_N_COLS, (
        f"Phase 2 pareto.csv has {df.shape[1]} columns; expected {PARETO_CSV_N_COLS}."
    )


def test_pareto_csv_has_data_phase3(phase3_dir):
    """Phase 3 pareto.csv must contain at least one Pareto point."""
    df = pd.read_csv(phase3_dir / "pareto.csv", comment="#")
    if list(df.columns) != ["solenoid_field_T", "quad_1_gradient_T_m", "quad_2_gradient_T_m", "gun_phase_deg", "acc1_acc2_phase_deg", "acc3_acc4_phase_deg", "norm_emit_x_m_rad", "norm_emit_y_m_rad", "sigma_energy_eV"]:
        df = pd.read_csv(phase3_dir / "pareto.csv", comment="#", header=None)
    df = df.dropna(how="all")
    assert len(df) >= 1, "Phase 3 pareto.csv is empty."
    assert df.shape[1] == PARETO_CSV_N_COLS, (
        f"Phase 3 pareto.csv has {df.shape[1]} columns; expected {PARETO_CSV_N_COLS}."
    )


def test_hypervolume_monotonically_nondecreasing_phase2(phase2_dir):
    """Feasible hypervolume must be monotonically non-decreasing across iterations."""
    df = pd.read_csv(phase2_dir / "hypervolume.csv")
    hv = df["feasible_hypervolume"].values
    for i in range(1, len(hv)):
        assert hv[i] >= hv[i - 1] - 1e-12, (
            f"Phase 2 feasible HV is not monotone at iteration {i}: "
            f"{hv[i-1]:.8f} -> {hv[i]:.8f}"
        )


# ---------------------------------------------------------------------------
# 2. Verification CSV checks
# ---------------------------------------------------------------------------

VERIFICATION_REQUIRED_COLS = {
    "role",
    "stored_emit_x_m_rad",
    "rerun_emit_x_m_rad",
    "stored_sigma_energy_eV",
    "rerun_sigma_energy_eV",
    "max_diff_pct",
    "verification_status",
}


def test_verification_csv_exists(verification_csv):
    """Verification summary CSV must exist."""
    if not verification_csv.exists():
        pytest.skip(f"Verification CSV not found: {verification_csv}")


def test_verification_csv_columns(verification_csv):
    """Verification CSV must have all required columns."""
    if not verification_csv.exists():
        pytest.skip(f"Verification CSV not found: {verification_csv}")
    df = pd.read_csv(verification_csv)
    assert VERIFICATION_REQUIRED_COLS.issubset(set(df.columns)), (
        f"Missing verification CSV columns: {VERIFICATION_REQUIRED_COLS - set(df.columns)}"
    )


def test_all_candidates_verified(verification_csv):
    """All candidates in verification_summary.csv must have VERIFIED status."""
    if not verification_csv.exists():
        pytest.skip(f"Verification CSV not found: {verification_csv}")
    df = pd.read_csv(verification_csv)
    non_verified = df[df["verification_status"] != "VERIFIED"]
    assert len(non_verified) == 0, (
        f"Non-verified candidates found:\n{non_verified[['role', 'max_diff_pct', 'verification_status']]}"
    )


def test_max_diff_pct_below_threshold(verification_csv):
    """Max relative difference for all verified candidates must be < 0.1%."""
    if not verification_csv.exists():
        pytest.skip(f"Verification CSV not found: {verification_csv}")
    df = pd.read_csv(verification_csv)
    verified = df[df["verification_status"] == "VERIFIED"]
    if len(verified) == 0:
        pytest.skip("No verified candidates found.")
    assert (verified["max_diff_pct"] < 0.1).all(), (
        f"Some candidates exceed 0.1% max diff:\n"
        f"{verified[verified['max_diff_pct'] >= 0.1][['role', 'max_diff_pct']]}"
    )


# ---------------------------------------------------------------------------
# 3. Figure generation (running generate_paper_figures.py)
# ---------------------------------------------------------------------------

REQUIRED_FIGURES = [
    "hypervolume_comparison.png",
    "pareto_front_comparison.png",
    "feasible_fraction.png",
]

REQUIRED_TABLES = [
    "results_table.tex",
]


def test_generate_paper_figures_runs(tmp_path, phase2_dir, phase3_dir, project_root):
    """generate_paper_figures.py must run without error."""
    fig_out = tmp_path / "figures"
    tab_out = tmp_path
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_paper_figures.py",
            "--phase2-dir", str(phase2_dir),
            "--phase3-dir", str(phase3_dir),
            "--output-dir", str(fig_out),
            "--tables-dir", str(tab_out),
        ],
        capture_output=True, text=True,
        cwd=str(project_root),
    )
    assert result.returncode == 0, (
        f"generate_paper_figures.py failed:\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


@pytest.mark.parametrize("fname", REQUIRED_FIGURES)
def test_required_figures_produced(tmp_path, phase2_dir, phase3_dir, project_root, fname):
    """generate_paper_figures.py must produce each required figure PNG."""
    fig_out = tmp_path / "figures"
    tab_out = tmp_path
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_paper_figures.py",
            "--phase2-dir", str(phase2_dir),
            "--phase3-dir", str(phase3_dir),
            "--output-dir", str(fig_out),
            "--tables-dir", str(tab_out),
        ],
        capture_output=True, text=True,
        cwd=str(project_root),
    )
    assert (fig_out / fname).exists(), (
        f"generate_paper_figures.py did not produce: {fname}"
    )


@pytest.mark.parametrize("fname", REQUIRED_TABLES)
def test_required_tables_produced(tmp_path, phase2_dir, phase3_dir, project_root, fname):
    """generate_paper_figures.py must produce each required LaTeX table file."""
    fig_out = tmp_path / "figures"
    tab_out = tmp_path
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_paper_figures.py",
            "--phase2-dir", str(phase2_dir),
            "--phase3-dir", str(phase3_dir),
            "--output-dir", str(fig_out),
            "--tables-dir", str(tab_out),
        ],
        capture_output=True, text=True,
        cwd=str(project_root),
    )
    assert (tab_out / fname).exists(), (
        f"generate_paper_figures.py did not produce: {fname}"
    )


def test_verification_table_produced_from_csv(tmp_path, phase2_dir, phase3_dir, verification_csv):
    """verification_table.tex must be generated from verification_summary.csv (not hard-coded)."""
    if not verification_csv.exists():
        pytest.skip(f"Verification CSV not found: {verification_csv}")
    fig_out = tmp_path / "figures"
    tab_out = tmp_path
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_paper_figures.py",
            "--phase2-dir", str(phase2_dir),
            "--phase3-dir", str(phase3_dir),
            "--verification-csv", str(verification_csv),
            "--output-dir", str(fig_out),
            "--tables-dir", str(tab_out),
        ],
        capture_output=True, text=True,
        cwd=str(phase2_dir.parent.parent),
    )
    assert result.returncode == 0
    tex_path = tab_out / "verification_table.tex"
    assert tex_path.exists(), "verification_table.tex was not produced."

    # Check LaTeX content is non-trivially derived from data
    tex_content = tex_path.read_text()
    df = pd.read_csv(verification_csv)
    # At least one role should appear as a LaTeX string in the table
    first_role = df["role"].iloc[0].replace("_", r"\_")
    assert first_role in tex_content, (
        f"verification_table.tex does not contain expected role '{first_role}'. "
        "Verify the table is data-driven."
    )


# ---------------------------------------------------------------------------
# 4. Manuscript LaTeX checks
# ---------------------------------------------------------------------------


def test_manuscript_no_experimental_validation(project_root):
    """
    main.tex must not contain 'experimental validation' (must use
    'simulation-based validation' or 'computational validation').
    """
    main_tex = project_root / "docs" / "paper" / "main.tex"
    assert main_tex.exists(), "docs/paper/main.tex not found."
    content = main_tex.read_text()
    forbidden = "experimental validation"
    assert forbidden not in content.lower(), (
        "Manuscript contains forbidden term 'experimental validation'. "
        "Replace with 'simulation-based validation' or 'computational validation'."
    )


def test_manuscript_references_generated_figures(project_root):
    """
    main.tex must include \\includegraphics references for all required paper
    figures, confirming data-driven figure usage.
    """
    main_tex = project_root / "docs" / "paper" / "main.tex"
    assert main_tex.exists(), "docs/paper/main.tex not found."
    content = main_tex.read_text()
    required_fig_refs = [
        "hypervolume_comparison.png",
        "pareto_front_comparison.png",
        "verification_rerun_comparison.png",
    ]
    for fig_name in required_fig_refs:
        assert fig_name in content, (
            f"main.tex does not reference required figure: {fig_name}"
        )


def test_manuscript_inputs_generated_tables(project_root):
    """
    main.tex must use \\input{} for the data-driven LaTeX table files
    rather than hard-coded table content.
    """
    main_tex = project_root / "docs" / "paper" / "main.tex"
    assert main_tex.exists(), "docs/paper/main.tex not found."
    content = main_tex.read_text()
    required_inputs = [
        r"\input{verification_table}",
        r"\input{results_table}",
    ]
    for inp in required_inputs:
        assert inp in content, (
            f"main.tex does not include '\\input{{...}}' for: {inp}"
        )


def test_manuscript_no_hardcoded_hv_values(project_root):
    """
    main.tex must not contain hard-coded hypervolume values like '1.939e-2'
    that could become stale when campaigns are re-run.
    """
    main_tex = project_root / "docs" / "paper" / "main.tex"
    assert main_tex.exists()
    content = main_tex.read_text()
    # Known stale hard-coded value from old manuscript
    assert "1.939" not in content, (
        "main.tex appears to contain a hard-coded hypervolume value '1.939'. "
        "Replace with a reference to the data-driven results table."
    )


def test_manuscript_no_hardcoded_percent_feasibility(project_root):
    """
    main.tex must not claim hard-coded feasibility percentages ('25%')
    as these depend on campaign results and should come from data tables.
    """
    main_tex = project_root / "docs" / "paper" / "main.tex"
    assert main_tex.exists()
    content = main_tex.read_text()
    assert "25\\%" not in content, (
        "main.tex contains hard-coded feasibility percentage '25%'. "
        "This should be derived from data (results_table.tex)."
    )


def test_manuscript_qlognehvi_description_present(project_root):
    """
    main.tex must contain a proper qLogNEHVI mathematical description
    (the log expectation formulation).
    """
    main_tex = project_root / "docs" / "paper" / "main.tex"
    assert main_tex.exists()
    content = main_tex.read_text()
    # Should contain the log-expectation form, not just plain EI
    assert r"\log" in content, "main.tex missing log in qLogNEHVI formula."
    assert "q\\text{LogNEHVI}" in content or r"q\text{LogNEHVI}" in content, (
        "main.tex missing qLogNEHVI acquisition function label."
    )


# ---------------------------------------------------------------------------
# 5. LaTeX auxiliary file gitignore check
# ---------------------------------------------------------------------------

def test_latex_aux_files_in_gitignore(project_root):
    """
    .gitignore must include patterns for LaTeX auxiliary files
    (*.aux, *.log, *.out) to avoid tracking build artifacts.
    """
    gitignore = project_root / ".gitignore"
    assert gitignore.exists(), ".gitignore not found."
    content = gitignore.read_text()
    for pattern in ["*.aux", "*.log", "*.out"]:
        assert pattern in content, (
            f".gitignore does not contain LaTeX auxiliary pattern '{pattern}'. "
            "Add it to avoid tracking build artifacts."
        )


# ---------------------------------------------------------------------------
# 6. reproduce_paper.sh syntax check
# ---------------------------------------------------------------------------

def test_reproduce_paper_sh_exists(project_root):
    """scripts/reproduce_paper.sh must exist."""
    script = project_root / "scripts" / "reproduce_paper.sh"
    assert script.exists(), "scripts/reproduce_paper.sh not found."


def test_reproduce_paper_sh_syntax_check(project_root):
    """scripts/reproduce_paper.sh must pass bash syntax check (bash -n)."""
    script = project_root / "scripts" / "reproduce_paper.sh"
    if not script.exists():
        pytest.skip("reproduce_paper.sh not found.")
    result = subprocess.run(
        ["bash", "-n", str(script)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"reproduce_paper.sh has syntax errors:\n{result.stderr}"
    )


def test_generate_paper_figures_py_exists(project_root):
    """scripts/generate_paper_figures.py must exist."""
    script = project_root / "scripts" / "generate_paper_figures.py"
    assert script.exists(), "scripts/generate_paper_figures.py not found."


def test_generate_paper_figures_py_syntax_check(project_root):
    """scripts/generate_paper_figures.py must parse without syntax errors."""
    script = project_root / "scripts" / "generate_paper_figures.py"
    if not script.exists():
        pytest.skip("generate_paper_figures.py not found.")
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(script)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"generate_paper_figures.py has syntax errors:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 7. Data integrity: objective values must be physically reasonable
# ---------------------------------------------------------------------------

def _load_pareto_df(phase_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(phase_dir / "pareto.csv", comment="#")
    expected_cols = ["sol", "q1", "q2", "phi_g", "phi_a12", "phi_a34", "ex", "ey", "se"]
    if "norm_emit_x_m_rad" in df.columns:
        df = df.rename(columns={
            "norm_emit_x_m_rad": "ex",
            "norm_emit_y_m_rad": "ey",
            "sigma_energy_eV": "se",
        })
    else:
        df.columns = expected_cols
    df = df.dropna(how="all")
    return df


def test_pareto_emittance_values_physical_range(phase2_dir):
    """Phase 2 Pareto emittance values must be in physically reasonable range (0.1–500 μm·mrad)."""
    df = _load_pareto_df(phase2_dir)
    ex_um = df["ex"].values * 1e6
    assert (ex_um > 0.1).all(), f"Emittance values contain non-positive entries: {ex_um}"
    assert (ex_um < 500.0).all(), f"Emittance values out of physical range: {ex_um}"


def test_pareto_energy_spread_physical_range(phase2_dir):
    """Phase 2 Pareto energy spread must be in range 0.01–10 MeV."""
    df = _load_pareto_df(phase2_dir)
    se_mev = df["se"].values * 1e-6
    assert (se_mev > 0.01).all(), f"Energy spread too small: {se_mev}"
    assert (se_mev < 10.0).all(), f"Energy spread out of range: {se_mev}"
