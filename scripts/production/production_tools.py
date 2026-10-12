"""Helpers for the step-by-step paper production scripts (scripts/production/NN_*.sh).

Subcommands:
  record     Freeze commit, configuration, ASTRA executable, static inputs and step parameters.
  summarize  Count evaluations, validity, feasibility, failures, runtimes and disk use of run
             directories; optionally enforce a stage exit gate.
  forecast   Project wall time and disk use of a stage from the pilot measurements.
  inventory  Index every stage's runs, audits, records and artifact checksums.
"""

import argparse
import datetime
import hashlib
import json
import math
import platform
import subprocess
import sys
from pathlib import Path

import pandas as pd

RUN_SKIP_PARTS = {"work", "provenance", "checkpoints", "gp_checkpoint", "figures"}


def sha256(path):
    path = Path(path)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def record(args):
    import mobo_linac
    from mobo_linac.config import load_config

    from mobo_linac.astra.runner import resolve_executable, resolve_template_dir

    config = load_config(args.config)
    executable = None if args.mock else str(resolve_executable(config))
    template_dir = resolve_template_dir(config)
    static = {name: sha256(template_dir / name)
              for name in [config.simulation.input_template, *config.simulation.static_files]}
    parameters = dict(item.split("=", 1) for item in args.parameters)
    versions = {}
    for package in ("torch", "botorch", "gpytorch", "numpy", "pandas", "scipy"):
        try:
            versions[package] = __import__(package).__version__
        except Exception:  # pragma: no cover - informational only
            versions[package] = None
    data = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "mock_evaluator": bool(args.mock),
        "parameters": parameters,
        "git": {"commit": git("rev-parse", "HEAD"),
                "dirty": bool(git("status", "--porcelain", "--untracked-files=no"))},
        "config": {"path": str(Path(args.config).resolve()), "sha256": sha256(args.config)},
        "astra_executable": {"path": executable, "sha256": sha256(executable) if executable else None},
        "static_inputs_sha256": static,
        "mobo_linac_version": mobo_linac.__version__,
        "python": platform.python_version(),
        "packages": versions,
        "host": platform.node(),
    }
    write_json(args.output, data)
    print(f"Step record: {args.output}")
    return 0


def find_runs(roots):
    runs = []
    for root in map(Path, roots):
        for path in sorted(root.rglob("evaluations.csv")):
            run = path.parent
            if not RUN_SKIP_PARTS.intersection(run.relative_to(root).parts):
                runs.append(run)
    # An aggregate (the Phase 1 suite directory) contains its case runs; count only the cases.
    return [run for run in runs if not any(other != run and run in other.parents for other in runs)]


def directory_bytes(path):
    return sum(item.stat().st_size for item in Path(path).rglob("*") if item.is_file())


def run_summary(run):
    frame = pd.read_csv(run / "evaluations.csv")
    valid = frame.get("simulation_valid", pd.Series(dtype=bool)).fillna(False).astype(bool)
    feasible = frame.get("physically_feasible", pd.Series(dtype=bool)).fillna(False).astype(bool)
    failures = frame.loc[~valid, "failure_category"].fillna("UNKNOWN").value_counts().to_dict() \
        if "failure_category" in frame else {}
    runtime = pd.to_numeric(frame.get("runtime_s", pd.Series(dtype=float)), errors="coerce").dropna()
    return {
        "run_dir": str(run),
        "complete": (run / "run_complete.json").is_file(),
        "evaluations": int(len(frame)),
        "valid": int(valid.sum()),
        "feasible": int(feasible.sum()),
        "failures": {str(k): int(v) for k, v in failures.items()},
        "runtimes": runtime.tolist(),
        "bytes": directory_bytes(run),
    }


def audit_summary(roots):
    audits = {}
    for root in map(Path, roots):
        for path in sorted(root.rglob("verification_summary.csv")):
            if "verification_runs" in path.parts:  # per-session copy of the summary
                continue
            frame = pd.read_csv(path)
            column = "verification_status" if "verification_status" in frame else None
            counts = frame[column].fillna("UNKNOWN").value_counts().to_dict() if column else {}
            audits[str(path)] = {"rows": int(len(frame)), "status": {str(k): int(v) for k, v in counts.items()}}
        for path in sorted(root.rglob("robustness_summary.csv")):
            audits[str(path)] = {"rows": int(len(pd.read_csv(path)))}
    return audits


def summarize(args):
    runs = [run_summary(run) for run in find_runs(args.roots)]
    if not runs and args.gate != "none":
        print("No run directories (evaluations.csv) found under: " + " ".join(args.roots))
        return 2
    runtimes = pd.Series([t for run in runs for t in run.pop("runtimes")], dtype=float)
    evaluations = sum(run["evaluations"] for run in runs)
    measured = {
        "runs": len(runs),
        "complete_runs": sum(run["complete"] for run in runs),
        "evaluations": evaluations,
        "valid": sum(run["valid"] for run in runs),
        "feasible": sum(run["feasible"] for run in runs),
        "median_runtime_s": float(runtimes.median()) if len(runtimes) else None,
        "p95_runtime_s": float(runtimes.quantile(0.95)) if len(runtimes) else None,
        "bytes_per_evaluation": sum(run["bytes"] for run in runs) / max(evaluations, 1),
    }
    if runs:
        print(f"\n{'run':<70} {'done':>4} {'evals':>5} {'valid':>5} {'feas':>5}  failures")
    for run in runs:
        name = run["run_dir"][-70:]
        print(f"{name:<70} {'yes' if run['complete'] else 'NO':>4} {run['evaluations']:>5} "
              f"{run['valid']:>5} {run['feasible']:>5}  {run['failures'] or '-'}")
    if runs:
        print(f"\nTotal: {measured['evaluations']} evaluations, {measured['valid']} valid, "
              f"{measured['feasible']} feasible in {measured['complete_runs']}/{measured['runs']} complete runs")
        if measured["median_runtime_s"] is not None:
            print(f"ASTRA runtime: median {measured['median_runtime_s']:.0f} s, "
                  f"p95 {measured['p95_runtime_s']:.0f} s")
        print(f"Disk: {measured['bytes_per_evaluation'] / 1e6:.2f} MB per evaluation")
    audits = audit_summary(args.roots)
    for path, info in audits.items():
        print(f"Audit {path}: {info}")

    problems = []
    if args.gate != "none":
        if measured["complete_runs"] != measured["runs"]:
            problems.append("some runs have no run_complete.json")
        if measured["valid"] == 0:
            problems.append("no valid ASTRA evaluation")
        if measured["feasible"] == 0:
            problems.append("no feasible candidate, so there is nothing to audit")
        if args.gate == "audited" and not any(info.get("rows") for info in audits.values()):
            problems.append("no verification or robustness rows were produced")
    write_json(args.output, {"measured": measured, "runs": runs, "audits": audits, "gate": args.gate,
                             "gate_problems": problems})
    print(f"Summary: {args.output}")
    if problems:
        print("\nEXIT GATE NOT MET:\n  - " + "\n  - ".join(problems))
        return 2
    if args.gate != "none":
        print("\nExit gate met (automatic checks). Review failures and audits before the next step.")
    return 0


def forecast(args):
    if args.workers < 1 or args.concurrent_campaigns < 1 or args.runs < 1:
        raise ValueError("Forecast workers, concurrent campaigns and run count must be positive.")
    measured = json.loads(Path(args.pilot_summary).read_text())["measured"]
    seconds = measured.get("median_runtime_s") or args.default_runtime
    slots = min(args.concurrent_campaigns, args.workers, args.runs)
    per_campaign = args.workers // slots
    rounds = math.ceil(args.initial / per_campaign) + args.iterations * math.ceil(args.batch / per_campaign)
    wall = (math.ceil(args.runs / slots) * rounds + math.ceil(args.extra_evaluations / args.workers)) * seconds
    evaluations = args.runs * (args.initial + args.iterations * args.batch) + args.extra_evaluations
    disk_gb = evaluations * measured["bytes_per_evaluation"] * 1.25 / 1e9
    print(f"Forecast: {evaluations} ASTRA evaluations; about {wall / 3600:.1f} h of simulator wall time "
          f"({wall / 86400:.1f} days) at {seconds:.0f} s per run with {args.workers} workers "
          f"({slots} campaigns, {per_campaign} workers each), "
          f"plus GP fitting; about {disk_gb:.1f} GB of outputs.")
    Path(args.disk_output).write_text(f"{max(1, math.ceil(disk_gb))}\n") if args.disk_output else None
    return 0


def inventory(args):
    root = Path(args.root)
    stages = {}
    for stage in sorted(p for p in root.iterdir() if p.is_dir() and p.name[:2].isdigit()):
        runs = []
        for run in find_runs([stage]):
            marker = run / "run_complete.json"
            runs.append({"run_dir": str(run.relative_to(root)), "complete": marker.is_file(),
                         "run_complete_sha256": sha256(marker)})
        records = sorted(str(p.relative_to(root)) for p in stage.rglob("step_record_*.json"))
        launches = sorted(str(p.relative_to(root)) for p in stage.rglob("launch_*.json"))
        stages[stage.name] = {"runs": runs, "step_records": records, "launch_records": launches,
                              "audits": {str(Path(k).relative_to(root)): v
                                         for k, v in audit_summary([stage]).items()}}
    data = {"created": datetime.datetime.now().isoformat(timespec="seconds"),
            "git_commit": git("rev-parse", "HEAD"), "stages": stages}
    write_json(args.output, data)
    incomplete = [run["run_dir"] for stage in stages.values() for run in stage["runs"] if not run["complete"]]
    print(f"Inventory: {args.output} ({sum(len(s['runs']) for s in stages.values())} runs)")
    if incomplete:
        print("Runs without run_complete.json:\n  " + "\n  ".join(incomplete))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--config", required=True)
    rec.add_argument("--mock", type=int, default=0)
    rec.add_argument("--output", required=True)
    rec.add_argument("parameters", nargs="*")
    summ = sub.add_parser("summarize")
    summ.add_argument("roots", nargs="+")
    summ.add_argument("--output", required=True)
    summ.add_argument("--gate", choices=["none", "feasible", "audited"], default="none")
    fc = sub.add_parser("forecast")
    fc.add_argument("--pilot-summary", required=True)
    for name in ("runs", "initial", "iterations", "batch", "workers"):
        fc.add_argument(f"--{name}", type=int, required=True)
    fc.add_argument("--extra-evaluations", type=int, default=0)
    fc.add_argument("--concurrent-campaigns", type=int, default=1)
    fc.add_argument("--default-runtime", type=float, default=300.0)
    fc.add_argument("--disk-output")
    inv = sub.add_parser("inventory")
    inv.add_argument("root")
    inv.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    return {"record": record, "summarize": summarize, "forecast": forecast, "inventory": inventory}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
