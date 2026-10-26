"""Reports expose missing evidence, custom projections and invalid reporting inputs."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import runpy
import sys

import numpy as np
import pandas as pd
import pytest
import torch
import matplotlib.pyplot as plt

from mobo_linac.cli import main
from mobo_linac.io.run_data import read_run_data
from mobo_linac.metrics import hypervolume as hv, latex, publication, reporting, selection
from mobo_linac.metrics.exports import RunArtifactWriter
from mobo_linac.plotting import common, convergence, diagnostics, parameters, pareto
from mobo_linac.reporting import paper, comparison
from mobo_linac.robustness import evaluator as robust
from mobo_linac.robustness.workflow import run_robustness_workflow
from mobo_linac.perturbations import PerturbationSpecification, LatticeChannel
from mobo_linac.result_schema import ResultSchema


def test_report_preconditions(publication_runs, tmp_path):
    run = read_run_data(publication_runs[0])
    config = run.config
    for call in [
        lambda: hv.validate_reference_point_compatibility([1], [1, 2]),
        lambda: hv.HypervolumeTracker([1], config),
        lambda: latex.objective_columns(config, names=["missing"]),
        lambda: latex.generate_phase1_cases_latex_table(tmp_path / "missing.csv", tmp_path / "table.tex"),
        lambda: publication.generate_campaign_summary_latex_table([], phase_names=[]),
        lambda: publication.generate_comparison_report([], [], [], tmp_path / "r.md"),
        lambda: publication.read_comparison_runs([run.directory], results=[[]]),
        lambda: reporting.compute_campaign_metrics_history(
            run.results, [1e-6, 1e-6, 1e6], [-3, -3, -2], elapsed_wall_times=[]
        ),
        lambda: reporting.compute_campaign_metrics_history(
            run.results, [1e-6, 1e-6, 1e6], [-3, -3, -2], elapsed_wall_times=[-1] * 3
        ),
        lambda: selection.select_representatives([], config, policy="bad"),
        lambda: selection.select_representatives([], ResultSchema.from_config(config)),
        lambda: RunArtifactWriter(tmp_path, config).write([], None),
        lambda: RunArtifactWriter(tmp_path, config).write(
            run.results, hv.HypervolumeTracker([-1, -1, -1], config), extra_columns={"run_id": [1] * 3}
        ),
    ]:
        with pytest.raises((ValueError, TypeError, FileNotFoundError)):
            call()
    assert hv.compute_hypervolume(None, [-1]) == 0
    assert hv.validate_reference_point_compatibility([1], [1, 2], raise_on_incompatible=False) is False
    tracker = hv.HypervolumeTracker([-1, -1, -1], config)
    for reference in ([0.0, 0.0, 0.0], torch.zeros(3)):
        assert tracker.track_iteration(0, torch.empty((0, 3)), torch.empty(0, dtype=torch.bool), reference)[
            "acquisition_ref_point_model"
        ] == [0.0, 0.0, 0.0]
    empty = replace(run, results=[])
    assert all(np.isnan(v) for v in publication.scalarized_case_statistics(empty)["all_valid_extrema"].values())
    assert comparison.load_phase_results(run.directory, config)
    assert not paper.check_manuscript_consistency(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path / "missing.csv")


def test_plotting_custom_outputs_and_missing_progress(publication_runs, tmp_path):
    run = read_run_data(publication_runs[0])
    config = deepcopy(run.config)
    assert list(convergence._progress_axis(pd.DataFrame({"unknown": [1, 2]}))[1:]) == ["Step"]
    convergence.plot_hypervolume_histories(
        {"empty": pd.DataFrame(), "one": pd.DataFrame({"feasible_hypervolume": [1.0]})}, tmp_path / "hv.png"
    )
    with pytest.raises(ValueError):
        convergence.plot_scalarized_objective_trace(run.results, [1], config=config)
    model = SimpleNamespace(posterior=lambda x: SimpleNamespace(mean=x[:, :1], variance=torch.ones_like(x[:, :1])))
    fig = diagnostics.plot_gp_surrogate_slice(
        model, config.get_parameter_bounds_tensor(), torch.tensor(config.get_nominal_parameters()), config, n_points=5
    )
    assert len(fig.axes[0].lines) == 1
    common.save_fig(fig, tmp_path / "slice.png", close=True)
    assert not plt.fignum_exists(fig.number)
    parameters.plot_parallel_coordinates(
        [run.results[0], replace(run.results[0], evaluation_id="extra")], config, n_lines=1
    )
    # Four objectives create six panels; five create ten and leave two grid cells unused.
    extra = deepcopy(config.objectives[-1])
    extra.name = "custom"
    extra.explicit_name = "custom_value"
    extra.reporting_scale = 1
    config.objectives.append(extra)
    extra2 = deepcopy(extra)
    extra2.name = "custom2"
    extra2.explicit_name = "custom_value2"
    config.objectives.append(extra2)
    rows = [
        replace(
            r,
            objectives_physical=(r.objectives_physical + [1, 2]) if r.objectives_physical else None,
            objectives_model=(r.objectives_model + [-1, -2]) if r.objectives_model else None,
        )
        for r in run.results
    ]
    fig = pareto.plot_pareto_front(rows, config=config)
    assert any(not ax.get_visible() for ax in fig.axes)
    fig = pareto.plot_pareto_front_overlay({"run": rows}, config)
    assert any(not ax.get_visible() for ax in fig.axes)
    config.objectives = config.objectives[:1]
    with pytest.raises(ValueError):
        pareto.plot_pareto_front(rows, config=config)
    with pytest.raises(ValueError):
        pareto.plot_pareto_front_3d(rows, config=config)
    plt.close("all")


def test_robustness_missing_data_and_validation(sample_config, tmp_path):
    from mobo_linac.evaluation import EvaluationResult

    config = sample_config
    config.perturbations = {"version": 2, "lattice": [], "source": []}
    assert robust.configured_perturbation_spec(config).lattice == ()
    spec = PerturbationSpecification((LatticeChannel("x", "unknown", "relative", 0.1),))
    for nominal, count in [({}, -1), ({}, 1)]:
        with pytest.raises(ValueError):
            robust.generate_perturbed_machine_states(nominal, spec, count)
    row = EvaluationResult("one", "run", config.get_nominal_parameters(), objectives_physical=[1, 1, 1])
    summary = robust.compute_robustness_summary("one", row, [], config)
    assert np.isnan(summary["probability_of_feasibility"])
    evaluator = robust.RobustnessEvaluator(config=config, base_output_dir=tmp_path)
    with pytest.raises(ValueError):
        evaluator.generate_evaluation_plan([row], roles=[])
    with pytest.raises(ValueError):
        evaluator.generate_evaluation_plan([replace(row, x_physical=[])])
    with pytest.raises(ValueError):
        evaluator.evaluate_candidates([row], num_perturbations=0)
    with pytest.raises(ValueError):
        run_robustness_workflow([], config, tmp_path, num_perturbations=0)
    with pytest.raises(ValueError):
        run_robustness_workflow([], config, tmp_path)


def test_cli_entrypoints_and_failure_plans(tmp_path, monkeypatch):
    for module in ["mobo_linac.cli", "mobo_linac.cli.__main__"]:
        monkeypatch.setattr(sys, "argv", ["mobo-linac", "--help"])
        with pytest.raises(SystemExit) as error:
            runpy.run_module(module, run_name="__main__")
        assert error.value.code == 0
    for arguments in [
        ["resume", "--run-dir", str(tmp_path), "--dry-run"],
        ["run-scalarized", "--suite", "option2", "--dry-run"],
        ["run-scalarized-suite", "--cases", "all", "--dry-run"],
        ["run-scalarized-suite", "--case", "balanced", "--dry-run"],
        ["run-validation", "--dry-run"],
    ]:
        main(arguments)
    with pytest.raises(SystemExit):
        main(["validate-config", "--config", str(tmp_path / "absent.yaml")])
    assert main(["paper-figures", "--phase2-dir", str(tmp_path / "absent"), "--phase3-dir", str(tmp_path)]) == 1
    assert main(["paper-figures", "--phase2-dir", str(tmp_path), "--phase3-dir", str(tmp_path), "--check-only"]) == 1


def test_cli_workflow_adapters(tmp_path, monkeypatch):
    from mobo_linac.campaigns.benchmark import BenchmarkCampaignRunner
    from mobo_linac.io import checkpoint

    called = []
    fake = SimpleNamespace(analyze_completed_results=lambda: (called.append(True), None))
    monkeypatch.setattr(BenchmarkCampaignRunner, "from_output_dir", lambda directory: fake)
    main(["analyze-benchmark", "--output-dir", str(tmp_path)])
    assert called
    main(
        [
            "run-validation",
            "--num-initial-samples",
            "1",
            "--n-iterations",
            "0",
            "--mock-evaluator",
            "--output-dir",
            str(tmp_path / "validation"),
            "--device",
            "cpu",
            "--quiet",
        ]
    )
    main(["run-scalarized", "--suite", "option2", "--case", "balanced", "--dry-run"])
    monkeypatch.setattr(sys, "argv", ["mobo-linac", "--help"])
    with pytest.raises(SystemExit):
        runpy.run_path(str(Path(__file__).parents[1] / "src/mobo_linac/cli/__init__.py"), run_name="__main__")
    monkeypatch.setattr(checkpoint, "load_run_checkpoint", lambda *a: SimpleNamespace(migrated_from=None))
    with pytest.raises(ValueError, match="legacy"):
        main(["resume", "--run-dir", str(tmp_path), "--legacy-scalar-weights", "1", "1", "1"])


def test_legacy_publication_frames_and_missing_verification(publication_runs, tmp_path, monkeypatch):
    from mobo_linac.plotting import publication as plots

    run = read_run_data(publication_runs[0])
    assert len(plots._load_pareto_csv(run.directory)) == 1
    original_loader = plots._load_hypervolume_csv
    monkeypatch.setattr(plots, "_load_hypervolume_csv", lambda directory: pd.DataFrame({"iteration": [0]}))
    plots.plot_feasible_fraction(publication_runs[1], publication_runs[2], tmp_path / "unknown.png")
    assert (tmp_path / "unknown.png").exists()
    monkeypatch.setattr(plots, "_load_hypervolume_csv", original_loader)
    # The table builder receives the actual recorded configuration when suite data is available.
    (run.directory / "cases_summary.csv").write_text("placeholder")
    recorded = []
    monkeypatch.setattr(paper, "generate_phase1_cases_latex_table", lambda *a, **k: recorded.append(k["config"]))
    paper.generate_paper_artifacts(
        publication_runs[1],
        publication_runs[2],
        tmp_path / "missing.csv",
        tmp_path / "figures",
        tmp_path / "tables",
        phase1_dir=run.directory,
    )
    assert recorded and recorded[0].objectives == run.config.objectives


def test_verifier_preconditions_and_identity_checks(sample_config, tmp_path):
    from mobo_linac.evaluation import EvaluationResult
    from mobo_linac.execution.candidate_evaluator import EvaluationTask, EvaluationOutcome
    from mobo_linac.verification.verifier import ParetoVerifier, save_verification_reports

    with pytest.raises(TypeError):
        ParetoVerifier(None)
    with pytest.raises(ValueError):
        ParetoVerifier(sample_config, tol_verified=2, tol_conditional=1)
    verifier = ParetoVerifier(sample_config, base_output_dir=tmp_path)
    row = EvaluationResult("original", "run", sample_config.get_nominal_parameters(), objectives_physical=[1, 1, 1])
    with pytest.raises(ValueError):
        verifier.generate_evaluation_plan([row], roles=[])
    with pytest.raises(ValueError):
        verifier.generate_evaluation_plan([replace(row, x_physical=[])])
    with pytest.raises(ValueError):
        verifier.verify_candidates({})
    task = EvaluationTask("submitted", "one", row.x_physical, nominal_result=row)
    outcome = EvaluationOutcome(task, replace(row, evaluation_id="foreign"))
    record = verifier.build_record(outcome, tmp_path / "session", mock=True)
    assert "MOCK_" in record["verification_status"]
    (tmp_path / "verification_summary.csv").touch()
    with pytest.raises(FileExistsError):
        save_verification_reports([], tmp_path, tmp_path, config=sample_config)


def test_unknown_robustness_nominal_is_not_scored(sample_config, tmp_path, monkeypatch):
    from mobo_linac.evaluation import EvaluationResult
    from mobo_linac.execution.candidate_evaluator import EvaluationTask, EvaluationOutcome

    spec = PerturbationSpecification(())
    evaluator = robust.RobustnessEvaluator(config=sample_config, base_output_dir=tmp_path, spec=spec)
    task = EvaluationTask("one", "one", sample_config.get_nominal_parameters())
    outcome = EvaluationOutcome(task, EvaluationResult("one", "run", task.parameters))
    monkeypatch.setattr(evaluator, "generate_evaluation_plan", lambda *a, **k: [task])
    monkeypatch.setattr(evaluator, "evaluate_plan_parallel", lambda *a, **k: [outcome])
    assert evaluator.evaluate_candidates([], num_perturbations=1) == []
