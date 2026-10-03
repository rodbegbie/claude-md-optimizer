import re

CJK_RANGES = [
    (0x3000, 0x303F),
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0x4E00, 0x9FFF),
    (0xAC00, 0xD7AF),
    (0x1100, 0x11FF),
    (0x3130, 0x318F),
]

_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_PATHS_KEY = re.compile(r"^paths:[ \t]*(.*)$")
_LIST_ITEM = re.compile(r"^\s*-\s+(.*)$")


def is_cjk_char(ch: str) -> bool:
    cp = ord(ch)
    return any(start <= cp <= end for start, end in CJK_RANGES)


def estimate_tokens(text: str) -> int:
    """
    Language-aware token estimation.
    English: ~4 chars per token. CJK: ~1.5 chars per token.
    """
    if not text:
        return 0

    english_chars = 0
    cjk_chars = 0
    other_chars = 0

    for ch in text:
        if is_cjk_char(ch):
            cjk_chars += 1
        elif ord(ch) < 128:
            english_chars += 1
        else:
            other_chars += 1

    tokens = (english_chars / 4) + (cjk_chars / 1.5) + (other_chars / 3)
    return int(tokens)


def fence_step(line: str, fence: str | None) -> tuple[str | None, bool]:
    """Advance a fenced-code scan by one line.

    `fence` is the opening delimiter run while inside a block, else None.
    Returns the new state and whether this line opened or closed a block.
    A block closes only on a bare run of the same character at least as long
    as the opener.
    """
    match = _FENCE.match(line)
    if not match:
        return fence, False
    run, rest = match.groups()
    if fence is None:
        if run[0] == "`" and "`" in rest:
            return None, False
        return run, True
    if run[0] == fence[0] and len(run) >= len(fence) and not rest.strip():
        return None, True
    return fence, False


def _strip_html_comments(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    fence: str | None = None
    in_comment = False
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        if in_comment:
            end = line.find("-->")
            if end == -1:
                continue
            in_comment = False
            rest = line[end + 3 :]
            if rest.strip():
                out.append((number, rest))
            continue
        fence, is_fence = fence_step(line, fence)
        if fence is None and not is_fence and line.lstrip().startswith("<!--"):
            start = line.index("<!--")
            end = line.find("-->", start + 4)
            if end == -1:
                in_comment = True
                continue
            rest = line[end + 3 :]
            if rest.strip():
                out.append((number, rest))
            continue
        out.append((number, line))
    return out


def strip_html_comments(text: str) -> str:
    return "".join(line for _, line in _strip_html_comments(text))


def split_frontmatter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            block = "".join(lines[1:i]).rstrip("\r\n")
            return block, "".join(lines[i + 1 :])
    return None, text


def _clean_item(item: str) -> str | None:
    item = item.strip()
    if item and item[0] in "\"'":
        if len(item) < 2 or item[-1] != item[0]:
            return None
        item = item[1:-1].strip()
    elif item and item[-1] in "\"'":
        return None
    return item


def _scan(value: str, *, split: bool) -> list[str] | None:
    pieces: list[str] = []
    current: list[str] = []
    quote: str | None = None
    depth = 0
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1].isspace()):
            break
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return None
        elif ch == "," and split and depth == 0:
            pieces.append("".join(current))
            current = []
            continue
        current.append(ch)
    if quote or depth:
        return None
    pieces.append("".join(current))
    return pieces


def parse_paths(block: str | None) -> list[str] | None:
    if block is None:
        return None
    lines = block.splitlines()
    raw_items: list[str] | None = []
    for i, line in enumerate(lines):
        match = _PATHS_KEY.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        if not value or value.startswith("#"):
            raw_items = []
            for following in lines[i + 1 :]:
                item = _LIST_ITEM.match(following)
                if not item:
                    break
                scanned = _scan(item.group(1), split=False)
                if scanned is None:
                    return None
                raw_items.extend(scanned)
        elif value.startswith("["):
            whole = _scan(value, split=False)
            if whole is None:
                return None
            inner = whole[0].strip()
            if not inner.endswith("]"):
                return None
            raw_items = _scan(inner[1:-1], split=True)
        else:
            raw_items = _scan(value, split=True)
        break
    else:
        return None
    if raw_items is None:
        return None

    items: list[str] = []
    for raw in raw_items:
        cleaned = _clean_item(raw)
        if cleaned is None:
            return None
        if cleaned:
            items.append(cleaned)
    return items or None


def effective_text_with_lines(text: str, *, is_rule: bool) -> tuple[str, list[int]]:
    removed = 0
    if is_rule:
        before = len(text.splitlines(keepends=True))
        _, text = split_frontmatter(text)
        removed = before - len(text.splitlines(keepends=True))
    kept = _strip_html_comments(text)
    return "".join(line for _, line in kept), [number + removed for number, _ in kept]


def effective_text(text: str, *, is_rule: bool) -> str:
    return effective_text_with_lines(text, is_rule=is_rule)[0]
