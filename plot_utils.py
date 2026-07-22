from mobo_utils import *
from utils import *
import matplotlib.pyplot as plt
import matplotlib
from skopt.plots import *
from botorch.utils.multi_objective.pareto import is_non_dominated
import torch
import pandas as pd

T = 200e6
gamma = get_gamma(T)
beta = get_beta(gamma)
geometric_emittance = 10e-9
target_norm_emittance = beta * gamma * geometric_emittance * 1e6
target_energy_deviation = T * 0.005 * 1e-6

###########################################################################################

def plot_hypervolume(hypervolumes, n_iterations, start_iteration):
    # Hypervolume vs Iteration Plot
    plt.figure(figsize=(8, 6))
    plt.plot(range(start_iteration, n_iterations), hypervolumes[start_iteration:], 
             marker='o', linestyle='-', color='b')
    plt.xlabel("Iteration", fontsize=16)
    plt.ylabel("Feasible Hypervolume", fontsize=16)
    plt.title("Feasible Hypervolume Progress Over Iterations", fontsize=16)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("img/mobo_hypervolume.png")
    plt.show()

###########################################################################################

def plot_pareto_objective_space(train_Y):
    """
    Plots 2D projections of the objective space, highlighting all points
    and the overall Pareto front.
    """
    # Prepare data for plotting (negate back to original scale)
    pareto_mask = is_non_dominated(train_Y)
    pareto_Y_original_scale = -train_Y[pareto_mask] # Negate back for plotting
    all_Y_original_scale = -train_Y # Negate back for plotting

    objective_labels = ["Emittance X [μm]", "Emittance Y [μm]", "Energy Deviation [MeV]"]
    objective_indices = [(0, 1), (2, 0), (2, 1)] # Pairs for (x, y) axes

    for i, (idx1, idx2) in enumerate(objective_indices):
        xa = all_Y_original_scale[:, idx1].numpy().copy()
        ya = all_Y_original_scale[:, idx2].numpy().copy()
        xb = pareto_Y_original_scale[:, idx1].numpy().copy()
        yb = pareto_Y_original_scale[:, idx2].numpy().copy()
        if idx1 == 2:
            xa *= 1e-6
            ya *= 1e6
            xb *= 1e-6
            yb *= 1e6
        else:
            xa *= 1e6
            ya *= 1e6
            xb *= 1e6
            yb *= 1e6
        
        plt.figure(figsize=(8, 6))
        
        # Plot all samples (original scale)
        #plt.scatter(all_Y_original_scale[:, idx1].numpy(), 
        #            all_Y_original_scale[:, idx2].numpy(),
        #            label="All samples", alpha=0.7, c='blue')
        plt.scatter(xa, ya, label="All samples", alpha=0.7, c='blue')
        
        # Plot Pareto front samples (original scale)
        #plt.scatter(pareto_Y_original_scale[:, idx1].numpy(), 
        #            pareto_Y_original_scale[:, idx2].numpy(),
        #            c="red", marker='o', s=100, edgecolors='k', label="Pareto front")
        plt.scatter(xb, yb, 
                    c="red", marker='o', s=100, edgecolors='k', label="Pareto front")

        if idx1 == 0:
            plt.axvline(target_norm_emittance, color='r', linestyle='--',
                        label=r'Target $\epsilon_{n,x}$ ='+f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
        elif idx2 == 0:
            plt.axhline(target_norm_emittance, color='r', linestyle='--', 
                        label=r'Target $\epsilon_{n,x}$ ='+f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
        if idx1 == 1:
            plt.axvline(target_norm_emittance, color='r', linestyle='--', 
                        label=r'Target $\epsilon_{n,y}$ ='+f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
        elif idx2 == 1:
            plt.axhline(target_norm_emittance, color='r', linestyle='--', 
                        label=r'Target $\epsilon_{n,y}$ ='+f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
        if idx1 == 2:
            plt.axvline(target_energy_deviation, color='r', linestyle='--', 
                        label=r'Target $\sigma_{E}$ ='+f'{target_energy_deviation:5.3f}'+r'$[MeV]$')
        elif idx2 == 2:
            plt.axhline(target_energy_deviation, color='r', linestyle='--', 
                        label=r'Target $\sigma_{E}$ ='+f'{target_energy_deviation:5.3f}'+r'$[MeV]$')
        
        plt.xlabel(objective_labels[idx1], fontsize=16)
        plt.ylabel(objective_labels[idx2], fontsize=16)
        plt.title(f"Pareto Front: {objective_labels[idx1]} vs {objective_labels[idx2]}",
                 fontsize=16)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f'img/mobo_pareto_objective_space_{i}.png')
        plt.show()

###########################################################################################

def plot_pareto_objective_space_best(train_Y):
    """
    Plots 2D projections of the objective space, highlighting all points
    and the overall Pareto front.
    """
    # Prepare data for plotting (negate back to original scale)
    pareto_mask = is_non_dominated(train_Y)
    pareto_Y_original_scale = -train_Y[pareto_mask] # Negate back for plotting

    objective_labels = ["Emittance X [μm]", "Emittance Y [μm]", "Energy Deviation [MeV]"]
    objective_indices = [(0, 1), (2, 0), (2, 1)] # Pairs for (x, y) axes

    for i, (idx1, idx2) in enumerate(objective_indices):
        xb = pareto_Y_original_scale[:, idx1].numpy().copy()
        yb = pareto_Y_original_scale[:, idx2].numpy().copy()
        if idx1 == 2:
            xb *= 1e-6
            yb *= 1e6
        else:
            xb *= 1e6
            yb *= 1e6
        
        plt.figure(figsize=(8, 6))
        
        # Plot Pareto front samples (original scale)
        #plt.scatter(pareto_Y_original_scale[:, idx1].numpy(), 
        #            pareto_Y_original_scale[:, idx2].numpy(),
        #            c="red", marker='o', s=100, edgecolors='k', label="Pareto front")
        plt.scatter(xb, yb, 
                    c="red", marker='o', s=100, edgecolors='k', label="Pareto front")

        if idx1 == 0:
            plt.axvline(target_norm_emittance, color='r', linestyle='--',
                        label=r'Target $\epsilon_{n,x}$ ='+f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
        elif idx2 == 0:
            plt.axhline(target_norm_emittance, color='r', linestyle='--', 
                        label=r'Target $\epsilon_{n,x}$ ='+f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
        if idx1 == 1:
            plt.axvline(target_norm_emittance, color='r', linestyle='--', 
                        label=r'Target $\epsilon_{n,y}$ ='+f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
        elif idx2 == 1:
            plt.axhline(target_norm_emittance, color='r', linestyle='--', 
                        label=r'Target $\epsilon_{n,y}$ ='+f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
        if idx1 == 2:
            plt.axvline(target_energy_deviation, color='r', linestyle='--', 
                        label=r'Target $\sigma_{E}$ ='+f'{target_energy_deviation:5.3f}'+r'$[MeV]$')
        elif idx2 == 2:
            plt.axhline(target_energy_deviation, color='r', linestyle='--', 
                        label=r'Target $\sigma_{E}$ ='+f'{target_energy_deviation:5.3f}'+r'$[MeV]$')
        
        plt.xlabel(objective_labels[idx1], fontsize=16)
        plt.ylabel(objective_labels[idx2], fontsize=16)
        plt.title(f"Pareto Front: {objective_labels[idx1]} vs {objective_labels[idx2]}",
        fontsize=16)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f'img/mobo_pareto_objective_space_best_{i}.png')
        plt.show()

###########################################################################################

def plot_all_constraints(constraints_log, train_feas_mask):
    """
    Plots various constraint parameters from the simulation diagnostics.
    Highlights feasible points.

    Args:
        constraints_log (list of dict): List of dictionaries containing diagnostic data for each sample.
        train_feas_mask (torch.Tensor): Boolean mask indicating feasible points.
    """
    df = pd.DataFrame(constraints_log)
    
    # Add a 'feasible' column to the DataFrame for easier plotting
    df['feasible'] = train_feas_mask.numpy()

    fig, axes = plt.subplots(2, 2, figsize=(16, 12)) # 2x2 grid of subplots
    axes = axes.flatten() # Flatten for easy iteration

    # Constraint 1: sigma_x vs sigma_xp
    ax = axes[0]
    ax.scatter(df['sigma_x'] * 1e3, df['sigma_xp'] * 1e3, c='steelblue', alpha=0.7, label='All Samples')
    ax.scatter(df[df['feasible']]['sigma_x'] * 1e3, df[df['feasible']]['sigma_xp'] * 1e3, 
               c='r', alpha=0.9, s=70, edgecolors='k', label='Feasible Samples') # Reverted label
    ax.axvline(1.0, color='r', linestyle='--', label='Constraint: 1.0 mm')
    ax.axhline(1.0, color='r', linestyle='--', label="Constraint: 1.0 mrad")
    ax.set_xlabel('$\sigma_x$ [mm]', fontsize=16)
    ax.set_ylabel("$\sigma_x'$ [mrad]", fontsize=16)
    ax.set_title('Constraint Space: $\sigma_x$ vs $\sigma_x\'$', fontsize=16)
    ax.grid(True)
    ax.legend()

    # Constraint 2: sigma_y vs sigma_yp
    ax = axes[1]
    ax.scatter(df['sigma_y'] * 1e3, df['sigma_yp'] * 1e3, c='steelblue', alpha=0.7, label='All Samples')
    ax.scatter(df[df['feasible']]['sigma_y'] * 1e3, df[df['feasible']]['sigma_yp'] * 1e3, 
               c='r', alpha=0.9, s=70, edgecolors='k', label='Feasible Samples') # Reverted label
    ax.axvline(1.0, color='r', linestyle='--', label='Constraint: 1.0 mm')
    ax.axhline(1.0, color='r', linestyle='--', label="Constraint: 1.0 mrad")
    ax.set_xlabel('$\sigma_y$ [mm]', fontsize=16)
    ax.set_ylabel("$\sigma_y'$ [mrad]", fontsize=16)
    ax.set_title('Constraint Space: $\sigma_y$ vs $\sigma_y\'$', fontsize=16)
    ax.grid(True)
    ax.legend()

    # Constraint 3: sigma_z over samples
    ax = axes[2]
    sample_indices = np.arange(len(df))
    ax.scatter(sample_indices, df['sigma_z'] * 1e3, c='steelblue', alpha=0.7, label='All Samples')
    ax.scatter(sample_indices[df['feasible']], df[df['feasible']]['sigma_z'] * 1e3, 
               c='r', alpha=0.9, s=70, edgecolors='k', label='Feasible Samples') # Reverted label
    ax.axhline(1.0, color='r', linestyle='--', label='Constraint: 1.0 mm')
    ax.set_xlabel('Sample Index', fontsize=16)
    ax.set_ylabel('$\sigma_z$ [mm]', fontsize=16)
    ax.set_title('Constraint Space: $\sigma_z$', fontsize=16)
    ax.grid(True)
    ax.legend()

    # Constraint 4: mean_kinetic_energy over samples
    ax = axes[3]
    ax.scatter(sample_indices, df['mean_kinetic_energy'] * 1e-6, c='steelblue', alpha=0.7, label='All Samples')
    ax.scatter(sample_indices[df['feasible']], df[df['feasible']]['mean_kinetic_energy'] * 1e-6, 
               c='r', alpha=0.9, s=70, edgecolors='k', label='Feasible Samples') # Reverted label
    ax.axhline(195, color='r', linestyle='--', label='Lower Constraint: 195 MeV')
    ax.axhline(205, color='r', linestyle='--', label='Upper Constraint: 205 MeV')
    ax.set_xlabel('Sample Index', fontsize=16)
    ax.set_ylabel('Mean Kinetic Energy [MeV]', fontsize=16)
    ax.set_title('Constraint Space: Mean Kinetic Energy', fontsize=16)
    ax.grid(True)
    ax.legend()

    plt.tight_layout()
    plt.savefig("img/mobo_all_constraints.png")
    plt.show()

###########################################################################################

def plot_objective_evolution(train_Y, n_iterations, start_iteration, num_initial_samples, q):
    """
    Plots the evolution of the best observed objective values over iterations.

    Args:
        train_Y (torch.Tensor): All observed objective values (negated).
        n_iterations (int): Total number of BO iterations planned.
        start_iteration (int): The iteration number from which the current run started.
        num_initial_samples (int): Number of initial samples before the BO loop.
        q (int): Number of new candidates generated per BO iteration.
    """
    # Negate objectives back to original scale for plotting (minimization)
    objectives_original_scale = -train_Y

    objective_labels = ["Emittance X [μm]", "Emittance Y [μm]", "Energy Spread [%]"]
    num_objectives = objectives_original_scale.shape[1]

    # Calculate cumulative best (minimum) for each objective
    # The first 'num_initial_samples' points are from initial sampling.
    # After that, 'q' new points are added per iteration.
    
    cumulative_best_objectives = []
    
    # Handle initial samples
    current_min_values = objectives_original_scale[:num_initial_samples].min(dim=0).values
    cumulative_best_objectives.append(current_min_values.numpy())

    # Handle BO iterations
    for i in range(n_iterations):
        # Calculate the index range for the current iteration's data
        # Initial samples are 0 to num_initial_samples-1
        # Iteration 0 adds points from num_initial_samples to num_initial_samples + q - 1
        # Iteration k adds points from num_initial_samples + k*q to num_initial_samples + (k+1)*q - 1
        current_data_end_idx = num_initial_samples + (i + 1) * q
        
        # Ensure we don't go beyond available data if the script stopped early
        current_data_end_idx = min(current_data_end_idx, objectives_original_scale.shape[0])
        
        if current_data_end_idx > 0: # Ensure there's data to consider
            current_data_slice = objectives_original_scale[:current_data_end_idx]
            current_min_values = current_data_slice.min(dim=0).values
            cumulative_best_objectives.append(current_min_values.numpy())
        else:
            # If no data yplot_hypervolumeet (e.g., in edge cases with very few initial samples), append previous best
            cumulative_best_objectives.append(cumulative_best_objectives[-1] if cumulative_best_objectives else np.full(num_objectives, np.inf))

    cumulative_best_objectives = np.array(cumulative_best_objectives)
    
    # Adjust iteration axis for plotting
    # The first point corresponds to initial samples, then each subsequent point is an iteration
    iteration_indices = np.arange(num_initial_samples, num_initial_samples + n_iterations * q + q, q)
    # Ensure iteration_indices matches the number of rows in cumulative_best_objectives
    # The length of cumulative_best_objectives is 1 (initial) + n_iterations (BO iterations)
    iteration_labels = np.arange(0, n_iterations + 1) # 0 for initial, then 1 to n_iterations

    objective_labels = ["Emittance X [μm]", "Emittance Y [μm]", "Energy Deviation [keV]"]


    for i in range(0, len(objective_labels)):
        plt.figure(figsize=(10, 7))
        if i == 2:
            plt.plot(iteration_labels, 
                     cumulative_best_objectives[:len(iteration_labels), i]*1e6,
                     marker='o', linestyle='-', label=objective_labels[0])
        else:
            plt.plot(iteration_labels, 
                     cumulative_best_objectives[:len(iteration_labels), i]*1e-6,
                     marker='o', linestyle='-', label=objective_labels[0])
        plt.xlabel("Iteration (0 = Initial Samples)", fontsize=16)
        plt.ylabel(f"{objective_labels[0]}", fontsize=16)
        plt.title("Evolution of Best Objective Values", fontsize=16)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f'img/mobo_objective_evolution_{i}.png')
        plt.show()


###########################################################################################

def plot_surrogate_with_ground_truth(
    model,
    train_X,
    train_Y,
    train_feas_mask,
    bounds,
    evaluate_objective,
    input_dim,
    objective_idx,
    input_transform,
    objective_label,
    do_ground_truth=True,
    n_points=100
):
    """
    Plot 1D slice of surrogate GP model along one input dimension with optional Astra ground truth overlay.

    Args:
        model (ModelListGP): The fitted BoTorch GP model.
        train_X (torch.Tensor): Training input data (parameters).
        train_Y (torch.Tensor): Training output data (objectives, negated).
        train_feas_mask (torch.Tensor): Boolean mask for feasible training points.
        bounds (torch.Tensor): Bounds of the input parameters.
        evaluate_objective (callable): Function to evaluate the objective (Astra simulation).
        input_dim (int): Index of the input dimension to slice along (e.g., 0 for solenoid:maxb(1)).
        objective_idx (int): Index of the objective to plot (0: emit_x, 1: emit_y, 2: sigma_energy).
        input_transform (botorch.models.transforms.Normalize): Input transform used for the model.
        objective_label (str): Label for the objective axis on the plot.
        do_ground_truth (bool): If True, also plot the ground truth from Astra.
        n_points (int): Number of points to sample for the sweep.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Step 1: Setup baseline for slicing
    # Get feasible points
    feasible_train_X = train_X[train_feas_mask]
    feasible_train_Y = train_Y[train_feas_mask]

    if feasible_train_X.numel() > 0:
        # Find the point with the best objective value among feasible points
        # (best means highest for negated objectives, so argmax)
        best_feasible_idx = feasible_train_Y[:, objective_idx].argmax()
        x_ref = feasible_train_X[best_feasible_idx]
    else:
        # Fallback: If no feasible points, use the first training point as reference
        print("Warning: No feasible points found. Using the first training point as reference for surrogate plot.")
        x_ref = train_X[0]

    # Create sweep points along the selected input dimension
    # Ensure x_ref is unsqueezed and repeated to match the batch shape for posterior
    x_sweep = torch.linspace(bounds[0, input_dim], bounds[1, input_dim], n_points) 
    
    # Create a tensor for prediction by copying x_ref and replacing the swept dimension
    X_predict = x_ref.unsqueeze(0).repeat(n_points, 1)
    X_predict[:, input_dim] = x_sweep

    # Step 2: Get GP predictions
    # Ensure model is in eval mode
    model.eval()
    with torch.no_grad():
        # Get posterior for the specific objective's GP
        # The model.models list corresponds to the objectives in order
        posterior = model.models[objective_idx].posterior(X_predict)
        mean = posterior.mean.squeeze().numpy()
        # --- FIX: Apply squeeze() and numpy() to each tensor in the tuple ---
        lower, upper = [t.squeeze().numpy() for t in posterior.confidence_region()]

    # Negate back for plotting if objectives are minimized
    mean_original_scale = -mean
    lower_original_scale = -upper # Swap lower/upper when negating confidence region
    upper_original_scale = -lower

    ax.plot(x_sweep.numpy(), mean_original_scale, label='GP Mean Prediction', color='blue')
    ax.fill_between(x_sweep.numpy(), lower_original_scale, upper_original_scale, alpha=0.2, color='blue', label='95% Confidence')

    # Plot original training data
    train_X_plot = train_X[:, input_dim].numpy()
    train_Y_plot = -train_Y[:, objective_idx].numpy() # Negate back for plotting
    ax.scatter(train_X_plot, train_Y_plot, color='black', marker='x', label='Training Data', s=50)

    # Highlight feasible training data
    feasible_train_X_plot = train_X[train_feas_mask][:, input_dim].numpy()
    feasible_train_Y_plot = -train_Y[train_feas_mask][:, objective_idx].numpy()
    ax.scatter(feasible_train_X_plot, feasible_train_Y_plot, color='green', marker='o', label='Feasible Training Data', s=70, edgecolors='k')


    # Step 3: Plot ground truth (optional)
    if do_ground_truth:
        print(f"Calculating ground truth for input dimension {input_dim}...")
        ground_truth_Y_list = []
        for i in range(n_points):
            # Create a parameter set for Astra simulation from X_predict
            # evaluate_objective expects a single torch.Tensor parameter set
            _, gt_feasible, _ = evaluate_objective(X_predict[i])
            # Only store if feasible, or store all and filter later
            # For plotting ground truth, we typically plot all points on the slice
            ground_truth_Y_list.append(evaluate_objective(X_predict[i])[0][objective_idx]) # Get only the objective value

        ground_truth_Y = torch.tensor(ground_truth_Y_list, dtype=torch.double).numpy()
        ax.plot(x_sweep.numpy(), -ground_truth_Y, label='Astra Ground Truth', color='red', linestyle='--') # Negate back

    ax.set_xlabel(f'Input Parameter {input_dim}', fontsize=16)
    ax.set_ylabel(objective_label, fontsize=16)
    ax.set_title(f'GP Surrogate for {objective_label} vs Input Parameter {input_dim}', 
                 fontsize=16)
    ax.grid(True)
    ax.legend()
    plt.tight_layout()
    plt.show()

############################################################################################

def plot_objective_space(min_index, norm_emit_x, norm_emit_y, sigma_energy):

    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    axs = axs.flatten()

    #for i in range(0, 100):
    #    axs[0].scatter(nex[i]*1e6, ney[i]*1e6, marker='*', s=2)
    axs[0].scatter([x*1e6 for x in norm_emit_x], [x*1e6 for x in norm_emit_y], c='b', marker='o', s=2)
    axs[0].scatter(norm_emit_x[min_index]*1e6, norm_emit_y[min_index]*1e6, c='r', marker='o', label='Best')
    axs[0].set_xlabel(r'$\epsilon_{n, x}$ [mm-mrad]', fontsize=16)
    axs[0].set_ylabel(r'$\epsilon_{n, y}$ [mm-mrad]', fontsize=16)
    axs[0].set_title(r'$\epsilon_{n, x}$ vs. $\epsilon_{n, y}$', fontsize=16)
    axs[0].grid(True)
    axs[0].legend(loc='best')

    axs[1].scatter([x*1e-6 for x in sigma_energy], [x*1e6 for x in norm_emit_x], c='b', marker='o', s=2)
    axs[1].scatter(sigma_energy[min_index]*1e-6, norm_emit_x[min_index]*1e6, c='r', marker='o', label='Best')
    axs[1].set_xlabel(r'$\sigma_{E} [MeV]$', fontsize=16)
    axs[1].set_ylabel(r'$\epsilon_{n, x}$ [mm-mrad]', fontsize=16)
    axs[1].set_title(r'$\sigma_{E}$ vs. $\epsilon_{n, x}$', fontsize=16)
    axs[1].grid(True)
    axs[1].legend(loc='best')

    axs[2].scatter([x*1e-6 for x in sigma_energy], [x*1e6 for x in norm_emit_y], c='b', marker='o', s=2)
    axs[2].scatter(sigma_energy[min_index]*1e-6, norm_emit_y[min_index]*1e6, c='r', marker='o', label='Best')
    axs[2].set_xlabel(r'$\sigma_{E} [MeV]$', fontsize=16)
    axs[2].set_ylabel(r'$\epsilon_{n, y}$ [mm-mrad]', fontsize=16)
    axs[2].set_title(r'$\sigma_{E}$ vs. $\epsilon_{n, y}$', fontsize=16)
    axs[2].grid(True)
    axs[2].legend(loc='best')

    plt.tight_layout()
    plt.savefig("img/sbo_objective_space.png")
    plt.show()

############################################################################################

def plot_constraint_space(min_index, sigma_x, sigma_y, sigma_xp, sigma_yp, sigma_z, mean_kinetic_energy):

    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    axs = axs.flatten()

    axs[0].scatter([x*1e3 for x in sigma_x], [x*1e3 for x in sigma_xp], c='b', marker='o', s=2)
    axs[0].scatter(sigma_x[min_index]*1e3, sigma_xp[min_index]*1e3, c='r', marker='o', label='Best')
    axs[0].axvline(1.0, color='purple', linestyle='--')
    axs[0].axhline(1.0, color='purple', linestyle='--')
    axs[0].set_xlabel(r'$\sigma_x$ [mm]', fontsize=16)
    axs[0].set_ylabel(r'$\sigma_{x^{\prime}}$ [mrad]', fontsize=16)
    axs[0].set_title(r'$\sigma_x$ vs. $\sigma_{x^{\prime}}$', fontsize=16)
    axs[0].grid(True)
    axs[0].legend(loc='best')

    axs[1].scatter([x*1e3 for x in sigma_y], [x*1e3 for x in sigma_yp], c='b', marker='o', s=2)
    axs[1].scatter(sigma_y[min_index]*1e3, sigma_yp[min_index]*1e3, c='r', marker='o', label='Best')
    axs[1].axvline(1.0, color='purple', linestyle='--')
    axs[1].axhline(1.0, color='purple', linestyle='--')
    axs[1].set_xlabel(r'$\sigma_y$ [mm]', fontsize=16)
    axs[1].set_ylabel(r'$\sigma_{y^{\prime}}$ [mrad]', fontsize=16)
    axs[1].set_title(r'$\sigma_y$ vs. $\sigma_{y^{\prime}}$', fontsize=16)
    axs[1].grid(True)
    axs[1].legend(loc='best')

    axs[2].scatter([x*1e3 for x in sigma_z], [x/1e6 for x in mean_kinetic_energy], c='b', marker='o', s=2)
    axs[2].scatter(sigma_z[min_index]*1e3, mean_kinetic_energy[min_index]/1e6, c='r', marker='o', label='Best')
    axs[2].axvline(1.0, color='purple', linestyle='--')
    axs[2].axhline(205, color='purple', linestyle='--')
    axs[2].axhline(195, color='purple', linestyle='--')
    axs[2].set_xlabel(r'$\sigma_z$ [mm]', fontsize=16)
    axs[2].set_ylabel(r'$<E>$ [MeV]', fontsize=16)
    axs[2].set_title(r'$\sigma_z$ vs. $<E>$', fontsize=16)
    axs[2].grid(True)
    axs[2].legend(loc='best')
    
    plt.tight_layout()
    plt.savefig("img/sbo_constraint_space.png")
    plt.show()

############################################################################################

def plot_convergence_gp(result, filename):
    plt.figure(figsize=(10, 6))
    plot_convergence(result)
    plt.title("Convergence Plot", fontsize=16)
    plt.xlabel("Number of Iterations", fontsize=16)
    plt.ylabel("Objective Function Value", fontsize=16)
    plt.grid(True)
    plt.savefig(filename)
    plt.show()

############################################################################################

def plot_objective_gp(result, filename):
    plt.figure(figsize=(10, 8))
    plot_objective(result)
    plt.suptitle("Partial Dependence Plot (Gaussian Process)", fontsize=16)
    plt.savefig(filename)
    plt.show()

############################################################################################

def plot_evaluations_gp(result, filename):
    plt.figure(figsize=(10, 8))
    plot_evaluations(result)
    plt.suptitle("Parameter Space Evaluations", fontsize=16)
    plt.savefig(filename)
    plt.show()

############################################################################################

def plot_regret_gp(result, filename):
    plt.figure(figsize=(10, 6))
    plot_regret(result)
    plt.title("Cumulative Regret Plot", fontsize=16)
    plt.xlabel("Number of Iterations", fontsize=16)
    plt.savefig(filename)
    plt.show()

############################################################################################

def plot_objective_space_best(filename, norm_emit_x, norm_emit_y, sigma_energy,
                             weight_combinations, min_indices):
    param = ['norm_emit_x', 'norm_emit_y', 'sigma_energy']

    # Create subplots for each parameter
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    axs = axs.flatten()

    for i in range(0, len(weight_combinations)):        
        axs[0].scatter(norm_emit_x[i][min_indices[i]]*1e6, norm_emit_y[i][min_indices[i]]*1e6, marker='o', label=weight_combinations[i])
        axs[0].set_xlabel(r'$\epsilon_{n, x}$ [mm-mrad]', fontsize=16)
        axs[0].set_ylabel(r'$\epsilon_{n, y}$ [mm-mrad]', fontsize=16)
        axs[0].set_title(r'$\epsilon_{n, x}$ vs. $\epsilon_{n, y}$', fontsize=16)
        axs[0].grid(True)
        axs[0].legend(loc='best')

        axs[1].scatter(sigma_energy[i][min_indices[i]]*1e-6, norm_emit_x[i][min_indices[i]]*1e6, marker='o', label=weight_combinations[i])
        
        axs[1].set_xlabel(r'$\sigma_{E} [MeV]$', fontsize=16)
        axs[1].set_ylabel(r'$\epsilon_{n, x}$ [mm-mrad]', fontsize=16)
        axs[1].set_title(r'$\sigma_{E}$ vs. $\epsilon_{n, x}$', fontsize=16)
        axs[1].grid(True)
        axs[1].legend(loc='best')

        axs[2].scatter(sigma_energy[i][min_indices[i]]*1e-6, norm_emit_y[i][min_indices[i]]*1e6, marker='o', label=weight_combinations[i])
        
        axs[2].set_xlabel(r'$\sigma_{E} [MeV]$', fontsize=16)
        axs[2].set_ylabel(r'$\epsilon_{n, y}$ [mm-mrad]', fontsize=16)
        axs[2].set_title(r'$\sigma_{E}$ vs. $\epsilon_{n, y}$', fontsize=16)
        axs[2].grid(True)
        axs[2].legend(loc='best')

    axs[0].axvline(target_norm_emittance, color='r', linestyle='--',
                   label=r'Target $\epsilon_{n,x}$ =' +    
                   f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
    axs[0].axhline(target_norm_emittance, color='r', linestyle='--',
                   label=r'Target $\epsilon_{n,x}$ =' + 
                   f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')

    axs[1].axvline(target_energy_deviation, color='r', linestyle='--', 
                   label=r'Target $\sigma_{E}$ =' + 
                   f'{target_energy_deviation:5.3f}'+r'$[MeV]$')
    axs[1].axhline(target_norm_emittance, color='r', linestyle='--',
                   label=r'Target $\epsilon_{n,x}$ =' + 
                   f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')

    axs[2].axvline(target_energy_deviation, color='r', linestyle='--', 
                   label=r'Target $\sigma_{E}$ =' + 
                   f'{target_energy_deviation:5.3f}'+r'$[MeV]$')
    axs[2].axhline(target_norm_emittance, color='r', linestyle='--',
                   label=r'Target $\epsilon_{n,x}$ =' + 
                   f'{target_norm_emittance:5.3f}'+r'$[mm-mrad]$')
    
    plt.tight_layout()
    plt.savefig(filename)
    plt.show()

############################################################################################

def plot_objective_space_all(filename, norm_emit_x, norm_emit_y, sigma_energy,
                            weight_combinations, min_indices):
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    axs = axs.flatten()

    for i in range(0, len(weight_combinations)):
        axs[0].scatter([x*1e6 for x in norm_emit_x[i]], [x*1e6 for x in norm_emit_y[i]], c='b', marker='o', s=2)
        axs[0].scatter(norm_emit_x[i][min_indices[i]]*1e6, norm_emit_y[i][min_indices[i]]*1e6, c='r', marker='o', label=weight_combinations[i])
        axs[0].set_xlabel(r'$\epsilon_{n, x}$ [mm-mrad]', fontsize=16)
        axs[0].set_ylabel(r'$\epsilon_{n, y}$ [mm-mrad]', fontsize=16)
        axs[0].set_title(r'$\epsilon_{n, x}$ vs. $\epsilon_{n, y}$', fontsize=16)
        axs[0].grid(True)
        #axs[0].legend(loc='best')

        axs[1].scatter([x*1e-6 for x in sigma_energy[i]], [x*1e6 for x in norm_emit_x[i]], c='b', marker='o', s=2)
        axs[1].scatter(sigma_energy[i][min_indices[i]]*1e-6, norm_emit_x[i][min_indices[i]]*1e6, c='r', marker='o', label=weight_combinations[i])
        axs[1].set_xlabel(r'$\sigma_{E} [MeV]$', fontsize=16)
        axs[1].set_ylabel(r'$\epsilon_{n, x}$ [mm-mrad]', fontsize=16)
        axs[1].set_title(r'$\sigma_{E}$ vs. $\epsilon_{n, x}$', fontsize=16)
        axs[1].grid(True)
        #axs[1].legend(loc='best')

        axs[2].scatter([x*1e-6 for x in sigma_energy[i]], [x*1e6 for x in norm_emit_y[i]], c='b', marker='o', s=2)
        axs[2].scatter(sigma_energy[i][min_indices[i]]*1e-6, norm_emit_y[i][min_indices[i]]*1e6, c='r', marker='o', label=weight_combinations[i])
        axs[2].set_xlabel(r'$\sigma_{E} [MeV]$', fontsize=16)
        axs[2].set_ylabel(r'$\epsilon_{n, y}$ [mm-mrad]', fontsize=16)
        axs[2].set_title(r'$\sigma_{E}$ vs. $\epsilon_{n, y}$', fontsize=16)
        axs[2].grid(True)
        #axs[2].legend(loc='best')

    plt.tight_layout()
    plt.savefig(filename)
    plt.show()

############################################################################################

def plot_objective_space_all_iter(filename, norm_emit_x, norm_emit_y, sigma_energy,
                                  weight_combinations, n_calls, min_indices):
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    axs = axs.flatten()
    colors = np.linspace(0, 1, 150)

    for i in range(0, len(weight_combinations)):
        axs[0].scatter([x*1e6 for x in norm_emit_x[i]], [x*1e6 for x in norm_emit_y[i]], marker='o', s=2, c=colors, cmap='cividis')
        axs[0].scatter(norm_emit_x[i][min_indices[i]]*1e6, norm_emit_y[i][min_indices[i]]*1e6, c='r', marker='o', label=weight_combinations[i])
        axs[0].set_xlabel(r'$\epsilon_{n, x}$ [mm-mrad]', fontsize=16)
        axs[0].set_ylabel(r'$\epsilon_{n, y}$ [mm-mrad]', fontsize=16)
        axs[0].set_title(r'$\epsilon_{n, x}$ vs. $\epsilon_{n, y}$', fontsize=16)
        axs[0].grid(True)
        #axs[0].legend(loc='best')

        axs[1].scatter([x*1e-6 for x in sigma_energy[i]], [x*1e6 for x in norm_emit_x[i]], marker='o', s=2, c=colors, cmap='viridis')
        axs[1].scatter(sigma_energy[i][min_indices[i]]*1e-6, norm_emit_x[i][min_indices[i]]*1e6, c='r', marker='o', label=weight_combinations[i])
        axs[1].set_xlabel(r'$\sigma_{E} [MeV]$', fontsize=16)
        axs[1].set_ylabel(r'$\epsilon_{n, x}$ [mm-mrad]', fontsize=16)
        axs[1].set_title(r'$\sigma_{E}$ vs. $\epsilon_{n, x}$', fontsize=16)
        axs[1].grid(True)
        #axs[1].legend(loc='best')

        axs[2].scatter([x*1e-6 for x in sigma_energy[i]], [x*1e6 for x in norm_emit_y[i]], marker='o', s=2, c=colors, cmap='viridis')
        axs[2].scatter(sigma_energy[i][min_indices[i]]*1e-6, norm_emit_y[i][min_indices[i]]*1e6, c='r', marker='o', label=weight_combinations[i])
        axs[2].set_xlabel(r'$\sigma_{E} [MeV]$', fontsize=16)
        axs[2].set_ylabel(r'$\epsilon_{n, y}$ [mm-mrad]', fontsize=16)
        axs[2].set_title(r'$\sigma_{E}$ vs. $\epsilon_{n, y}$', fontsize=16)
        axs[2].grid(True)
        #axs[2].legend(loc='best')

    plt.tight_layout()
    plt.savefig(filename)
    plt.show()

############################################################################################

def plot_constraint_space_all(filename, sigma_x, sigma_xp, sigma_y, sigma_yp, sigma_z, 
                              mean_kinetic_energy, weight_combinations, min_indices):
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    axs = axs.flatten()

    for i in range(0, len(weight_combinations)):

        axs[0].scatter([x*1e3 for x in sigma_x[i]], [x*1e3 for x in sigma_xp[i]], c='b', marker='o', s=2)
        axs[0].scatter(sigma_x[i][min_indices[i]]*1e3, sigma_xp[i][min_indices[i]]*1e3, c='r', marker='o', label=weight_combinations[i])
        axs[0].axvline(1.0, color='purple', linestyle='--')
        axs[0].axhline(1.0, color='purple', linestyle='--')
        axs[0].set_xlabel(r'$\sigma_x$ [mm]', fontsize=16)
        axs[0].set_ylabel(r'$\sigma_{x^{\prime}}$ [mrad]', fontsize=16)
        axs[0].set_title(r'$\sigma_x$ vs. $\sigma_{x^{\prime}}$', fontsize=16)
        axs[0].grid(True)
        #axs[0].legend(loc='best')

        axs[1].scatter([x*1e3 for x in sigma_y[i]], [x*1e3 for x in sigma_yp[i]], c='b', marker='o', s=2)
        axs[1].scatter(sigma_y[i][min_indices[i]]*1e3, sigma_yp[i][min_indices[i]]*1e3, c='r', marker='o', label=weight_combinations[i])
        axs[1].axvline(1.0, color='purple', linestyle='--')
        axs[1].axhline(1.0, color='purple', linestyle='--')
        axs[1].set_xlabel(r'$\sigma_y$ [mm]', fontsize=16)
        axs[1].set_ylabel(r'$\sigma_{y^{\prime}}$ [mrad]', fontsize=16)
        axs[1].set_title(r'$\sigma_y$ vs. $\sigma_{y^{\prime}}$', fontsize=16)
        axs[1].grid(True)
        #axs[1].legend(loc='best')

        axs[2].scatter([x*1e3 for x in sigma_z[i]], [x/200e6 for x in mean_kinetic_energy[i]], c='b', marker='o', s=2) 
        axs[2].scatter(sigma_z[i][min_indices[i]]*1e3, mean_kinetic_energy[i][min_indices[i]]/200e6, c='r', marker='o', label=weight_combinations[i])
        axs[2].axvline(1.0, color='purple', linestyle='--')
        axs[2].axhline(205/200, color='purple', linestyle='--')
        axs[2].axhline(195/200, color='purple', linestyle='--')
        axs[2].set_xlabel(r'$\sigma_z$ [mm]', fontsize=16)
        axs[2].set_ylabel(r'$<E>$ [MeV]', fontsize=16)
        axs[2].set_title(r'$\sigma_z$ vs. $<E>$', fontsize=16)
        axs[2].grid(True)
        #axs[2].legend(loc='best')
    
    plt.tight_layout()
    plt.savefig(filename)
    plt.show()

############################################################################################

def plot_convergence_all(*args, cc, label, ax):
    
    for results, color in zip(args, cc):

        if isinstance(results, OptimizeResult):
            n_calls = len(results.x_iters)
            mins = [np.min(results.func_vals[:i])
                    for i in range(1, n_calls + 1)]
            ax.plot(range(1, n_calls + 1), mins, c=cc,
                    marker=".", markersize=12, lw=2, label=label)

        elif isinstance(results, list):
            n_calls = len(results[0].x_iters)
            iterations = range(1, n_calls + 1)
            mins = [[np.min(r.func_vals[:i]) for i in iterations]
                    for r in results]

            for m in mins:
                ax.plot(iterations, m, c=color, alpha=0.2)

            ax.plot(iterations, np.mean(mins, axis=0), c=color,
                    marker=".", markersize=12, lw=2, label=name)
            ax.grid()

            ############################################################################################

def plot_regret_all(*args, cc, label, ax, true_minimum=None):
    if true_minimum is None:
        new_results = []
        for res in args:
            if isinstance(res, tuple):
                res = res[1]
            if isinstance(res, OptimizeResult):
                new_results.append(res)
            elif isinstance(res, list):
                new_results.extend(res)
            true_minimum = np.min([np.min(r.func_vals) for r in new_results])

    for results, color in zip(args, cc):
        if isinstance(results, OptimizeResult):
            n_calls = len(results.x_iters)
        
            regrets = [
                np.sum(results.func_vals[:i] - true_minimum)
                for i in range(1, n_calls + 1)
            ]
        
            ax.plot(
                range(1, n_calls + 1),
                regrets,
                c=cc,
                marker=".",
                markersize=12,
                lw=2,
                label=label,
            )

############################################################################################

def astra_plot(astra_sim, filename, beamsize=False):
    plt.figure(figsize=(15,8))
    if beamsize:
        astra_sim.plot()
        plt.savefig(filename)
    else:
        astra_sim.plot(['norm_emit_x', 'norm_emit_y'], y2='sigma_energy')
        plt.savefig(filename)
    plt.show()
