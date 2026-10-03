import re
from collections.abc import Iterator
from dataclasses import dataclass

from claude_md.text import _FENCE

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


@dataclass(frozen=True)
class FencedBlock:
    start: int
    length: int


def prose_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield (1-based line number, line) for lines outside fenced blocks.

    Fence delimiter lines themselves are not yielded.
    """
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = _FENCE.match(line)
        if match:
            if fence is None:
                fence = match.group(1)
            elif fence == match.group(1):
                fence = None
            continue
        if fence is None:
            yield number, line


def fenced_blocks(text: str) -> list[FencedBlock]:
    """Fenced blocks as (opening fence line, number of lines inside).

    An unterminated block runs to the end of the text.
    """
    lines = text.splitlines()
    blocks: list[FencedBlock] = []
    fence: str | None = None
    start = 0
    for number, line in enumerate(lines, start=1):
        match = _FENCE.match(line)
        if not match:
            continue
        if fence is None:
            fence, start = match.group(1), number
        elif fence == match.group(1):
            blocks.append(FencedBlock(start, number - start - 1))
            fence = None
    if fence is not None:
        blocks.append(FencedBlock(start, len(lines) - start))
    return blocks


_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s")
_HRULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_SETEXT = re.compile(r"^\s*(=+|-+)\s*$")
_LINK_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s")
_CONTINUATION_INDENT = 2
_CODE_INDENT = 4


def _frontmatter_end(lines: list[str]) -> int:
    if not lines or lines[0].rstrip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return i + 1
    return 0


def paragraph_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield (1-based line number, line) for plain paragraph text only.

    Excludes frontmatter, fenced blocks, headings (ATX and setext), list items
    with their indented or lazy continuation lines, tables, blockquotes, HTML,
    link definitions, horizontal rules and indented code.
    """
    frontmatter_end = _frontmatter_end(text.splitlines())
    lines = dict(prose_lines(text))
    container: str | None = None
    previous_blank = True
    previous = 0
    for number in sorted(lines):
        line = lines[number]
        lazy = number == previous + 1 and not previous_blank
        previous = number
        previous_blank = not line.strip()
        if number <= frontmatter_end or previous_blank:
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if (
            _HRULE.match(line)
            or _SETEXT.match(line)
            or _LINK_DEF.match(line)
            or stripped.startswith(("#", "|", "<"))
        ):
            container = None
        elif stripped.startswith(">"):
            container = "quote"
        elif _LIST_ITEM.match(line):
            container = "list"
        elif (
            container == "list"
            and (indent >= _CONTINUATION_INDENT or lazy)
            or container == "quote"
            and lazy
        ):
            pass
        else:
            container = None
            if indent < _CODE_INDENT and not _SETEXT.match(lines.get(number + 1, "x")):
                yield number, line


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    found: list[tuple[int, int, str]] = []
    fenced = False
    for number, line in enumerate(lines, start=1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        elif not fenced and (match := _HEADING.match(line)):
            found.append((number, len(match.group(1)), match.group(2)))
    return found
