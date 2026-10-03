import re

from claude_md.checks._common import is_loaded, loaded
from claude_md.checks._markdown import prose_lines
from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile, LoadMode, Scope

HEURISTIC = Source("heuristic", None)

MIN_WITHIN_CHARS = 21
MIN_ACROSS_CHARS = 25
ALWAYS_ON_FIX = "Keep the line in the always-loaded file and delete it from the others."
SAME_PATHS_FIX = (
    "These rules share the same paths, so keep the line in one of them and "
    "delete it from the others."
)
LONG_FILE_LINES = 80

_PROJECT_LEVEL = frozenset({Scope.PROJECT, Scope.LOCAL, Scope.ANCESTOR, Scope.AGENTS})

TRIGGER_PATTERNS = [
    r"(read|see|refer to|check)\s+[`\"]?[\w/.-]+[`\"]?\s+(when|if|before|after|for)",
    r"when\s+(modifying|editing|working|changing|adding|creating)\s+",
]


def _has_text(line: str) -> bool:
    return any(ch.isalnum() for ch in line)


@check("duplicate-within", HEURISTIC, weight=1, cap=3)
def duplicate_within(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    found: list[Finding] = []
    for file in loaded(files):
        counts: dict[str, int] = {}
        first_repeat: int | None = None
        for number, line in prose_lines(file.source_text):
            stripped = line.strip().lower()
            if len(stripped) < MIN_WITHIN_CHARS or not _has_text(stripped):
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
                    f"{file.path}:{first_repeat} is the first repeat of {repeated} "
                    f"duplicated {'line' if repeated == 1 else 'lines'} within "
                    "this file.",
                    "Remove the repeated lines to save context tokens.",
                    HEURISTIC,
                )
            )
    return found


@check("duplicate-across", HEURISTIC, weight=1, cap=3)
def duplicate_across(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    occurrences: dict[str, list[tuple[LoadedFile, int]]] = {}
    for file in files:
        if not is_loaded(file):
            continue
        seen: set[str] = set()
        for number, line in prose_lines(file.source_text):
            stripped = line.strip().lower()
            if (
                len(stripped) < MIN_ACROSS_CHARS
                or stripped.startswith("#")
                or not _has_text(stripped)
            ):
                continue
            normalized = " ".join(stripped.split())
            if normalized not in seen:
                seen.add(normalized)
                occurrences.setdefault(normalized, []).append((file, number))

    found: list[Finding] = []
    for text, hits in occurrences.items():
        group = _redundant_group(hits)
        if group is None:
            continue
        paths = list(dict.fromkeys(file.path for file, _ in group))
        first_file, first_line = group[0]
        listing = ", ".join(str(p) for p in paths)
        always_on = any(file.mode == LoadMode.ALWAYS for file, _ in group)
        found.append(
            Finding(
                "duplicate-across",
                "warning",
                first_file.path,
                first_line,
                f"{first_file.path}:{first_line} repeats a line found in "
                f"{len(paths)} loaded files ({listing}): '{text[:80]}'.",
                ALWAYS_ON_FIX if always_on else SAME_PATHS_FIX,
                HEURISTIC,
            )
        )
    return found


def _redundant_group(
    hits: list[tuple[LoadedFile, int]],
) -> list[tuple[LoadedFile, int]] | None:
    if any(file.mode == LoadMode.ALWAYS for file, _ in hits):
        candidates = [hits]
    else:
        by_scope: dict[frozenset[str], list[tuple[LoadedFile, int]]] = {}
        for file, number in hits:
            by_scope.setdefault(frozenset(file.paths or ()), []).append((file, number))
        candidates = list(by_scope.values())
    for group in candidates:
        if len({file.path for file, _ in group}) >= 2:
            return group
    return None


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
