"""
Unit tests for Phase 1 Option 2 Multi-Case Scalarized BO Suite.
"""

from pathlib import Path
import pytest
import torch

from mobo_linac.campaigns.scalarized_suite import (
    OPTION_2_CASES,
    aggregate_scalarized_cases,
    export_phase1_cases_latex_table,
    get_option2_case,
    get_option2_cases,
    run_scalarized_suite,
)
from mobo_linac.cli.common import CliMockEvaluator


def test_option_2_cases_specification():
    """Verify all 5 Option 2 cases are properly defined with normalized weights."""
    cases = get_option2_cases()
    expected_keys = ["balanced", "high_brightness", "low_energy_spread", "x_dominant", "y_dominant"]
    assert list(cases.keys()) == expected_keys

    for key, c in cases.items():
        assert "name" in c
        assert "weights" in c
        assert "description" in c
        assert len(c["weights"]) == 3
        assert pytest.approx(sum(c["weights"]), rel=1e-5) == 1.0

    # Check specific weights
    assert pytest.approx(cases["balanced"]["weights"]) == [1/3, 1/3, 1/3]
    assert cases["high_brightness"]["weights"] == [0.45, 0.45, 0.10]
    assert cases["low_energy_spread"]["weights"] == [0.10, 0.10, 0.80]
    assert cases["x_dominant"]["weights"] == [0.60, 0.20, 0.20]
    assert cases["y_dominant"]["weights"] == [0.20, 0.60, 0.20]


def test_get_option2_case():
    """Test getting single case and error on invalid case."""
    c = get_option2_case("high_brightness")
    assert c["name"] == "High-Brightness FEL Mode"

    with pytest.raises(ValueError, match="Unknown Option 2 case"):
        get_option2_case("non_existent_case")


def test_scalarized_suite_execution_with_mock_evaluator(tmp_path):
    """Test running Option 2 suite with CliMockEvaluator across multiple cases."""
    suite_dir = tmp_path / "phase1_suite_test"
    evaluator = CliMockEvaluator(suite_dir)

    # Run a 2-case subset for test speed
    target_cases = ["balanced", "high_brightness"]
    agg_meta = run_scalarized_suite(
        config="configs/mobo_200MeV.yaml",
        n_iterations=1,
        batch_size=2,
        num_initial_samples=4,
        seed=100,
        output_dir=suite_dir,
        cases_to_run=target_cases,
        evaluator=evaluator,
    )

    assert agg_meta["num_cases"] == 2
    assert "balanced" in agg_meta["cases"]
    assert "high_brightness" in agg_meta["cases"]
    assert agg_meta["total_evaluations"] == 12  # 6 per case (4 init + 2 batch 1)

    # Verify per-case subdirectories
    for c_name in target_cases:
        c_dir = suite_dir / c_name
        assert c_dir.is_dir()
        assert (c_dir / "evaluations.csv").exists()
        assert (c_dir / "train_X.csv").exists()
        assert (c_dir / "train_Y.csv").exists()
        assert (c_dir / "pareto.csv").exists()
        assert (c_dir / "hypervolume.csv").exists()

    # Verify aggregate files in suite_dir root
    assert (suite_dir / "cases_summary.csv").exists()
    assert (suite_dir / "cases_summary.json").exists()
    assert (suite_dir / "evaluations.csv").exists()
    assert (suite_dir / "train_X.csv").exists()
    assert (suite_dir / "train_Y.csv").exists()
    assert (suite_dir / "pareto.csv").exists()
    assert (suite_dir / "hypervolume.csv").exists()

    # Verify LaTeX table export inside tmp_path
    out_tex = tmp_path / "test_table.tex"
    export_phase1_cases_latex_table(suite_dir / "cases_summary.csv", out_tex)
    assert out_tex.exists()
    content = out_tex.read_text(encoding="utf-8")
    assert r"\begin{table}" in content
    assert r"\texttt{balanced}" in content
    assert r"\texttt{high_brightness}" in content

    # Verify publication table docs/paper/phase1_cases_table.tex was NOT overwritten by mock test
    paper_table = Path("docs/paper/phase1_cases_table.tex")
    if paper_table.exists():
        paper_content = paper_table.read_text(encoding="utf-8")
        assert "176" in paper_content, "docs/paper/phase1_cases_table.tex must not be overwritten by mock tests!"


def test_cli_suite_arguments():
    """Verify CLI parsing for --suite and --case flags."""
    from scripts.run_scalarized_bo import parse_args
    import sys

    sys.argv = [
        "run_scalarized_bo.py",
        "--suite", "option2",
        "--case", "all",
        "--n-iterations", "10",
    ]
    args = parse_args()
    assert args.suite == "option2"
    assert args.case == "all"
    assert args.n_iterations == 10
