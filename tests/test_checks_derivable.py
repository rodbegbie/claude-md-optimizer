from pathlib import Path

from claude_md import checks  # noqa: F401
from claude_md.checks.derivable import derivable_content
from claude_md.discovery import discover
from claude_md.findings import REGISTRY, Context, run_checks
from claude_md.model import LoadedFile, LoadMode, Scope

CTX = Context(Path("/p"), Path("/h"))
DOCS = "https://code.claude.com/docs/en/best-practices"
FIXTURES = Path(__file__).parent / "fixtures"
BANNED = ["per request", "every request", "each request", "per turn", "turns"]
BANNED += ["compound", "session cost"]


def make(text: str, mode: LoadMode = LoadMode.ALWAYS) -> LoadedFile:
    return LoadedFile(Path("/p/CLAUDE.md"), Scope.PROJECT, mode, 0, text, text)


TREE = """# Project

```text
app/
├── __init__.py
├── models.py
└── routes.py
```
"""


def test_registered_with_docs_source():
    assert REGISTRY["derivable-content"].source.kind == "docs"
    assert REGISTRY["derivable-content"].source.url == DOCS


def test_flags_directory_tree():
    found = derivable_content([make(TREE)], CTX)
    assert len(found) == 1
    assert found[0].check_id == "derivable-content"
    assert found[0].line == 3
    assert "directory tree" in found[0].message
    assert "read this from the code or config" in found[0].message
    assert "approval" in found[0].fix
    assert found[0].source.url == DOCS
    assert not any(b in found[0].message.lower() for b in BANNED)


def test_flags_indented_path_tree():
    text = "```\nsrc/\n  app/\n    main.py\n    util.py\n  tests/\n```\n"
    found = derivable_content([make(text)], CTX)
    assert len(found) == 1
    assert "directory tree" in found[0].message


def test_flags_dependency_list():
    text = "# Deps\n\n- flask 3.0.3\n- jinja2 3.1.4\n- pytest==8.3.2\n"
    text += "- ruff 0.6.2\n- alembic >=1.13.2\n"
    found = derivable_content([make(text)], CTX)
    assert len(found) == 1
    assert found[0].line == 3
    assert "dependency list" in found[0].message


def test_short_dependency_list_ignored():
    text = "- flask 3.0.3\n- jinja2 3.1.4\n- pytest 8.3.2\n"
    assert derivable_content([make(text)], CTX) == []


def test_flags_long_architecture_section_of_list_items():
    items = "\n".join(f"- `mod{i}.py`: does thing {i}" for i in range(11))
    text = f"# P\n\n## Architecture\n\n{items}\n\n## Next\n\nx\n"
    found = derivable_content([make(text)], CTX)
    assert len(found) == 1
    assert found[0].line == 3
    assert "Architecture" in found[0].message


def test_short_architecture_section_ignored():
    items = "\n".join(f"- `mod{i}.py`: does thing {i}" for i in range(4))
    text = f"## Architecture\n\n{items}\n"
    assert derivable_content([make(text)], CTX) == []


def test_architecture_prose_mention_ignored():
    text = "Keep the architecture simple.\n" * 12
    assert derivable_content([make(text)], CTX) == []


def test_ignores_short_command_block():
    text = "```bash\nuv run pytest\nuv run ruff check .\nuv run ruff format .\n```\n"
    assert derivable_content([make(text)], CTX) == []


def test_ignores_table_and_command_list():
    text = "| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n| 5 | 6 |\n"
    text += "\n".join(f"- run `cmd{i} --flag`" for i in range(6)) + "\n"
    assert derivable_content([make(text)], CTX) == []


def test_only_loaded_files():
    assert derivable_content([make(TREE, LoadMode.ON_DEMAND)], CTX) == []


def run_fixture(name: str, tmp_path: Path) -> set[str]:
    project = FIXTURES / name / "project"
    home = tmp_path / "home"
    home.mkdir()
    managed = tmp_path / "managed"
    files = discover(project, home, managed)
    return {f.check_id for f in run_checks(files, Context(project, home))}


def test_fixture_derivable_tree_includes_id(tmp_path):
    assert "derivable-content" in run_fixture("derivable-tree", tmp_path)


def test_fixtures_excluding_id_do_not_flag(tmp_path):
    import json

    for expected in FIXTURES.glob("*/expected.json"):
        data = json.loads(expected.read_text())
        if "derivable-content" in data["must_exclude"]:
            ids = run_fixture(expected.parent.name, tmp_path)
            assert "derivable-content" not in ids, expected.parent.name


def test_repo_agents_md_not_flagged():
    path = Path(__file__).parent.parent / "AGENTS.md"
    text = path.read_text()
    assert derivable_content([make(text)], CTX) == []
