#!/usr/bin/env python3
"""Build and check the supplement S1 evidence map for the manuscript.

``--build`` writes ``docs/paper/supplement/ledger_manifest.json``: the code commit, the
configuration hash and the command-line settings of each production step, and the size and
SHA-256 of every run-level input ledger (evaluations, resolved configuration, completion
marker) that the evidence files are computed from. The full run directories are not
distributed. ``--check`` (the default) verifies that every map entry exists, that every
file in the evidence directory is mapped, that each manuscript location is a defined
label, that every generator has an entry in ``input_inventory.csv`` with known input classes
and a reproduction level, and, when the raw results are present, that the recorded ledger
checksums still hold. The inventory records which inputs each generator needs; passing this
check does not itself regenerate any evidence (see ``scripts/check_supplement_regeneration.py``).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPLEMENT = ROOT / "docs/paper/supplement"
MAP = SUPPLEMENT / "evidence_map.csv"
MANIFEST = SUPPLEMENT / "ledger_manifest.json"
INVENTORY = SUPPLEMENT / "input_inventory.csv"
INPUT_CLASSES = {"ledgers", "run_records", "gp_checkpoints", "tracking_outputs", "retracking_records",
                 "derived_evidence", "tracking"}
LEVELS = {"2a", "2b", "3"}
EVIDENCE = ROOT / "docs/paper/revisions/evidence"
PAPER = ROOT / "docs/paper"
RESULTS = ("results/paper_production", "results/revision_round2")
LEDGERS = ("evaluations.csv", "config.json", "run_complete.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def step_records() -> list[dict]:
    records = []
    for path in sorted((ROOT / RESULTS[0]).glob("*/step_record_*.json")):
        record = json.loads(path.read_text())
        records.append({"record": str(path.relative_to(ROOT)), "step": record["parameters"]["step"],
                        "git_commit": record["git"]["commit"], "git_dirty": record["git"]["dirty"],
                        "config_sha256": record["config"]["sha256"], "parameters": record["parameters"]})
    return records


def ledgers() -> list[dict]:
    rows = []
    for base in RESULTS:
        for marker in sorted((ROOT / base).rglob("run_complete.json")):
            for name in LEDGERS:
                path = marker.parent / name
                if path.exists():
                    rows.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                                 "sha256": sha256(path)})
    return rows


def build() -> dict:
    manifest = {"description": "Supplement S1 ledger manifest; raw run directories are not distributed",
                "production_steps": step_records(), "ledgers": ledgers()}
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def labels() -> set[str]:
    sources = [PAPER / "main.tex", *EVIDENCE.glob("*.tex"), *PAPER.glob("*.tex")]
    return {label for path in sources for label in re.findall(r"\\label\{([^}]*)\}", path.read_text())}


def check() -> list[str]:
    errors = []
    with MAP.open() as handle:
        rows = list(csv.DictReader(handle))
    defined = labels()
    for row in rows:
        for key in ("path", "generator"):
            if row[key] and not (ROOT / row[key]).exists():
                errors.append(f"{row['item']}: missing {key} {row[key]}")
        if row["manuscript_location"] and row["manuscript_location"] not in defined:
            errors.append(f"{row['item']}: undefined label {row['manuscript_location']}")
    inventory = {}
    if INVENTORY.exists():
        with INVENTORY.open() as handle:
            inventory = {entry["generator"]: entry for entry in csv.DictReader(handle)}
    for generator in sorted({row["generator"] for row in rows if row["generator"]}):
        entry = inventory.get(generator)
        if entry is None:
            errors.append(f"generator without input inventory entry: {generator}")
            continue
        unknown = set(entry["input_classes"].split(";")) - INPUT_CLASSES
        if unknown or entry["level"] not in LEVELS:
            errors.append(f"invalid inventory entry for {generator}: {sorted(unknown)} {entry['level']}")
    mapped = {row["path"] for row in rows}
    for path in sorted(EVIDENCE.iterdir()):
        if str(path.relative_to(ROOT)) not in mapped:
            errors.append(f"unmapped evidence file {path.relative_to(ROOT)}")
    if MANIFEST.exists() and (ROOT / RESULTS[0]).exists():
        for entry in json.loads(MANIFEST.read_text())["ledgers"]:
            path = ROOT / entry["path"]
            if path.exists() and sha256(path) != entry["sha256"]:
                errors.append(f"ledger checksum changed: {entry['path']}")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="Rewrite the ledger manifest first.")
    args = parser.parse_args(argv)
    if args.build:
        manifest = build()
        print(f"{len(manifest['ledgers'])} ledgers, {len(manifest['production_steps'])} step records")
    errors = check()
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
