import re
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1] / "docs/paper"
# Revision-integration tags such as "% C05 ...", "% Q12 ...", "% R3-01 ..." or "% Integrate before ...".
TAG = re.compile(r"(?<!\\)%\s*(C\d{2}\b|C\d-\d{2}\b|Q\d{1,2}\b|R\d-\d{2}\b|T\d{1,2}\b|Integrate\b|Discussion limitation)")


def manuscript_sources() -> list[Path]:
    main = PAPER / "main.tex"
    sources = [main]
    for name in re.findall(r"\\(?:input|inputwide)\{([^}]*)\}", main.read_text()):
        path = PAPER / (name if name.endswith(".tex") else f"{name}.tex")
        if path.exists():
            sources.append(path)
    return sources


def test_manuscript_sources_have_no_revision_tag_comments():
    hits = [f"{path.name}:{n}" for path in manuscript_sources()
            for n, line in enumerate(path.read_text().splitlines(), 1) if TAG.search(line)]
    assert hits == []


def test_tag_pattern_matches_revision_comments_only():
    assert TAG.search("proposal and reported. % C05 replacement for the reference")
    assert TAG.search("% Integrate before the unchanged paragraph")
    assert not TAG.search(r"a \SI{95}{\percent} interval")
    assert not TAG.search("% Include a generated figure, or a visible placeholder")
