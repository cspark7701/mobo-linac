"""Relative links in the versioned Markdown documentation resolve to existing files."""

import re
import subprocess
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


def _ignored_by_git(paths):
    """Targets a fresh checkout lacks although they exist in this working tree."""
    if not paths:
        return set()
    try:
        result = subprocess.run(
            ["git", "check-ignore", "--stdin"], cwd=ROOT, input="\n".join(paths),
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return set()
    return set(result.stdout.splitlines()) if result.returncode in (0, 1) else set()


def test_relative_documentation_links_resolve():
    broken = []
    present = {}
    documents = list(_documents())
    unversioned = _ignored_by_git([d.relative_to(ROOT).as_posix() for d in documents])
    for document in documents:
        if document.relative_to(ROOT).as_posix() in unversioned:
            continue
        text = re.sub(r"```.*?```", "", document.read_text(encoding="utf-8"), flags=re.S)
        for target in LINK.findall(text):
            path = target.split("#", 1)[0]
            if not path or re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            resolved = (document.parent / path).resolve()
            if not resolved.exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")
            elif resolved.is_relative_to(ROOT) and resolved != ROOT:
                present.setdefault(resolved.relative_to(ROOT).as_posix(), []).append(f"{document.relative_to(ROOT)} -> {target}")
    ignored = _ignored_by_git(sorted(present))
    broken.extend(link for path in sorted(ignored) for link in present[path])
    assert broken == []


def test_no_legacy_tree_or_duplicate_site_sync():
    assert not (ROOT / "legacy").exists()
    assert not (ROOT / "scripts" / "sync_site.sh").exists()
    assert (ROOT / "tools" / "sync_site.py").exists()
