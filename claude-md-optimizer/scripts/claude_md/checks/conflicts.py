import re

from claude_md.checks._common import loaded
from claude_md.checks._markdown import prose_lines
from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile

HEURISTIC = Source("heuristic", None)

MAX_OBJECT_WORDS = 3
QUOTE_CHARS = 60

_RULE = re.compile(
    r"\b(always use|never use|don['’]t use|do not use|prefer|avoid|never|use)\s+(.*)",
    re.IGNORECASE,
)
_POSITIVE = frozenset({"always use", "prefer", "use"})
_CLAUSE_END = re.compile(r"[.,;:!?()\[\]—–]|\s-\s")
_WORD = re.compile(r"[\w+#/.-]+")
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "any",
        "all",
        "your",
        "our",
        "my",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "to",
        "of",
        "for",
        "in",
        "on",
        "with",
        "when",
        "if",
        "unless",
        "instead",
        "and",
        "or",
        "but",
        "is",
        "are",
        "be",
        "as",
        "at",
        "by",
        "from",
        "only",
        "over",
        "than",
        "then",
        "so",
        "not",
        "no",
        "more",
        "most",
        "less",
        "very",
        "just",
        "also",
    }
)

FIX = (
    "Decide which instruction wins, then remove or qualify the other so the "
    "two no longer pull in opposite directions."
)


def _instruction(line: str) -> tuple[bool, frozenset[str]] | None:
    match = _RULE.search(line.replace("`", ""))
    if not match:
        return None
    positive = match.group(1).lower() in _POSITIVE
    rest = _CLAUSE_END.split(match.group(2), maxsplit=1)[0]
    words: list[str] = []
    for raw in _WORD.findall(rest.lower()):
        word = raw.strip(".-/")
        if not word or word in STOPWORDS:
            if words:
                break
            continue
        words.append(word.removesuffix("s") if len(word) > 3 else word)
        if len(words) == MAX_OBJECT_WORDS:
            break
    return (positive, frozenset(words)) if words else None


def _quote(line: str) -> str:
    text = " ".join(line.split())
    return text if len(text) <= QUOTE_CHARS else text[: QUOTE_CHARS - 3] + "..."


@check("possible-conflict", HEURISTIC, weight=1, cap=2)
def possible_conflict(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    entries: list[tuple[LoadedFile, int, str, bool, frozenset[str]]] = []
    for file in sorted(loaded(files), key=lambda f: f.order):
        for number, line in prose_lines(file.text):
            parsed = _instruction(line)
            if parsed:
                entries.append((file, number, line, *parsed))

    found: list[Finding] = []
    for i, (later, l_num, l_line, l_pos, l_obj) in enumerate(entries):
        for earlier, e_num, e_line, e_pos, e_obj in entries[:i]:
            if earlier.scope == later.scope or l_pos == e_pos or l_obj != e_obj:
                continue
            found.append(
                Finding(
                    "possible-conflict",
                    "suggestion",
                    later.path,
                    l_num,
                    f"{later.path}:{l_num} ('{_quote(l_line)}') may conflict "
                    f"with {earlier.path}:{e_num} ('{_quote(e_line)}'). This "
                    "is a low-confidence heuristic that matches the same "
                    "object with opposite polarity, so check whether the two "
                    "really clash.",
                    FIX,
                    HEURISTIC,
                )
            )
    return found
