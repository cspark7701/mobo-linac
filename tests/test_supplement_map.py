import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("supplement", ROOT / "scripts/build_supplement_manifest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_evidence_map_is_complete_and_resolvable():
    assert load().check() == []


def test_map_items_are_documented():
    with (ROOT / "docs/paper/supplement/evidence_map.csv").open() as handle:
        items = {row["item"] for row in csv.DictReader(handle)}
    readme = (ROOT / "docs/paper/supplement/README.md").read_text()
    assert all(f"| {item} |" in readme for item in items)
    assert items == {f"S1.{n}" for n in range(1, 16)}


def test_manifest_records_clean_production_commits():
    manifest = json.loads((ROOT / "docs/paper/supplement/ledger_manifest.json").read_text())
    steps = {entry["step"]: entry for entry in manifest["production_steps"]}
    assert steps["04_primary"]["git_commit"].startswith("8ad6c2c")
    assert not any(entry["git_dirty"] for entry in manifest["production_steps"])
    assert all(len(entry["sha256"]) == 64 for entry in manifest["ledgers"])


def test_inventory_covers_every_generator_and_flags_gaps(tmp_path, monkeypatch):
    module = load()
    with module.INVENTORY.open() as handle:
        entries = list(csv.DictReader(handle))
    assert {e["level"] for e in entries} <= module.LEVELS
    assert next(e for e in entries if e["generator"].endswith("analyze_revision_predictions.py"))["level"] == "2b"
    short = tmp_path / "input_inventory.csv"
    short.write_text("generator,input_classes,run_files,level\n"
                     "scripts/analyze_revision_acceptance.py,ledgers;telepathy,evaluations.csv,9\n")
    monkeypatch.setattr(module, "INVENTORY", short)
    errors = module.check()
    assert any("without input inventory entry" in error for error in errors)
    assert any("invalid inventory entry for scripts/analyze_revision_acceptance.py" in error for error in errors)
