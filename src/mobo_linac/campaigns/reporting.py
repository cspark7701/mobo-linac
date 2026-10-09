"""Final artifact publication, separated from proposal and backend execution."""
from mobo_linac.io.artifacts import atomic_json


def finalize_campaign(writer, results, tracker, run_dir, config, proposal_history,
                      export_plots, elapsed_wall_time_s, plotters):
    names = ("hypervolume_progress", "pareto_front", "objective_evolution", "constraint_diagnostics")
    if export_plots:
        figures_dir = run_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        plotters[0](tracker.to_dataframe(), figures_dir / f"{names[0]}.png")
        plotters[1](results, figures_dir / f"{names[1]}.png", config=config)
        plotters[2](results, figures_dir / f"{names[2]}.png", config=config)
        plotters[3](results, figures_dir / f"{names[3]}.png")
    atomic_json(run_dir / "proposal_history.json", proposal_history)
    required = ["config.json", "config.yaml", "checkpoints/checkpoint.pt", "proposal_history.json"]
    if export_plots:
        required += [f"figures/{name}.png" for name in names]
    writer.complete(len(results), elapsed_wall_time_s, required)
