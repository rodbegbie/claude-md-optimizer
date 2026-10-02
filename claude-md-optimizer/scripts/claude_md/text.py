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

_FENCE = re.compile(r"^\s*(```|~~~)")
_PATHS_KEY = re.compile(r"^paths:[ \t]*(.*)$")
_LIST_ITEM = re.compile(r"^\s+-\s+(.*)$")


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


def strip_html_comments(text: str) -> str:
    out: list[str] = []
    fence: str | None = None
    in_comment = False
    for line in text.splitlines(keepends=True):
        if in_comment:
            end = line.find("-->")
            if end == -1:
                continue
            in_comment = False
            rest = line[end + 3 :]
            if rest.strip():
                out.append(rest)
            continue
        match = _FENCE.match(line)
        if match:
            if fence is None:
                fence = match.group(1)
            elif fence == match.group(1):
                fence = None
        if fence is None and not match and line.lstrip().startswith("<!--"):
            start = line.index("<!--")
            end = line.find("-->", start + 4)
            if end == -1:
                in_comment = True
                continue
            rest = line[end + 3 :]
            if rest.strip():
                out.append(rest)
            continue
        out.append(line)
    return "".join(out)


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


def parse_paths(block: str | None) -> list[str] | None:
    if block is None:
        return None
    lines = block.splitlines()
    raw_items: list[str] = []
    for i, line in enumerate(lines):
        match = _PATHS_KEY.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        if not value:
            for following in lines[i + 1 :]:
                item = _LIST_ITEM.match(following)
                if not item:
                    break
                raw_items.append(item.group(1))
        elif value.startswith("["):
            if not value.endswith("]"):
                return None
            raw_items = value[1:-1].split(",")
        else:
            raw_items = value.split(",")
        break
    else:
        return None

    items: list[str] = []
    for raw in raw_items:
        cleaned = _clean_item(raw)
        if cleaned is None:
            return None
        if cleaned:
            items.append(cleaned)
    return items or None


def effective_text(text: str, *, is_rule: bool) -> str:
    if is_rule:
        _, text = split_frontmatter(text)
    return strip_html_comments(text)
