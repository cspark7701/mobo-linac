from run_astra import *
import torch

def evaluate_objective(params):
    with torch.no_grad():
        # Ensure params are on CPU for external simulation call
        values = params.detach().tolist() # Removed .cpu() as device is now always CPU
        
        # Run Astra simulation
        stats = run_astra_simulation(values)
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
        # Return a single boolean tensor for consistent stacking
        feasible = torch.tensor(is_feasible_bool, dtype=torch.bool) 

        # Negate objectives for minimization (BoTorch maximizes by default)
        objective = torch.tensor([-emit_x, -emit_y, -sigma_energy], dtype=torch.double)
        
        return objective, feasible, diags

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