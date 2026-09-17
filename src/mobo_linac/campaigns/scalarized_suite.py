"""
Scalarized Multi-Weight Suite Module for mobo_linac.

Implements Option 2: Representative Operational Linac Archetypes for Phase 1 Scalarized BO:
1. Balanced Linac Operation (equal weighting across transverse and longitudinal)
2. High-Brightness FEL Injector Mode (transverse emittance priority)
3. Low Energy Spread Mode (longitudinal energy spread priority)
4. Horizontal-Dominant Optics (quadrupole doublet horizontal waist focus)
5. Vertical-Dominant Optics (quadrupole doublet vertical waist focus)

Provides suite execution, per-case orchestration, multi-case result aggregation,
and publication LaTeX table generation.
"""

from collections import OrderedDict
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import torch
from botorch.utils.multi_objective.pareto import is_non_dominated

from mobo_linac.campaigns.runner import MoboCampaignRunner
from mobo_linac.io.results import (
    DESIGN_VAR_COLUMNS,
    MODEL_OBJ_COLUMNS,
    PHYSICAL_OBJ_COLUMNS,
    results_to_dataframe,
)
from mobo_linac.metrics.hypervolume import HypervolumeTracker, compute_reference_point
from mobo_linac.metrics.reporting import (
    DEFAULT_REPORTING_REF_POINT_MODEL_NORM,
    DEFAULT_REPORTING_SCALES,
    compute_normalized_hypervolume,
    normalize_objectives_model,
)

# Canonical Option 2 Weight Cases
OPTION_2_CASES: OrderedDict[str, Dict[str, Any]] = OrderedDict([
    (
        "balanced",
        {
            "name": "Balanced Linac Operation",
            "weights": [0.33333333, 0.33333333, 0.33333334],
            "description": "Equal compromise across transverse emittance and energy spread",
            "symbol": r"w_{\mathrm{bal}} = [\frac{1}{3},\,\frac{1}{3},\,\frac{1}{3}]",
        },
    ),
    (
        "high_brightness",
        {
            "name": "High-Brightness FEL Mode",
            "weights": [0.45, 0.45, 0.10],
            "description": "Transverse-dominant emittance minimization for maximum FEL peak brightness",
            "symbol": r"w_{\mathrm{FEL}} = [0.45,\,0.45,\,0.10]",
        },
    ),
    (
        "low_energy_spread",
        {
            "name": "Low Energy Spread Mode",
            "weights": [0.10, 0.10, 0.80],
            "description": "Longitudinal-dominant energy spread minimization for spectrometer transport",
            "symbol": r"w_{\sigma_E} = [0.10,\,0.10,\,0.80]",
        },
    ),
    (
        "x_dominant",
        {
            "name": "Horizontal-Dominant Optics",
            "weights": [0.60, 0.20, 0.20],
            "description": "Quadrupole doublet asymmetry prioritizing horizontal emittance waist",
            "symbol": r"w_{x} = [0.60,\,0.20,\,0.20]",
        },
    ),
    (
        "y_dominant",
        {
            "name": "Vertical-Dominant Optics",
            "weights": [0.20, 0.60, 0.20],
            "description": "Quadrupole doublet asymmetry prioritizing vertical emittance waist",
            "symbol": r"w_{y} = [0.20,\,0.60,\,0.20]",
        },
    ),
])


def get_option2_cases() -> Dict[str, Dict[str, Any]]:
    """Returns dictionary of all Option 2 weight cases."""
    return dict(OPTION_2_CASES)


def get_option2_case(case_name: str) -> Dict[str, Any]:
    """
    Returns specific Option 2 case configuration by key.
    
    Raises:
        ValueError: If case_name is not recognised.
    """
    if case_name not in OPTION_2_CASES:
        valid_keys = list(OPTION_2_CASES.keys())
        raise ValueError(f"Unknown Option 2 case '{case_name}'. Valid cases: {valid_keys}")
    return OPTION_2_CASES[case_name]


def aggregate_scalarized_cases(
    base_dir: Union[str, Path],
    case_dirs: Optional[Sequence[Union[str, Path]]] = None,
) -> Dict[str, Any]:
    """
    Aggregates results from multiple scalarized BO cases into a unified dataset.
    
    Produces in base_dir:
      - cases_summary.csv / cases_summary.json (per-case summary statistics)
      - evaluations.csv / candidate_history.csv (merged evaluations across cases)
      - train_X.csv / train_Y.csv (merged training matrices)
      - pareto.csv / pareto_all.csv / pareto_feasible.csv (global Pareto front across all cases)
      - hypervolume.csv (cumulative hypervolume trajectory)

    Args:
        base_dir: Root directory for the Phase 1 scalarized suite.
        case_dirs: Optional list of explicit case directories. If None, auto-discovers
                   child directories corresponding to OPTION_2_CASES or containing evaluations.csv.

    Returns:
        Dict containing aggregated summary statistics and record counts.
    """
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    # 1. Discover subdirectories to aggregate
    discovered_dirs: List[Tuple[str, Path]] = []
    if case_dirs is not None:
        for p in case_dirs:
            p_path = Path(p)
            if p_path.is_dir():
                discovered_dirs.append((p_path.name, p_path))
    else:
        # Check canonical Option 2 case names first
        for case_key in OPTION_2_CASES.keys():
            candidate = base_path / case_key
            if candidate.is_dir() and (candidate / "evaluations.csv").exists():
                discovered_dirs.append((case_key, candidate))

        # Check for any other subdirectories containing evaluations.csv
        for sub in sorted(base_path.iterdir()):
            if sub.is_dir() and sub.name not in [k for k, _ in discovered_dirs]:
                if (sub / "evaluations.csv").exists():
                    discovered_dirs.append((sub.name, sub))

    if not discovered_dirs:
        # If no subdirectories found but base_dir itself has evaluations.csv, treat base_dir as a single case
        if (base_path / "evaluations.csv").exists():
            discovered_dirs.append(("balanced", base_path))

    summary_rows = []
    all_eval_dfs = []
    all_cand_dfs = []

    for case_key, case_path in discovered_dirs:
        eval_csv = case_path / "evaluations.csv"
        cand_csv = case_path / "candidate_history.csv"
        hv_csv = case_path / "hypervolume.csv"

        if not eval_csv.exists():
            continue

        df_eval = pd.read_csv(eval_csv)
        df_eval["case"] = case_key
        all_eval_dfs.append(df_eval)

        if cand_csv.exists():
            df_cand = pd.read_csv(cand_csv)
            df_cand["case"] = case_key
            all_cand_dfs.append(df_cand)

        # Per-case statistics
        n_eval = len(df_eval)
        n_valid = int(df_eval["simulation_valid"].sum()) if "simulation_valid" in df_eval.columns else n_eval
        n_feas = int(df_eval["physically_feasible"].sum()) if "physically_feasible" in df_eval.columns else 0
        feas_pct = (n_feas / n_valid * 100.0) if n_valid > 0 else 0.0

        min_ex_um = float(df_eval["norm_emit_x_m_rad"].min() * 1e6) if "norm_emit_x_m_rad" in df_eval.columns else np.nan
        min_ey_um = float(df_eval["norm_emit_y_m_rad"].min() * 1e6) if "norm_emit_y_m_rad" in df_eval.columns else np.nan
        min_se_mev = float(df_eval["sigma_energy_eV"].min() / 1e6) if "sigma_energy_eV" in df_eval.columns else np.nan

        # Feasible minimums
        df_feas = df_eval[df_eval["physically_feasible"] == True] if "physically_feasible" in df_eval.columns else pd.DataFrame()
        min_ex_feas_um = float(df_feas["norm_emit_x_m_rad"].min() * 1e6) if not df_feas.empty and "norm_emit_x_m_rad" in df_feas.columns else np.nan
        min_ey_feas_um = float(df_feas["norm_emit_y_m_rad"].min() * 1e6) if not df_feas.empty and "norm_emit_y_m_rad" in df_feas.columns else np.nan
        min_se_feas_mev = float(df_feas["sigma_energy_eV"].min() / 1e6) if not df_feas.empty and "sigma_energy_eV" in df_feas.columns else np.nan

        final_hv = 0.0
        if hv_csv.exists():
            df_hv = pd.read_csv(hv_csv)
            if "feasible_hypervolume" in df_hv.columns and not df_hv.empty:
                final_hv = float(df_hv["feasible_hypervolume"].iloc[-1])

        case_meta = OPTION_2_CASES.get(case_key, {
            "name": case_key.replace("_", " ").title(),
            "weights": [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0],
            "description": f"Custom scalarized case: {case_key}",
            "symbol": case_key,
        })

        summary_rows.append({
            "case_id": case_key,
            "name": case_meta["name"],
            "description": case_meta["description"],
            "w_emit_x": float(case_meta["weights"][0]),
            "w_emit_y": float(case_meta["weights"][1]),
            "w_energy_spread": float(case_meta["weights"][2]),
            "num_evaluations": n_eval,
            "num_valid": n_valid,
            "num_feasible": n_feas,
            "feasible_fraction_pct": round(feas_pct, 2),
            "min_norm_emit_x_um": round(min_ex_um, 4),
            "min_norm_emit_y_um": round(min_ey_um, 4),
            "min_sigma_energy_MeV": round(min_se_mev, 4),
            "min_norm_emit_x_feas_um": round(min_ex_feas_um, 4) if not np.isnan(min_ex_feas_um) else None,
            "min_norm_emit_y_feas_um": round(min_ey_feas_um, 4) if not np.isnan(min_ey_feas_um) else None,
            "min_sigma_energy_feas_MeV": round(min_se_feas_mev, 4) if not np.isnan(min_se_feas_mev) else None,
            "final_feasible_hv": round(final_hv, 6),
        })

    # Save summary
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(base_path / "cases_summary.csv", index=False)
    with open(base_path / "cases_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_rows, f, indent=2)

    # 2. Merge all evaluations
    if all_eval_dfs:
        df_merged_eval = pd.concat(all_eval_dfs, ignore_index=True)
        # Drop duplicates by parameters if any
        df_merged_eval.to_csv(base_path / "evaluations.csv", index=False)

        if all_cand_dfs:
            df_merged_cand = pd.concat(all_cand_dfs, ignore_index=True)
            df_merged_cand.to_csv(base_path / "candidate_history.csv", index=False)
        else:
            df_merged_eval.to_csv(base_path / "candidate_history.csv", index=False)

        # Merge train_X and train_Y
        valid_mask = df_merged_eval["simulation_valid"] == True
        df_valid = df_merged_eval[valid_mask]

        if not df_valid.empty and all(c in df_valid.columns for c in DESIGN_VAR_COLUMNS):
            train_X = torch.tensor(df_valid[DESIGN_VAR_COLUMNS].values, dtype=torch.double)
            pd.DataFrame(train_X.numpy(), columns=DESIGN_VAR_COLUMNS).to_csv(
                base_path / "train_X.csv", index=False
            )

            # Model objectives: [-ex, -ey, -se]
            phys_objs = df_valid[PHYSICAL_OBJ_COLUMNS].values
            train_Y = torch.tensor(-phys_objs, dtype=torch.double)
            pd.DataFrame(
                train_Y.numpy(),
                columns=["model_emit_x_neg", "model_emit_y_neg", "model_sigma_energy_neg"],
            ).to_csv(base_path / "train_Y.csv", index=False)

            # Physical objectives
            df_valid[PHYSICAL_OBJ_COLUMNS].to_csv(base_path / "objectives_physical.csv", index=False)

            # Recompute global non-dominated Pareto front across ALL cases
            pareto_mask_all = is_non_dominated(train_Y)
            p_X_all = train_X[pareto_mask_all]
            p_Y_all_phys = -train_Y[pareto_mask_all]
            df_pareto_all = pd.DataFrame(
                np.hstack([p_X_all.numpy(), p_Y_all_phys.numpy()]),
                columns=DESIGN_VAR_COLUMNS + PHYSICAL_OBJ_COLUMNS,
            )
            df_pareto_all.to_csv(base_path / "pareto.csv", index=False)
            df_pareto_all.to_csv(base_path / "pareto_all.csv", index=False)

            # Feasible Pareto front
            feas_mask = torch.tensor(df_valid["physically_feasible"].values, dtype=torch.bool)
            if feas_mask.sum().item() > 0:
                feas_X = train_X[feas_mask]
                feas_Y = train_Y[feas_mask]
                feas_pareto_mask = is_non_dominated(feas_Y)
                p_feas_X = feas_X[feas_pareto_mask]
                p_feas_Y_phys = -feas_Y[feas_pareto_mask]
                df_pareto_feas = pd.DataFrame(
                    np.hstack([p_feas_X.numpy(), p_feas_Y_phys.numpy()]),
                    columns=DESIGN_VAR_COLUMNS + PHYSICAL_OBJ_COLUMNS,
                )
                df_pareto_feas.to_csv(base_path / "pareto_feasible.csv", index=False)
            else:
                pd.DataFrame(columns=DESIGN_VAR_COLUMNS + PHYSICAL_OBJ_COLUMNS).to_csv(
                    base_path / "pareto_feasible.csv", index=False
                )

            # Construct cumulative hypervolume progression
            reporting_ref_point = compute_reference_point(train_Y, offset_ratio=0.10)
            tracker = HypervolumeTracker(reporting_ref_point=reporting_ref_point)
            cum_Y_list, cum_feas_list = [], []
            for i, (_, row) in enumerate(df_merged_eval.iterrows()):
                if not row.get("simulation_valid", True):
                    continue
                cum_Y_list.append([-row[c] for c in PHYSICAL_OBJ_COLUMNS])
                cum_feas_list.append(bool(row.get("physically_feasible", False)))

                if (i + 1) % 8 == 0 or (i + 1) == len(df_merged_eval):
                    step_Y = torch.tensor(cum_Y_list, dtype=torch.double)
                    step_feas = torch.tensor(cum_feas_list, dtype=torch.bool)
                    tracker.track_iteration(
                        iteration=len(tracker.history),
                        train_Y=step_Y,
                        train_feas_mask=step_feas,
                    )

            if tracker.history:
                tracker.save_csv(base_path / "hypervolume.csv")

    # Copy config files to base_path if present in any case dir
    for _, case_path in discovered_dirs:
        for cfg_name in ["config.json", "config.yaml"]:
            src_cfg = case_path / cfg_name
            dst_cfg = base_path / cfg_name
            if src_cfg.exists() and not dst_cfg.exists():
                shutil.copy2(src_cfg, dst_cfg)

    agg_meta = {
        "num_cases": len(summary_rows),
        "cases": [r["case_id"] for r in summary_rows],
        "total_evaluations": sum(r["num_evaluations"] for r in summary_rows),
        "total_feasible": sum(r["num_feasible"] for r in summary_rows),
    }
    return agg_meta


def export_phase1_cases_latex_table(
    cases_summary_path: Union[str, Path],
    output_path: Union[str, Path],
) -> None:
    """
    Exports publication-grade LaTeX table of Phase 1 Option 2 cases.
    """
    summary_path = Path(cases_summary_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not summary_path.exists():
        return

    df = pd.read_csv(summary_path)

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Phase 1 Scalarized BO multi-case campaign summary across representative operational linac archetypes (Option 2). Fixed reporting reference point $\mathbf{r}_{\mathrm{rep}} = [6.65\times10^{-5},\,1.07\times10^{-4},\,3.37\times10^{6}]$ (physical, [m$\cdot$rad, m$\cdot$rad, eV]).}",
        r"\label{tab:phase1_cases}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llcccccc}",
        r"\toprule",
        r"\textbf{Case} & \textbf{Operating Mode} & $\mathbf{w} = [w_x, w_y, w_E]$ & \textbf{Evals} & \textbf{Feas. (\%)} & \textbf{Min} $\varepsilon_{n,x}$ [$\mu$m] & \textbf{Min} $\varepsilon_{n,y}$ [$\mu$m] & \textbf{Min} $\sigma_E$ [MeV] \\",
        r"\midrule",
    ]

    for _, row in df.iterrows():
        case_id = str(row["case_id"])
        name = str(row["name"])
        wx = float(row["w_emit_x"])
        wy = float(row["w_emit_y"])
        we = float(row["w_energy_spread"])
        w_str = f"$[{wx:.2f}, {wy:.2f}, {we:.2f}]$"
        n_eval = int(row["num_evaluations"])
        feas_str = f"{int(row['num_feasible'])} ({float(row['feasible_fraction_pct']):.1f}\\%)"
        min_ex = f"{float(row['min_norm_emit_x_um']):.4f}" if pd.notna(row['min_norm_emit_x_um']) else "-"
        min_ey = f"{float(row['min_norm_emit_y_um']):.4f}" if pd.notna(row['min_norm_emit_y_um']) else "-"
        min_se = f"{float(row['min_sigma_energy_MeV']):.4f}" if pd.notna(row['min_sigma_energy_MeV']) else "-"

        lines.append(
            f"\\texttt{{{case_id}}} & {name} & {w_str} & {n_eval} & {feas_str} & {min_ex} & {min_ey} & {min_se} \\\\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}}",
        r"\end{table}",
    ])

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_scalarized_suite(
    config: Union[str, Path] = "configs/mobo_200MeV.yaml",
    n_iterations: int = 20,
    batch_size: int = 8,
    num_initial_samples: int = 16,
    num_workers: Optional[int] = 4,
    seed: int = 42,
    output_dir: Union[str, Path] = "results/full_production/phase1_scalarized",
    device: str = "auto",
    cases_to_run: Optional[Sequence[str]] = None,
    resume: bool = False,
    evaluator: Optional[Any] = None,
    export_paper_table_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Executes the Option 2 multi-weight Phase 1 Scalarized BO suite.

    Args:
        config: Path to ASTRA/MOBO configuration YAML.
        n_iterations: BO iterations per case.
        batch_size: Candidate proposal batch size q per iteration.
        num_initial_samples: Sobol initialization points per case.
        num_workers: Parallel workers for ASTRA.
        seed: Random seed base (each case receives seed + case_index).
        output_dir: Base output directory (cases saved under subdirectories).
        device: PyTorch device ('auto', 'cuda', 'cpu').
        cases_to_run: List of case keys to run. Defaults to all keys in OPTION_2_CASES.
        resume: Whether to resume existing case runs from checkpoints.
        evaluator: Optional custom evaluator (e.g. CliMockEvaluator for testing).
        export_paper_table_dir: Optional directory to copy phase1_cases_table.tex to.

    Returns:
        Aggregation metadata dictionary.
    """
    base_out = Path(output_dir)
    base_out.mkdir(parents=True, exist_ok=True)

    if cases_to_run is None or len(cases_to_run) == 0:
        target_cases = list(OPTION_2_CASES.keys())
    else:
        target_cases = [c for c in cases_to_run if c in OPTION_2_CASES]
        if not target_cases:
            target_cases = list(OPTION_2_CASES.keys())

    print("======================================================================")
    print("  Phase 1 Option 2: Multi-Case Scalarized BO Suite")
    print("======================================================================")
    print(f"  Target Cases: {target_cases}")
    print(f"  Iterations per Case: {n_iterations} (Batch size q={batch_size})")
    print(f"  Initial Samples: {num_initial_samples}")
    print(f"  Base Output Directory: {base_out}")
    print("======================================================================\n")

    for idx, case_key in enumerate(target_cases):
        case_info = OPTION_2_CASES[case_key]
        case_dir = base_out / case_key
        case_seed = seed + idx * 100

        print(f"\n[{idx + 1}/{len(target_cases)}] Executing Case '{case_key}': {case_info['name']}")
        print(f"  - Weights [wx, wy, wE]: {case_info['weights']}")
        print(f"  - Output Dir: {case_dir}")

        runner = MoboCampaignRunner(
            config=str(config),
            run_name=f"scalarized_{case_key}",
            output_dir=case_dir,
            num_initial_samples=num_initial_samples,
            num_batches=n_iterations,
            batch_size=batch_size,
            num_workers=num_workers,
            seed=case_seed,
            optimization_mode="scalarized_bo",
            scalar_weights=case_info["weights"],
            resume=resume,
            export_plots=True,
            evaluator=evaluator,
            device=device,
        )
        runner.run()

    # Aggregate all completed cases into root base_out
    print("\n[Aggregating Option 2 Results across all cases...]")
    agg_meta = aggregate_scalarized_cases(base_out)
    print(f"  ✓ Aggregated {agg_meta['num_cases']} cases -> Total {agg_meta['total_evaluations']} evaluations")

    # Export local LaTeX table within base_out run directory
    local_tab = base_out / "phase1_cases_table.tex"
    export_phase1_cases_latex_table(base_out / "cases_summary.csv", local_tab)

    if export_paper_table_dir is not None:
        paper_tab = Path(export_paper_table_dir) / "phase1_cases_table.tex"
        export_phase1_cases_latex_table(base_out / "cases_summary.csv", paper_tab)
        print(f"  ✓ Exported LaTeX summary table to {paper_tab}")

    return agg_meta
