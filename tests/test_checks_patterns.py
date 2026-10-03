from pathlib import Path

from claude_md import checks  # noqa: F401
from claude_md.checks._markdown import (
    FencedBlock,
    fenced_blocks,
    paragraph_lines,
    prose_lines,
)
from claude_md.checks.patterns import (
    code_block_long,
    linter_rule,
    narrative_paragraph,
    vague_instruction,
)
from claude_md.findings import REGISTRY, Context
from claude_md.model import LoadedFile, LoadMode, Scope

CTX = Context(Path("/p"), Path("/h"))


def make(text: str, mode: LoadMode = LoadMode.ALWAYS) -> LoadedFile:
    return LoadedFile(Path("/p/CLAUDE.md"), Scope.PROJECT, mode, 0, text, text)


def test_prose_lines_skip_fenced_blocks_and_number_from_one():
    text = "a\n```py\ncode\n```\nb\n~~~\nmore\n~~~\n"
    assert list(prose_lines(text)) == [(1, "a"), (5, "b")]


def test_prose_lines_mismatched_fence_does_not_close():
    text = "```\nx\n~~~\ny\n```\nz\n"
    assert list(prose_lines(text)) == [(6, "z")]


def test_fenced_blocks_report_start_and_length():
    text = "a\n```\n1\n2\n```\nb\n~~~\n3\n~~~\n"
    assert fenced_blocks(text) == [FencedBlock(2, 2), FencedBlock(7, 1)]


def test_fenced_blocks_unterminated_runs_to_end():
    assert fenced_blocks("x\n```\n1\n2\n") == [FencedBlock(2, 2)]


def test_registered_with_expected_sources():
    assert REGISTRY["vague-instruction"].source.kind == "docs"
    assert (
        REGISTRY["vague-instruction"].source.url
        == "https://code.claude.com/docs/en/best-practices"
    )
    for check_id in ("linter-rule", "narrative-paragraph", "code-block-long"):
        assert REGISTRY[check_id].source.kind == "heuristic"
    assert REGISTRY["linter-rule"].cap < REGISTRY["vague-instruction"].cap


def test_vague_flags_follow_best_practices():
    found = vague_instruction([make("# T\n\n- Follow best practices.\n")], CTX)
    assert len(found) == 1
    assert found[0].check_id == "vague-instruction"
    assert found[0].line == 3
    assert "CLAUDE.md:3" in found[0].message
    assert found[0].fix


def test_vague_ignores_specific_instruction():
    text = "- Run `make test` before committing.\n```\nfollow best practices\n```\n"
    assert vague_instruction([make(text)], CTX) == []


def test_vague_skips_excluded_files():
    text = "Follow best practices\n"
    assert vague_instruction([make(text, LoadMode.EXCLUDED)], CTX) == []


def test_linter_flags_formatting_rule_once_per_file():
    text = "- Use semicolons\n- Run prettier\n"
    found = linter_rule([make(text)], CTX)
    assert len(found) == 1
    assert found[0].line == 1
    assert found[0].source.kind == "heuristic"


def test_linter_ignores_ordinary_rule():
    assert linter_rule([make("- Run `pytest -q` before pushing.\n")], CTX) == []


def test_narrative_flags_three_line_paragraph():
    text = "# T\n\nThis is one.\nThis is two.\nThis is three.\n\n- item\n"
    found = narrative_paragraph([make(text)], CTX)
    assert len(found) == 1
    assert found[0].line == 3
    assert "3 lines" in found[0].message


def test_narrative_ignores_short_prose_and_lists():
    text = "One.\nTwo.\n\n- a\n- b\n- c\n- d\n\n# H1\n# H2\n# H3\n"
    assert narrative_paragraph([make(text)], CTX) == []


def test_narrative_run_ends_at_list_item_and_fence():
    text = "One.\nTwo.\n- item\nThree.\nFour.\n```\nx\n```\nFive.\n"
    assert narrative_paragraph([make(text)], CTX) == []


def test_narrative_paragraph_at_end_of_file_without_blank_line():
    found = narrative_paragraph([make("A.\nB.\nC.")], CTX)
    assert [f.line for f in found] == [1]


def test_code_block_long_flags_over_five_lines():
    body = "\n".join(f"line {i}" for i in range(6))
    found = code_block_long([make(f"intro\n```\n{body}\n```\n")], CTX)
    assert len(found) == 1
    assert found[0].line == 2
    assert "file:line" in found[0].fix


def test_code_block_long_ignores_five_line_block():
    body = "\n".join(f"line {i}" for i in range(5))
    assert code_block_long([make(f"```\n{body}\n```\n")], CTX) == []


def narrative_lines(text: str) -> list[int]:
    return [f.line for f in narrative_paragraph([make(text)], CTX)]


def test_wrapped_list_items_are_not_narrative():
    indented = "- First item that wraps\n  onto a second line\n  and a third line\n"
    lazy = "- First item that wraps\nonto a second line\nand a third line\n"
    numbered = "1. First item\n   second line\n   third line\n"
    assert narrative_lines(indented) == []
    assert narrative_lines(lazy) == []
    assert narrative_lines(numbered) == []


def test_loose_list_item_paragraph_with_continuation_indent_is_not_narrative():
    text = "- Item\n\n  Para one.\n  Para two.\n  Para three.\n"
    assert narrative_lines(text) == []


def test_tables_blockquotes_html_and_definitions_are_not_narrative():
    table = "| a | b |\n|---|---|\n| 1 | 2 |\n"
    quote = "> one\n> two\n> three\n"
    lazy_quote = "> one\ntwo\nthree\n"
    html = "<details>\n<summary>x</summary>\n<p>y</p>\n"
    defs = "[a]: http://a\n[b]: http://b\n[c]: http://c\n"
    for text in (table, quote, lazy_quote, html, defs):
        assert narrative_lines(text) == [], text


def test_frontmatter_setext_and_rules_are_not_narrative():
    front = "---\nname: x\ndescription: y\n---\n"
    setext = "Title\n=====\nSub\n---\n"
    rules = "---\n***\n___\n"
    for text in (front, setext, rules):
        assert narrative_lines(text) == [], text


def test_real_paragraph_after_heading_is_flagged():
    assert narrative_lines("# H\nOne.\nTwo.\nThree.\n") == [2]


def test_real_paragraph_after_list_and_blank_is_flagged():
    text = "- item\n  wrapped\n\nOne.\nTwo.\nThree.\n"
    assert narrative_lines(text) == [4]


def test_real_paragraph_after_frontmatter_is_flagged():
    assert narrative_lines("---\nname: x\n---\nOne.\nTwo.\nThree.\n") == [4]


def test_paragraph_lines_helper_keeps_only_plain_prose():
    text = "# H\nplain\n- item\n  cont\n> q\n| t |\n\nlast\n"
    assert list(paragraph_lines(text)) == [(2, "plain"), (8, "last")]
