from collections.abc import Iterator
from dataclasses import dataclass

from claude_md.text import _FENCE


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
