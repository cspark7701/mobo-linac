"""
Unit test for Documentation and Web Page Synchronization (Task 32).
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from mobo_linac.config import load_config
from scripts.verify_docs_sync import verify_html_sync, verify_latex_sync


def test_docs_and_web_sync():
    """Verify that docs/index.html, docs/site/index.html, and consolidated_report.tex match configs/mobo_200MeV.yaml."""
    config_path = root_dir / "configs" / "mobo_200MeV.yaml"
    html_path = root_dir / "docs" / "index.html"
    site_html_path = root_dir / "docs" / "site" / "index.html"
    tex_path = root_dir / "docs" / "consolidated_report" / "consolidated_report.tex"

    config = load_config(config_path)

    html_errors = verify_html_sync(config, html_path.read_text())
    assert not html_errors, f"HTML sync errors found: {html_errors}"

    site_html_errors = verify_html_sync(config, site_html_path.read_text())
    assert not site_html_errors, f"Site HTML sync errors found: {site_html_errors}"

    tex_errors = verify_latex_sync(config, tex_path.read_text())
    assert not tex_errors, f"LaTeX sync errors found: {tex_errors}"
