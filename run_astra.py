import os
if "ASTRA_BIN" not in os.environ:
    os.environ["ASTRA_BIN"] = "/home/cspark/Work/simulation_codes-working/lume-astra/bin/astra"
if "GENERATOR_BIN" not in os.environ:
    os.environ["GENERATOR_BIN"] = "/home/cspark/Work/simulation_codes-working/lume-astra/bin/generator"

from astra import Astra
from utils import *

def run_astra_simulation(parameters, verbose=False, timeout=30):
    """
    Runs an Astra simulation with the given parameters and returns objectives and diagnostics.

    Args:
        parameters (list): A list of 6 independent parameters for the Astra simulation:
                           [solenoid:maxb(1), quad:q_grad(1), quad:q_grad(2),
                            cavity:phi(1), common_phi_2_3, common_phi_4_5]
        timeout (int): Timeout in seconds for ASTRA execution.
    Returns:
        dict or None: ASTRA statistics dictionary if successful, None if timed out/failed.
    """
    astra_sim = Astra('astra.in') # Ensure astra.in is accessible
    astra_sim.timeout = timeout
    astra_sim.verbose = verbose

    print(f"Running simulation with parameters: {parameters}")

    # Map 6 independent parameters to 8 Astra input variables
    astra_sim['solenoid:maxb(1)'] = parameters[0]
    astra_sim['quadrupole:q_grad(1)'] = parameters[1]
    astra_sim['quadrupole:q_grad(2)'] = parameters[2]
    astra_sim['cavity:phi(1)'] = parameters[3]
    astra_sim['cavity:phi(2)'] = parameters[4] # Common phase for cavity 2 & 3
    astra_sim['cavity:phi(3)'] = parameters[4] # Common phase for cavity 2 & 3
    astra_sim['cavity:phi(4)'] = parameters[5] # Common phase for cavity 4 & 5
    astra_sim['cavity:phi(5)'] = parameters[5] # Common phase for cavity 4 & 5

    try:
        astra_sim.run()
        return astra_sim.output['stats']
    except Exception as e:
        print(f"ASTRA simulation execution failed/timed out: {e}")
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
    # Extract results from the simulation
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

    # Objective: Minimize the sum of horizontal emittance, vertical emittance, and energy spread
    weighted_objective = ((w1 * norm_emit_x + w2 * norm_emit_y) / norm_emit0 
                  + w3 * sigma_energy / sigma_energy0)
    print(weighted_objective)

    return weighted_objective




