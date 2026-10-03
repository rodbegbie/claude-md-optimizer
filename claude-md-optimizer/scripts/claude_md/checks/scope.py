import re
from collections.abc import Iterator

from claude_md.checks._common import loaded
from claude_md.checks._markdown import headings, prose_lines
from claude_md.discovery import _import_tokens, _looks_like_path
from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile, LoadMode

MEMORY = Source("docs", "https://code.claude.com/docs/en/memory")

MIN_SCOPED_LINES = 3

_SCOPED_LINE = re.compile(
    r"^\s*(?:(?:[-*+]|\d+[.)])\s+)?when\s+(?:editing|working\s+in|touching)\b(.*)$",
    re.IGNORECASE,
)
_PATH_SPAN = re.compile(r"`[^`\n]*[/*][^`\n]*`")
_BARE_PATH = re.compile(r"(?<![\w`])(?:\*+[\w.*/\-]+|[\w.\-]+/[\w.\-*/]*)")
_CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
_IMPORT_WORD = r"(?P<imp>\bimport\w*)"
_SAVING = r"\b(?:save|saving|reduce|reducing|cut|cutting|lower|lowering)\s+(?:\w+\s+){0,2}(?:context|tokens?)\b"
_NEAR = r"[^.!?]{0,80}?"
_NEGATOR = re.compile(r"\b(?:not|no|never|without|cannot)\b|n't\b", re.IGNORECASE)
_NEGATED_TAIL = re.compile(r"(?:\b(?:not|no|never|cannot)|n't)\s+$", re.IGNORECASE)
_MISCONCEPTION = (
    re.compile(_IMPORT_WORD + _NEAR + _SAVING, re.IGNORECASE),
    re.compile(_SAVING + _NEAR + _IMPORT_WORD, re.IGNORECASE),
)

SCOPE_FIX = (
    "Move these rules into a `.claude/rules/<name>.md` file with `paths:` "
    "frontmatter listing the globs they apply to, or into a nested CLAUDE.md "
    "in the directory they cover, so they only load when Claude works on "
    "matching files."
)
IMPORT_FIX = (
    "Keep the import if it helps organise the file, but do not count on it "
    "to shrink context. To load rules only when relevant, use `paths:` "
    "frontmatter in `.claude/rules/` or a nested CLAUDE.md."
)


@check("scope-candidate", MEMORY, weight=1, cap=3)
def scope_candidate(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for file in loaded(files):
        if file.mode is not LoadMode.ALWAYS:
            continue
        for number, title, count in _scoped_sections(file.text):
            findings.append(
                Finding(
                    "scope-candidate",
                    "suggestion",
                    file.path,
                    number,
                    f"{file.path}:{number} section '{title}' has {count} rules "
                    "that apply only when working on particular paths, yet it "
                    "loads at launch. Path-scoped rules and nested "
                    "CLAUDE.md files load only when they are relevant.",
                    SCOPE_FIX,
                    MEMORY,
                )
            )
    return findings


def _scoped_sections(text: str) -> Iterator[tuple[int, str, int]]:
    lines = text.splitlines()
    prose = dict(prose_lines(text))
    marks = headings(lines)
    for index, (number, _, title) in enumerate(marks):
        end = marks[index + 1][0] if index + 1 < len(marks) else len(lines) + 1
        count = sum(
            1
            for n in range(number + 1, end)
            if n in prose and _is_scoped_line(prose[n])
        )
        if count >= MIN_SCOPED_LINES:
            yield number, title, count


def _is_scoped_line(line: str) -> bool:
    match = _SCOPED_LINE.match(line)
    if not match:
        return False
    rest = match.group(1)
    if _PATH_SPAN.search(rest):
        return True
    return any(token.lower() != "and/or" for token in _BARE_PATH.findall(rest))


@check("import-misconception", MEMORY, weight=1, cap=2)
def import_misconception(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for file in loaded(files):
        if not any(_looks_like_path(t) for t in _import_tokens(file.text)):
            continue
        number = _first_claim_line(file.text)
        if number is None:
            continue
        findings.append(
            Finding(
                "import-misconception",
                "suggestion",
                file.path,
                number,
                f"{file.path}:{number} suggests imports save context. Imported "
                "files are loaded at launch alongside the file that imports "
                "them, so an @path import does not reduce context.",
                IMPORT_FIX,
                MEMORY,
            )
        )
    return findings


def _first_claim_line(text: str) -> int | None:
    for paragraph in _paragraphs(text):
        joined = " ".join(line for _, line in paragraph)
        hits = [
            m.start("imp")
            for rx in _MISCONCEPTION
            for m in rx.finditer(joined)
            if not _negated(joined, m)
        ]
        if not hits:
            continue
        offset = min(hits)
        position = 0
        for number, line in paragraph:
            position += len(line) + 1
            if offset < position:
                return number
    return None


def _negated(text: str, match: re.Match[str]) -> bool:
    before = text[max(0, match.start() - 20) : match.start()]
    return bool(_NEGATOR.search(match.group()) or _NEGATED_TAIL.search(before))


def _paragraphs(text: str) -> Iterator[list[tuple[int, str]]]:
    current: list[tuple[int, str]] = []
    for number, line in prose_lines(text):
        stripped = _CODE_SPAN.sub(lambda m: " " * len(m.group()), line)
        if stripped.strip() and (not current or current[-1][0] == number - 1):
            current.append((number, stripped))
            continue
        if current:
            yield current
        current = [(number, stripped)] if stripped.strip() else []
    if current:
        yield current
