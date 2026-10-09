"""
Isolated ASTRA Runner Module.

Executes ASTRA simulation within an isolated evaluation directory,
extracting objectives and diagnostics and generating execution manifests.
"""

import os
import shutil
import time
import shlex
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

# Default ASTRA binary path fallbacks if environment variables are not set
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_BIN_DIR = _PROJECT_ROOT / "bin"


def resolve_executable_path(
    env_var: str,
    binary_name: str,
    local_bin_dir: Optional[Path] = None,
    candidate_paths: Optional[Sequence[Union[str, Path]]] = None,
) -> str:
    """
    Resolves an executable binary path using hierarchical fallback:
    1. Explicit environment variable if valid and exists.
    2. Local project bin/ directory.
    3. System PATH via shutil.which.
    4. Known candidate installation paths.
    5. Fallback to default local bin path.
    """
    # 1. Check existing environment variable if set and valid
    env_val = os.environ.get(env_var)
    if env_val:
        p = Path(env_val).expanduser().resolve()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)

    # 2. Check local project bin directory
    bin_dir = local_bin_dir if local_bin_dir is not None else _LOCAL_BIN_DIR
    local_bin = (bin_dir / binary_name).resolve()
    if local_bin.is_file() and os.access(local_bin, os.X_OK):
        return str(local_bin)

    # 3. Check system PATH
    which_bin = shutil.which(binary_name)
    if which_bin:
        return which_bin

    # 4. Known candidate paths
    candidates = list(candidate_paths) if candidate_paths else []
    candidates.extend([
        Path("/home/cspark/Work/simulation_codes-working/lume-astra/bin") / binary_name,
        Path.home() / "Work/simulation_codes-working/lume-astra/bin" / binary_name,
    ])
    for cand in candidates:
        cand_p = Path(cand).expanduser().resolve()
        if cand_p.is_file() and os.access(cand_p, os.X_OK):
            return str(cand_p)

    # 5. Fallback to default local bin path
    fallback = str(local_bin)
    return fallback


# Public injection seam for recording simulators; importing this module is inert.
Astra = None


def initialize_astra_backend():
    """Resolve executables and load the optional runtime only for a real attempt."""
    global Astra
    if Astra is not None:
        return Astra
    os.environ["ASTRA_BIN"] = resolve_executable_path("ASTRA_BIN", "astra")
    os.environ["GENERATOR_BIN"] = resolve_executable_path("GENERATOR_BIN", "generator")
    try:
        import distgen
        if not hasattr(distgen, "Generator"):
            from distgen.generator import Generator
            distgen.Generator = Generator
    except ImportError:
        pass
    from astra import Astra as astra_class
    Astra = astra_class
    return Astra


from mobo_linac.astra.parser import (
    AstraOutputParser,
    ParsedAstraResult,
    SimulationStatus,
)
from mobo_linac.astra.workdir import AstraWorkDirManager, format_eval_id, file_sha256, write_once_json

def apply_parameters_to_astra(
    astra_sim: Any,
    parameters: Sequence[float],
    config: Union[Any, Dict[str, Any]],
    namelist_overrides: Optional[Dict[str, Any]] = None,
    applied_values: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Applies design parameters and optional namelist overrides to an ASTRA simulation instance.

    Args:
        astra_sim: Astra instance or dict-like object representing ASTRA namelists.
        parameters: Sequence of floating-point values matching the design variables.
        config: MoboConfig or config dictionary containing design_variables definitions.
        namelist_overrides: Optional dict mapping ASTRA keys (e.g. 'charge:lspch') to override values.

    Returns:
        List of parameter names that were applied. Failed assignments raise; optional
        applied_values records successful assignments, including explicit overrides.
    """
    def assign(key, value):
        astra_sim[key] = value
        if applied_values is not None:
            applied_values[key] = value

    if hasattr(config, "design_variables"):
        design_vars = config.design_variables
    elif isinstance(config, dict) and "design_variables" in config:
        design_vars = config["design_variables"]
    else:
        raise TypeError("Parameter mapping requires a configuration defining design_variables.")
    if len(parameters) != len(design_vars):
        raise ValueError(
            f"Parameter vector length ({len(parameters)}) does not match "
            f"configured design variables count ({len(design_vars)})"
        )

    applied_names: List[str] = []
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

        applied_names.append(name)

        if is_coupled and coupled_targets:
            for target_key in coupled_targets:
                assign(target_key, val)
        elif astra_key:
            assign(astra_key, val)

    if namelist_overrides:
        for override_key, override_val in namelist_overrides.items():
            assign(override_key, override_val)

    return applied_names


def applied_lattice_perturbations(parameters, config, assigned_values, requested_deltas):
    """Confirm that each channel's complete configured target set kept its requested value."""
    channels = [
        ("solenoid_field_T", "solenoid_field_relative_error", ["solenoid:maxb(1)"]),
        ("quad_1_gradient_T_m", "quad1_gradient_relative_error", ["quadrupole:q_grad(1)"]),
        ("quad_2_gradient_T_m", "quad2_gradient_relative_error", ["quadrupole:q_grad(2)"]),
        ("gun_phase_deg", "gun_phase_error_deg", ["cavity:phi(1)"]),
        ("acc1_acc2_phase_deg", "cavity_phase_acc12_error_deg", ["cavity:phi(2)", "cavity:phi(3)"]),
        ("acc3_acc4_phase_deg", "cavity_phase_acc34_error_deg", ["cavity:phi(4)", "cavity:phi(5)"]),
    ]
    by_name = {name: (channel, targets) for name, channel, targets in channels}
    targets_and_values = []
    for variable, value in zip(config.design_variables, parameters):
        if variable.name not in by_name:
            continue
        channel, _ = by_name[variable.name]
        targets = variable.coupled_targets if variable.is_coupled else [variable.astra_key]
        targets_and_values.append((channel, targets, value))
    return {channel: requested_deltas[channel] for channel, targets, value in targets_and_values
            if channel in requested_deltas and targets
            and all(assigned_values.get(target) == float(value) for target in targets)}


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
    attempt_id: Optional[str] = None,
    retry_index: int = 0,
    source_settings: Optional[Dict[str, float]] = None,
    request_metadata: Optional[Dict[str, Any]] = None,
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
        attempt_id: Optional explicit identity; a previously reserved attempt is rejected.
        retry_index: Zero-based retry ordinal retained in attempt provenance.
        source_settings: Requested source scales, retained as unsupported with the fixed distribution.
        request_metadata: Candidate identity, seeds and requested perturbations for audit.

    Returns:
        Dict containing execution status, objectives, diagnostics, paths, and manifest info.
    """
    from mobo_linac.config import MoboConfig, config_from_dict, validate_evaluation_settings, ExecutionConfig
    if isinstance(config, dict):
        config = config_from_dict(config)
    if not isinstance(config, MoboConfig):
        raise TypeError("run_astra_eval requires the campaign configuration.")
    config.validate()
    ExecutionConfig(timeout_sec=timeout, clean_on_success=clean_on_success).validate()
    validate_evaluation_settings(parameters, config, namelist_overrides, source_settings)
    if workdir_manager is None:
        workdir_manager = AstraWorkDirManager(
            base_results_dir=base_results_dir,
            template_dir=template_dir,
        )

    formatted_eval_id = format_eval_id(eval_id)
    attempt_id, provenance_dir = workdir_manager.reserve_attempt(run_id, formatted_eval_id, attempt_id)
    eval_dir = workdir_manager.get_eval_dir(run_id, formatted_eval_id) / attempt_id

    t_start = time.time()
    iso_start = datetime.fromtimestamp(t_start).isoformat()

    input_file = eval_dir / "astra.in"
    status = SimulationStatus.UNHANDLED_EXCEPTION
    error_msg: Optional[str] = None
    objectives: Optional[Dict[str, float]] = None
    diagnostics: Optional[Dict[str, float]] = None
    telemetry: Dict[str, float] = {}
    astra_sim = None
    applied_param_names: List[str] = [dv.name for dv in config.design_variables]
    astra_cmd: str = os.environ.get("ASTRA_BIN", "")

    request_metadata = request_metadata or {}
    source_settings = source_settings or {}
    applied_perturbations = {}
    applied_overrides = {}
    applied_namelist_values = {}
    input_hashes = {}
    executed_input_hashes = {}
    output_hashes = {}
    executable = {"command": astra_cmd, "path": None, "sha256": None}
    write_once_json(provenance_dir / "attempt_started.json", {
        "schema_version": 1, "run_id": run_id, "eval_id": formatted_eval_id,
        "attempt_id": attempt_id, "retry_index": retry_index,
        "parameters": [float(p) for p in parameters], "eval_dir": str(eval_dir),
        "start_time": iso_start,
        "source_settings": source_settings, "request_metadata": request_metadata,
        "namelist_overrides": namelist_overrides,
    })

    try:
        workdir_manager.prepare_eval_dir(run_id, formatted_eval_id, template_in=template_in,
                                        use_symlinks=use_symlinks, attempt_id=attempt_id)
        parser = AstraOutputParser(config=config)
        # Initialize Astra inside isolated eval_dir
        astra_sim = initialize_astra_backend()(
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
            applied_values=applied_namelist_values,
        )

        applied_overrides = dict(namelist_overrides or {})
        applied_perturbations = applied_lattice_perturbations(
            parameters, config, applied_namelist_values,
            request_metadata.get("channel_deltas", {}))
        # Materialize effective inputs before launch, then preserve their exact bytes.
        if hasattr(astra_sim, "write_input"):
            astra_sim.write_input()
        input_hashes = workdir_manager.snapshot_inputs(eval_dir, provenance_dir)
        command_path = Path(astra_cmd).expanduser()
        if not command_path.is_file():
            tokens = shlex.split(astra_cmd)
            token = tokens[0] if tokens else ""
            resolved = shutil.which(token) or str(eval_dir / token)
            command_path = Path(resolved)
        executable = {"command": astra_cmd, "path": str(command_path.resolve()),
                      "sha256": file_sha256(command_path) if command_path.is_file() else None}
        # Execute simulation. lume-astra's run() ignores the instance timeout, so the
        # configured limit is passed explicitly when the runtime supports it.
        run_with_timeout = getattr(astra_sim, "run_astra", None)
        if callable(run_with_timeout):
            run_with_timeout(timeout=timeout)
        else:
            astra_sim.run()

        parsed_result = parser.parse_astra_simulation(
            astra_sim=astra_sim,
            eval_dir=eval_dir,
        )
        objectives = parsed_result.objectives
        diagnostics = parsed_result.diagnostics
        telemetry = parsed_result.telemetry
        error_msg = parsed_result.error_message
        status = parsed_result.status

    except Exception as e:
        parsed_result = AstraOutputParser(config=config).parse_astra_simulation(
            astra_sim=astra_sim,
            eval_dir=eval_dir,
            error=e,
        )
        error_msg = parsed_result.error_message
        status = parsed_result.status

    t_end = time.time()
    iso_end = datetime.fromtimestamp(t_end).isoformat()
    duration = t_end - t_start

    provenance_error = None
    try:
        if eval_dir.exists():
            if not input_hashes:
                if (provenance_dir / "inputs").exists():
                    raise RuntimeError("Input snapshot did not complete; partial provenance retained.")
                input_hashes = workdir_manager.snapshot_inputs(eval_dir, provenance_dir)
            executed_input_hashes = workdir_manager.snapshot_inputs(
                eval_dir, provenance_dir, "inputs_after_execution", input_hashes)
            output_hashes = {str(path.relative_to(eval_dir)): file_sha256(path)
                             for path in eval_dir.rglob("*") if path.is_file()
                             and str(path.relative_to(eval_dir)) not in input_hashes}
    except Exception as exc:
        provenance_error = str(exc)
        status = SimulationStatus.PROVENANCE_ERROR
        error_msg = f"{error_msg or ''} Provenance capture failed: {exc}".strip()

    manifest = {
        "schema_version": 1,
        "provenance_error": provenance_error,
        "attempt_id": attempt_id,
        "retry_index": retry_index,
        "input_hashes": input_hashes,
        "input_hashes_after_execution": executed_input_hashes,
        "output_hashes": output_hashes,
        "executable": executable,
        "provenance_dir": str(provenance_dir),
        "namelist_overrides": namelist_overrides,
        "applied_namelist_overrides": applied_overrides,
        "applied_namelist_values": applied_namelist_values,
        "source_settings": source_settings,
        "source_application": {key: "nominal" if value == 1.0 else "unsupported"
                               for key, value in source_settings.items()},
        "request_metadata": request_metadata,
        "requested_perturbations": request_metadata.get("channel_deltas", {}),
        "applied_perturbations": applied_perturbations,
        "run_id": run_id,
        "eval_id": formatted_eval_id,
        "parameters": [float(p) for p in parameters],
        "parameter_names": applied_param_names,
        "status": status.value,
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
        "telemetry": telemetry,
    }

    manifest_path = workdir_manager.save_manifest(provenance_dir, manifest)

    result = {
        "run_id": run_id, "eval_id": formatted_eval_id,
        "parameters": [float(p) for p in parameters],
        "attempt_id": attempt_id,
        "status": status.value,
        "objectives": objectives,
        "diagnostics": diagnostics,
        "telemetry": telemetry,
        "eval_dir": str(eval_dir),
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "error": error_msg,
    }

    if status is SimulationStatus.SUCCESS and clean_on_success:
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
        config: Union[Any, Dict[str, Any]] = None,
    ):
        if config is None:
            raise TypeError("AstraRunner requires the campaign configuration.")
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
