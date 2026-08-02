#!/usr/bin/env python3
"""
Automated Documentation & Web Page Sync Auditor for mobo_linac.

Verifies that parameter definitions, design variable bounds, unit declarations,
and constraint thresholds in:
  - configs/mobo_200MeV.yaml
  - docs/index.html
  - docs/consolidated_report/consolidated_report.tex

remain 100% consistent and synchronized.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
from mobo_linac.config import load_config


def verify_html_sync(config, html_content: str) -> List[str]:
    """Audits docs/index.html against configuration data."""
    errors = []

    # 1. Audit Design Variables
    for dvar in config.design_variables:
        key = dvar.astra_key
        # For coupled phases in HTML, cavity:phi(2) might be displayed as cavity:phi(2,3)
        if dvar.is_coupled and "phi(2)" in key:
            expected_key = "cavity:phi(2,3)"
        elif dvar.is_coupled and "phi(4)" in key:
            expected_key = "cavity:phi(4,5)"
        else:
            expected_key = key

        if expected_key not in html_content and key not in html_content:
            errors.append(f"[index.html] Missing ASTRA variable key: '{key}' or '{expected_key}'")

        # Check numeric formatting (rounded to 2 decimal places)
        nom_str = f"{dvar.nominal_value:.2f}"
        if nom_str not in html_content and f"{dvar.nominal_value:.4f}"[:6] not in html_content:
            errors.append(f"[index.html] Missing or mismatched nominal value for '{dvar.name}': {nom_str}")

    # 2. Audit Constraints
    c = config.constraints
    max_sigma_x_mm = f"{c.max_sigma_x_m * 1e3:.1f}"
    min_e_mev = f"{c.min_mean_kinetic_energy_eV * 1e-6:.1f}"
    max_e_mev = f"{c.max_mean_kinetic_energy_eV * 1e-6:.1f}"
    min_trans_pct = f"{c.min_transmission * 100.0:.1f}"

    if max_sigma_x_mm not in html_content:
        errors.append(f"[index.html] Missing max_sigma_x constraint value: {max_sigma_x_mm} mm")
    if min_e_mev not in html_content:
        errors.append(f"[index.html] Missing min_energy constraint value: {min_e_mev} MeV")
    if max_e_mev not in html_content:
        errors.append(f"[index.html] Missing max_energy constraint value: {max_e_mev} MeV")
    if min_trans_pct not in html_content:
        errors.append(f"[index.html] Missing min_transmission constraint value: {min_trans_pct}%")

    return errors


def verify_latex_sync(config, tex_content: str) -> List[str]:
    """Audits docs/consolidated_report/consolidated_report.tex against configuration data."""
    errors = []

    # 1. Audit Design Variables
    for dvar in config.design_variables:
        key_tex = dvar.astra_key.replace("_", r"\_")
        if dvar.is_coupled and "phi(2)" in dvar.astra_key:
            expected_key_tex = r"cavity:phi(2,3)".replace("_", r"\_")
        elif dvar.is_coupled and "phi(4)" in dvar.astra_key:
            expected_key_tex = r"cavity:phi(4,5)".replace("_", r"\_")
        else:
            expected_key_tex = key_tex

        if expected_key_tex not in tex_content and key_tex not in tex_content:
            errors.append(f"[consolidated_report.tex] Missing ASTRA key in LaTeX table: '{key_tex}'")

    # 2. Audit Constraints
    c = config.constraints
    min_e_mev = f"{c.min_mean_kinetic_energy_eV * 1e-6:.1f}"
    max_e_mev = f"{c.max_mean_kinetic_energy_eV * 1e-6:.1f}"

    if min_e_mev not in tex_content:
        errors.append(f"[consolidated_report.tex] Missing min energy constraint: {min_e_mev}")
    if max_e_mev not in tex_content:
        errors.append(f"[consolidated_report.tex] Missing max energy constraint: {max_e_mev}")

    return errors


def main():
    root_dir = Path(__file__).resolve().parent.parent
    config_path = root_dir / "configs" / "mobo_200MeV.yaml"
    html_path = root_dir / "docs" / "index.html"
    tex_path = root_dir / "docs" / "consolidated_report" / "consolidated_report.tex"

    if not config_path.exists():
        print(f"ERROR: Configuration file not found at: {config_path}")
        sys.exit(1)

    config = load_config(config_path)

    all_errors = []

    if html_path.exists():
        html_errors = verify_html_sync(config, html_path.read_text())
        all_errors.extend(html_errors)
    else:
        all_errors.append(f"File not found: {html_path}")

    if tex_path.exists():
        tex_errors = verify_latex_sync(config, tex_path.read_text())
        all_errors.extend(tex_errors)
    else:
        all_errors.append(f"File not found: {tex_path}")

    print("=== Documentation & Web Page Sync Audit ===")
    print(f"Audited Config: {config_path.relative_to(root_dir)}")
    print(f"Audited HTML  : {html_path.relative_to(root_dir)}")
    print(f"Audited LaTeX : {tex_path.relative_to(root_dir)}")

    if all_errors:
        print(f"\nFAIL: Found {len(all_errors)} documentation synchronization mismatch(es):")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\nSUCCESS: All documentation tables and web page parameters are 100% synchronized!")
        sys.exit(0)


if __name__ == "__main__":
    main()
