from pathlib import Path

from claude_md import checks  # noqa: F401
from claude_md.checks._common import loaded
from claude_md.checks.duplicates import duplicate_across, duplicate_within
from claude_md.checks.patterns import vague_instruction
from claude_md.checks.scope import import_misconception, scope_candidate
from claude_md.discovery import encode_project_path
from claude_md.findings import REGISTRY, Context
from claude_md.model import LoadedFile, LoadMode, Scope

CTX = Context(Path("/p"), Path("/h"))
LINE = "Always run the full test suite before committing"

ALL_CHECK_IDS = {
    "vague-instruction",
    "linter-rule",
    "narrative-paragraph",
    "code-block-long",
    "size-file",
    "size-memory",
    "size-always-on",
    "derivable-content",
    "hook-candidate",
    "emphasis-dilution",
    "possible-conflict",
    "duplicate-within",
    "duplicate-across",
    "no-trigger",
    "non-english",
    "stale-reference",
    "scope-candidate",
    "import-misconception",
}


def make(
    text: str,
    mode: LoadMode = LoadMode.ALWAYS,
    path: str = "/p/CLAUDE.md",
    scope: Scope = Scope.PROJECT,
) -> LoadedFile:
    return LoadedFile(Path(path), scope, mode, 0, text, text)


def import_text(sentence: str) -> str:
    return f"# P\n\n{sentence}\n\n@docs/conventions.md\n"


def test_all_check_ids_are_registered_by_importing_checks():
    assert set(REGISTRY) == ALL_CHECK_IDS


def test_loaded_includes_on_demand_but_not_memory_topics_or_excluded():
    nested = make("x", LoadMode.ON_DEMAND, "/p/s/CLAUDE.md", Scope.NESTED)
    topic = make("x", LoadMode.ON_DEMAND, "/m/t.md", Scope.MEMORY)
    index = make("x", LoadMode.ALWAYS, "/m/MEMORY.md", Scope.MEMORY)
    excluded = make("x", LoadMode.EXCLUDED)
    assert loaded([nested, topic, index, excluded]) == [nested, index]


def nested_project(tree):
    filler = "\n".join(f"- Rule number {i} is distinct." for i in range(300))
    return tree(
        {
            "project/CLAUDE.md": "# Root\n\n- Run tests.\n",
            "project/sub/CLAUDE.md": (
                "# Sub\n\n- Follow best practices.\n"
                "- See `missing/file.py` for details.\n" + filler + "\n"
            ),
        }
    )


def test_cli_checks_nested_claude_md(tree, run_cli):
    findings = run_cli(nested_project(tree) / "project")["findings"]
    nested = {f["check_id"] for f in findings if f["path"].endswith("sub/CLAUDE.md")}
    assert {"size-file", "vague-instruction", "stale-reference"} <= nested


def test_cli_does_not_check_memory_topic_files(tree, run_cli, tmp_path):
    project = tree({"project/CLAUDE.md": "# Root\n\n- Run tests.\n"}) / "project"
    memory = (
        tmp_path
        / "home"
        / ".claude"
        / "projects"
        / encode_project_path(project.resolve())
        / "memory"
    )
    memory.mkdir(parents=True)
    (memory / "MEMORY.md").write_text("- [topic](topic.md) - notes\n")
    filler = "\n".join(f"- Note {i} is distinct." for i in range(300))
    (memory / "topic.md").write_text("Follow best practices.\n" + filler + "\n")
    result = run_cli(project)
    assert any(f["path"].endswith("topic.md") for f in result["files"])
    assert not [f for f in result["findings"] if f["path"].endswith("topic.md")]


def test_cli_wrapper_registers_conflict_duplicate_and_trigger_checks(tree, run_cli):
    body = "\n".join(f"- Distinct rule {i}." for i in range(90))
    repeat = "- Run the full test suite before every commit please\n"
    root = tree(
        {
            "home/.claude/CLAUDE.md": "- Always use tabs.\n",
            "project/CLAUDE.md": (f"# Root\n\n- Never use tabs.\n{repeat * 2}{body}\n"),
        }
    )
    ids = {f["check_id"] for f in run_cli(root / "project")["findings"]}
    assert {"possible-conflict", "duplicate-within", "no-trigger"} <= ids


def test_duplicate_across_ignores_on_demand_files():
    files = [
        make(LINE + "\n"),
        make(LINE + "\n", LoadMode.ON_DEMAND, "/p/sub/CLAUDE.md", Scope.NESTED),
    ]
    assert duplicate_across(files, CTX) == []


def test_duplicate_within_checks_on_demand_files():
    nested = make(f"{LINE}\n{LINE}\n", LoadMode.ON_DEMAND, "/p/s/CLAUDE.md")
    assert duplicate_within([nested], CTX)


def test_scope_candidate_stays_always_only():
    text = "## UI\n" + "".join(f"- When editing `src/{c}/*.ts` do x\n" for c in "abc")
    assert scope_candidate([make(text)], CTX)
    assert scope_candidate([make(text, LoadMode.ON_DEMAND)], CTX) == []


def test_scope_candidate_message_says_loads_at_launch():
    text = "## UI\n" + "".join(f"- When editing `src/{c}/*.ts` do x\n" for c in "abc")
    message = scope_candidate([make(text)], CTX)[0].message
    assert "loads at launch" in message
    assert "every task" not in message


def test_import_negated_statements_are_not_flagged():
    for sentence in (
        "Imports do not save tokens, so keep this file short.",
        "Imports don't reduce context.",
        "Imports never cut tokens.",
        "Imports cannot reduce context at all.",
        "Imports without saving tokens are fine.",
    ):
        assert import_misconception([make(import_text(sentence))], CTX) == [], sentence


def test_import_positive_statements_still_flagged():
    for sentence in (
        "Splitting into imports to save tokens.",
        "Use imports to reduce context.",
        "We use imports so we cut tokens.",
    ):
        assert len(import_misconception([make(import_text(sentence))], CTX)) == 1, (
            sentence
        )


TABLE = "| a | b | c | d |\n| --- | --- | --- | --- |\n| 1 | 2 | 3 | 4 |\n"


def test_table_delimiter_rows_are_not_duplicates():
    text = f"{TABLE}\ntext\n\n| w | x | y | z |\n| --- | --- | --- | --- |\n"
    assert duplicate_within([make(text)], CTX) == []
    both = [make(TABLE), make(TABLE, path="/p/b.md")]
    assert not [f for f in duplicate_across(both, CTX) if "---" in f.message]


def test_horizontal_rules_are_not_duplicates():
    text = "-" * 30 + "\nx\n" + "-" * 30 + "\n"
    assert duplicate_within([make(text)], CTX) == []


def test_fenced_repeats_are_not_duplicates():
    block = f"```\n{LINE}\n```\n"
    assert duplicate_within([make(block + "\n" + block)], CTX) == []
    across = duplicate_across(
        [make(block), make(block, path="/p/b.md")],
        CTX,
    )
    assert across == []


def test_real_repeated_prose_line_still_flagged():
    assert duplicate_within([make(f"{LINE}\n\n{LINE}\n")], CTX)
    both = [make(f"{LINE} now\n"), make(f"{LINE} now\n", path="/p/b.md")]
    assert duplicate_across(both, CTX)


def test_duplicate_within_message_grammar():
    one = duplicate_within([make(f"{LINE}\n{LINE}\n")], CTX)[0].message
    other = "Second repeated line here ok"
    many = duplicate_within([make(f"{LINE}\n{LINE}\n{other}\n{other}\n")], CTX)[
        0
    ].message
    assert "1 duplicated line " in one
    assert "2 duplicated lines " in many


def test_vague_one_finding_per_line():
    text = "Try to keep code clean and follow best practices\n"
    assert len(vague_instruction([make(text)], CTX)) == 1
