import re
from dataclasses import dataclass

from claude_md.checks._common import loaded
from claude_md.checks._markdown import prose_lines
from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile

HEURISTIC = Source("heuristic", None)

MAX_OBJECT_WORDS = 3
QUOTE_CHARS = 60

_NEGATIVE = re.compile(
    r"\b(?:never use|don['’]t use|do not use|avoid|never)\s+(.*)", re.IGNORECASE
)
_POSITIVE = [
    re.compile(r"\b(?:always|should|must|please)\s+use\s+(.*)", re.IGNORECASE),
    re.compile(r"\bprefer\s+(.*)", re.IGNORECASE),
    re.compile(r"^use\s+(.*)", re.IGNORECASE),
]
_LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_DOUBLE_NEGATION = re.compile(
    r"\b(?:do not|don['’]t|never)\s+(?:avoid|never)\b", re.IGNORECASE
)
_CLAUSE_END = re.compile(r"[.,;:!?()\[\]—–]|\s-\s")
_WORD = re.compile(r"[\w+#/.-]+")
QUALIFIERS = frozenset(
    "for in on when unless except only with within during if where".split()  # noqa: SIM905
)
STOPWORDS = frozenset(
    """a an the any all your our my this that these those it its to of for in on
    with when if unless instead and or but is are be as at by from only over than
    then so not no more most less very just also using""".split()  # noqa: SIM905
)

FIX = (
    "Decide which instruction wins, then remove or qualify the other so the "
    "two no longer pull in opposite directions."
)


@dataclass(frozen=True)
class _Instruction:
    file: LoadedFile
    number: int
    line: str
    positive: bool
    key: frozenset[str]


def _parse(line: str) -> tuple[bool, frozenset[str]] | None:
    """Return (positive, object words), or None when the line is not a plain rule."""
    text = _LIST_MARKER.sub("", line).replace("`", "").replace("*", "").strip()
    if _DOUBLE_NEGATION.search(text):
        return None
    candidates: list[tuple[int, bool, str]] = []
    if match := _NEGATIVE.search(text):
        candidates.append((match.start(), False, match.group(1)))
    for pattern in _POSITIVE:
        if match := pattern.search(text):
            candidates.append((match.start(), True, match.group(1)))
    if not candidates:
        return None
    _, positive, rest = min(candidates, key=lambda c: c[0])
    clause = _CLAUSE_END.split(rest, maxsplit=1)[0]
    tokens = [t.strip(".-/") for t in _WORD.findall(clause.lower())]
    words: list[str] = []
    remaining: list[str] = []
    for index, token in enumerate(tokens):
        if not token or token in STOPWORDS:
            if words:
                remaining = tokens[index:]
                break
            continue
        words.append(token.removesuffix("s") if len(token) > 3 else token)
        if len(words) == MAX_OBJECT_WORDS:
            remaining = tokens[index + 1 :]
            break
    tail = _WORD.findall(rest[len(clause) :].lower())
    if not words or QUALIFIERS.intersection(remaining + tail):
        return None
    return positive, frozenset(words)


def _quote(line: str) -> str:
    text = " ".join(line.split())
    return text if len(text) <= QUOTE_CHARS else text[: QUOTE_CHARS - 3] + "..."


@check("possible-conflict", HEURISTIC, weight=1, cap=2)
def possible_conflict(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    buckets: dict[frozenset[str], dict[bool, list[_Instruction]]] = {}
    found: list[Finding] = []
    for file in sorted(loaded(files), key=lambda f: f.order):
        for number, line in prose_lines(file.text):
            parsed = _parse(line)
            if not parsed:
                continue
            positive, key = parsed
            later = _Instruction(file, number, line, positive, key)
            bucket = buckets.setdefault(key, {True: [], False: []})
            earlier = next(
                (
                    e
                    for e in bucket[not positive]
                    if e.file.scope != file.scope and e.file.path != file.path
                ),
                None,
            )
            bucket[positive].append(later)
            if earlier:
                found.append(_finding(earlier, later))
    return found


def _finding(earlier: _Instruction, later: _Instruction) -> Finding:
    return Finding(
        "possible-conflict",
        "suggestion",
        later.file.path,
        later.number,
        f"{later.file.path}:{later.number} ('{_quote(later.line)}') may "
        f"conflict with {earlier.file.path}:{earlier.number} "
        f"('{_quote(earlier.line)}'). This is a low-confidence heuristic that "
        "matches the same object with opposite polarity, so check whether the "
        "two really clash.",
        FIX,
        HEURISTIC,
    )
