"""Relative links in the versioned Markdown documentation resolve to existing files."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
UNVERSIONED = re.compile(r"^docs/0\d_")  # local planning folders (git-ignored)


def _documents():
    yield from (ROOT / name for name in ("README.md", "AGENTS.md", "INSTALL.md", "REPRODUCIBILITY.md", "CHANGELOG.md"))
    for path in sorted((ROOT / "docs").rglob("*.md")):
        if not UNVERSIONED.match(path.relative_to(ROOT).as_posix()):
            yield path
    yield ROOT / "tools" / "README.md"


def test_relative_documentation_links_resolve():
    broken = []
    for document in _documents():
        text = re.sub(r"```.*?```", "", document.read_text(encoding="utf-8"), flags=re.S)
        for target in LINK.findall(text):
            path = target.split("#", 1)[0]
            if not path or re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            if not (document.parent / path).exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")
    assert broken == []


def test_no_legacy_tree_or_duplicate_site_sync():
    assert not (ROOT / "legacy").exists()
    assert not (ROOT / "scripts" / "sync_site.sh").exists()
    assert (ROOT / "tools" / "sync_site.py").exists()
