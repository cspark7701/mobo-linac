"""Durable evaluation journal with separate candidate and batch metadata.

The campaign parent is the single writer. JSONL is authoritative; CSV is a
derived view and must never be used to recover typed campaign state.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import List, Optional, Union
import warnings

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.io.results import results_to_dataframe


@dataclass
class JournalRecord:
    result: EvaluationResult
    batch_idx: Optional[int] = None
    candidate_idx: Optional[int] = None

    def to_dict(self):
        return {"version": "1.0", "batch_idx": self.batch_idx,
                "candidate_idx": self.candidate_idx, "evaluation": self.result.to_dict()}


def same_evaluation(left: EvaluationResult, right: EvaluationResult) -> bool:
    # Canonical JSON also compares failure diagnostics containing NaN consistently.
    return json.dumps(left.to_dict(), sort_keys=True) == json.dumps(right.to_dict(), sort_keys=True)


def _decode(payload) -> JournalRecord:
    if not isinstance(payload, dict):
        raise ValueError("Journal record must be an object.")
    if "evaluation" in payload:
        if payload.get("version") != "1.0":
            raise ValueError("Unsupported evaluation journal version.")
        if set(payload) - {"version", "batch_idx", "candidate_idx", "evaluation"}:
            raise ValueError("Unexpected journal envelope fields.")
        result_data = payload["evaluation"]
    else:
        # Legacy flat JSONL stored batch_idx alongside the dataclass fields.
        result_data = {k: v for k, v in payload.items() if k not in ("batch_idx", "candidate_idx")}
    record = JournalRecord(EvaluationResult.from_dict(result_data),
                           payload.get("batch_idx"), payload.get("candidate_idx"))
    for name in ("batch_idx", "candidate_idx"):
        value = getattr(record, name)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"Invalid journal {name}.")
    if not isinstance(record.result.evaluation_id, str) or not isinstance(record.result.run_id, str):
        raise ValueError("Journal evaluation identities must be strings.")
    return record


def _incomplete_tail(line, error) -> bool:
    if isinstance(error, UnicodeDecodeError):
        return error.reason == "unexpected end of data" and error.end == len(line)
    tail = error.doc[error.pos:].rstrip()
    return (error.msg.startswith("Unterminated string")
            or not tail
            or (error.msg == "Expecting value" and tail in ("t", "tr", "tru", "f", "fa", "fal", "fals", "n", "nu", "nul"))
            or (error.msg == "Expecting ',' delimiter" and re.fullmatch(r"[eE][+-]?|\.", tail) is not None)
            or (error.msg.startswith("Invalid \\uXXXX escape")
                and re.fullmatch(r"u[0-9a-fA-F]{0,3}", tail) is not None))


def _read(output_dir):
    path = Path(output_dir) / "evaluations_stream.jsonl"
    if not path.exists():
        return [], 0, False
    data = path.read_bytes()
    records = []
    identities = {}
    offset = 0
    lines = data.splitlines(keepends=True)
    for number, line in enumerate(lines, 1):
        try:
            payload = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            if (number == len(lines) and not line.endswith(b"\n")
                    and _incomplete_tail(line, error)):
                warnings.warn(f"Ignoring truncated trailing journal record at {path}:{number}.", RuntimeWarning)
                return records, offset, True
            raise ValueError(f"Malformed journal record at {path}:{number}: {error}") from error
        try:
            record = _decode(payload)
            key = (record.result.run_id, record.result.evaluation_id)
            previous = identities.get(key)
            if previous is not None:
                if (not same_evaluation(previous.result, record.result)
                        or previous.batch_idx != record.batch_idx
                        or previous.candidate_idx != record.candidate_idx):
                    raise ValueError(f"Conflicting duplicate journal identity: {key}.")
            else:
                identities[key] = record
                records.append(record)
        except (TypeError, ValueError, KeyError) as error:
            raise ValueError(f"Invalid journal record at {path}:{number}: {error}") from error
        offset += len(line)
    return records, offset, False


def load_streaming_records(output_dir: Union[str, Path]) -> List[JournalRecord]:
    """Read versioned or legacy records; tolerate only an incomplete final JSON line."""
    return _read(output_dir)[0]


def repair_journal_tail(output_dir: Union[str, Path]) -> None:
    """Repair a tolerated partial tail before further appends, after validation."""
    _, offset, truncated = _read(output_dir)
    path = Path(output_dir) / "evaluations_stream.jsonl"
    if truncated:
        with path.open("r+b") as stream:
            stream.truncate(offset)
            stream.flush()
            os.fsync(stream.fileno())
    elif path.exists() and path.stat().st_size:
        with path.open("r+b") as stream:
            stream.seek(-1, os.SEEK_END)
            if stream.read(1) != b"\n":
                stream.seek(0, os.SEEK_END)
                stream.write(b"\n")
                stream.flush()
                os.fsync(stream.fileno())


def write_streaming_csv(output_dir: Union[str, Path], records=None, config=None) -> Path:
    """Atomically rebuild the CSV view from validated, deduplicated JSONL records."""
    out_dir = Path(output_dir)
    records = load_streaming_records(out_dir) if records is None else records
    records = sorted(records, key=lambda r: (r.batch_idx if r.batch_idx is not None else -1,
                                            r.candidate_idx if r.candidate_idx is not None else -1,
                                            r.result.evaluation_id))
    frame = results_to_dataframe([r.result for r in records], config=config)
    frame["batch_idx"] = [r.batch_idx for r in records]
    frame["candidate_idx"] = [r.candidate_idx for r in records]
    path = out_dir / "evaluations_stream.csv"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=out_dir, delete=False) as stream:
            temporary = Path(stream.name)
            frame.to_csv(stream, index=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return path


def append_record(output_dir, result, batch_idx=None, candidate_idx=None, config=None) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    records = load_streaming_records(out_dir)
    record = _decode(JournalRecord(result, batch_idx, candidate_idx).to_dict())
    previous = next((r for r in records if (r.result.run_id, r.result.evaluation_id)
                     == (result.run_id, result.evaluation_id)), None)
    if previous is not None:
        if (not same_evaluation(previous.result, result) or previous.batch_idx != batch_idx
                or previous.candidate_idx != candidate_idx):
            raise ValueError("Conflicting duplicate journal completion.")
    else:
        repair_journal_tail(out_dir)
        with (out_dir / "evaluations_stream.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record.to_dict()) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(out_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        records.append(record)
    return write_streaming_csv(out_dir, records, config=config)
