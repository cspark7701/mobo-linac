"""
Structured Console Logging and Verbosity Management for mobo_linac.

Provides multi-level logging (DEBUG, INFO, SUCCESS, WARNING, ERROR),
quiet mode suppression, ANSI formatting, and file mirroring.
"""

from enum import IntEnum
import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Union


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    QUIET = 50


_GLOBAL_LOG_LEVEL = LogLevel.INFO
_GLOBAL_LOG_FILE: Optional[Path] = None
_LOGGERS: Dict[str, "MoboLogger"] = {}


class MoboLogger:
    """Lightweight structured logger with level filtering and formatting."""

    def __init__(self, name: str):
        self.name = name

    def _log(self, level: LogLevel, prefix: str, msg: str) -> None:
        if level < _GLOBAL_LOG_LEVEL:
            return

        formatted = f"{prefix} {msg}" if prefix else msg
        if level >= LogLevel.ERROR:
            sys.stderr.write(f"{formatted}\n")
            sys.stderr.flush()
        else:
            sys.stdout.write(f"{formatted}\n")
            sys.stdout.flush()

        if _GLOBAL_LOG_FILE is not None:
            try:
                with open(_GLOBAL_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{level.name}] [{self.name}] {msg}\n")
            except Exception:
                pass

    def debug(self, msg: str) -> None:
        self._log(LogLevel.DEBUG, "[DEBUG]", msg)

    def info(self, msg: str) -> None:
        self._log(LogLevel.INFO, "", msg)

    def success(self, msg: str) -> None:
        self._log(LogLevel.SUCCESS, "✓", msg)

    def warning(self, msg: str) -> None:
        self._log(LogLevel.WARNING, "[WARNING]", msg)

    def error(self, msg: str) -> None:
        self._log(LogLevel.ERROR, "[ERROR]", msg)

    def section(self, title: str) -> None:
        if LogLevel.INFO >= _GLOBAL_LOG_LEVEL:
            sep = "=" * 60
            self.info(f"\n{sep}\n  {title}\n{sep}")


def configure_logging(
    level: Union[int, str] = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    quiet: bool = False,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """
    Globally configures mobo_linac logging verbosity and file destination.
    """
    global _GLOBAL_LOG_LEVEL, _GLOBAL_LOG_FILE

    if quiet:
        _GLOBAL_LOG_LEVEL = LogLevel.WARNING
    elif debug:
        _GLOBAL_LOG_LEVEL = LogLevel.DEBUG
    elif verbose:
        _GLOBAL_LOG_LEVEL = LogLevel.DEBUG
    elif isinstance(level, str):
        lvl_upper = level.upper()
        if lvl_upper in LogLevel.__members__:
            _GLOBAL_LOG_LEVEL = LogLevel[lvl_upper]
        else:
            _GLOBAL_LOG_LEVEL = LogLevel.INFO
    elif isinstance(level, int):
        _GLOBAL_LOG_LEVEL = LogLevel(level)

    if log_file is not None:
        p = Path(log_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        _GLOBAL_LOG_FILE = p
    else:
        _GLOBAL_LOG_FILE = None


def get_logger(name: str = "mobo_linac") -> MoboLogger:
    """Returns a cached MoboLogger instance."""
    if name not in _LOGGERS:
        _LOGGERS[name] = MoboLogger(name)
    return _LOGGERS[name]
