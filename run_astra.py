import os
import sys
import uuid
from pathlib import Path

if "ASTRA_BIN" not in os.environ:
    os.environ["ASTRA_BIN"] = "/home/cspark/Work/simulation_codes-working/lume-astra/bin/astra"
if "GENERATOR_BIN" not in os.environ:
    os.environ["GENERATOR_BIN"] = "/home/cspark/Work/simulation_codes-working/lume-astra/bin/generator"

# Ensure src is in sys.path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from astra import Astra
from utils import *
from mobo_linac.astra.runner import run_astra_eval


def run_astra_simulation(parameters, verbose=False, timeout=30, run_id="legacy_run", eval_id=None):
    """
    Runs an Astra simulation with the given parameters and returns objectives and diagnostics.
    Uses isolated evaluation directories to prevent file overwrites.

    Args:
        parameters (list): A list of 6 independent parameters for the Astra simulation.
        verbose (bool): Whether to output detailed Astra logs.
        timeout (int): Timeout in seconds for ASTRA execution.
        run_id (str): Optional identifier for the run.
        eval_id (str/int): Optional unique identifier for this evaluation.
    Returns:
        dict or None: ASTRA statistics dictionary if successful, None if timed out/failed.
    """
    if eval_id is None:
        eval_id = uuid.uuid4().hex[:8]

    res = run_astra_eval(
        parameters=parameters,
        run_id=run_id,
        eval_id=eval_id,
        timeout=timeout,
        verbose=verbose,
    )

    if res["status"] == "success":
        eval_dir = res["eval_dir"]
        input_file = os.path.join(eval_dir, "astra.in")
        astra_sim = Astra(input_file, workdir=eval_dir, use_temp_dir=False)
        astra_sim.load_output()
        return astra_sim.output.get("stats")
    else:
        print(f"ASTRA simulation execution failed/timed out: {res.get('error')}")
        return None


def get_objectives(stats):
    norm_emit_x = stats['norm_emit_x'][-1]
    norm_emit_y = stats['norm_emit_y'][-1]
    sigma_energy = stats['sigma_energy'][-1]

    return (norm_emit_x, norm_emit_y, sigma_energy)


def get_diagnostics(stats):
    diagnostics = {
        'emit_x': stats['norm_emit_x'][-1],
        'emit_y': stats['norm_emit_y'][-1],
        'sigma_energy': stats['sigma_energy'][-1],
        'sigma_x': stats['sigma_x'][-1],
        'sigma_y': stats['sigma_y'][-1],
        'sigma_xp': stats['sigma_xp'][-1],
        'sigma_yp': stats['sigma_yp'][-1],
        'sigma_z': stats['sigma_z'][-1],
        'mean_kinetic_energy': stats['mean_kinetic_energy'][-1],
    }
    return diagnostics


def get_weighted_objective(parameters, weights):
    stats = run_astra_simulation(parameters)
    norm_emit_x = stats['norm_emit_x'][-1]
    norm_emit_y = stats['norm_emit_y'][-1]
    sigma_energy = stats['sigma_energy'][-1]
    w1, w2, w3 = weights

    kinetic_energy = 200e6
    target_norm_emit = 10e-9
    target_energy_spread = 0.005

    gamma = get_gamma(kinetic_energy)
    beta = get_beta(gamma)

    norm_emit0 = target_norm_emit * beta * gamma
    sigma_energy0 = kinetic_energy * target_energy_spread

    weighted_objective = ((w1 * norm_emit_x + w2 * norm_emit_y) / norm_emit0 
                  + w3 * sigma_energy / sigma_energy0)
    print(weighted_objective)

    return weighted_objective
