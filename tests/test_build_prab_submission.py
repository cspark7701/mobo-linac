import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_prab_submission as submission  # noqa: E402

MAIN = r"""\documentclass[aps,prab,reprint]{revtex4-2}
\newcommand{\inputwide}[1]{\input{#1}}
\begin{document}
\datafigure{figures/a.pdf}{\linewidth}
\inputwide{table_a}
\IfFileExists{table_b.tex}{\inputwide{table_b}}{\pendingtable{table_b}{Caption {B}.}{tab:b}}
\IfFileExists{absent.tex}{\inputwide{absent}}{\pendingtable{absent}{Absent.}{tab:c}}
% \inputwide{commented}
\bibliography{references}
\end{document}
"""


def paper(tmp_path):
    (tmp_path / "figures").mkdir(parents=True)
    (tmp_path / "figures/a.pdf").write_bytes(b"%PDF")
    (tmp_path / "main.tex").write_text(MAIN)
    (tmp_path / "table_a.tex").write_text("\\begin{table}[htbp]A\\end{table}\n")
    (tmp_path / "table_b.tex").write_text("\\begin{table}B\\end{table}\n")
    (tmp_path / "main.bbl").write_text("\\begin{thebibliography}{1}\\end{thebibliography}\n")
    return tmp_path


def test_flatten_inlines_tables_figures_and_bibliography(tmp_path):
    flat, figures = submission.flatten(paper(tmp_path))
    assert r"\begin{table*}[htbp]A\end{table*}" in flat and r"\begin{table*}B\end{table*}" in flat
    assert r"\pendingtable{absent}{Absent.}{tab:c}" in flat and "table_b}{Caption" not in flat
    assert r"\datafigure{a.pdf}{\linewidth}" in flat and figures == [tmp_path / "figures/a.pdf"]
    assert r"\begin{thebibliography}" in flat and r"\bibliography{" not in flat
    assert r"% \inputwide{commented}" in flat


def test_flatten_rejects_missing_inputs(tmp_path):
    root = paper(tmp_path)
    (root / "figures/a.pdf").unlink()
    with pytest.raises(FileNotFoundError):
        submission.flatten(root)
    (root / "main.tex").write_text(MAIN.replace(r"\inputwide{table_a}", r"\input{table_a}"))
    with pytest.raises(ValueError):
        submission.flatten(root)
    with pytest.raises(ValueError):
        submission.group("x{", 0)
    with pytest.raises(ValueError):
        submission.group("{{}", 0)


def test_build_writes_the_folder_and_manifest(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.txt").write_text("old")
    record = submission.build(paper(tmp_path / "paper"), out, archive=False)
    assert sorted(record["files"]) == ["a.pdf", "manuscript.tex"]
    assert json.loads((out / "submission_manifest.json").read_text()) == record


def test_main_archives_head_without_the_reviews(tmp_path, monkeypatch):
    monkeypatch.setattr(submission, "PAPER", paper(tmp_path / "paper"))
    compiled = []
    monkeypatch.setattr(submission, "compile_copy", compiled.append)
    assert submission.main(["--output-dir", str(tmp_path / "out"), "--compile"]) == 0
    record = json.loads((tmp_path / "out/submission_manifest.json").read_text())
    assert record["commit"] == submission.git("rev-parse", "HEAD")
    assert record["supplement_excludes"] == ["docs/paper/reviews"] and "supplement_S1.zip" in record["files"]
    assert compiled == [tmp_path / "out"]
