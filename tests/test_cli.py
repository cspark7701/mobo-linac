"""
Unit tests for CLI Workflow Execution, Dry-Run Mode, and Mock-Evaluator (Task 05).
"""

import pytest
import sys
from pathlib import Path
from mobo_linac.cli import main


def test_cli_help(capsys):
    """Verify CLI --help execution for all subcommands."""
    for cmd in ["run-unconstrained", "run-constrained", "run-benchmark", "run-robustness", "run-verification", "resume"]:
        sys.argv = ["mobo-linac", cmd, "--help"]
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert f"usage: mobo-linac {cmd}" in captured.out or f"usage: mobo-linac" in captured.out


def test_cli_dry_run(capsys, tmp_path):
    """Verify --dry-run flag for all workflow subcommands."""
    subcommands = [
        ["run-unconstrained", "--dry-run", "--output-dir", str(tmp_path / "dry_un")],
        ["run-constrained", "--dry-run", "--output-dir", str(tmp_path / "dry_co")],
        ["run-scalarized", "--dry-run", "--output-dir", str(tmp_path / "dry_sc")],
        ["run-benchmark", "--dry-run", "--output-dir", str(tmp_path / "dry_bm")],
        ["run-robustness", "--dry-run", "--output-dir", str(tmp_path / "dry_rob")],
        ["run-verification", "--dry-run", "--output-dir", str(tmp_path / "dry_ver")],
    ]

    for cmd_args in subcommands:
        sys.argv = ["mobo-linac"] + cmd_args
        main()
        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out


def test_cli_mock_evaluator_workflows(tmp_path):
    """Verify full workflow execution using --mock-evaluator."""
    # 1. run-unconstrained
    dir_un = tmp_path / "mock_un"
    sys.argv = ["mobo-linac", "run-unconstrained", "--n-iterations", "1", "-q", "2", "--num-initial-samples", "4", "--output-dir", str(dir_un), "--mock-evaluator"]
    main()
    assert (dir_un / "candidate_history.csv").exists()

    # 2. run-constrained
    dir_co = tmp_path / "mock_co"
    sys.argv = ["mobo-linac", "run-constrained", "--n-iterations", "1", "-q", "2", "--num-initial-samples", "4", "--output-dir", str(dir_co), "--mock-evaluator"]
    main()
    assert (dir_co / "candidate_history.csv").exists()

    # 3. run-scalarized
    dir_sc = tmp_path / "mock_sc"
    sys.argv = ["mobo-linac", "run-scalarized", "--n-iterations", "1", "-q", "2", "--num-initial-samples", "4", "--output-dir", str(dir_sc), "--mock-evaluator"]
    main()
    assert (dir_sc / "candidate_history.csv").exists()

    # 4. run-robustness
    dir_rob = tmp_path / "mock_rob"
    sys.argv = ["mobo-linac", "run-robustness", "--input", str(dir_un), "--num-perturbations", "2", "--output-dir", str(dir_rob), "--mock-evaluator"]
    main()
    assert (dir_rob / "robustness_summary.csv").exists()

    # 5. run-verification
    dir_ver = tmp_path / "mock_ver"
    sys.argv = ["mobo-linac", "run-verification", "--input", str(dir_un), "--output-dir", str(dir_ver), "--mock-evaluator"]
    main()
    assert (dir_ver / "verification_manifest.json").exists()


def test_benchmark_cli_forwards_workers_and_algorithm_settings(tmp_path, monkeypatch):
    from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner

    captured = {}

    class RecordingBenchmarkRunner:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def execute_benchmark_campaigns(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "mobo_linac.campaigns.benchmark.BenchmarkCampaignRunner", RecordingBenchmarkRunner
    )
    main([
        "run-benchmark", "--algorithms", "scalarized_bo", "qlogehvi",
        "--seeds", "7", "8", "--num-workers", "3", "--budget", "5",
        "--n-sobol-init", "2", "-q", "2", "--device", "cpu",
        "--output-dir", str(tmp_path), "--mock-evaluator",
    ])
    assert captured["num_workers"] == 3
    assert captured["algorithms"] == ["scalarized_bo", "qlogehvi"]
    assert captured["seeds"] == [7, 8]
    assert captured["total_eval_budget"] == 5
    assert captured["batch_size"] == 2
    assert captured["device"] == "cpu"
    assert captured["mock_evaluator"] is not None


@pytest.mark.parametrize("algorithm", ["nsga2", "sobol"])
def test_benchmark_cli_rejects_unimplemented_algorithms(tmp_path, algorithm):
    with pytest.raises(ValueError, match="no implemented executor"):
        main([
            "run-benchmark", "--algorithms", algorithm, "--seeds", "42",
            "--output-dir", str(tmp_path / "unsupported"), "--dry-run",
        ])
    assert not (tmp_path / "unsupported").exists()


def test_cli_resume_restores_scalarized_nondefault_campaign(tmp_path):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution import MockBatchEvaluator
    from mobo_linac.io.results import load_run_checkpoint

    run_dir = tmp_path / "scalarized_resume"
    MoboCampaignRunner(
        output_dir=run_dir, num_initial_samples=1, num_batches=0, batch_size=2,
        seed=123, num_workers=3, optimization_mode="scalarized_bo",
        scalar_weights=[0.6, 0.3, 0.1], evaluator=MockBatchEvaluator(run_dir),
        device="cpu", export_plots=False, export_env_info=False,
    ).run()
    original_config = (run_dir / "config.yaml").read_bytes()
    main(["resume", "--run-dir", str(run_dir), "--n-iterations", "1", "--mock-evaluator"])
    state = load_run_checkpoint(run_dir)
    assert state.optimization_mode == "scalarized_bo"
    assert state.acquisition_mode == "scalarized_qLogNEI"
    assert state.num_initial_samples == 1
    assert state.scalar_weights == pytest.approx([0.6, 0.3, 0.1])
    assert state.seed == 123
    assert state.num_workers == 3
    assert state.batch_size == 2
    assert state.evaluation_batches == [0, 1, 1]
    assert state.sobol_state["num_generated"] == 3
    assert (run_dir / "config.yaml").read_bytes() == original_config


def test_cli_resume_defaults_to_saved_plan(tmp_path):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution import MockBatchEvaluator
    from mobo_linac.io.results import load_run_checkpoint

    MoboCampaignRunner(
        output_dir=tmp_path, num_initial_samples=1, num_batches=0,
        evaluator=MockBatchEvaluator(tmp_path), device="cpu", export_plots=False,
    ).run()
    before = load_run_checkpoint(tmp_path)
    main(["resume", "--run-dir", str(tmp_path), "--mock-evaluator"])
    after = load_run_checkpoint(tmp_path)
    assert after.iteration == before.iteration == 0
    assert len(after.results) == len(before.results) == 1


def test_cli_resume_rejects_missing_checkpoint_without_creating_directory(tmp_path):
    missing = tmp_path / "missing_resume"
    with pytest.raises(FileNotFoundError, match="No valid checkpoint"):
        main(["resume", "--run-dir", str(missing), "--mock-evaluator"])
    assert not missing.exists()


def test_cli_resume_uses_embedded_config_outside_project_cwd(tmp_path, monkeypatch):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution import MockBatchEvaluator
    from mobo_linac.io.results import load_run_checkpoint

    run_dir = tmp_path / "original"
    MoboCampaignRunner(
        output_dir=run_dir, num_initial_samples=1, num_batches=0,
        evaluator=MockBatchEvaluator(run_dir), device="cpu", export_plots=False,
    ).run()
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    main(["resume", "--run-dir", str(run_dir), "--mock-evaluator"])
    assert len(load_run_checkpoint(run_dir).results) == 1


def test_cli_recovers_initial_design_before_first_completed_checkpoint(tmp_path):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution import MockBatchEvaluator
    from mobo_linac.io.results import load_run_checkpoint, load_streaming_evaluations

    class InterruptedEvaluator(MockBatchEvaluator):
        def evaluate_batch(self, candidates, run_id, eval_ids, on_evaluation_complete):
            result = self._generate_candidate_result(candidates[1], run_id, eval_ids[1])
            on_evaluation_complete(result)
            raise RuntimeError("before checkpoint zero")

    with pytest.raises(RuntimeError, match="before checkpoint zero"):
        MoboCampaignRunner(
            output_dir=tmp_path, num_initial_samples=3, num_batches=0,
            optimization_mode="scalarized_bo", scalar_weights=[0.6, 0.3, 0.1],
            evaluator=InterruptedEvaluator(tmp_path), device="cpu", export_plots=False,
        ).run()
    assert not (tmp_path / "checkpoints" / "checkpoint.pt").exists()
    main(["resume", "--run-dir", str(tmp_path), "--mock-evaluator"])
    state = load_run_checkpoint(tmp_path)
    assert state.iteration == 0
    assert state.optimization_mode == "scalarized_bo"
    assert state.scalar_weights == pytest.approx([0.6, 0.3, 0.1])
    assert [r.evaluation_id for r in state.results] == ["eval_000001", "eval_000002", "eval_000003"]
    assert len(load_streaming_evaluations(tmp_path)) == 3


def test_verification_absent_input_requires_explicit_mock(tmp_path, monkeypatch):
    import argparse
    import json
    from mobo_linac.cli.commands.audit import run_verification
    config = Path(__file__).resolve().parents[1] / 'configs/publication_200MeV.yaml'
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(config=str(config), output_dir=str(tmp_path / 'verification'),
                              history_path=None, dry_run=False, mock_evaluator=False)
    with pytest.raises(ValueError, match='requires measured candidate history'):
        run_verification(args)
    assert not (tmp_path / 'verification').exists()
    args.history_path = str(tmp_path / 'does_not_exist.json')
    with pytest.raises(FileNotFoundError, match='Candidate input not found'):
        run_verification(args)
    args.history_path = None
    args.mock_evaluator = True
    run_verification(args)
    records = json.loads((tmp_path / 'verification' / 'verification_manifest.json').read_text())['records']
    assert records and all(record['verification_status'].startswith('MOCK_') for record in records)
    assert all(record['input_sha256'] is None for record in records)


@pytest.mark.parametrize("command", ["run-unconstrained", "run-constrained", "run-scalarized",
    "run-scalarized-suite", "run-validation", "run-benchmark", "run-robustness", "run-verification"])
def test_cli_missing_explicit_config_fails_before_output(tmp_path, command):
    destination = tmp_path / "output"
    with pytest.raises(FileNotFoundError, match="Requested configuration"):
        main([command, "--config", str(tmp_path / "missing.yaml"), "--output-dir", str(destination), "--dry-run"])
    assert not destination.exists()


@pytest.mark.parametrize("weights", [["nan", "1", "1"], ["-1", "1", "1"],
    ["0", "0", "0"], ["1", "1"]])
def test_cli_invalid_scalar_weights_fail_even_in_dry_run(tmp_path, weights):
    destination = tmp_path / "output"
    with pytest.raises(ValueError, match="Scalar weights"):
        main(["run-scalarized", "--weights", *weights, "--output-dir", str(destination), "--dry-run"])
    assert not destination.exists()


@pytest.mark.parametrize("option,value", [("--num-initial-samples", "0"), ("--n-iterations", "-1"),
    ("--batch-size", "0"), ("--num-workers", "0"), ("--seed", "-1")])
def test_cli_invalid_run_limits_fail_before_output(tmp_path, option, value):
    destination = tmp_path / "output"
    with pytest.raises(ValueError):
        main(["run-unconstrained", option, value, "--output-dir", str(destination), "--dry-run"])
    assert not destination.exists()


def test_cli_scalarized_weights_follow_custom_objective_count(tmp_path, capsys):
    from mobo_linac.config import load_config
    config = load_config("configs/mobo_200MeV.yaml")
    config.objectives = config.objectives[:2]
    path = tmp_path / "two_objectives.yaml"
    config.save_yaml(path)
    main(["run-scalarized", "--config", str(path), "--weights", "2", "1", "--dry-run"])
    assert "[DRY-RUN]" in capsys.readouterr().out
    with pytest.raises(ValueError, match="Scalar weights"):
        main(["run-scalarized-suite", "--config", str(path), "--dry-run"])


def test_cli_default_plan_reports_actual_resolved_path(capsys):
    from mobo_linac.config import resolve_config_path
    main(["run-unconstrained", "--dry-run"])
    assert str(resolve_config_path()) in capsys.readouterr().out


def test_scalarized_cli_rejects_incompatible_acquisition(tmp_path):
    output = tmp_path / "invalid"
    with pytest.raises(ValueError, match="scalarized_bo uses qLogNEI"):
        main(["run-scalarized", "--acquisition", "qLogEHVI", "--output-dir", str(output), "--dry-run"])
    assert not output.exists()


@pytest.mark.parametrize('command', ['run-unconstrained', 'run-constrained', 'run-scalarized', 'run-scalarized-suite'])
def test_shared_reporting_reference_reaches_campaign_and_suite(command, monkeypatch, tmp_path):
    import mobo_linac.campaigns.runner as runner_module
    import mobo_linac.campaigns.scalarized_suite as suite_module
    received = []
    class Runner:
        def __init__(self, **kwargs): received.append(kwargs)
        def run(self): return None
    monkeypatch.setattr(runner_module, 'MoboCampaignRunner', Runner)
    monkeypatch.setattr(suite_module, 'run_scalarized_suite', lambda **kwargs: received.append(kwargs))
    main([command, '--config', 'configs/publication_200MeV.yaml', '--output-dir', str(tmp_path),
          '--reporting-ref-point', '-0.0000015', '-0.0000015', '-1500000', '--n-iterations', '0'])
    assert received[0]['reporting_ref_point'] == [-1.5e-6, -1.5e-6, -1.5e6]


def test_cli_rejects_invalid_reference_before_dry_run_output(tmp_path):
    with pytest.raises(ValueError, match='Reporting reference'):
        main(['run-unconstrained', '--dry-run', '--output-dir', str(tmp_path / 'invalid'),
              '--reporting-ref-point', '-1', '-2'])
    assert not (tmp_path / 'invalid').exists()


@pytest.mark.parametrize("script, command", [
    ("run_constrained_mobo", "run-constrained"), ("run_unconstrained_mobo", "run-unconstrained"),
    ("run_scalarized_bo", "run-scalarized"), ("run_scalarized_suite", "run-scalarized-suite")])
def test_scripts_and_cli_resolve_identical_plans(script, command, monkeypatch):
    import importlib
    from mobo_linac.cli import build_parser
    from mobo_linac.cli.commands.run import resolve_plan
    module = importlib.import_module(f"scripts.{script}")
    argv = ["--config", "configs/publication_200MeV.yaml", "--seed", "5"]
    script_args = module.parse_args(argv)
    cli_args = build_parser().parse_args([command, *argv])
    assert vars(script_args) == vars(cli_args)
    mode = "scalarized_bo" if "scalarized" in command else "unconstrained_mobo"
    config, options = resolve_plan(cli_args, mode)
    assert options["num_workers"] == config.execution.max_workers  # never a hidden CLI default
    assert options["num_batches"] == config.campaign.num_batches and options["seed"] == 5


def test_validation_runs_in_its_own_directory_without_repository_scripts(tmp_path):
    import subprocess
    import sys as system
    code = (
        "import sys; sys.path = [p for p in sys.path if p not in ('', '.')];"
        "from mobo_linac.cli import main;"
        f"main(['run-validation', '--config', 'configs/mobo_200MeV.yaml', '--output-dir', r'{tmp_path}',"
        " '--n-iterations', '0', '--num-initial-samples', '2', '--mock-evaluator', '--device', 'cpu'])"
    )
    env = dict(__import__("os").environ, PYTHONPATH="src")
    subprocess.run([system.executable, "-c", code], check=True, env=env, cwd=Path(__file__).resolve().parents[1])
    runs = sorted(tmp_path.glob("validation_*"))
    assert len(runs) == 1 and (runs[0] / "run_complete.json").exists()
    assert not (tmp_path / "candidate_history.csv").exists()


def test_analyze_exports_the_figures_it_reports(tmp_path, capsys):
    run_dir = tmp_path / "run"
    main(["run-unconstrained", "--config", "configs/mobo_200MeV.yaml", "--n-iterations", "0",
          "--num-initial-samples", "3", "--output-dir", str(run_dir), "--mock-evaluator", "--device", "cpu"])
    figures = tmp_path / "figures"
    main(["analyze", "--run-dir", str(run_dir), "--output-dir", str(figures)])
    assert "Figures exported" in capsys.readouterr().out
    assert {p.name for p in figures.glob("*.png")} >= {"hypervolume_progress.png", "pareto_front.png"}
