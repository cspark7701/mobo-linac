"""
Standard-library logging: levels, console routing, log files and per-run logs.
"""

import logging

import pytest

from mobo_linac.utils import configure_logging, get_logger


@pytest.fixture(autouse=True)
def restore_logging():
    yield
    configure_logging(level="INFO")


def test_loggers_are_standard_and_inside_the_package_hierarchy():
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "mobo_linac.test_module"
    assert get_logger("mobo_linac.campaigns.runner").name == "mobo_linac.campaigns.runner"


def test_console_levels_and_quiet_mode(capsys):
    logger = get_logger("test_module")
    configure_logging(level="INFO")
    logger.info("Informational message")
    logger.debug("Hidden debug message")
    logger.warning("Caution advised")
    captured = capsys.readouterr()
    assert "Informational message" in captured.out
    assert "Hidden debug message" not in captured.out
    assert "[WARNING] Caution advised" in captured.out

    configure_logging(quiet=True)
    logger.info("Quiet info message")
    logger.warning("Quiet warning message")
    logger.error("Critical failure")
    captured = capsys.readouterr()
    assert "Quiet info message" not in captured.out
    assert "[WARNING] Quiet warning message" in captured.out
    assert "[ERROR] Critical failure" in captured.err


def test_debug_and_verbose_modes(capsys):
    logger = get_logger("debug_module")
    configure_logging(debug=True)
    logger.debug("Detailed diagnostic state")
    assert "[DEBUG] Detailed diagnostic state" in capsys.readouterr().out
    configure_logging(verbose=True)
    logger.debug("not shown in verbose mode")
    logger.info("timestamped")
    out = capsys.readouterr().out
    assert "not shown" not in out
    line = next(l for l in out.splitlines() if "timestamped" in l)
    assert line[:4].isdigit() and line[4] == "-"  # verbose INFO carries timestamps


def test_log_file_records_levels_and_module_names(tmp_path):
    log_file = tmp_path / "execution.log"
    configure_logging(level="INFO", log_file=log_file)
    logger = get_logger("file_logger")
    logger.info("Logging to disk test")
    logger.warning("Disk warning test")
    content = log_file.read_text(encoding="utf-8")
    assert "[INFO] [mobo_linac.file_logger] Logging to disk test" in content
    assert "[WARNING] [mobo_linac.file_logger] Disk warning test" in content


def test_records_reach_caplog():
    logger = get_logger("caplog_module")
    handler_records = []

    class Collect(logging.Handler):
        def emit(self, record):
            handler_records.append(record)

    collector = Collect()
    logging.getLogger("mobo_linac").addHandler(collector)
    try:
        logger.warning("structured")
    finally:
        logging.getLogger("mobo_linac").removeHandler(collector)
    assert handler_records[0].levelno == logging.WARNING and handler_records[0].name == "mobo_linac.caplog_module"


def test_device_and_proposal_logging_obey_quiet_mode(monkeypatch, capsys):
    import torch
    import mobo_linac.acquisition.mobo as acquisition
    from mobo_linac.utils import get_device
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(acquisition, "optimize_acqf", lambda **kwargs: (
        kwargs["bounds"].mean(0).repeat(kwargs["q"], 1), torch.zeros(1)))
    configure_logging(quiet=True)
    get_device("cuda:0")
    acquisition.generate_next_candidates(torch.nn.Linear(1, 1), torch.tensor([[0.], [1.]]))
    output = capsys.readouterr()
    assert "CUDA is unavailable" in output.out
    assert "succeeded" not in output.out
    configure_logging(debug=True)
    acquisition.generate_next_candidates(torch.nn.Linear(1, 1), torch.tensor([[0.], [1.]]))
    assert "[DEBUG] Acquisition proposal succeeded" in capsys.readouterr().out


def test_campaign_progress_obeys_quiet_mode_and_writes_run_log(tmp_path, capsys):
    from mobo_linac.campaigns.runner import MoboCampaignRunner
    from mobo_linac.execution import MockEvaluator
    configure_logging(quiet=True)
    MoboCampaignRunner(output_dir=tmp_path, num_initial_samples=2, num_batches=0,
                       evaluator=MockEvaluator(tmp_path), device="cpu",
                       export_plots=False, export_env_info=False).run()
    assert "Starting Optimization Campaign" not in capsys.readouterr().out
    configure_logging(level="INFO")
    run_dir = tmp_path / "second"
    MoboCampaignRunner(output_dir=run_dir, num_initial_samples=2, num_batches=0,
                       evaluator=MockEvaluator(run_dir), device="cpu",
                       export_plots=False, export_env_info=False).run()
    log = (run_dir / "run.log").read_text()
    assert "[INFO] [mobo_linac.campaigns.runner] === Starting Optimization Campaign" in log
    assert log.splitlines()[0][:4].isdigit()  # every line is timestamped
    assert not logging.getLogger("mobo_linac").handlers[-1].__class__.__name__ == "FileHandler"


def test_robustness_dry_run_is_logged_and_silenced_by_quiet(tmp_path, capsys):
    from mobo_linac.config import load_config
    from mobo_linac.robustness.workflow import run_robustness_workflow
    config = load_config("configs/mobo_200MeV.yaml")
    run_robustness_workflow([], config, tmp_path, num_perturbations=2, num_workers=1, dry_run=True)
    assert "Robustness Analysis Plan" in capsys.readouterr().out
    configure_logging(quiet=True)
    run_robustness_workflow([], config, tmp_path, num_perturbations=2, num_workers=1, dry_run=True)
    assert capsys.readouterr().out == ""


def test_library_code_prints_only_in_cli():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src" / "mobo_linac"
    offenders = [str(path.relative_to(root)) for path in root.rglob("*.py")
                 if "cli" not in path.relative_to(root).parts and "print(" in path.read_text()]
    assert offenders == []
