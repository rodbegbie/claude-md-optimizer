import unicodedata

from claude_md.checks._common import is_checked
from claude_md.findings import Context, Finding, Source, check
from claude_md.model import LoadedFile
from claude_md.text import is_cjk_char

HEURISTIC = Source("heuristic", None)

CJK_RATIO_THRESHOLD = 0.05
EXTRA_TOKENS_PER_CJK_CHAR = 1.25


@check("non-english", HEURISTIC, weight=2, cap=4)
def non_english(files: list[LoadedFile], ctx: Context) -> list[Finding]:
    found: list[Finding] = []
    for file in files:
        if not is_checked(file):
            continue
        letters = cjk = 0
        for ch in file.text:
            if unicodedata.category(ch)[0] in "LN":
                letters += 1
                cjk += is_cjk_char(ch)
        if letters and cjk / letters > CJK_RATIO_THRESHOLD:
            found.append(
                Finding(
                    "non-english",
                    "warning",
                    file.path,
                    None,
                    f"Non-English content is {cjk / letters:.0%} of text in "
                    f"{file.path} (~{int(cjk * EXTRA_TOKENS_PER_CJK_CHAR)} "
                    "extra tokens).",
                    "Write instructions in English where possible; CJK text "
                    "tokenizes less efficiently.",
                    HEURISTIC,
                )
            )
    return found
