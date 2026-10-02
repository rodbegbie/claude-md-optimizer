import analyze_claude_md
from claude_md import text


def test_strip_html_comments_removes_block_comment():
    src = "before\n<!-- a\nmulti-line\ncomment -->\nafter\n"
    assert text.strip_html_comments(src) == "before\nafter\n"


def test_strip_html_comments_removes_single_line_comment():
    assert text.strip_html_comments("a\n  <!-- note -->\nb\n") == "a\nb\n"


def test_strip_html_comments_keeps_remainder_after_close():
    assert text.strip_html_comments("<!-- x -->tail\nb\n") == "tail\nb\n"


def test_strip_html_comments_keeps_inline_comment():
    src = "keep <!-- inline --> this\n"
    assert text.strip_html_comments(src) == src


def test_strip_html_comments_keeps_comment_in_code_block():
    src = "```html\n<!-- keep me -->\n```\n~~~\n<!-- and me -->\n~~~\n"
    assert text.strip_html_comments(src) == src


def test_strip_html_comments_unterminated_strips_to_end():
    assert text.strip_html_comments("a\n<!-- open\nstill\n") == "a\n"


def test_split_frontmatter():
    block, body = text.split_frontmatter("---\npaths: a\n---\nbody\n")
    assert block == "paths: a"
    assert body == "body\n"


def test_split_frontmatter_absent():
    src = "# Title\n---\nnot frontmatter\n---\n"
    assert text.split_frontmatter(src) == (None, src)


def test_split_frontmatter_unclosed():
    src = "---\npaths: a\nbody\n"
    assert text.split_frontmatter(src) == (None, src)


def test_parse_paths_list():
    block = 'paths:\n  - "src/**/*.ts"\n  - tests/**\nother: x'
    assert text.parse_paths(block) == ["src/**/*.ts", "tests/**"]


def test_parse_paths_comma_string():
    assert text.parse_paths("paths: src/**/*.ts, tests/**") == [
        "src/**/*.ts",
        "tests/**",
    ]


def test_parse_paths_flow_list():
    assert text.parse_paths("paths: [\"a\", 'b']") == ["a", "b"]


def test_parse_paths_malformed_returns_none():
    assert text.parse_paths("paths: [unclosed") is None
    assert text.parse_paths('paths: "unclosed') is None


def test_parse_paths_flow_list_with_brace_glob():
    block = 'paths: ["src/**/*.{ts,tsx}", "tests/**"]'
    assert text.parse_paths(block) == ["src/**/*.{ts,tsx}", "tests/**"]


def test_parse_paths_comma_string_with_brace_glob():
    assert text.parse_paths("paths: src/**/*.{ts,tsx}, tests/**") == [
        "src/**/*.{ts,tsx}",
        "tests/**",
    ]


def test_parse_paths_nested_brace_group():
    assert text.parse_paths("paths: src/{a,{b,c}}/*.ts, x") == [
        "src/{a,{b,c}}/*.ts",
        "x",
    ]


def test_parse_paths_quoted_item_with_comma():
    assert text.parse_paths('paths: "a,b", c') == ["a,b", "c"]


def test_parse_paths_unbalanced_brace_returns_none():
    assert text.parse_paths("paths: src/{a,b") is None


def test_parse_paths_unindented_list():
    assert text.parse_paths("paths:\n- a\n- b") == ["a", "b"]


def test_parse_paths_trailing_comment_flow_list():
    assert text.parse_paths("paths: [a, b] # c") == ["a", "b"]


def test_parse_paths_trailing_comment_comma_string():
    assert text.parse_paths("paths: a, b # c") == ["a", "b"]


def test_parse_paths_trailing_comment_block_item():
    assert text.parse_paths("paths:\n  - a # x\n  - b") == ["a", "b"]


def test_parse_paths_hash_in_quotes_or_word_is_not_comment():
    assert text.parse_paths('paths: "a #b", c#d') == ["a #b", "c#d"]


def test_parse_paths_absent_returns_none():
    assert text.parse_paths(None) is None
    assert text.parse_paths("description: x") is None
    assert text.parse_paths("paths:") is None


def test_effective_text_strips_frontmatter_for_rules():
    src = "---\npaths: a\n---\n<!-- c -->\nbody\n"
    assert text.effective_text(src, is_rule=True) == "body\n"


def test_effective_text_keeps_frontmatter_for_non_rules():
    src = "---\nx: 1\n---\n<!-- c -->\nbody\n"
    assert text.effective_text(src, is_rule=False) == "---\nx: 1\n---\nbody\n"


def test_estimate_tokens_matches_legacy():
    samples = [
        "The quick brown fox jumps over the lazy dog. " * 5,
        "Use English words 日本語のテキスト and 한국어 mixed café",
        "",
    ]
    for sample in samples:
        assert text.estimate_tokens(sample) == analyze_claude_md.estimate_tokens(sample)
