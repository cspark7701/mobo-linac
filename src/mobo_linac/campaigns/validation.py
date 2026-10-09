"""Reproducible validation campaign: one unconstrained MOBO run with every standard artifact."""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from mobo_linac.config import MoboConfig
from mobo_linac.campaigns.runner import MoboCampaignRunner


def run_validation_campaign(
    config: MoboConfig,
    options: Dict[str, Any],
    base_results_dir: Union[str, Path] = "results",
    device: str = "auto",
    evaluator: Optional[Any] = None,
) -> Path:
    """Run a validation campaign in ``<base_results_dir>/validation_<timestamp>``.

    ``options`` are resolved campaign options (see ``config.resolve_campaign_options``).
    The standard campaign figures and artifacts are the validation outputs.
    """

    runner = MoboCampaignRunner(
        config=config,
        run_name="validation",
        base_results_dir=base_results_dir,
        num_initial_samples=options["num_initial_samples"],
        num_batches=options["num_batches"],
        batch_size=options["batch_size"],
        num_workers=options["num_workers"],
        seed=options["seed"],
        acq_type=options["acquisition"],
        export_plots=True,
        evaluator=evaluator,
        device=device,
    )
    _, _, run_dir = runner.run()
    return run_dir
