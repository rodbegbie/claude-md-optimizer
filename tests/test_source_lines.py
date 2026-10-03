import re
from pathlib import Path

from claude_md import checks  # noqa: F401
from claude_md.discovery import discover
from claude_md.findings import Context, run_checks

COMMENT = "<!-- maintainer note\nspans three lines\nof comment -->\n"
COMMENT_LINES = 3

PROJECT = (
    "# Title\n"
    "\n"
    "- Follow best practices.\n"
    "- Use semicolons at the end of every statement.\n"
    "- Always run `ruff check` after each edit.\n"
    "- Never use tabs.\n"
    "\n"
    "A prose line that opens a paragraph here.\n"
    "A second prose line in the same paragraph.\n"
    "A third prose line in the same paragraph.\n"
    "\n"
    "```text\n"
    "code line 1\n"
    "code line 2\n"
    "code line 3\n"
    "code line 4\n"
    "code line 5\n"
    "code line 6\n"
    "```\n"
    "\n"
    "```text\n"
    "├── app\n"
    "│   ├── models.py\n"
    "│   └── views.py\n"
    "└── tests\n"
    "```\n"
    "\n"
    "## Rules\n"
    "\n"
    "- Keep every migration in a separate file with a clear name.\n"
    "- Keep every migration in a separate file with a clear name.\n"
    "\n"
    "See `missing/file.py` for the details.\n"
    "\n"
    "## Frontend\n"
    "\n"
    "- When editing `src/**` keep components small.\n"
    "- When working in `web/` use the design tokens.\n"
    "- When touching *.css files avoid deep nesting.\n"
    "\n"
    "## Imports\n"
    "\n"
    "We split this file into imports to save tokens.\n"
    "\n"
    "@docs/extra.md\n"
    "\n"
    "IMPORTANT: rule number 1 applies\n"
    "IMPORTANT: rule number 2 applies\n"
    "IMPORTANT: rule number 3 applies\n"
    "IMPORTANT: rule number 4 applies\n"
    "IMPORTANT: rule number 5 applies\n"
    "IMPORTANT: rule number 6 applies\n"
)
USER = "Always use tabs.\n"
RULE = (
    "---\n"
    "description: shared\n"
    "---\n"
    "- Keep every migration in a separate file with a clear name.\n"
)


def build(root: Path, comment: str) -> tuple[Path, Path, Path]:
    project = root / "project"
    (project / ".claude" / "rules").mkdir(parents=True)
    (project / "docs").mkdir()
    (project / "docs" / "extra.md").write_text("- extra\n")
    (project / "CLAUDE.md").write_text(comment + PROJECT)
    (project / ".claude" / "rules" / "dup.md").write_text(RULE)
    home = root / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "CLAUDE.md").write_text(comment + USER)
    return project, home, root


def findings(root: Path, comment: str):
    project, home, _ = build(root, comment)
    files = discover(project, home, None)
    return run_checks(files, Context(project, home)), project, home


def keyed(items, root: Path):
    return sorted(
        (f.check_id, str(f.path.relative_to(root)) if f.path else "", f.line or 0, f)
        for f in items
        if f.check_id != "duplicate-across"
    )


def test_every_line_reported_is_a_line_of_the_file_on_disk(tmp_path):
    plain, *_ = findings(tmp_path / "plain", "")
    commented, *_ = findings(tmp_path / "commented", COMMENT)
    plain_keys = keyed(plain, tmp_path / "plain")
    commented_keys = keyed(commented, tmp_path / "commented")

    assert {k[0] for k in plain_keys} >= {
        "vague-instruction",
        "linter-rule",
        "hook-candidate",
        "narrative-paragraph",
        "code-block-long",
        "derivable-content",
        "duplicate-within",
        "stale-reference",
        "scope-candidate",
        "import-misconception",
        "emphasis-dilution",
        "possible-conflict",
    }
    assert [(k[0], k[1]) for k in plain_keys] == [(k[0], k[1]) for k in commented_keys]
    for (check_id, rel, line, before), (_, _, shifted, after) in zip(
        plain_keys, commented_keys
    ):
        if line:
            assert shifted == line + COMMENT_LINES, (check_id, rel, line, shifted)
        numbers_before = [int(n) for n in re.findall(r"\.md:(\d+)", before.message)]
        numbers_after = [int(n) for n in re.findall(r"\.md:(\d+)", after.message)]
        assert numbers_after == [n + COMMENT_LINES for n in numbers_before], (
            check_id,
            before.message,
            after.message,
        )


def test_duplicate_across_points_at_the_line_on_disk_not_the_stripped_line(tmp_path):
    items, project, _ = findings(tmp_path, COMMENT)
    across = [f for f in items if f.check_id == "duplicate-across"]
    assert len(across) == 1
    claude = project / "CLAUDE.md"
    on_disk = (
        claude.read_text()
        .splitlines()
        .index("- Keep every migration in a separate file with a clear name.")
    )
    assert f"{claude}:{on_disk + 1}" in across[0].message, across[0].message


def test_rule_frontmatter_does_not_shift_reported_lines(tmp_path):
    project = tmp_path / "project"
    (project / ".claude" / "rules").mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    (project / ".claude" / "rules" / "r.md").write_text(
        "---\ndescription: x\n---\n\n\n- Follow best practices.\n"
    )
    files = discover(project, home, None)
    found = [
        f
        for f in run_checks(files, Context(project, home))
        if f.check_id == "vague-instruction"
    ]
    assert [f.line for f in found] == [6]
    assert "r.md:6" in found[0].message
