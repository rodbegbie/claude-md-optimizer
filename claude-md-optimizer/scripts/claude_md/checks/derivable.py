import re
from dataclasses import dataclass

from claude_md.checks._common import loaded
from claude_md.checks._markdown import fenced_blocks, headings
from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile

BEST_PRACTICES = Source("docs", "https://code.claude.com/docs/en/best-practices")

MIN_TREE_LINES = 3
MIN_DEPENDENCY_RUN = 5
MAX_SECTION_LINES = 10

_TREE_GLYPH = re.compile(r"[├└]──")
_PATH_TOKEN = re.compile(r"^[\w.\-]+/$|^[\w\-]+(\.[\w\-]+)+$")
_DEPENDENCY = re.compile(
    r"""^\s*(?:[-*+]\s+)?["'`]?[A-Za-z][\w.\-]*(?:\[[\w,]+\])?["'`]?
    \s*(?:==|>=|<=|~=|\^|@|:|\s)\s*["'`]?v?\d+(?:\.\d+)+[\w.+\-]*["'`]?,?\s*$""",
    re.VERBOSE,
)
_DERIVABLE_HEADING = re.compile(r"architecture|project\s+structure", re.IGNORECASE)
_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s")

FIX = (
    "Delete it with the user's approval, or replace it with a one-line "
    "pointer to the real file or command."
)
SUFFIX = "Claude can read this from the code or config, so it can usually be cut."


@dataclass(frozen=True)
class _Hit:
    line: int
    shape: str


@check("derivable-content", BEST_PRACTICES, weight=2, cap=6)
def derivable_content(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    return [
        Finding(
            "derivable-content",
            "issue",
            file.path,
            hit.line,
            f"{file.path}:{hit.line} looks like {hit.shape}. {SUFFIX}",
            FIX,
            BEST_PRACTICES,
        )
        for file in loaded(files)
        for hit in _hits(file.source_text)
    ]


def _hits(text: str) -> list[_Hit]:
    lines = text.splitlines()
    hits = _tree_hits(lines) + _dependency_hits(lines)
    hits += _section_hits(lines, [h.line for h in hits])
    return sorted(hits, key=lambda h: h.line)


def _tree_hits(lines: list[str]) -> list[_Hit]:
    hits: list[_Hit] = []
    for block in fenced_blocks("\n".join(lines)):
        body = lines[block.start : block.start + block.length]
        if _is_tree(body):
            hits.append(_Hit(block.start, "a directory tree"))
    return hits


def _is_tree(body: list[str]) -> bool:
    if sum(1 for line in body if _TREE_GLYPH.search(line)) >= MIN_TREE_LINES:
        return True
    content = [line for line in body if line.strip()]
    if len(content) <= MIN_TREE_LINES:
        return False
    pathlike = [line for line in content if _PATH_TOKEN.match(line.strip())]
    indents = {len(line) - len(line.lstrip()) for line in pathlike}
    return len(pathlike) >= 0.8 * len(content) and len(indents) >= 2


def _dependency_hits(lines: list[str]) -> list[_Hit]:
    hits: list[_Hit] = []
    run_start = 0
    for number, line in enumerate(lines + [""], start=1):
        if _DEPENDENCY.match(line):
            run_start = run_start or number
            continue
        if run_start and number - run_start >= MIN_DEPENDENCY_RUN:
            hits.append(_Hit(run_start, "a dependency list"))
        run_start = 0
    return hits


def _section_hits(lines: list[str], covered: list[int]) -> list[_Hit]:
    """Long Architecture or Project structure sections made mostly of list items.

    Sections that already contain another hit are skipped, so each block is
    reported once.
    """
    marks = headings(lines)
    hits: list[_Hit] = []
    for index, (number, level, title) in enumerate(marks):
        if not _DERIVABLE_HEADING.search(title):
            continue
        end = next(
            (n for n, lvl, _ in marks[index + 1 :] if lvl <= level),
            len(lines) + 1,
        )
        body = [line for line in lines[number : end - 1] if line.strip()]
        if any(number < line < end for line in covered):
            continue
        items = sum(1 for line in body if _LIST_ITEM.match(line))
        if len(body) > MAX_SECTION_LINES and items * 2 >= len(body):
            hits.append(_Hit(number, f"a long '{title}' section"))
    return hits
