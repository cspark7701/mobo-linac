"""Final artifact publication, separated from proposal and backend execution."""
from mobo_linac.io.durable import atomic_json


def finalize_campaign(writer, results, tracker, run_dir, config, proposal_history,
                      export_plots, elapsed_wall_time_s, figures):
    """Export registered figures (``(stem, plot(results, tracker, config, path))``), then publish completion."""
    if export_plots:
        from mobo_linac.plotting.common import figure_scope
        figures_dir = run_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        with figure_scope():  # campaign figures never accumulate across runs or suites
            for stem, plot in figures:
                plot(results, tracker, config, figures_dir / f"{stem}.png")
    atomic_json(run_dir / "proposal_history.json", proposal_history)
    from mobo_linac.metrics.selection import select_representatives
    try:
        select_representatives(results, config).write(run_dir / "representatives.json")
    except ValueError as error:  # no measured feasible point: record that explicitly
        atomic_json(run_dir / "representatives.json", {"schema_version": 1, "roles": {}, "reason": str(error)})
    required = ["config.json", "config.yaml", "checkpoints/checkpoint.pt", "proposal_history.json"]
    if export_plots:
        required += [f"figures/{stem}.png" for stem, _ in figures]
    writer.complete(len(results), elapsed_wall_time_s, required)
