"""
Standard-library logging for mobo_linac.

All package loggers live under the ``mobo_linac`` logger. ``configure_logging`` installs one
console handler (errors to stderr, other records to stdout) and optionally a file handler;
``run_log`` adds a per-run ``run.log`` with timestamps, levels and module names for the
duration of a campaign.
"""

from contextlib import contextmanager
import logging
from pathlib import Path
import sys
from typing import Iterator, Optional, Union

PACKAGE = "mobo_linac"
FILE_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"


class _ConsoleHandler(logging.StreamHandler):
    """Errors go to stderr, everything else to stdout; streams are resolved at emit time."""

    def __init__(self):
        super().__init__(sys.stdout)

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stderr if record.levelno >= logging.ERROR else sys.stdout
        super().emit(record)


class _ConsoleFormatter(logging.Formatter):
    """Plain INFO lines; other levels carry a ``[LEVEL]`` prefix; ``timestamps`` for --verbose."""

    def __init__(self, timestamps: bool = False):
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")
        self.timestamps = timestamps

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.levelno != logging.INFO:
            message = f"[{record.levelname}] {message}"
        if self.timestamps:
            message = f"{self.formatTime(record, self.datefmt)} {message}"
        return message


def _package_logger() -> logging.Logger:
    logger = logging.getLogger(PACKAGE)
    logger.propagate = False  # the package owns its console/file handlers
    return logger


def configure_logging(
    level: Union[int, str] = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Set package verbosity and (re)install the console handler and optional log file.

    ``quiet``: warnings and errors only; ``verbose``: INFO with timestamps; ``debug``: DEBUG.
    """
    logger = _package_logger()
    if quiet:
        resolved = logging.WARNING
    elif debug:
        resolved = logging.DEBUG
    elif verbose:
        resolved = logging.INFO
    elif isinstance(level, str):
        resolved = logging.getLevelName(level.upper()) if isinstance(logging.getLevelName(level.upper()), int) else logging.INFO
    else:
        resolved = int(level)
    logger.setLevel(resolved)
    for handler in list(logger.handlers):
        if isinstance(handler, _ConsoleHandler) or getattr(handler, "_mobo_configured_file", False):
            logger.removeHandler(handler)
            handler.close()
    console = _ConsoleHandler()
    console.setFormatter(_ConsoleFormatter(timestamps=verbose or debug))
    logger.addHandler(console)
    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        file_handler._mobo_configured_file = True
        logger.addHandler(file_handler)


def get_logger(name: str = PACKAGE) -> logging.Logger:
    """A logger inside the ``mobo_linac`` hierarchy (configured with defaults on first use)."""
    package = _package_logger()
    if not any(isinstance(handler, _ConsoleHandler) for handler in package.handlers):
        configure_logging()
    return logging.getLogger(name if name == PACKAGE or name.startswith(PACKAGE + ".") else f"{PACKAGE}.{name}")


@contextmanager
def run_log(run_dir: Union[str, Path]) -> Iterator[Path]:
    """Append every record the package emits to ``<run_dir>/run.log`` while active."""
    path = Path(run_dir) / "run.log"  # the run directory must already exist
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(FILE_FORMAT))
    logger = _package_logger()
    logger.addHandler(handler)
    try:
        yield path
    finally:
        logger.removeHandler(handler)
        handler.close()
