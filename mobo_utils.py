from run_astra import *
import torch

def evaluate_objective(params, timeout=30):
    with torch.no_grad():
        values = params.detach().tolist()
        try:
            stats = run_astra_simulation(values, timeout=timeout)
            if stats is None or len(stats.get('norm_emit_x', [])) == 0:
                raise ValueError("ASTRA simulation produced empty or invalid stats.")

            emit_x, emit_y, sigma_energy = get_objectives(stats)
            diags = get_diagnostics(stats)

            # Check feasibility based on diagnostics
            is_feasible_bool = (
                bool(diags['sigma_x'] <= 1.0e-3) and
                bool(diags['sigma_y'] <= 1.0e-3) and
                bool(diags['sigma_xp'] <= 1.0e-3) and
                bool(diags['sigma_yp'] <= 1.0e-3) and
                bool(diags['sigma_z'] <= 1.0e-3) and
                bool(diags['mean_kinetic_energy'] >= 195e6) and # Lower bound
                bool(diags['mean_kinetic_energy'] <= 205e6)    # Upper bound
            )
        except Exception as e:
            print(f"Simulation error/timeout for params {values}: {e}")
            emit_x, emit_y, sigma_energy = 1.0e-3, 1.0e-3, 1.0e8
            diags = {
                'emit_x': emit_x, 'emit_y': emit_y, 'sigma_energy': sigma_energy,
                'sigma_x': 999.0, 'sigma_y': 999.0, 'sigma_xp': 999.0, 'sigma_yp': 999.0, 'sigma_z': 999.0,
                'mean_kinetic_energy': 0.0
            }
            is_feasible_bool = False

def evaluate_constrained_objective(params, timeout=30):
    """
    Evaluates simulation and returns 9 outcomes:
    [emit_x_neg, emit_y_neg, sigma_energy_neg, sigma_x, sigma_y, sigma_xp, sigma_yp, sigma_z, mean_kinetic_energy]
    """
    with torch.no_grad():
        values = params.detach().tolist()
        try:
            stats = run_astra_simulation(values, timeout=timeout)
            if stats is None or len(stats.get('norm_emit_x', [])) == 0:
                raise ValueError("ASTRA simulation produced empty or invalid stats.")

            emit_x, emit_y, sigma_energy = get_objectives(stats)
            diags = get_diagnostics(stats)

            is_feasible_bool = (
                bool(diags['sigma_x'] <= 1.0e-3) and
                bool(diags['sigma_y'] <= 1.0e-3) and
                bool(diags['sigma_xp'] <= 1.0e-3) and
                bool(diags['sigma_yp'] <= 1.0e-3) and
                bool(diags['sigma_z'] <= 1.0e-3) and
                bool(diags['mean_kinetic_energy'] >= 195e6) and
                bool(diags['mean_kinetic_energy'] <= 205e6)
            )
        except Exception as e:
            print(f"Simulation error/timeout for params {values}: {e}")
            emit_x, emit_y, sigma_energy = 1.0e-3, 1.0e-3, 1.0e8
            diags = {
                'emit_x': emit_x, 'emit_y': emit_y, 'sigma_energy': sigma_energy,
                'sigma_x': 999.0, 'sigma_y': 999.0, 'sigma_xp': 999.0, 'sigma_yp': 999.0, 'sigma_z': 999.0,
                'mean_kinetic_energy': 0.0
            }
            is_feasible_bool = False

        feasible = torch.tensor(is_feasible_bool, dtype=torch.bool)
        objectives_neg = torch.tensor([-emit_x, -emit_y, -sigma_energy], dtype=torch.double)
        outcomes_9 = torch.tensor([
            -emit_x, -emit_y, -sigma_energy,
            diags['sigma_x'], diags['sigma_y'], diags['sigma_xp'],
            diags['sigma_yp'], diags['sigma_z'], diags['mean_kinetic_energy']
        ], dtype=torch.double)

        return objectives_neg, outcomes_9, feasible, diags



def compute_ref_point(train_Y):
    """
    Computes a reference point for Hypervolume calculation.
    For minimization (negated objectives), the reference point should be
    "worse" (i.e., smaller) than all observed negated objectives.
    """
    min_vals_negated = train_Y.min(dim=0).values
    max_vals_negated = train_Y.max(dim=0).values
    
    # Calculate range in the negated space
    ranges_negated = max_vals_negated - min_vals_negated
    
    # Add a small epsilon to ranges to prevent division by zero or very small ranges
    epsilon = 1e-6 
    offset = 0.05 * (ranges_negated + epsilon) # Use 5% of the range as offset

    # The reference point for maximization should be below the minimum observed negated values
    ref_point = min_vals_negated - offset
    return ref_point