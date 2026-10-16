#!/usr/bin/env python3
"""Time one full saved MOBO proposal without fitting GPs or running ASTRA.

Run each device in a fresh process against the same preserved input directory.
The JSON result is written atomically, including failures; status is separate.
"""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import pandas as pd
import torch
from botorch.models import ModelListGP

from mobo_linac.acquisition.mobo import (
    FallbackPolicy, SliceObjective, build_acquisition_function, generate_next_candidates,
)
from mobo_linac.config import load_config
from mobo_linac.constraints import get_botorch_constraint_functions
from mobo_linac.models.pipeline import SurrogatePipeline
from mobo_linac.result_schema import ResultSchema
from mobo_linac.utils.durable import atomic_json


def benchmark(args):
    source, output = Path(args.input), Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    device = torch.device(args.device)
    label = str(device).replace(":", "_")
    status_path = output / f"{label}_status.json"
    result_path = output / f"{label}_result.json"
    if result_path.exists():
        raise FileExistsError(f"Refusing to overwrite benchmark result: {result_path}")
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    result = {"device": str(device), "dtype": "float64", "seed": args.seed,
              "threads": args.threads, "started_at": time.time(), "status": "running",
              "model_sha256": hashlib.sha256((source / "model.pt").read_bytes()).hexdigest(),
              "physical_validation": "unchanged; proposal timing only, no ASTRA execution"}

    def phase(name):
        atomic_json(status_path, {**result, "phase": name, "updated_at": time.time()})
        print(name, flush=True)

    def sync():
        if device.type == "cuda":
            torch.cuda.synchronize(device)

    try:
        phase("restore")
        if device.type == "cuda":
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is unavailable; CPU fallback is disabled for this benchmark")
            torch.cuda.set_device(device)
            torch.cuda.manual_seed_all(args.seed)
            torch.cuda.reset_peak_memory_stats(device)
            result["gpu_name"] = torch.cuda.get_device_name(device)
        config = load_config(source / "config.yaml")
        schema = ResultSchema.from_config(config)
        pipeline = SurrogatePipeline.load_artifact(source / "model.pt", device=device)
        history = pd.read_csv(source / "evaluations.csv").set_index(["run_id", "evaluation_id"])
        rows = history.loc[pipeline.training_ids]
        X = torch.tensor(rows[list(schema.design_columns)].to_numpy(), dtype=torch.double, device=device)
        Y = torch.tensor(rows[list(schema.model_columns)].to_numpy(), dtype=torch.double, device=device)
        feasible = torch.tensor(rows.physically_feasible.to_numpy(), dtype=torch.bool, device=device)
        proposal = next(row for row in json.loads((source / "proposal_history.json").read_text())
                        if row["batch_idx"] == pipeline.campaign_metadata["proposal_iteration"])
        primary = proposal["metadata"]["attempts"][0]
        reference = torch.tensor(proposal["metadata"]["acquisition_reference"]["point_model"],
                                 dtype=torch.double, device=device)
        model, constraints, objective = pipeline.objective_model, None, None
        if pipeline.constraint_model is not None:
            model = ModelListGP(*model.models, *pipeline.constraint_model.models).to(device=device, dtype=torch.double)
            constraints = get_botorch_constraint_functions(config, num_objectives=Y.shape[-1])
            objective = SliceObjective(Y.shape[-1])
        # Identical restart chunking on both devices; total search budgets are
        # copied from the archived production proposal, never reduced on failure.
        options = dict(primary["options"], batch_limit=args.batch_limit)
        result.update(training_count=len(X), proposal_iteration=proposal["batch_idx"],
                      acquisition=config.execution.acquisition if hasattr(config.execution, "acquisition") else "qLogNEHVI",
                      batch_size=8, num_restarts=primary["num_restarts"], raw_samples=primary["raw_samples"],
                      options=options, archived_options=primary["options"])
        phase("construct_acquisition")
        sync()
        start = time.perf_counter()
        acq = build_acquisition_function(model, X, Y, reference, feasible,
                                         acq_type="qLogNEHVI", constraints=constraints, objective=objective)
        sync()
        result["construction_s"] = time.perf_counter() - start
        result["mc_sample_shape"] = list(acq.sampler.sample_shape)
        phase("optimize_full_proposal")
        start = time.perf_counter()
        next_batch = generate_next_candidates(
            acq, pipeline.bounds.to(device=device, dtype=torch.double), batch_size=8,
            num_restarts=primary["num_restarts"], raw_samples=primary["raw_samples"],
            maxiter=options["maxiter"], options=options, device=device, retry_on_failure=False,
            policy=replace(FallbackPolicy.from_execution(config.execution), cuda_batch_limit=args.batch_limit))
        sync()
        result.update(status="completed", optimization_s=time.perf_counter() - start,
                      candidates=next_batch.candidates.detach().cpu().tolist(),
                      values=next_batch.acq_values.detach().cpu().tolist(), metadata=next_batch.metadata)
        if device.type == "cuda":
            result["peak_allocated_bytes"] = torch.cuda.max_memory_allocated(device)
    except Exception:
        result.update(status="failed", error=traceback.format_exc())
        raise
    finally:
        result["finished_at"] = time.time()
        result["elapsed_s"] = result["finished_at"] - result["started_at"]
        atomic_json(result_path, result)
        phase(result["status"])


def compare(args):
    """Finish the comparison and optional user-authorized cleanup unattended."""
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    primary = root / "results/paper_production/04_primary"
    if args.remove_primary and (output == primary or primary in output.parents):
        raise ValueError("Benchmark evidence must be outside the directory being removed")
    children = []
    for device in ("cpu", "cuda:0"):
        label = device.replace(":", "_")
        command = [sys.executable, "-u", str(Path(__file__).resolve()), "--input", str(Path(args.input).resolve()),
                   "--output", str(output), "--device", device, "--threads", str(args.threads),
                   "--seed", str(args.seed), "--batch-limit", str(args.batch_limit)]
        with (output / f"{label}.log").open("w") as log:
            child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        children.append((label, child))
    atomic_json(output / "comparison_status.json", {
        "status": "running", "started_at": time.time(),
        "pids": {label: child.pid for label, child in children},
        "cleanup_after_success": args.remove_primary})
    codes = {label: child.wait() for label, child in children}
    results = {}
    for label, _ in children:
        path = output / f"{label}_result.json"
        if path.exists():
            results[label] = json.loads(path.read_text())
    completed = all(code == 0 for code in codes.values()) and len(results) == 2
    record = {"status": "completed" if completed else "failed", "finished_at": time.time(),
              "exit_codes": codes, "results": results, "primary_removed": False}
    if completed:
        cpu, gpu = results["cpu"], results["cuda_0"]
        for key in ("model_sha256", "dtype", "training_count", "batch_size", "num_restarts", "raw_samples", "options", "mc_sample_shape"):
            if cpu[key] != gpu[key]:
                raise ValueError(f"Mismatched benchmark workload: {key}; retaining primary outputs")
        record["proposal_speedup"] = ((cpu["construction_s"] + cpu["optimization_s"]) /
                                      (gpu["construction_s"] + gpu["optimization_s"]))
        if args.remove_primary:
            # Refuse to delete a restarted production run. Only this explicitly
            # named stage is removed; screening and benchmark inputs are retained.
            processes = subprocess.run(["ps", "-eo", "args"], check=True, capture_output=True, text=True).stdout
            if any("-m mobo_linac.cli run-benchmark" in line and "04_primary/benchmark" in line
                   for line in processes.splitlines()):
                record["cleanup_error"] = "Primary benchmark has restarted; outputs retained"
            elif primary.is_symlink():
                record["cleanup_error"] = "Primary output directory is a symlink; outputs retained"
            else:
                if primary.exists():
                    shutil.rmtree(primary)
                production = primary.parent
                for path in (production / "status").glob("04_primary.*"):
                    path.unlink()
                for path in (production / "logs").glob("04_primary_*.log"):
                    path.unlink()
                record["primary_removed"] = True
    atomic_json(output / "comparison.json", record)
    atomic_json(output / "comparison_status.json", {key: value for key, value in record.items() if key != "results"})
    lines = ["# Saved late-stage proposal CPU/GPU comparison", "", f"Status: {record['status']}.", "",
             "Same saved 152-observation surrogate, float64, qLogNEHVI, eight candidates, ten restarts,",
             "1,024 raw samples, up to 200 optimizer iterations, and 128 MC samples.",
             "Both devices use restart batch limit one; the archived CPU proposal used five.",
             "This changes restart chunking, not the search budget. No GP refit or ASTRA evaluation was run.",
             "The CPU and GPU workers ran concurrently with one PyTorch CPU thread each;",
             "these are workload timings, not a claim of bitwise equal candidates or an end-to-end production speedup.", ""]
    for label, result in results.items():
        lines.append(f"- {label}: {result['status']}; elapsed {result['elapsed_s']:.2f} s.")
        if result["status"] == "completed":
            lines.append(f"  Acquisition construction {result['construction_s']:.2f} s; optimization {result['optimization_s']:.2f} s.")
    if "proposal_speedup" in record:
        lines.extend(["", f"Measured acquisition construction + proposal speedup: {record['proposal_speedup']:.2f}×."])
    lines.extend(["", f"Old primary output removed: {record['primary_removed']}.",
                  "Physical constraints, validation counts, seeds, budgets, and ASTRA settings in the scripts are unchanged.",
                  "Production was not restarted. Raw per-device results and logs are retained in this directory."])
    if record.get("cleanup_error"):
        lines.extend(["", record["cleanup_error"]])
    (output / "comparison.md").write_text("\n".join(lines) + "\n")
    if args.task_record:
        with Path(args.task_record).open("a") as stream:
            stream.write("\n## Benchmark Completion\n" + "\n".join(lines[2:]) + "\n")
    if not completed:
        raise RuntimeError("Saved proposal benchmark failed; primary results retained")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", required=True, choices=["cpu", "cuda:0", "both"])
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-limit", type=int, default=1)
    parser.add_argument("--remove-primary", action="store_true", help="After both devices succeed, remove old stage-04 outputs")
    parser.add_argument("--task-record", help="Append the eventual comparison and cleanup result to this task record")
    arguments = parser.parse_args()
    if arguments.device == "both":
        compare(arguments)
    else:
        benchmark(arguments)
