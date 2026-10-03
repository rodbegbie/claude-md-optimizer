from pathlib import Path

from claude_md.findings import Finding, Source
from claude_md.model import LoadedFile, LoadMode, Scope, Totals
from claude_md.report import render, to_json_data
from claude_md.scoring import Deduction, Score

DOCS = Source("docs", "https://code.claude.com/docs/en/memory")
HEURISTIC = Source("heuristic", None)
BANNED = [
    "per request",
    "every request",
    "each request",
    "per turn",
    "turns",
    "compound",
    "session cost",
]


def finding(check_id: str, source: Source, message: str) -> Finding:
    return Finding(
        check_id, "warning", Path("/p/CLAUDE.md"), 3, message, "do it", source
    )


SAMPLE = LoadedFile(
    Path("/p/CLAUDE.md"), Scope.PROJECT, LoadMode.ALWAYS, 1, "- a\n", "- a\n"
)


def render_with(findings, score, files=None, unverified=None):
    return render(
        files if files is not None else [SAMPLE],
        Totals(10, 20, 30),
        findings,
        score,
        unverified or [],
        Path("/p"),
        Path("/home/.claude/projects/-p/memory"),
        False,
    )


def test_report_groups_by_source():
    text = render_with(
        [
            finding("size-file", DOCS, "docs message"),
            finding("linter-rule", HEURISTIC, "heuristic message"),
        ],
        Score(95, []),
    )
    docs_at = text.index("Backed by Anthropic docs")
    heuristics_at = text.index("Heuristics")
    assert docs_at < text.index("docs message") < heuristics_at
    assert heuristics_at < text.index("heuristic message")
    assert DOCS.url in text[docs_at:heuristics_at]
    assert DOCS.url not in text[heuristics_at:]


def test_report_lists_every_deduction():
    deductions = [
        Deduction("size-file", 4, 9, True),
        Deduction("linter-rule", 1, 2, False),
    ]
    text = render_with([], Score(89, deductions))
    assert "size-file: 4 finding(s), -9 (capped)" in text
    assert "linter-rule: 1 finding(s), -2" in text
    assert "linter-rule: 1 finding(s), -2 (capped)" not in text
    assert "Score: 89/100" in text


def test_report_shows_context_memory_and_unverified():
    text = render_with([], Score(100, []), unverified=["COMBINED_LINES"])
    assert "Context load" in text
    assert "Always-on:   ~10" in text
    assert "Conditional: ~20" in text
    assert "On demand:   ~30" in text
    assert "Memory directory: /home/.claude/projects/-p/memory (not found)" in text
    assert "Unverified limits: COMBINED_LINES" in text


def test_report_omits_unverified_line_when_empty():
    assert "Unverified limits" not in render_with([], Score(100, []))


def test_report_for_empty_project():
    text = render_with([], Score(100, []), files=[])
    assert "No instruction files found for /p." in text
    assert "Memory directory:" in text
    assert "Score" not in text


def test_report_has_no_banned_phrases_or_rating_bands():
    text = render_with(
        [finding("size-file", DOCS, "m")],
        Score(91, [Deduction("size-file", 1, 3, False)]),
    ).lower()
    for phrase in [*BANNED, "rating:", "excellent"]:
        assert phrase not in text


def test_json_data_shape():
    data = to_json_data(
        [],
        Totals(1, 2, 3),
        [finding("size-file", DOCS, "m"), finding("linter-rule", HEURISTIC, "n")],
        Score(91, [Deduction("size-file", 1, 3, False)]),
        ["COMBINED_LINES"],
        Path("/m"),
        True,
    )
    assert set(data) == {
        "files",
        "totals",
        "findings",
        "score",
        "unverified",
        "memory_directory",
    }
    assert data["totals"] == {"always": 1, "conditional": 2, "on_demand": 3}
    assert data["score"] == {
        "value": 91,
        "deductions": [
            {"check_id": "size-file", "count": 1, "points": 3, "capped": False}
        ],
    }
    by_id = {f["check_id"]: f for f in data["findings"]}
    assert set(by_id["size-file"]) == {
        "check_id",
        "severity",
        "path",
        "line",
        "message",
        "fix",
        "source",
    }
    assert by_id["size-file"]["source"] == {"kind": "docs", "url": DOCS.url}
    assert by_id["linter-rule"]["source"] == {"kind": "heuristic", "url": None}
    assert by_id["size-file"]["path"] == "/p/CLAUDE.md"
    assert data["memory_directory"] == {"path": "/m", "found": True}


def test_report_adds_location_only_when_message_lacks_it():
    with_path = finding("size-file", DOCS, "/p/CLAUDE.md is long")
    without = finding("linter-rule", HEURISTIC, "too long")
    text = render_with([with_path, without], Score(90, []))
    assert "/p/CLAUDE.md is long (" not in text
    assert "too long (/p/CLAUDE.md:3)" in text
