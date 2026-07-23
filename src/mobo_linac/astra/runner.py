"""
Isolated ASTRA Runner Module.

Executes ASTRA simulation within an isolated evaluation directory,
extracting objectives and diagnostics and generating execution manifests.
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

# Default ASTRA binary path fallbacks if environment variables are not set
if "ASTRA_BIN" not in os.environ:
    os.environ["ASTRA_BIN"] = "/home/cspark/Work/simulation_codes-working/lume-astra/bin/astra"
if "GENERATOR_BIN" not in os.environ:
    os.environ["GENERATOR_BIN"] = "/home/cspark/Work/simulation_codes-working/lume-astra/bin/generator"

from astra import Astra
from mobo_linac.astra.workdir import AstraWorkDirManager, format_eval_id

PARAMETER_NAMES = [
    "solenoid:maxb(1)",
    "quadrupole:q_grad(1)",
    "quadrupole:q_grad(2)",
    "cavity:phi(1)",
    "cavity:phi(2,3)",
    "cavity:phi(4,5)",
]


def run_astra_eval(
    parameters: Sequence[float],
    run_id: str = "default_run",
    eval_id: Union[int, str] = 1,
    base_results_dir: Union[str, Path] = "results",
    template_dir: Union[str, Path] = ".",
    template_in: str = "astra.in",
    timeout: int = 30,
    clean_on_success: bool = False,
    verbose: bool = False,
    use_symlinks: bool = False,
    workdir_manager: Optional[AstraWorkDirManager] = None,
) -> Dict[str, Any]:
    """
    Runs an isolated ASTRA simulation for a given candidate parameter set.

    Args:
        parameters: Sequence of 6 independent parameters:
            [solenoid:maxb(1), quad:q_grad(1), quad:q_grad(2),
             cavity:phi(1), common_phi_2_3, common_phi_4_5]
        run_id: Unique identifier for the optimization run.
        eval_id: Unique identifier for this evaluation.
        base_results_dir: Root results output directory.
        template_dir: Source directory for static input/field files.
        template_in: Template ASTRA input file name.
        timeout: Timeout in seconds for ASTRA execution.
        clean_on_success: If True, remove evaluation working directory after successful run.
        verbose: Print detailed ASTRA execution log.
        use_symlinks: Use symlinks for static data files instead of copying.
        workdir_manager: Optional custom AstraWorkDirManager instance.

    Returns:
        Dict containing execution status, objectives, diagnostics, paths, and manifest info.
    """
    if len(parameters) != 6:
        raise ValueError(f"Expected 6 design parameters, got {len(parameters)}")

    if workdir_manager is None:
        workdir_manager = AstraWorkDirManager(
            base_results_dir=base_results_dir,
            template_dir=template_dir,
        )

    formatted_eval_id = format_eval_id(eval_id)
    eval_dir = workdir_manager.prepare_eval_dir(
        run_id=run_id,
        eval_id=formatted_eval_id,
        template_in=template_in,
        use_symlinks=use_symlinks,
    )

    t_start = time.time()
    iso_start = datetime.fromtimestamp(t_start).isoformat()

    input_file = eval_dir / "astra.in"
    status = "failed"
    error_msg: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    objectives: Optional[Dict[str, float]] = None
    diagnostics: Optional[Dict[str, float]] = None
    astra_cmd: str = os.environ.get("ASTRA_BIN", "")

    try:
        # Initialize Astra inside isolated eval_dir
        astra_sim = Astra(
            input_file=str(input_file),
            workdir=str(eval_dir),
            use_temp_dir=False,
        )
        astra_sim.timeout = timeout
        astra_sim.verbose = verbose

        if hasattr(astra_sim, "command") and astra_sim.command:
            astra_cmd = str(astra_sim.command)

        # Map 6 independent parameters to 8 ASTRA variables
        astra_sim["solenoid:maxb(1)"] = float(parameters[0])
        astra_sim["quadrupole:q_grad(1)"] = float(parameters[1])
        astra_sim["quadrupole:q_grad(2)"] = float(parameters[2])
        astra_sim["cavity:phi(1)"] = float(parameters[3])
        astra_sim["cavity:phi(2)"] = float(parameters[4])
        astra_sim["cavity:phi(3)"] = float(parameters[4])
        astra_sim["cavity:phi(4)"] = float(parameters[5])
        astra_sim["cavity:phi(5)"] = float(parameters[5])

        # Execute simulation
        astra_sim.run()

        if hasattr(astra_sim, "output") and "stats" in astra_sim.output:
            raw_stats = astra_sim.output["stats"]
            if raw_stats and "norm_emit_x" in raw_stats and len(raw_stats["norm_emit_x"]) > 0:
                stats = raw_stats
                status = "success"

                norm_emit_x = float(raw_stats["norm_emit_x"][-1])
                norm_emit_y = float(raw_stats["norm_emit_y"][-1])
                sigma_energy = float(raw_stats["sigma_energy"][-1])

                objectives = {
                    "norm_emit_x": norm_emit_x,
                    "norm_emit_y": norm_emit_y,
                    "sigma_energy": sigma_energy,
                }

                diagnostics = {
                    "emit_x": norm_emit_x,
                    "emit_y": norm_emit_y,
                    "sigma_energy": sigma_energy,
                    "sigma_x": float(raw_stats["sigma_x"][-1]),
                    "sigma_y": float(raw_stats["sigma_y"][-1]),
                    "sigma_xp": float(raw_stats["sigma_xp"][-1]),
                    "sigma_yp": float(raw_stats["sigma_yp"][-1]),
                    "sigma_z": float(raw_stats["sigma_z"][-1]),
                    "mean_kinetic_energy": float(raw_stats["mean_kinetic_energy"][-1]),
                }
            else:
                error_msg = "ASTRA output stats empty or missing key metrics"
        else:
            error_msg = "ASTRA output dictionary missing 'stats'"

    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            status = "timeout"

    t_end = time.time()
    iso_end = datetime.fromtimestamp(t_end).isoformat()
    duration = t_end - t_start

    manifest = {
        "run_id": run_id,
        "eval_id": formatted_eval_id,
        "parameters": [float(p) for p in parameters],
        "parameter_names": PARAMETER_NAMES,
        "status": status,
        "error": error_msg,
        "timestamps": {
            "start_time": iso_start,
            "end_time": iso_end,
            "duration_sec": duration,
        },
        "astra_command": astra_cmd,
        "eval_dir": str(eval_dir),
        "objectives": objectives,
        "diagnostics": diagnostics,
    }

    manifest_path = workdir_manager.save_manifest(eval_dir, manifest)

    result = {
        "status": status,
        "objectives": objectives,
        "diagnostics": diagnostics,
        "eval_dir": str(eval_dir),
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "error": error_msg,
    }

    if status == "success" and clean_on_success:
        workdir_manager.cleanup_eval_dir(eval_dir)

    return result


class AstraRunner:
    """
    Stateful runner for managing isolated ASTRA evaluations in an optimization campaign.
    """

    def __init__(
        self,
        run_id: str,
        base_results_dir: Union[str, Path] = "results",
        template_dir: Union[str, Path] = ".",
        template_in: str = "astra.in",
        timeout: int = 30,
        clean_on_success: bool = False,
        use_symlinks: bool = False,
    ):
        self.run_id = run_id
        self.timeout = timeout
        self.clean_on_success = clean_on_success
        self.use_symlinks = use_symlinks
        self.workdir_manager = AstraWorkDirManager(
            base_results_dir=base_results_dir,
            template_dir=template_dir,
        )
        self.template_in = template_in

    def run(
        self,
        parameters: Sequence[float],
        eval_id: Union[int, str],
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a single evaluation.
        """
        return run_astra_eval(
            parameters=parameters,
            run_id=self.run_id,
            eval_id=eval_id,
            template_in=self.template_in,
            timeout=self.timeout,
            clean_on_success=self.clean_on_success,
            verbose=verbose,
            use_symlinks=self.use_symlinks,
            workdir_manager=self.workdir_manager,
        )
