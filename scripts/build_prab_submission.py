#!/usr/bin/env python3
"""Write the flat PRAB upload folder for the manuscript.

APS takes the manuscript as one LaTeX file with its figures in the same folder. This script
reads ``docs/paper/main.tex`` and its last build's ``main.bbl`` and writes, by default to
``build/prab_submission/``:

* ``manuscript.tex``: the manuscript with every generated table (``\\inputwide``) and the
  bibliography inlined; ``\\IfFileExists`` placeholders resolve to the existing file;
* the cited figures, without subdirectories;
* ``supplement_S1.zip``: the Supplemental Material, a ``git archive`` of the committed
  snapshot without the referee correspondence in ``docs/paper/reviews/``;
* ``submission_manifest.json``: the commit, whether the working tree was clean, and the size
  and SHA-256 of every written file.

``--compile`` builds ``manuscript.tex`` in the folder to check that it is self-contained.
Nothing is uploaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "docs/paper"
OUTPUT = ROOT / "build/prab_submission"
EXCLUDED = ("docs/paper/reviews",)


def group(text: str, start: int) -> int:
    """Index just past the balanced brace group that opens at ``start``."""
    if text[start] != "{":
        raise ValueError(f"expected '{{' at offset {start}")
    depth = 0
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return i + 1
    raise ValueError(f"unbalanced group at offset {start}")


def arguments(text: str, start: int, count: int) -> tuple[list[str], int]:
    """The ``count`` brace arguments that follow ``start`` and the index after them."""
    args = []
    for _ in range(count):
        while text[start].isspace():
            start += 1
        end = group(text, start)
        args.append(text[start + 1:end - 1])
        start = end
    return args, start


def replace_command(text: str, name: str, count: int, render) -> str:
    """Replace each ``\\name{..}..`` with ``render(args)``."""
    out, pos = [], 0
    pattern = re.compile(re.escape("\\" + name) + r"(?![A-Za-z])")
    while match := pattern.search(text, pos):
        line = text[text.rfind("\n", 0, match.start()) + 1:match.start()]
        if re.search(r"(?<!\\)%", line):
            out.append(text[pos:match.end()])  # inside a comment
            pos = match.end()
            continue
        args, end = arguments(text, match.end(), count)
        out.append(text[pos:match.start()] + render(args))
        pos = end
    return "".join(out) + text[pos:]


def cited_keys(text: str) -> set[str]:
    """The citation keys of every ``\\cite``-family command outside comments."""
    text = re.sub(r"(?<!\\)%.*", "", text)
    groups = re.findall(r"\\cite[A-Za-z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}", text)
    return {key.strip() for keys in groups for key in keys.split(",") if key.strip()}


def bibitem_keys(bbl: str) -> set[str]:
    """The keys of the ``\\bibitem`` entries in a ``.bbl`` file."""
    keys = set()
    for match in re.finditer(r"\\bibitem(?![A-Za-z])", bbl):
        pos = match.end()
        while bbl[pos].isspace():
            pos += 1
        if bbl[pos] == "[":  # optional label, which may hold braces and brackets
            depth = 0
            while not (bbl[pos] == "]" and depth == 0):
                depth += {"{": 1, "}": -1}.get(bbl[pos], 0)
                pos += 1
            pos += 1
            while bbl[pos].isspace():
                pos += 1
        keys.add(bbl[pos + 1:group(bbl, pos) - 1].strip())
    return keys


def wide_table(paper: Path, name: str) -> str:
    """A generated table as a page-wide float, as ``\\inputwide`` sets it."""
    body = (paper / f"{name}.tex").read_text().rstrip("\n")
    body = re.sub(r"\\(begin|end)\{table\}", r"\\\1{table*}", body)
    return f"% Inlined from {name}.tex\n{body}"


def flatten(paper: Path) -> tuple[str, list[Path]]:
    """The self-contained manuscript text and the figure files it cites."""
    text = (paper / "main.tex").read_text()
    body = text.index("\\begin{document}")
    head, text = text[:body], text[body:]
    text = replace_command(text, "IfFileExists", 3,
                           lambda a: a[1] if (paper / a[0]).exists() else a[2])
    text = replace_command(text, "inputwide", 1, lambda a: wide_table(paper, a[0]))
    figures = []

    def figure(args):
        figures.append(paper / args[0])
        return f"\\datafigure{{{Path(args[0]).name}}}{{{args[1]}}}"

    text = replace_command(text, "datafigure", 2, figure)
    bbl = (paper / "main.bbl").read_text().rstrip("\n")
    stale = sorted(cited_keys(text) - bibitem_keys(bbl))
    if stale:
        raise ValueError(f"main.bbl lacks cited keys {stale}; rebuild it with "
                         "latexmk -cd -pdf docs/paper/main.tex")
    text = replace_command(text, "bibliography", 1, lambda a: f"% Inlined from main.bbl\n{bbl}")
    flat = head + text
    if re.search(r"^[^%\n]*\\(input|include|bibliography)\{", text, re.M):
        raise ValueError("an unresolved \\input, \\include or \\bibliography remains")
    missing = [str(f) for f in figures if not f.exists()]
    if missing:
        raise FileNotFoundError(f"missing figures: {missing}")
    if len({f.name for f in figures}) != len(set(figures)):
        raise ValueError("two figures share a file name")
    return flat, sorted(set(figures))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(paper: Path, out: Path, archive: bool = True) -> dict:
    flat, figures = flatten(paper)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "manuscript.tex").write_text(flat)
    for path in figures:
        shutil.copy2(path, out / path.name)
    record = {"manuscript": "docs/paper/main.tex", "bibliography": "docs/paper/main.bbl"}
    if archive:
        commit = git("rev-parse", "HEAD")
        subprocess.run(["git", "archive", "--format=zip", f"--output={out / 'supplement_S1.zip'}",
                        "HEAD", "--", ".", *(f":(exclude){p}" for p in EXCLUDED)],
                       cwd=ROOT, check=True)
        record |= {"commit": commit, "clean_working_tree": git("status", "--porcelain") == "",
                   "supplement_excludes": list(EXCLUDED)}
    record["files"] = {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)}
                       for p in sorted(out.iterdir())}
    (out / "submission_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def compile_copy(out: Path) -> None:
    """Build manuscript.tex in a scratch copy of the folder, so that it stays upload-only."""
    scratch = out.parent / f"{out.name}_check"
    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(out, scratch, ignore=shutil.ignore_patterns("*.zip", "*.json"))
    subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
                    "manuscript.tex"], cwd=scratch, check=True, capture_output=True)
    log = (scratch / "manuscript.log").read_text(errors="replace")
    if re.search(r"(Citation|Reference) .* undefined", log):
        raise RuntimeError(f"undefined references in {scratch / 'manuscript.log'}")
    print(f"compiled {scratch / 'manuscript.pdf'}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--compile", action="store_true", help="build the flat copy as a check")
    args = parser.parse_args(argv)
    record = build(PAPER, args.output_dir)
    if not record["clean_working_tree"]:
        print("warning: the working tree has uncommitted changes; supplement_S1.zip holds HEAD")
    if args.compile:
        compile_copy(args.output_dir)
    print(f"wrote {len(record['files'])} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
