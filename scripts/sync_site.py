#!/usr/bin/env python3
"""
Automated Site Sync & Export Script for mobo-linac.github.io.

Synchronizes isolated web files into `docs/site/` and optionally deploys
or copies them to a standalone `mobo-linac.github.io` repository directory.

Usage:
    # Sync internal docs/site/ directory:
    python scripts/sync_site.py

    # Sync and copy to external mobo-linac.github.io repository:
    python scripts/sync_site.py --target-repo /path/to/mobo-linac.github.io
"""

import argparse
import shutil
import sys
from pathlib import Path


def sync_site_files(root_dir: Path, target_repo: Path = None) -> bool:
    """
    Syncs website assets from docs/ to docs/site/ and optionally to target_repo.
    """
    docs_dir = root_dir / "docs"
    site_dir = docs_dir / "site"

    site_dir.mkdir(parents=True, exist_ok=True)
    report_target_dir = site_dir / "consolidated_report"
    report_target_dir.mkdir(parents=True, exist_ok=True)

    print("=== Synchronizing mobo_linac Web Portal into docs/site/ ===")

    # 1. Sync index.html
    src_html = docs_dir / "index.html"
    dst_html = site_dir / "index.html"
    if src_html.exists():
        shutil.copy2(src_html, dst_html)
        print(f"  ✓ Copied {src_html.relative_to(root_dir)} -> {dst_html.relative_to(root_dir)}")

    # 2. Sync style.css
    src_css = docs_dir / "style.css"
    dst_css = site_dir / "style.css"
    if src_css.exists():
        shutil.copy2(src_css, dst_css)
        print(f"  ✓ Copied {src_css.relative_to(root_dir)} -> {dst_css.relative_to(root_dir)}")

    # 3. Sync .nojekyll
    nojekyll = site_dir / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.touch()
        print(f"  ✓ Created {nojekyll.relative_to(root_dir)}")

    # 4. Sync consolidated_report.pdf
    src_pdf = docs_dir / "consolidated_report" / "consolidated_report.pdf"
    dst_pdf = report_target_dir / "consolidated_report.pdf"
    if src_pdf.exists():
        shutil.copy2(src_pdf, dst_pdf)
        print(f"  ✓ Copied {src_pdf.relative_to(root_dir)} -> {dst_pdf.relative_to(root_dir)}")
    else:
        print(f"  ⚠ Warning: Source PDF not found at {src_pdf.relative_to(root_dir)}")

    # 5. Copy to target repo if specified
    if target_repo is not None:
        target_path = Path(target_repo).resolve()
        print(f"\n=== Deploying site files to external repository: {target_path} ===")
        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created directory: {target_path}")

        for item in site_dir.iterdir():
            dest = target_path / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
                print(f"  ✓ Copied directory: {item.name}/ -> {dest}")
            else:
                shutil.copy2(item, dest)
                print(f"  ✓ Copied file: {item.name} -> {dest}")

        print(f"  ✓ Successfully deployed all site files to {target_path}")

    print("\nSUCCESS: docs/site/ synchronization complete.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Sync website files into docs/site/ and optional mobo-linac.github.io repo.")
    parser.add_argument("--target-repo", type=Path, default=None, help="Path to standalone mobo-linac.github.io repository directory.")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    sync_site_files(root_dir, target_repo=args.target_repo)


if __name__ == "__main__":
    main()
