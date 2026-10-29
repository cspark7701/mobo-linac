#!/usr/bin/env python3
"""C3-07: test that ledger-only (level 2a) evidence regenerates from the minimal input set.

A scratch tree is assembled with the analysis scripts, the distributed derived evidence and
only the minimal run-level ledgers listed in ``docs/paper/supplement/ledger_manifest.json``
(``evaluations.csv``, ``config.json`` and ``run_complete.json`` of every run). No other run
file, GP checkpoint or tracking output is copied. Representative level-2a generators are run
in that tree, and their outputs are compared with the committed evidence files. Generators
of level 2b (run records, GP checkpoints, tracking outputs) and 3 (ASTRA) are not tested
here; ``input_inventory.csv`` lists what they need.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = "docs/paper/revisions/evidence"
MANIFEST = ROOT / "docs/paper/supplement/ledger_manifest.json"
# generator -> (arguments relative to the scratch tree, evidence files to compare)
CASES = {
    "analyze_revision_resolution_bounds.py": (["--output-dir", "out"],
                                              ["r3_resolution_bounds_runs.csv", "r3_resolution_bounds_paired.csv"]),
    "analyze_revision_sobol_uncertainty.py": (["--output-dir", "out"],
                                              ["r3_sobol_uncertainty_runs.csv", "r3_sobol_uncertainty_summary.csv"]),
    "analyze_revision_attribution.py": (["--root", "results/paper_production/04_primary/benchmark/per_seed",
                                         "--output", "out", "--figure", "out/attribution.pdf"],
                                        ["r2_attribution_runs.csv", "r2_attribution_gap.csv",
                                         "r2_attribution_paired.csv"]),
}


def assemble(tree: Path) -> int:
    shutil.copytree(ROOT / "scripts", tree / "scripts")
    shutil.copytree(ROOT / EVIDENCE, tree / EVIDENCE)
    entries = json.loads(MANIFEST.read_text())["ledgers"]
    for entry in entries:
        target = tree / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / entry["path"], target)
    return len(entries)


def same(produced: Path, committed: Path) -> bool:
    a, b = pd.read_csv(produced), pd.read_csv(committed)
    if list(a.columns) != list(b.columns) or len(a) != len(b):
        return False
    numeric = a.select_dtypes("number").columns
    return bool(a.drop(columns=numeric).astype(str).equals(b.drop(columns=numeric).astype(str))
                and ((a[numeric] - b[numeric]).abs() <= 1e-12).all().all())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / EVIDENCE / "r3_regeneration_check.json")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as scratch:
        tree = Path(scratch)
        copied = assemble(tree)
        cases = []
        for script, (arguments, files) in CASES.items():
            run = subprocess.run([sys.executable, str(tree / "scripts" / script), *arguments], cwd=tree,
                                 capture_output=True, text=True)
            matches = {name: run.returncode == 0 and same(tree / "out" / name, ROOT / EVIDENCE / name)
                       for name in files}
            cases.append({"generator": f"scripts/{script}", "returncode": run.returncode, "matches": matches})
    report = {"check": "C3-07 regeneration of level-2a evidence from the minimal ledger set",
              "ledger_files_copied": copied,
              "copied": ["scripts/", f"{EVIDENCE}/", "evaluations.csv, config.json and run_complete.json per run"],
              "not_copied": "all other run files, GP checkpoints and tracking outputs",
              "cases": cases, "passed": all(all(c["matches"].values()) for c in cases)}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
