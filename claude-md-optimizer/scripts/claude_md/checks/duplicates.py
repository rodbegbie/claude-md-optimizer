import re

from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile, LoadMode, Scope

HEURISTIC = Source("heuristic", None)

MIN_WITHIN_CHARS = 21
MIN_ACROSS_CHARS = 25
LONG_FILE_LINES = 80

_LOADED = frozenset({LoadMode.ALWAYS, LoadMode.CONDITIONAL})
_PROJECT_LEVEL = frozenset({Scope.PROJECT, Scope.LOCAL, Scope.ANCESTOR, Scope.AGENTS})

TRIGGER_PATTERNS = [
    r"(read|see|refer to|check)\s+[`\"]?[\w/.-]+[`\"]?\s+(when|if|before|after|for)",
    r"when\s+(modifying|editing|working|changing|adding|creating)\s+",
]


def _loaded(files: list[LoadedFile]) -> list[LoadedFile]:
    return [f for f in files if f.mode in _LOADED]


@check("duplicate-within", HEURISTIC, weight=1, cap=3)
def duplicate_within(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    found: list[Finding] = []
    for file in _loaded(files):
        counts: dict[str, int] = {}
        first_repeat: int | None = None
        for number, line in enumerate(file.text.splitlines(), start=1):
            stripped = line.strip().lower()
            if len(stripped) < MIN_WITHIN_CHARS:
                continue
            counts[stripped] = counts.get(stripped, 0) + 1
            if counts[stripped] == 2 and first_repeat is None:
                first_repeat = number
        repeated = sum(1 for n in counts.values() if n > 1)
        if repeated:
            found.append(
                Finding(
                    "duplicate-within",
                    "warning",
                    file.path,
                    first_repeat,
                    f"{file.path}:{first_repeat} is one of {repeated} duplicate "
                    "lines within this file.",
                    "Remove the repeated lines to save context tokens.",
                    HEURISTIC,
                )
            )
    return found


@check("duplicate-across", HEURISTIC, weight=1, cap=3)
def duplicate_across(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    occurrences: dict[str, list[tuple[LoadedFile, int]]] = {}
    for file in _loaded(files):
        seen: set[str] = set()
        for number, line in enumerate(file.text.splitlines(), start=1):
            stripped = line.strip().lower()
            if len(stripped) < MIN_ACROSS_CHARS or stripped.startswith("#"):
                continue
            normalized = " ".join(stripped.split())
            if normalized not in seen:
                seen.add(normalized)
                occurrences.setdefault(normalized, []).append((file, number))

    found: list[Finding] = []
    for text, hits in occurrences.items():
        paths = list(dict.fromkeys(file.path for file, _ in hits))
        if len(paths) < 2:
            continue
        first_file, first_line = hits[0]
        listing = ", ".join(str(p) for p in paths)
        found.append(
            Finding(
                "duplicate-across",
                "warning",
                first_file.path,
                first_line,
                f"{first_file.path}:{first_line} repeats a line found in "
                f"{len(paths)} loaded files ({listing}): '{text[:80]}'.",
                "Keep the line in one file and delete it from the others.",
                HEURISTIC,
            )
        )
    return found


@check("no-trigger", HEURISTIC, weight=1, cap=1)
def no_trigger(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    return [
        Finding(
            "no-trigger",
            "suggestion",
            file.path,
            None,
            f"{file.path} has {file.lines} lines and no trigger conditions.",
            "Add 'Read X when modifying Y' lines for referenced documents so "
            "detail loads only when needed.",
            HEURISTIC,
        )
        for file in files
        if file.mode == LoadMode.ALWAYS
        and file.scope in _PROJECT_LEVEL
        and file.lines > LONG_FILE_LINES
        and not any(re.search(p, file.text.lower()) for p in TRIGGER_PATTERNS)
    ]
