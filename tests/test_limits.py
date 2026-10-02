import dataclasses

import pytest
from claude_md import limits

URL = "https://code.claude.com/docs/en/memory"


@pytest.mark.parametrize(
    ("limit", "value"),
    [
        (limits.FILE_LINES, 200),
        (limits.MEMORY_LINES, 200),
        (limits.MEMORY_BYTES, 25 * 1024),
        (limits.MAX_FILE_BYTES, 4 * 1024 * 1024),
    ],
)
def test_verified_limits(limit, value):
    assert limit.value == value
    assert limit.verified is True
    assert limit.source == URL


def test_unverified_limits():
    assert limits.MAX_IMPORT_DEPTH == limits.Limit(5, False, "unverified")
    assert limits.COMBINED_LINES == limits.Limit(0, False, "unverified")


def test_limit_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        limits.FILE_LINES.value = 1
