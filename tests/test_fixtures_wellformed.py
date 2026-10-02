import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"

CHECK_IDS = {
    "size-file",
    "size-memory",
    "size-always-on",
    "derivable-content",
    "hook-candidate",
    "emphasis-dilution",
    "stale-reference",
    "scope-candidate",
    "import-misconception",
    "vague-instruction",
    "duplicate-across",
}

CASES = {
    "derivable-tree",
    "import-for-savings",
    "scoped-in-always-on",
    "hook-candidates",
    "emphasis-overload",
    "stale-refs",
    "oversized",
    "clean",
}


def test_every_fixture_is_wellformed():
    found = (
        {p.name for p in FIXTURES.iterdir() if p.is_dir()}
        if FIXTURES.is_dir()
        else set()
    )
    assert found == CASES

    for case in sorted(found):
        root = FIXTURES / case
        assert (root / "project").is_dir(), case
        expected = json.loads((root / "expected.json").read_text())
        assert set(expected) == {"must_include", "must_exclude"}, case
        for key in expected:
            assert isinstance(expected[key], list), (case, key)
            assert set(expected[key]) <= CHECK_IDS, (case, key)
        if case == "clean":
            assert expected["must_include"] == []
            assert set(expected["must_exclude"]) == CHECK_IDS
