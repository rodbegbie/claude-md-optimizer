from pathlib import Path

import pytest
from claude_md import findings
from claude_md.findings import Context, Finding, Source, check, run_checks
from claude_md.model import LoadedFile, LoadMode, Scope

DOCS = Source("docs", "https://code.claude.com/docs/en/memory")
HEURISTIC = Source("heuristic", None)


@pytest.fixture(autouse=True)
def restore_registry():
    saved = dict(findings.REGISTRY)
    yield
    findings.REGISTRY.clear()
    findings.REGISTRY.update(saved)


def make_file(name: str, mode: LoadMode) -> LoadedFile:
    return LoadedFile(Path(name), Scope.PROJECT, mode, 0, "x", "x")


def test_every_check_declares_source():
    @check("t-docs", DOCS, weight=1, cap=1)
    def docs_check(files, ctx):
        return []

    @check("t-heuristic", HEURISTIC, weight=1, cap=1)
    def heuristic_check(files, ctx):
        return []

    for spec in findings.REGISTRY.values():
        assert spec.source.kind in ("docs", "heuristic")
        if spec.source.kind == "docs":
            assert spec.source.url
        else:
            assert spec.source.url is None


def test_docs_source_requires_url():
    with pytest.raises(ValueError):
        Source("docs", None)


def test_heuristic_source_rejects_url():
    with pytest.raises(ValueError):
        Source("heuristic", "https://example.com")


def test_check_records_weight_and_cap():
    @check("t-spec", HEURISTIC, weight=3, cap=9)
    def spec_check(files, ctx):
        return []

    spec = findings.REGISTRY["t-spec"]
    assert (spec.id, spec.weight, spec.cap) == ("t-spec", 3, 9)
    assert spec.fn is spec_check


def test_duplicate_check_id_rejected():
    @check("t-dup", HEURISTIC, weight=1, cap=1)
    def first(files, ctx):
        return []

    with pytest.raises(ValueError, match="t-dup"):

        @check("t-dup", HEURISTIC, weight=1, cap=1)
        def second(files, ctx):
            return []


def test_run_checks_skips_excluded_and_dormant_files(tmp_path):
    seen: list[Path] = []

    @check("t-seen", HEURISTIC, weight=1, cap=1)
    def recorder(files, ctx):
        seen.extend(f.path for f in files)
        return [
            Finding("t-seen", "issue", f.path, None, "m", "f", HEURISTIC) for f in files
        ]

    files = [
        make_file(f"{mode.value}.md", mode)
        for mode in (
            LoadMode.ALWAYS,
            LoadMode.CONDITIONAL,
            LoadMode.ON_DEMAND,
            LoadMode.EXCLUDED,
            LoadMode.DORMANT,
            LoadMode.SKIPPED,
        )
    ]
    ctx = Context(project_dir=tmp_path, home_dir=tmp_path)

    results = run_checks(files, ctx)

    assert seen == [Path("always.md"), Path("conditional.md")]
    assert [f.path for f in results] == seen
