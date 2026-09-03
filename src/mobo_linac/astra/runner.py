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
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_BIN_DIR = _PROJECT_ROOT / "bin"

if "ASTRA_BIN" not in os.environ:
    _local_astra = _LOCAL_BIN_DIR / "astra"
    os.environ["ASTRA_BIN"] = str(_local_astra) if _local_astra.exists() else str(_PROJECT_ROOT / "bin" / "astra")
if "GENERATOR_BIN" not in os.environ:
    _local_gen = _LOCAL_BIN_DIR / "generator"
    os.environ["GENERATOR_BIN"] = str(_local_gen) if _local_gen.exists() else str(_PROJECT_ROOT / "bin" / "generator")

try:
    import distgen
    if not hasattr(distgen, "Generator"):
        from distgen.generator import Generator
        setattr(distgen, "Generator", Generator)
except Exception:
    pass

from astra import Astra
from mobo_linac.astra.parser import (
    AstraOutputParser,
    ParsedAstraResult,
    SimulationStatus,
)
from mobo_linac.astra.workdir import AstraWorkDirManager, format_eval_id

PARAMETER_NAMES = [
    "solenoid:maxb(1)",
    "quadrupole:q_grad(1)",
    "quadrupole:q_grad(2)",
    "cavity:phi(1)",
    "cavity:phi(2,3)",
    "cavity:phi(4,5)",
]


def apply_parameters_to_astra(
    astra_sim: Any,
    parameters: Sequence[float],
    config: Optional[Union[Any, Dict[str, Any]]] = None,
    namelist_overrides: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Applies design parameters and optional namelist overrides to an ASTRA simulation instance.

    Args:
        astra_sim: Astra instance or dict-like object representing ASTRA namelists.
        parameters: Sequence of floating-point values matching the design variables.
        config: Optional MoboConfig or config dictionary containing design_variables definitions.
        namelist_overrides: Optional dict mapping ASTRA keys (e.g. 'charge:q_total') to override values.

    Returns:
        List of parameter names that were applied.
    """
    applied_names: List[str] = []
    if config is not None:
        if hasattr(config, "design_variables"):
            design_vars = config.design_variables
        elif isinstance(config, dict) and "design_variables" in config:
            design_vars = config["design_variables"]
        else:
            design_vars = None

        if design_vars is not None:
            if len(parameters) != len(design_vars):
                raise ValueError(
                    f"Parameter vector length ({len(parameters)}) does not match "
                    f"configured design variables count ({len(design_vars)})"
                )

            param_names = []
            for idx, dv in enumerate(design_vars):
                val = float(parameters[idx])
                if hasattr(dv, "name"):
                    name = dv.name
                    astra_key = dv.astra_key
                    is_coupled = getattr(dv, "is_coupled", False)
                    coupled_targets = getattr(dv, "coupled_targets", []) or []
                else:
                    name = dv.get("name", f"param_{idx}")
                    astra_key = dv.get("astra_key", "")
                    is_coupled = dv.get("is_coupled", False)
                    coupled_targets = dv.get("coupled_targets", []) or []

                param_names.append(name)

                if is_coupled and coupled_targets:
                    for target_key in coupled_targets:
                        astra_sim[target_key] = val
                elif astra_key:
                    astra_sim[astra_key] = val

            applied_names = param_names
    else:
        # Default 6-parameter mapping for backward compatibility
        if len(parameters) != 6:
            raise ValueError(f"Expected 6 design parameters for default mapping, got {len(parameters)}")

        astra_sim["solenoid:maxb(1)"] = float(parameters[0])
        astra_sim["quadrupole:q_grad(1)"] = float(parameters[1])
        astra_sim["quadrupole:q_grad(2)"] = float(parameters[2])
        astra_sim["cavity:phi(1)"] = float(parameters[3])
        astra_sim["cavity:phi(2)"] = float(parameters[4])
        astra_sim["cavity:phi(3)"] = float(parameters[4])
        astra_sim["cavity:phi(4)"] = float(parameters[5])
        astra_sim["cavity:phi(5)"] = float(parameters[5])
        applied_names = list(PARAMETER_NAMES)

    if namelist_overrides:
        for override_key, override_val in namelist_overrides.items():
            try:
                astra_sim[override_key] = override_val
            except Exception:
                pass

    return applied_names


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
    config: Optional[Union[Any, Dict[str, Any]]] = None,
    namelist_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Runs an isolated ASTRA simulation for a given candidate parameter set.

    Args:
        parameters: Sequence of design parameter values.
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
        config: Optional MoboConfig or config dictionary for dynamic parameter mapping.

    Returns:
        Dict containing execution status, objectives, diagnostics, paths, and manifest info.
    """
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
    applied_param_names: List[str] = list(PARAMETER_NAMES)
    astra_cmd: str = os.environ.get("ASTRA_BIN", "")

    target_z = 16.2
    z_tol = 0.1
    if config is not None:
        if hasattr(config, "execution"):
            if hasattr(config.execution, "z_stop_m"):
                target_z = float(config.execution.z_stop_m)
            if hasattr(config.execution, "z_loss_tolerance_m"):
                z_tol = float(config.execution.z_loss_tolerance_m)
        elif isinstance(config, dict) and "execution" in config:
            target_z = float(config["execution"].get("z_stop_m", target_z))
            z_tol = float(config["execution"].get("z_loss_tolerance_m", z_tol))

    parser = AstraOutputParser(target_z_stop=target_z, z_loss_tolerance=z_tol)

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

        # Apply parameters and optional namelist overrides to ASTRA simulation
        applied_param_names = apply_parameters_to_astra(
            astra_sim,
            parameters,
            config=config,
            namelist_overrides=namelist_overrides,
        )

        # Execute simulation
        astra_sim.run()

        parsed_result = parser.parse_astra_simulation(
            astra_sim=astra_sim,
            eval_dir=eval_dir,
        )
        objectives = parsed_result.objectives
        diagnostics = parsed_result.diagnostics
        error_msg = parsed_result.error_message

        if parsed_result.status == SimulationStatus.SUCCESS:
            status = "success"
        elif parsed_result.status == SimulationStatus.TIMEOUT:
            status = "timeout"
        else:
            status = "failed"

    except Exception as e:
        error_msg = str(e)
        parsed_result = parser.parse_astra_simulation(
            astra_sim=None,
            eval_dir=eval_dir,
            error_context=error_msg,
        )
        if parsed_result.status == SimulationStatus.TIMEOUT:
            status = "timeout"
        else:
            status = "failed"

    t_end = time.time()
    iso_end = datetime.fromtimestamp(t_end).isoformat()
    duration = t_end - t_start

    manifest = {
        "run_id": run_id,
        "eval_id": formatted_eval_id,
        "parameters": [float(p) for p in parameters],
        "parameter_names": applied_param_names,
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
        config: Optional[Union[Any, Dict[str, Any]]] = None,
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
        self.config = config

    def run(
        self,
        parameters: Sequence[float],
        eval_id: Union[int, str],
        verbose: bool = False,
        namelist_overrides: Optional[Dict[str, Any]] = None,
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
            config=self.config,
            namelist_overrides=namelist_overrides,
        )
