"""
Unit tests for Structured Console Logging & Verbosity Controls (Task 23).
"""

from pathlib import Path
import pytest

from mobo_linac.utils import LogLevel, configure_logging, get_logger


def test_logger_levels_and_quiet_mode(capsys):
    """Verify logger output filtering across standard and quiet modes."""
    logger = get_logger("test_module")

    # 1. Standard INFO mode
    configure_logging(level="INFO")
    logger.info("Informational message")
    logger.debug("Hidden debug message")
    logger.success("Operation successful")
    logger.warning("Caution advised")

    captured = capsys.readouterr()
    assert "Informational message" in captured.out
    assert "Hidden debug message" not in captured.out
    assert "✓ Operation successful" in captured.out
    assert "[WARNING] Caution advised" in captured.out

    # 2. Quiet mode: suppresses info & success, retains warnings & errors
    configure_logging(quiet=True)
    logger.info("Quiet info message")
    logger.success("Quiet success message")
    logger.warning("Quiet warning message")
    logger.error("Critical failure")

    captured_quiet = capsys.readouterr()
    assert "Quiet info message" not in captured_quiet.out
    assert "Quiet success message" not in captured_quiet.out
    assert "[WARNING] Quiet warning message" in captured_quiet.out
    assert "[ERROR] Critical failure" in captured_quiet.err


def test_logger_debug_and_verbose_mode(capsys):
    """Verify debug and verbose flags reveal debug messages."""
    logger = get_logger("debug_module")

    configure_logging(debug=True)
    logger.debug("Detailed diagnostic state")

    captured = capsys.readouterr()
    assert "[DEBUG] Detailed diagnostic state" in captured.out


def test_logger_file_mirroring(tmp_path):
    """Verify logs are written to an external log file when configured."""
    log_file = tmp_path / "execution.log"
    configure_logging(level="INFO", log_file=log_file)

    logger = get_logger("file_logger")
    logger.info("Logging to disk test")
    logger.warning("Disk warning test")

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "[INFO] [file_logger] Logging to disk test" in content
    assert "[WARNING] [file_logger] Disk warning test" in content


def test_logger_section_formatting(capsys):
    """Verify section banner formatting."""
    configure_logging(level="INFO")
    logger = get_logger("section_logger")
    logger.section("Optimization Campaign Started")

    captured = capsys.readouterr()
    assert "Optimization Campaign Started" in captured.out
    assert "====" in captured.out
