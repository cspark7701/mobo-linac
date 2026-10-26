"""
tests/test_paper_outputs.py — Manuscript Consistency & Paper Output Tests
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
import json
import math
import os
import shlex
from pathlib import Path

import pandas as pd
import pytest

from mobo_linac.config import load_config
from mobo_linac.result_schema import ResultSchema



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


@pytest.fixture(autouse=True)
def preserve_manuscript_artifacts():
    """Every publication test must leave existing manuscript sources/figures unchanged."""
    root = Path(__file__).resolve().parents[1] / "docs" / "paper"
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file() and path.suffix in (".tex", ".png", ".pdf")}
    yield
    after = {path: path.read_bytes() for path in root.rglob("*") if path.is_file() and path.suffix in (".tex", ".png", ".pdf")}
    assert before == after


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def phase1_dir(request, project_root) -> Path:
    cli_val = request.config.getoption("--phase1-dir")
    if cli_val:
        return Path(cli_val)
    detected = _auto_detect_phase_dir(project_root / "results", "phase1_scalarized", "phase1_scalarized_")
    if detected is None:
        pytest.skip("No Phase 1 campaign directory found; skipping.")
    return detected


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
    full_prod_ver = project_root / "results" / "full_production" / "analysis" / "verification" / "verification_summary.csv"
    if full_prod_ver.exists():
        return full_prod_ver
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

def _assert_pareto_data(directory):
    schema = ResultSchema.from_config(load_config(directory / "config.yaml"))
    columns = list(schema.design_columns + schema.physical_columns)
    frame = pd.read_csv(directory / "pareto.csv", comment="#")
    if not set(columns).issubset(frame.columns):
        # Headerless legacy exports have numeric first-row labels. Arbitrary
        # malformed headers must fail instead of silently becoming observations.
        assert len(frame.columns) == len(columns)
        assert all(math.isfinite(float(value)) for value in frame.columns)
        frame = pd.read_csv(directory / "pareto.csv", comment="#", header=None, names=columns)
    values = frame[columns].apply(pd.to_numeric, errors="raise")
    assert len(values) >= 1, f"Empty Pareto export: {directory}"
    assert all(math.isfinite(value) for value in values.to_numpy().flat)
    if {"run_id", "evaluation_id"}.issubset(frame.columns):
        assert not frame[["run_id", "evaluation_id"]].isna().any().any()
        assert not frame.duplicated(["run_id", "evaluation_id"]).any()


@pytest.mark.parametrize("fname", REQUIRED_RESULT_FILES)
def test_phase1_result_files_exist(phase1_dir, fname):
    """All required Phase 1 result files must exist."""
    assert (phase1_dir / fname).exists(), (
        f"Missing Phase 1 result file: {phase1_dir / fname}"
    )


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


def test_hypervolume_csv_columns_phase1(phase1_dir):
    """Phase 1 hypervolume.csv must have required columns."""
    df = pd.read_csv(phase1_dir / "hypervolume.csv")
    assert HYPERVOLUME_REQUIRED_COLS.issubset(set(df.columns)), (
        f"Missing columns in Phase 1 hypervolume.csv: "
        f"{HYPERVOLUME_REQUIRED_COLS - set(df.columns)}"
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


def test_pareto_csv_has_data_phase1(phase1_dir):
    """Phase 1 pareto.csv must contain at least one Pareto point."""
    _assert_pareto_data(phase1_dir)


def test_pareto_csv_has_data_phase2(phase2_dir):
    """Phase 2 pareto.csv must contain at least one Pareto point."""
    _assert_pareto_data(phase2_dir)


def test_pareto_csv_has_data_phase3(phase3_dir):
    """Phase 3 pareto.csv must contain at least one Pareto point."""
    _assert_pareto_data(phase3_dir)


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
    if {"stored_objectives", "rerun_objectives", "objective_order", "objective_units"}.issubset(df.columns):
        for row in df.to_dict("records"):
            order = json.loads(row["objective_order"])
            units = json.loads(row["objective_units"])
            assert order and len(order) == len(set(order))
            assert all(name in units for name in order)
            for field in ("stored_objectives", "rerun_objectives"):
                objectives = json.loads(row[field])
                assert all(name in objectives and math.isfinite(float(objectives[name])) for name in order)
    else:
        legacy = {"stored_emit_x_m_rad", "rerun_emit_x_m_rad", "stored_sigma_energy_eV", "rerun_sigma_energy_eV"}
        assert legacy.issubset(df.columns)
        values = df[sorted(legacy)].apply(pd.to_numeric, errors="raise")
        assert all(math.isfinite(value) for value in values.to_numpy().flat)


def test_reproduction_stops_on_selected_dataset_validation_failure(tmp_path, project_root):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "pytest_calls"
    for name in ("python", "python3"):
        executable = fake_bin / name
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
    executable = fake_bin / "pytest"
    executable.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> {shlex.quote(str(calls))}\nexit 17\n")
    executable.chmod(0o755)
    directories = []
    for name in ("phase1", "phase2", "phase3"):
        directory = tmp_path / name
        directory.mkdir()
        directories.append(directory)
    verification = tmp_path / "verification.csv"
    verification.write_text("role\n")
    result = subprocess.run(["bash", "scripts/reproduce_paper.sh", "--check-only",
                             "--phase1-dir", str(directories[0]), "--phase2-dir", str(directories[1]),
                             "--phase3-dir", str(directories[2]), "--verification-csv", str(verification)],
                            cwd=project_root, env=dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ["PATH"]),
                            capture_output=True, text=True)
    assert result.returncode == 17
    assert len(calls.read_text().splitlines()) == 1
    assert str(directories[0]) in calls.read_text()


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


def test_generate_paper_figures_runs(tmp_path, project_root, publication_runs):
    """generate_paper_figures.py must run without error."""
    phase1_dir, phase2_dir, phase3_dir, verification_csv = publication_runs
    fig_out = tmp_path / "figures"
    tab_out = tmp_path
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_paper_figures.py",
            "--phase1-dir", str(phase1_dir),
            "--phase2-dir", str(phase2_dir),
            "--phase3-dir", str(phase3_dir),
            "--verification-csv", str(verification_csv),
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
def test_required_figures_produced(tmp_path, project_root, publication_runs, fname):
    """generate_paper_figures.py must produce each required figure PNG."""
    phase1_dir, phase2_dir, phase3_dir, verification_csv = publication_runs
    fig_out = tmp_path / "figures"
    tab_out = tmp_path
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_paper_figures.py",
            "--phase1-dir", str(phase1_dir),
            "--phase2-dir", str(phase2_dir),
            "--phase3-dir", str(phase3_dir),
            "--verification-csv", str(verification_csv),
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
def test_required_tables_produced(tmp_path, project_root, publication_runs, fname):
    """generate_paper_figures.py must produce each required LaTeX table file."""
    phase1_dir, phase2_dir, phase3_dir, verification_csv = publication_runs
    fig_out = tmp_path / "figures"
    tab_out = tmp_path
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_paper_figures.py",
            "--phase1-dir", str(phase1_dir),
            "--phase2-dir", str(phase2_dir),
            "--phase3-dir", str(phase3_dir),
            "--verification-csv", str(verification_csv),
            "--output-dir", str(fig_out),
            "--tables-dir", str(tab_out),
        ],
        capture_output=True, text=True,
        cwd=str(project_root),
    )
    assert (tab_out / fname).exists(), (
        f"generate_paper_figures.py did not produce: {fname}"
    )
    if fname == "results_table.tex":
        content = (tab_out / fname).read_text(encoding="utf-8")
        assert "Phase 1 (Scalarized)" in content, "results_table.tex missing Phase 1 (Scalarized) column."


def test_verification_table_produced_from_csv(tmp_path, project_root, publication_runs):
    """verification_table.tex must be generated from verification_summary.csv (not hard-coded)."""
    phase1_dir, phase2_dir, phase3_dir, verification_csv = publication_runs
    if not verification_csv.exists():
        pytest.skip(f"Verification CSV not found: {verification_csv}")
    fig_out = tmp_path / "figures"
    tab_out = tmp_path
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_paper_figures.py",
            "--phase1-dir", str(phase1_dir),
            "--phase2-dir", str(phase2_dir),
            "--phase3-dir", str(phase3_dir),
            "--verification-csv", str(verification_csv),
            "--output-dir", str(fig_out),
            "--tables-dir", str(tab_out),
        ],
        capture_output=True, text=True,
        cwd=str(project_root),
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
        "benchmark_feasibility_comparison.pdf",
        "primary_pareto_points.pdf",
        "survey_pareto_points.pdf",
        "injector_linac_layout.pdf",
        "verification_rerun_comparison.png",
        "feasible_fraction.png",
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


def test_pareto_emittance_values_physical_range_phase1(phase1_dir):
    """Phase 1 Pareto emittance values must be in physically reasonable range (0.1–500 μm·mrad)."""
    df = _load_pareto_df(phase1_dir)
    ex_um = df["ex"].values * 1e6
    assert (ex_um > 0.1).all(), f"Emittance values contain non-positive entries: {ex_um}"
    assert (ex_um < 500.0).all(), f"Emittance values out of physical range: {ex_um}"


def test_pareto_energy_spread_physical_range_phase1(phase1_dir):
    """Phase 1 Pareto energy spread must be in range 0.01–10 MeV."""
    df = _load_pareto_df(phase1_dir)
    se_mev = df["se"].values * 1e-6
    assert (se_mev > 0.01).all(), f"Energy spread too small: {se_mev}"
    assert (se_mev < 10.0).all(), f"Energy spread out of range: {se_mev}"


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


def test_new_run_artifacts_have_publication_headers_even_when_empty(tmp_path):
    from mobo_linac.config import load_config
    from mobo_linac.metrics.exports import RunArtifactWriter
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    config = load_config("configs/mobo_200MeV.yaml")
    writer = RunArtifactWriter(tmp_path, config)
    writer.write([], HypervolumeTracker([-1e-5, -1e-5, -1e6], config))
    assert list(pd.read_csv(tmp_path / "train_X.csv").columns) == [v.name for v in config.design_variables]
    assert list(pd.read_csv(tmp_path / "pareto.csv").columns) == ["run_id", "evaluation_id"] + [v.name for v in config.design_variables] + [o.explicit_name for o in config.objectives]
    assert HYPERVOLUME_REQUIRED_COLS <= set(pd.read_csv(tmp_path / "hypervolume.csv").columns)
    assert not (tmp_path / "train_X.csv").read_text().startswith("#")


def test_script_and_package_campaign_tables_agree(publication_runs, tmp_path):
    from scripts.generate_paper_figures import main as paper_script
    from mobo_linac.metrics.publication import generate_campaign_summary_latex_table
    p1, p2, p3, verification = publication_runs
    assert paper_script(["--phase1-dir", str(p1), "--phase2-dir", str(p2), "--phase3-dir", str(p3),
                         "--verification-csv", str(verification), "--output-dir", str(tmp_path / "figures"),
                         "--tables-dir", str(tmp_path / "tables")]) == 0
    script = (tmp_path / "tables" / "results_table.tex").read_text()
    package = generate_campaign_summary_latex_table([p1, p2, p3], phase_names=[
        'Phase 1 (Scalarized)', 'Phase 2 (Unconstrained)', 'Phase 3 (Constrained)'])
    assert script == package
    assert 'Total ASTRA Evaluations & 3 & 3 & 3' in script
    assert 'Feasibility Rate, All Evaluations' in script
    assert '33.3' in script and '1.0000' in script
    assert '6.65' not in script


def test_publication_plots_reject_conventions_before_creating_output(publication_runs, tmp_path):
    import json
    import matplotlib.pyplot as plt
    from mobo_linac.plotting.publication import plot_pareto_front_comparison
    p1, p2, p3, _ = publication_runs
    metadata = p3 / 'reporting_metadata.json'
    data = json.loads(metadata.read_text())
    data['reporting_ref_point'][0] *= 2
    data['reporting_ref_point_normalized'][0] *= 2
    metadata.write_text(json.dumps(data))
    output = tmp_path / 'new' / 'plot.png'
    before = plt.get_fignums()
    with pytest.raises(ValueError, match='Incompatible reporting|Hypervolume reference'):
        plot_pareto_front_comparison(p2, p3, output)
    assert not output.exists() and plt.get_fignums() == before


def test_custom_objective_figures_keep_recorded_units_and_close_figures(tmp_path):
    import torch
    from mobo_linac.config import load_config, ObjectiveConfig
    from mobo_linac.evaluation import EvaluationResult
    from mobo_linac.metrics.exports import RunArtifactWriter
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    from mobo_linac.metrics.publication import generate_campaign_summary_latex_table
    from mobo_linac.plotting.publication import plot_pareto_front_comparison, plot_verification_comparison
    import matplotlib.pyplot as plt
    config = load_config('configs/mobo_200MeV.yaml')
    config.objectives = [ObjectiveConfig('power', 'power_W', 'W', 'maximize', 1, reporting_scale=1.)]
    directories = []
    for name in ('first', 'second'):
        path = tmp_path / name
        path.mkdir()
        config.save_json(path / 'config.json')
        result = EvaluationResult(evaluation_id='eval_000001', run_id=name,
            x_physical=[v.nominal_value for v in config.design_variables],
            objectives_physical=[3.], objectives_model=[3.], diagnostics={},
            simulation_valid=True, physically_feasible=True, failure_category='SUCCESS')
        tracker = HypervolumeTracker([0.], config)
        tracker.track_iteration(0, torch.tensor([[3.]], dtype=torch.double), torch.tensor([True]))
        RunArtifactWriter(path, config).write([result], tracker)
        directories.append(path)
    before = plt.get_fignums()
    plot_pareto_front_comparison(*directories, tmp_path / 'pareto.png')
    source = tmp_path / 'verification.csv'
    import json
    pd.DataFrame([{'role': 'power_50%&', 'objective_order': json.dumps(['power_W']),
                  'objective_units': json.dumps({'power_W': 'W'}),
                  'stored_objectives': json.dumps({'power_W': 3.}),
                  'rerun_objectives': json.dumps({'power_W': None}), 'verification_status': 'RERUN_FAILED'}]).to_csv(source, index=False)
    plot_verification_comparison(source, tmp_path / 'verification.png')
    assert plt.get_fignums() == before
    assert (tmp_path / 'pareto.png').exists() and (tmp_path / 'verification.png').exists()
    content = generate_campaign_summary_latex_table(directories)
    assert r'Best power\_W [W]' in content and '3.0000' in content
