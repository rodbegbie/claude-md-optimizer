from pathlib import Path

import claude_md.checks  # noqa: F401
import pytest
from claude_md import findings
from claude_md.findings import Finding, Source, check
from claude_md.scoring import Deduction, score

DOCS = Source("docs", "https://code.claude.com/docs/en/memory")
HEURISTIC = Source("heuristic", None)


@pytest.fixture(autouse=True)
def restore_registry():
    saved = dict(findings.REGISTRY)
    yield
    findings.REGISTRY.clear()
    findings.REGISTRY.update(saved)


def make_finding(check_id: str, n: int = 0) -> Finding:
    return Finding(
        check_id, "warning", Path(f"f{n}.md"), None, f"m{n}", "fix", HEURISTIC
    )


def register(check_id: str, weight: int, cap: int) -> None:
    check(check_id, HEURISTIC, weight=weight, cap=cap)(lambda files, ctx: [])


def test_score_starts_at_100():
    result = score([])
    assert result.value == 100
    assert result.deductions == []


def test_score_deducts_weight_per_finding():
    register("t-a", 2, 10)
    result = score([make_finding("t-a", i) for i in range(3)])
    assert result.value == 94
    assert result.deductions == [Deduction("t-a", 3, 6, False)]


def test_score_caps_per_check():
    register("t-a", 3, 9)
    result = score([make_finding("t-a", i) for i in range(10)])
    assert result.value == 91
    assert result.deductions == [Deduction("t-a", 10, 9, True)]


def test_score_at_exactly_the_cap_is_not_flagged_capped():
    register("t-a", 3, 9)
    result = score([make_finding("t-a", i) for i in range(3)])
    assert result.deductions == [Deduction("t-a", 3, 9, False)]


def test_score_floor_zero():
    for i in range(30):
        register(f"t-{i}", 10, 10)
    result = score([make_finding(f"t-{i}") for i in range(30)])
    assert result.value == 0


def test_score_is_independent_of_finding_order():
    register("t-a", 2, 4)
    register("t-b", 1, 3)
    found = [make_finding("t-a", 1), make_finding("t-b", 2), make_finding("t-a", 3)]
    assert score(found) == score(list(reversed(found)))
    assert score(found) == score(found)


def test_heuristic_cap_lower_than_docs_cap():
    specs = findings.REGISTRY.values()
    heuristic = [s.cap for s in specs if s.source.kind == "heuristic"]
    docs = [s.cap for s in specs if s.source.kind == "docs"]
    assert heuristic and docs
    assert max(heuristic) <= max(docs)
    assert sum(heuristic) < sum(docs)
