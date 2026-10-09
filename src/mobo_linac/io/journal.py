"""Durable evaluation journal with separate candidate and batch metadata.

The campaign parent is the single writer. JSONL is authoritative; CSV is a
derived view and must never be used to recover typed campaign state.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import List, Optional, Union
import warnings

from mobo_linac.evaluation import EvaluationResult
from mobo_linac.utils.durable import append_line_durable, atomic_csv, ensure_trailing_newline, truncate_durable
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
        truncate_durable(path, offset)
    else:
        ensure_trailing_newline(path)


def write_streaming_csv(output_dir: Union[str, Path], records=None, *, config) -> Path:
    """Atomically rebuild the CSV view from validated, deduplicated JSONL records."""
    out_dir = Path(output_dir)
    records = load_streaming_records(out_dir) if records is None else records
    records = sorted(records, key=lambda r: (r.batch_idx if r.batch_idx is not None else -1,
                                            r.candidate_idx if r.candidate_idx is not None else -1,
                                            r.result.evaluation_id))
    frame = results_to_dataframe([r.result for r in records], config=config)
    frame["batch_idx"] = [r.batch_idx for r in records]
    frame["candidate_idx"] = [r.candidate_idx for r in records]
    return atomic_csv(out_dir / "evaluations_stream.csv", frame)


class EvaluationJournal:
    """Campaign-owned journal: validated once on open, then constant-time appends.

    The identity index replaces the per-append re-read of the whole JSONL file. The CSV
    view is rebuilt only on :meth:`write_csv` (batch boundaries), not per evaluation.
    """

    def __init__(self, output_dir: Union[str, Path], config):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.path = self.output_dir / "evaluations_stream.jsonl"
        repair_journal_tail(self.output_dir)  # validates the full journal exactly once
        self.records = load_streaming_records(self.output_dir)
        self._index = {(r.result.run_id, r.result.evaluation_id): r for r in self.records}

    def __len__(self) -> int:
        return len(self.records)

    @property
    def results(self) -> List[EvaluationResult]:
        return [record.result for record in self.records]

    def append(self, result: EvaluationResult, batch_idx=None, candidate_idx=None) -> bool:
        """Durably append one completion; returns False for an identical duplicate."""
        record = _decode(JournalRecord(result, batch_idx, candidate_idx).to_dict())
        previous = self._index.get((result.run_id, result.evaluation_id))
        if previous is not None:
            if (not same_evaluation(previous.result, result) or previous.batch_idx != batch_idx
                    or previous.candidate_idx != candidate_idx):
                raise ValueError("Conflicting duplicate journal completion.")
            return False
        append_line_durable(self.path, json.dumps(record.to_dict()))
        self._index[(result.run_id, result.evaluation_id)] = record
        self.records.append(record)
        return True

    def write_csv(self) -> Path:
        return write_streaming_csv(self.output_dir, self.records, config=self.config)


def append_record(output_dir, result, batch_idx=None, candidate_idx=None, *, config) -> Path:
    """Stand-alone append (validates the journal and rebuilds the CSV view on every call).

    Campaigns hold an :class:`EvaluationJournal` instead, which appends in constant time.
    """
    journal = EvaluationJournal(output_dir, config)
    journal.append(result, batch_idx, candidate_idx)
    return journal.write_csv()


def append_streaming_evaluation(output_dir, result, batch_idx=None, candidate_idx=None, *, config) -> Path:
    """Durably append JSONL first, then derive the CSV view; write errors propagate."""
    return append_record(output_dir, result, batch_idx, candidate_idx, config=config)


def load_streaming_evaluations(output_dir: Union[str, Path]) -> List[EvaluationResult]:
    """Load exact typed JSONL records, including legacy batch metadata, without CSV fallback."""
    return [record.result for record in load_streaming_records(output_dir)]
