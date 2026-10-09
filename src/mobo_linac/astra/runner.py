"""
Isolated ASTRA attempt execution.

One attempt is reserved, prepared from the configured template and static files, executed
with an explicitly resolved executable, parsed, and recorded in an immutable manifest.
Importing this module, and running mock campaigns, never touches ``os.environ``.
"""

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import shlex
import shutil
import time
from typing import Any, Dict, List, Optional, Sequence, Union

from mobo_linac.astra.parser import AstraOutputParser, SimulationStatus
from mobo_linac.astra.workdir import AstraWorkDirManager, file_sha256, format_eval_id
from mobo_linac.io.durable import write_once_json


def _configured_path(value: Optional[str], config) -> Optional[Path]:
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():  # in-memory configurations: relative to their file, else the cwd
        base = config.source_path.parent if config.source_path is not None else Path.cwd()
        path = base / path
    return path.resolve()


def resolve_template_dir(config) -> Path:
    """Absolute template directory (``simulation.template_dir``); unset is an error, never the cwd."""
    path = _configured_path(config.simulation.template_dir, config)
    if path is None:
        raise ValueError("simulation.template_dir is not configured; set it in the configuration file.")
    return path


def resolve_executable_path(env_var: str, binary_name: str, configured: Optional[Union[str, Path]] = None) -> str:
    """Executable from the configured path, then ``$env_var``, then ``PATH``; raises when absent.

    Read-only: the environment is never modified.
    """
    candidates = [configured, os.environ.get(env_var), shutil.which(binary_name)]
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser().resolve()
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
    raise FileNotFoundError(f"ASTRA executable '{binary_name}' not found: configure simulation.executable, "
                            f"set ${env_var}, or put it on PATH.")


def resolve_executable(config) -> str:
    return resolve_executable_path("ASTRA_BIN", "astra", _configured_path(config.simulation.executable, config))


# Public injection seam for recording simulators; importing this module is inert.
Astra = None


def _install_distgen_compatibility() -> None:
    """lume-astra imports ``distgen.Generator``; newer distgen exposes it only from a submodule."""
    try:
        import distgen
        if not hasattr(distgen, "Generator"):
            from distgen.generator import Generator
            distgen.Generator = Generator
    except ImportError:
        pass


def initialize_astra_backend():
    """Load the optional lume-astra runtime only for a real attempt (no environment changes)."""
    global Astra
    if Astra is None:
        _install_distgen_compatibility()
        from astra import Astra as astra_class
        Astra = astra_class
    return Astra


def apply_parameters_to_astra(
    astra_sim: Any,
    parameters: Sequence[float],
    config: Any,
    namelist_overrides: Optional[Dict[str, Any]] = None,
    applied_values: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Applies design parameters and optional namelist overrides to an ASTRA simulation instance.

    Args:
        astra_sim: Astra instance or dict-like object representing ASTRA namelists.
        parameters: Sequence of floating-point values matching the design variables.
        config: MoboConfig defining the design variables.
        namelist_overrides: Optional dict mapping ASTRA keys (e.g. 'charge:lspch') to override values.

    Returns:
        List of parameter names that were applied. Failed assignments raise; optional
        applied_values records successful assignments, including explicit overrides.
    """
    def assign(key, value):
        astra_sim[key] = value
        if applied_values is not None:
            applied_values[key] = value

    from mobo_linac.config import MoboConfig
    if not isinstance(config, MoboConfig):
        raise TypeError("Parameter mapping requires the campaign MoboConfig.")
    design_vars = config.design_variables
    if len(parameters) != len(design_vars):
        raise ValueError(
            f"Parameter vector length ({len(parameters)}) does not match "
            f"configured design variables count ({len(design_vars)})"
        )

    applied_names: List[str] = []
    for idx, dv in enumerate(design_vars):
        val = float(parameters[idx])
        applied_names.append(dv.name)
        if dv.is_coupled and dv.coupled_targets:
            for target_key in dv.coupled_targets:
                assign(target_key, val)
        else:
            assign(dv.astra_key, val)

    if namelist_overrides:
        for override_key, override_val in namelist_overrides.items():
            assign(override_key, override_val)

    return applied_names


def applied_lattice_perturbations(parameters, config, assigned_values, requested_deltas, channel_targets):
    """Confirm that each lattice channel's complete configured target set kept its requested value.

    ``channel_targets`` maps a requested channel to the design variable it perturbs; channels
    without a design variable (source settings) are never reported as applied.
    """
    variables = {variable.name: (variable, value) for variable, value in zip(config.design_variables, parameters)}
    applied = {}
    for channel, delta in requested_deltas.items():
        target = channel_targets.get(channel)
        if target not in variables:
            continue
        variable, value = variables[target]
        targets = variable.coupled_targets if variable.is_coupled else [variable.astra_key]
        if targets and all(assigned_values.get(key) == float(value) for key in targets):
            applied[channel] = delta
    return applied


@dataclass
class _Attempt:
    """Mutable record of one attempt, filled stage by stage and frozen into its manifest."""

    run_id: str
    eval_id: str
    attempt_id: str
    retry_index: int
    eval_dir: Path
    provenance_dir: Path
    parameters: List[float]
    command: str
    namelist_overrides: Optional[Dict[str, Any]]
    source_settings: Dict[str, float]
    request_metadata: Dict[str, Any]
    parameter_names: List[str]
    started: float = field(default_factory=time.monotonic)
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    status: SimulationStatus = SimulationStatus.UNHANDLED_EXCEPTION
    error: Optional[str] = None
    objectives: Optional[Dict[str, float]] = None
    diagnostics: Optional[Dict[str, float]] = None
    telemetry: Dict[str, float] = field(default_factory=dict)
    applied_overrides: Dict[str, Any] = field(default_factory=dict)
    applied_values: Dict[str, Any] = field(default_factory=dict)
    applied_perturbations: Dict[str, Any] = field(default_factory=dict)
    input_hashes: Dict[str, str] = field(default_factory=dict)
    executed_input_hashes: Dict[str, str] = field(default_factory=dict)
    output_hashes: Dict[str, str] = field(default_factory=dict)
    executable: Dict[str, Any] = field(default_factory=dict)
    provenance_error: Optional[str] = None
    end_time: Optional[str] = None
    duration_sec: Optional[float] = None


def prepare_attempt(parameters, run_id, eval_id, workdir_manager, config, *, attempt_id, retry_index,
                    namelist_overrides, source_settings, request_metadata) -> _Attempt:
    """Validate the request, resolve the executable, then reserve the attempt and record its start."""
    from mobo_linac.execution.requests import validate_evaluation_settings
    validate_evaluation_settings(parameters, config, namelist_overrides, source_settings)
    command = resolve_executable(config)  # a missing executable fails before any reservation
    formatted = format_eval_id(eval_id)
    attempt_id, provenance_dir = workdir_manager.reserve_attempt(run_id, formatted, attempt_id)
    attempt = _Attempt(run_id=run_id, eval_id=formatted, attempt_id=attempt_id, retry_index=retry_index,
                       eval_dir=workdir_manager.get_eval_dir(run_id, formatted) / attempt_id,
                       provenance_dir=provenance_dir, parameters=[float(p) for p in parameters], command=command,
                       namelist_overrides=namelist_overrides, source_settings=dict(source_settings or {}),
                       request_metadata=dict(request_metadata or {}),
                       parameter_names=[dv.name for dv in config.design_variables])
    attempt.executable = {"command": command, "path": None, "sha256": None}
    write_once_json(provenance_dir / "attempt_started.json", {
        "schema_version": 1, "run_id": run_id, "eval_id": formatted, "attempt_id": attempt_id,
        "retry_index": retry_index, "parameters": attempt.parameters, "eval_dir": str(attempt.eval_dir),
        "start_time": attempt.start_time, "source_settings": attempt.source_settings,
        "request_metadata": attempt.request_metadata, "namelist_overrides": namelist_overrides,
    })
    return attempt


def apply_settings(attempt: _Attempt, astra_sim, config) -> None:
    """Assign design values and overrides, recording what each lattice perturbation actually changed."""
    attempt.parameter_names = apply_parameters_to_astra(astra_sim, attempt.parameters, config=config,
                                                        namelist_overrides=attempt.namelist_overrides,
                                                        applied_values=attempt.applied_values)
    attempt.applied_overrides = dict(attempt.namelist_overrides or {})
    attempt.applied_perturbations = applied_lattice_perturbations(
        attempt.parameters, config, attempt.applied_values,
        attempt.request_metadata.get("channel_deltas", {}), attempt.request_metadata.get("channel_targets", {}))


def _executable_record(command: str, eval_dir: Path) -> Dict[str, Any]:
    path = Path(command).expanduser()
    if not path.is_file():
        tokens = shlex.split(command)
        token = tokens[0] if tokens else ""
        path = Path(shutil.which(token) or str(eval_dir / token))
    return {"command": command, "path": str(path.resolve()), "sha256": file_sha256(path) if path.is_file() else None}


def execute(attempt: _Attempt, workdir_manager, config, *, timeout, verbose, use_symlinks) -> None:
    """Prepare the workdir, run the simulation and parse it; failures become typed statuses."""
    astra_sim = None
    simulation = config.simulation
    try:
        workdir_manager.prepare_eval_dir(attempt.run_id, attempt.eval_id, static_files=simulation.static_files,
                                         template_in=simulation.input_template, use_symlinks=use_symlinks,
                                         attempt_id=attempt.attempt_id)
        astra_sim = initialize_astra_backend()(input_file=str(attempt.eval_dir / "astra.in"),
                                               workdir=str(attempt.eval_dir), use_temp_dir=False,
                                               command=attempt.command)
        astra_sim.timeout = timeout
        astra_sim.verbose = verbose
        attempt.command = str(getattr(astra_sim, "command", None) or attempt.command)
        apply_settings(attempt, astra_sim, config)
        # Materialize effective inputs before launch, then preserve their exact bytes.
        if hasattr(astra_sim, "write_input"):
            astra_sim.write_input()
        attempt.input_hashes = workdir_manager.snapshot_inputs(attempt.eval_dir, attempt.provenance_dir)
        attempt.executable = _executable_record(attempt.command, attempt.eval_dir)
        # lume-astra's run() ignores the instance timeout; pass the limit explicitly when supported.
        run_with_timeout = getattr(astra_sim, "run_astra", None)
        if callable(run_with_timeout):
            run_with_timeout(timeout=timeout)
        else:
            astra_sim.run()
        parsed = AstraOutputParser(config=config).parse_astra_simulation(astra_sim=astra_sim, eval_dir=attempt.eval_dir)
        attempt.objectives, attempt.diagnostics, attempt.telemetry = parsed.objectives, parsed.diagnostics, parsed.telemetry
    except Exception as error:
        parsed = AstraOutputParser(config=config).parse_astra_simulation(astra_sim=astra_sim, eval_dir=attempt.eval_dir,
                                                                         error=error)
    attempt.status, attempt.error = parsed.status, parsed.error_message
    attempt.duration_sec = time.monotonic() - attempt.started
    attempt.end_time = datetime.now().isoformat()


def capture_provenance(attempt: _Attempt, workdir_manager) -> None:
    """Hash inputs before/after execution and every output; a capture failure is its own status."""
    try:
        if attempt.eval_dir.exists():
            if not attempt.input_hashes:
                if (attempt.provenance_dir / "inputs").exists():
                    raise RuntimeError("Input snapshot did not complete; partial provenance retained.")
                attempt.input_hashes = workdir_manager.snapshot_inputs(attempt.eval_dir, attempt.provenance_dir)
            attempt.executed_input_hashes = workdir_manager.snapshot_inputs(
                attempt.eval_dir, attempt.provenance_dir, "inputs_after_execution", attempt.input_hashes)
            attempt.output_hashes = {str(path.relative_to(attempt.eval_dir)): file_sha256(path)
                                     for path in attempt.eval_dir.rglob("*") if path.is_file()
                                     and str(path.relative_to(attempt.eval_dir)) not in attempt.input_hashes}
    except Exception as exc:
        attempt.provenance_error = str(exc)
        attempt.status = SimulationStatus.PROVENANCE_ERROR
        attempt.error = f"{attempt.error or ''} Provenance capture failed: {exc}".strip()


def build_manifest(attempt: _Attempt) -> Dict[str, Any]:
    return {
        "schema_version": 1, "provenance_error": attempt.provenance_error, "attempt_id": attempt.attempt_id,
        "retry_index": attempt.retry_index, "input_hashes": attempt.input_hashes,
        "input_hashes_after_execution": attempt.executed_input_hashes, "output_hashes": attempt.output_hashes,
        "executable": attempt.executable, "provenance_dir": str(attempt.provenance_dir),
        "namelist_overrides": attempt.namelist_overrides, "applied_namelist_overrides": attempt.applied_overrides,
        "applied_namelist_values": attempt.applied_values, "source_settings": attempt.source_settings,
        "source_application": {key: "nominal" if value == 1.0 else "unsupported"
                               for key, value in attempt.source_settings.items()},
        "request_metadata": attempt.request_metadata,
        "requested_perturbations": attempt.request_metadata.get("channel_deltas", {}),
        "applied_perturbations": attempt.applied_perturbations, "run_id": attempt.run_id, "eval_id": attempt.eval_id,
        "parameters": attempt.parameters, "parameter_names": attempt.parameter_names, "status": attempt.status.value,
        "error": attempt.error,
        "timestamps": {"start_time": attempt.start_time, "end_time": attempt.end_time,
                       "duration_sec": attempt.duration_sec},
        "astra_command": attempt.command, "eval_dir": str(attempt.eval_dir), "objectives": attempt.objectives,
        "diagnostics": attempt.diagnostics, "telemetry": attempt.telemetry,
    }


def run_astra_eval(
    parameters: Sequence[float],
    run_id: str = "default_run",
    eval_id: Union[int, str] = 1,
    base_results_dir: Union[str, Path] = "results",
    template_dir: Optional[Union[str, Path]] = None,
    timeout: Optional[int] = None,
    clean_on_success: Optional[bool] = None,
    verbose: bool = False,
    use_symlinks: bool = False,
    workdir_manager: Optional[AstraWorkDirManager] = None,
    config: Any = None,
    namelist_overrides: Optional[Dict[str, Any]] = None,
    attempt_id: Optional[str] = None,
    retry_index: int = 0,
    source_settings: Optional[Dict[str, float]] = None,
    request_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run one isolated, immutable ASTRA attempt for a parameter vector.

    ``config`` must be the validated campaign ``MoboConfig`` (serialized configurations are
    converted once at the worker boundary). Template, static files and executable come from
    ``config.simulation`` (``template_dir`` overrides the directory); timeout and cleanup default
    to ``config.execution``. The returned record references the manifest instead of embedding it.
    """
    from mobo_linac.config import MoboConfig
    if not isinstance(config, MoboConfig):
        raise TypeError("run_astra_eval requires the campaign MoboConfig.")
    config.validate()
    timeout = config.execution.timeout_sec if timeout is None else timeout
    if type(timeout) is not int or timeout < 1:
        raise ValueError("timeout must be a positive integer.")
    clean_on_success = config.execution.clean_on_success if clean_on_success is None else bool(clean_on_success)
    if workdir_manager is None:
        workdir_manager = AstraWorkDirManager(base_results_dir=base_results_dir,
                                              template_dir=template_dir if template_dir is not None
                                              else resolve_template_dir(config))
    attempt = prepare_attempt(parameters, run_id, eval_id, workdir_manager, config, attempt_id=attempt_id,
                              retry_index=retry_index, namelist_overrides=namelist_overrides,
                              source_settings=source_settings, request_metadata=request_metadata)
    execute(attempt, workdir_manager, config, timeout=timeout, verbose=verbose, use_symlinks=use_symlinks)
    capture_provenance(attempt, workdir_manager)
    manifest = build_manifest(attempt)
    manifest_path = workdir_manager.save_manifest(attempt.provenance_dir, manifest)
    if attempt.status is SimulationStatus.SUCCESS and clean_on_success:
        workdir_manager.cleanup_eval_dir(attempt.eval_dir)
    return {"run_id": run_id, "eval_id": attempt.eval_id, "parameters": attempt.parameters,
            "attempt_id": attempt.attempt_id, "status": attempt.status.value, "objectives": attempt.objectives,
            "diagnostics": attempt.diagnostics, "telemetry": attempt.telemetry, "timestamps": manifest["timestamps"],
            "eval_dir": str(attempt.eval_dir), "manifest_path": str(manifest_path), "error": attempt.error}
