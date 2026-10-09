"""
Unit tests for Phase 1 Option 2 Multi-Case Scalarized BO Suite.
"""

from pathlib import Path
import pytest
import torch

from mobo_linac.campaigns.scalarized_suite import (
    aggregate_scalarized_cases,
    case_seed,
    export_phase1_cases_latex_table,
    get_scalarized_case,
    run_scalarized_suite,
)
from mobo_linac.cli.common import CliMockEvaluator
from mobo_linac.config import load_config

CONFIG = load_config("configs/mobo_200MeV.yaml")


def test_configured_cases_specification():
    """The five published cases are configuration data with stable seed offsets."""
    cases = CONFIG.scalarized_cases
    assert list(cases) == ["balanced", "high_brightness", "low_energy_spread", "x_dominant", "y_dominant"]
    for case in cases.values():
        assert case.label and case.description
        assert len(case.weights) == len(CONFIG.objectives)
        assert pytest.approx(sum(case.weights), rel=1e-5) == 1.0
    assert pytest.approx(cases["balanced"].weights) == [1/3, 1/3, 1/3]
    assert cases["high_brightness"].weights == [0.45, 0.45, 0.10]
    assert cases["low_energy_spread"].weights == [0.10, 0.10, 0.80]
    assert cases["x_dominant"].weights == [0.60, 0.20, 0.20]
    assert cases["y_dominant"].weights == [0.20, 0.60, 0.20]
    assert [case.seed_offset for case in cases.values()] == [0, 100, 200, 300, 400]


def test_get_scalarized_case():
    assert get_scalarized_case(CONFIG, "high_brightness").label == "High-Brightness FEL Mode"
    with pytest.raises(ValueError, match="Unknown scalarized case"):
        get_scalarized_case(CONFIG, "non_existent_case")


def test_case_seed_is_independent_of_selected_subset():
    # Previously the seed came from the position in the selected subset.
    assert case_seed(CONFIG, "low_energy_spread", 42, 0) == case_seed(CONFIG, "low_energy_spread", 42, 2) == 242
    assert case_seed(CONFIG, "low_energy_spread", 42, 0, "legacy_subset_index") == 42


def test_case_weights_must_match_objectives():
    from dataclasses import asdict
    from mobo_linac.config import config_from_dict
    data = asdict(CONFIG)
    data["scalarized_cases"]["balanced"]["weights"] = [0.5, 0.5]
    config = config_from_dict(data)
    with pytest.raises(ValueError, match="Scalar weights"):
        get_scalarized_case(config, "balanced")


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

    # Weights and seeds come from each case's own checkpoint.
    import json
    import pandas as pd
    summary = pd.read_csv(suite_dir / "cases_summary.csv").set_index("case_id")
    assert json.loads(summary.loc["high_brightness", "weights"]) == pytest.approx([0.45, 0.45, 0.10])
    assert summary.loc["high_brightness", "seed"] == 200
    hypervolume = pd.read_csv(suite_dir / "hypervolume.csv")
    assert len(hypervolume) == 2  # one cumulative row per case boundary
    assert hypervolume["num_valid_points"].tolist() == [6, 12]

    # Verify LaTeX table export inside tmp_path
    out_tex = tmp_path / "test_table.tex"
    export_phase1_cases_latex_table(suite_dir / "cases_summary.csv", out_tex)
    assert out_tex.exists()
    content = out_tex.read_text(encoding="utf-8")
    assert r"\begin{table}" in content
    assert r"\texttt{balanced}" in content
    assert r"\texttt{high\_brightness}" in content

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


def test_scalarized_aggregation_rejects_different_reporting_references(tmp_path):
    import json
    from mobo_linac.config import load_config
    from mobo_linac.io.artifacts import RunArtifactWriter
    from mobo_linac.metrics.hypervolume import HypervolumeTracker
    config = load_config("configs/mobo_200MeV.yaml")
    for name, ref in [("first", [-1e-5, -1e-5, -1e6]), ("second", [-2e-5, -1e-5, -1e6])]:
        directory = tmp_path / name
        writer = RunArtifactWriter(directory, config)
        config.save_json(directory / "config.json")
        writer.write([], HypervolumeTracker(ref, config))
        writer.complete(0, 0.0)
    with pytest.raises(ValueError, match="Incompatible reporting"):
        aggregate_scalarized_cases(tmp_path)
    assert not (tmp_path / "cases_summary.csv").exists()


def test_scalarized_case_export_uses_shared_escaping_and_preserves_source(tmp_path):
    import pandas as pd
    from mobo_linac.metrics.latex import generate_phase1_cases_latex_table, escape_latex
    source = tmp_path / 'cases.csv'
    name = r'special_50% & {case} #1 $x$ ~ ^ \path'
    pd.DataFrame([{'case_id': name, 'name': name, 'w_emit_x': .3, 'w_emit_y': .3,
        'w_energy_spread': .4, 'num_evaluations': 3, 'num_feasible': 1, 'feasible_fraction_pct': 100/3,
        'min_norm_emit_x_um': 1., 'min_norm_emit_y_um': 2., 'min_sigma_energy_MeV': .5}]).to_csv(source, index=False)
    before = source.read_bytes()
    script_path, package_path = tmp_path / 'adapter.tex', tmp_path / 'package.tex'
    export_phase1_cases_latex_table(source, script_path)
    generate_phase1_cases_latex_table(source, package_path)
    assert script_path.read_bytes() == package_path.read_bytes()
    assert escape_latex(name) in script_path.read_text()
    assert source.read_bytes() == before


def test_case_alone_matches_case_within_suite(tmp_path):
    import json
    common = dict(config="configs/mobo_200MeV.yaml", n_iterations=1, batch_size=2,
                  num_initial_samples=3, seed=11, device="cpu")
    run_scalarized_suite(output_dir=tmp_path / "alone", cases_to_run=["x_dominant"],
                         evaluator=CliMockEvaluator(tmp_path / "m1"), **common)
    run_scalarized_suite(output_dir=tmp_path / "suite", cases_to_run=["balanced", "x_dominant"],
                         evaluator=CliMockEvaluator(tmp_path / "m2"), **common)
    alone = json.loads((tmp_path / "alone" / "x_dominant" / "candidate_history.json").read_text())
    within = json.loads((tmp_path / "suite" / "x_dominant" / "candidate_history.json").read_text())
    assert [r["x_physical"] for r in alone] == [r["x_physical"] for r in within]
