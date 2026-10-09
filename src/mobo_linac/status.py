"""Typed simulation status, failure categories and the retry policy shared by all backends.

The simulator adapter reports a :class:`SimulationStatus`. It travels unchanged through
worker results and attempt manifests and is mapped to a scientific
:class:`FailureCategory` in exactly one table.
"""

from enum import Enum
import subprocess
from typing import Any, Optional


class SimulationStatus(str, Enum):
    """Classification status for one simulation attempt."""

    SUCCESS = "SUCCESS"
    PREMATURE_LOSS = "PREMATURE_LOSS"
    CHARGE_ZERO = "CHARGE_ZERO"
    TIMEOUT = "TIMEOUT"
    RUN_FAILED = "RUN_FAILED"
    NUMERICAL_ERROR = "NUMERICAL_ERROR"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    OUTPUT_MISSING = "OUTPUT_MISSING"
    PROVENANCE_ERROR = "PROVENANCE_ERROR"
    WORKER_CRASH = "WORKER_CRASH"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"


class FailureCategory(str, Enum):
    """Scientific categories of evaluation outcomes."""

    SUCCESS = "SUCCESS"
    INFEASIBLE_BEAM = "INFEASIBLE_BEAM"
    PREMATURE_BEAM_LOSS = "PREMATURE_BEAM_LOSS"
    ASTRA_TIMEOUT = "ASTRA_TIMEOUT"
    NONZERO_RETURN = "NONZERO_RETURN"
    MISSING_OUTPUT = "MISSING_OUTPUT"
    CORRUPTED_OUTPUT = "CORRUPTED_OUTPUT"
    EMPTY_OUTPUT = "EMPTY_OUTPUT"
    NAN_INF_DIAGNOSTICS = "NAN_INF_DIAGNOSTICS"
    INVALID_TRANSMISSION = "INVALID_TRANSMISSION"
    PROVENANCE_FAILURE = "PROVENANCE_FAILURE"
    WORKER_CRASH = "WORKER_CRASH"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"


# Every non-success simulation status maps to exactly one failure category.
FAILURE_CATEGORY_BY_STATUS = {
    SimulationStatus.PREMATURE_LOSS: FailureCategory.PREMATURE_BEAM_LOSS,
    SimulationStatus.CHARGE_ZERO: FailureCategory.EMPTY_OUTPUT,
    SimulationStatus.TIMEOUT: FailureCategory.ASTRA_TIMEOUT,
    SimulationStatus.RUN_FAILED: FailureCategory.NONZERO_RETURN,
    SimulationStatus.NUMERICAL_ERROR: FailureCategory.NAN_INF_DIAGNOSTICS,
    SimulationStatus.FILE_CORRUPTED: FailureCategory.CORRUPTED_OUTPUT,
    SimulationStatus.OUTPUT_MISSING: FailureCategory.MISSING_OUTPUT,
    SimulationStatus.PROVENANCE_ERROR: FailureCategory.PROVENANCE_FAILURE,
    SimulationStatus.WORKER_CRASH: FailureCategory.WORKER_CRASH,
    SimulationStatus.UNHANDLED_EXCEPTION: FailureCategory.UNHANDLED_EXCEPTION,
}

# Infrastructure outcomes that a fresh attempt can change. Deterministic physics
# outcomes (beam loss, numerical errors, missing statistics) are never retried by default.
DEFAULT_RETRY_STATUSES = ("TIMEOUT", "WORKER_CRASH", "PROVENANCE_ERROR", "UNHANDLED_EXCEPTION")

# Archived manifests and worker dictionaries recorded lowercase coarse strings.
_LEGACY_STATUS = {"success": SimulationStatus.SUCCESS, "timeout": SimulationStatus.TIMEOUT,
                  "failed": SimulationStatus.UNHANDLED_EXCEPTION}


def decode_status(value: Any) -> SimulationStatus:
    """Decode a recorded status, including archived lowercase strings."""
    if isinstance(value, SimulationStatus):
        return value
    if isinstance(value, str):
        if value in SimulationStatus.__members__:
            return SimulationStatus[value]
        if value in _LEGACY_STATUS:
            return _LEGACY_STATUS[value]
    return SimulationStatus.UNHANDLED_EXCEPTION


def is_success(value: Any) -> bool:
    return decode_status(value) is SimulationStatus.SUCCESS


def classify_exception(error: BaseException, astra_sim: Optional[Any] = None) -> SimulationStatus:
    """Classify an execution exception by type and recorded run information, never by message text."""
    run_info = {}
    output = getattr(astra_sim, "output", None)
    if isinstance(output, dict) and isinstance(output.get("run_info"), dict):
        run_info = output["run_info"]
    if run_info.get("why_error") == "timeout" or isinstance(error, (subprocess.TimeoutExpired, TimeoutError)):
        return SimulationStatus.TIMEOUT
    if isinstance(error, (FloatingPointError, OverflowError, ZeroDivisionError)):
        return SimulationStatus.NUMERICAL_ERROR
    if isinstance(error, FileNotFoundError):
        return SimulationStatus.OUTPUT_MISSING
    if isinstance(error, (EOFError, UnicodeDecodeError)):
        return SimulationStatus.FILE_CORRUPTED
    if run_info.get("why_error") or ("start_time" in run_info and "run_time" not in run_info):
        # The executable was launched but did not report a finished simulation.
        return SimulationStatus.RUN_FAILED
    return SimulationStatus.UNHANDLED_EXCEPTION
