from dataclasses import dataclass

MEMORY_DOCS_URL = "https://code.claude.com/docs/en/memory"


@dataclass(frozen=True)
class Limit:
    value: int
    verified: bool
    source: str


FILE_LINES = Limit(200, True, MEMORY_DOCS_URL)
MEMORY_LINES = Limit(200, True, MEMORY_DOCS_URL)
MEMORY_BYTES = Limit(25 * 1024, True, MEMORY_DOCS_URL)
MAX_FILE_BYTES = Limit(4 * 1024 * 1024, True, MEMORY_DOCS_URL)
MAX_IMPORT_DEPTH = Limit(4, True, MEMORY_DOCS_URL)
COMBINED_LINES = Limit(0, False, "unverified")


def unverified_limit_names() -> list[str]:
    return [
        name
        for name, value in globals().items()
        if isinstance(value, Limit) and not value.verified
    ]
