from pathlib import Path

from claude_md import checks  # noqa: F401
from claude_md.checks.size import size_always_on, size_file, size_memory
from claude_md.discovery import discover, memory_dir
from claude_md.findings import REGISTRY, Context
from claude_md.model import LoadedFile, LoadMode, Scope

CTX = Context(Path("/p"), Path("/h"))
DOCS = "https://code.claude.com/docs/en/memory"
BANNED = ["per request", "every request", "each request", "per turn", "turns"]
BANNED += ["compound", "session cost"]


def make(
    lines: int, mode: LoadMode = LoadMode.ALWAYS, name: str = "CLAUDE.md"
) -> LoadedFile:
    text = "x\n" * lines
    return LoadedFile(Path("/p") / name, Scope.PROJECT, mode, 0, text, text)


def test_registered_with_expected_sources():
    assert REGISTRY["size-file"].source.kind == "docs"
    assert REGISTRY["size-file"].source.url == DOCS
    assert REGISTRY["size-memory"].source.url == DOCS
    assert REGISTRY["size-always-on"].source.kind == "heuristic"


def test_size_file_flags_201_lines():
    found = size_file([make(201)], CTX)
    assert len(found) == 1
    assert found[0].check_id == "size-file"
    assert "201 lines" in found[0].message
    assert "1 over" in found[0].message
    assert "recommend" in found[0].message
    assert found[0].source.url == DOCS


def test_size_file_ok_at_200_lines():
    assert size_file([make(200)], CTX) == []


def test_size_file_covers_conditional_and_skips_excluded():
    assert len(size_file([make(250, LoadMode.CONDITIONAL)], CTX)) == 1
    assert size_file([make(250, LoadMode.EXCLUDED)], CTX) == []


def write_memory(tmp_path: Path, content: str) -> list[LoadedFile]:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    index = memory_dir(repo.resolve(), home) / "MEMORY.md"
    index.parent.mkdir(parents=True)
    index.write_text(content)
    return [f for f in discover(repo, home) if f.scope == Scope.MEMORY]


def test_size_memory_flags_bytes_only(tmp_path):
    files = write_memory(tmp_path, ("y" * 999 + "\n") * 30)
    assert len(files[0].raw.splitlines()) == 30
    assert files[0].lines < 200
    found = size_memory(files, CTX)
    assert len(found) == 1
    assert "bytes" in found[0].message
    assert "lines" not in found[0].message
    assert found[0].source.url == DOCS


def test_size_memory_judges_size_before_truncation(tmp_path):
    files = write_memory(tmp_path, "x\n" * 300)
    assert files[0].lines == 200
    found = size_memory(files, CTX)
    assert len(found) == 1
    assert "300 lines" in found[0].message
    assert "100 over" in found[0].message


def test_size_memory_ok_when_within_limits(tmp_path):
    assert size_memory(write_memory(tmp_path, "x\n" * 200), CTX) == []


def test_size_memory_ignores_other_files():
    assert size_memory([make(500)], CTX) == []


def test_size_always_on_message_says_unverified():
    found = size_always_on([make(300), make(250, name="b.md")], CTX)
    assert len(found) == 1
    assert found[0].source.kind == "heuristic"
    assert "unverified" in found[0].message
    assert "550 lines" in found[0].message


def test_size_always_on_within_threshold_and_ignores_conditional():
    files = [make(300), make(200, name="b.md"), make(900, LoadMode.CONDITIONAL)]
    assert size_always_on(files, CTX) == []


def test_messages_avoid_banned_phrases():
    memory = LoadedFile(
        Path("/m/MEMORY.md"), Scope.MEMORY, LoadMode.ALWAYS, 0, "x\n" * 300, "x\n"
    )
    found = (
        size_file([make(600)], CTX)
        + size_memory([memory], CTX)
        + size_always_on([make(600)], CTX)
    )
    assert len(found) == 3
    for finding in found:
        text = f"{finding.message} {finding.fix}".lower()
        assert not [b for b in BANNED if b in text]
