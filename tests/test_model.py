import json
from pathlib import Path

from claude_md import model, text
from claude_md.model import LoadedFile, LoadMode, Scope


def make(mode, body="x" * 40, scope=Scope.PROJECT, order=0):
    return LoadedFile(
        path=Path("CLAUDE.md"),
        scope=scope,
        mode=mode,
        order=order,
        raw=body,
        text=body,
    )


def test_totals_split_by_mode():
    files = [
        make(LoadMode.ALWAYS, "a" * 40),
        make(LoadMode.CONDITIONAL, "b" * 80),
        make(LoadMode.ON_DEMAND, "c" * 120),
        make(LoadMode.EXCLUDED, "d" * 400),
    ]
    result = model.totals(files)
    assert result == model.Totals(always=10, conditional=20, on_demand=30)


def test_dormant_and_skipped_count_nowhere():
    files = [make(LoadMode.DORMANT), make(LoadMode.SKIPPED)]
    assert model.totals(files) == model.Totals()


def test_lines_ignore_stripped_comments():
    raw = "one\n<!--\nhidden\nmore hidden\n-->\ntwo\n"
    loaded = make(LoadMode.ALWAYS)
    loaded.raw = raw
    loaded.text = text.effective_text(raw, is_rule=False)
    assert loaded.lines == 2
    assert loaded.lines < len(raw.splitlines())


def test_source_text_keeps_removed_lines_as_blanks():
    raw = "one\n<!--\nhidden\n-->\ntwo\n"
    loaded = make(LoadMode.ALWAYS)
    loaded.raw = raw
    loaded.text, loaded.line_numbers = text.effective_text_with_lines(
        raw, is_rule=False
    )
    assert loaded.text == "one\ntwo\n"
    assert loaded.source_text == "one\n\n\n\ntwo\n"
    assert loaded.source_text.splitlines()[4] == "two"


def test_source_text_is_text_without_a_line_map():
    assert make(LoadMode.ALWAYS, "a\nb\n").source_text == "a\nb\n"


def test_source_text_follows_a_truncated_text():
    loaded = make(LoadMode.ALWAYS, "a\nb\nc\n")
    loaded.line_numbers = [3, 4, 6]
    loaded.text = "a\nb\n"
    assert loaded.source_text == "\n\na\nb\n"


def test_empty_text_has_zero_lines():
    assert make(LoadMode.ALWAYS, "").lines == 0


def test_bytes_counts_utf8_bytes():
    assert make(LoadMode.ALWAYS, "café").bytes == 5


def test_enum_values_serialise_as_lowercase_strings():
    assert json.dumps(Scope.USER_RULE) == '"user_rule"'
    assert json.dumps(LoadMode.ON_DEMAND) == '"on_demand"'
    assert Scope.PROJECT == "project"


def test_loaded_file_defaults():
    a = make(LoadMode.ALWAYS)
    b = make(LoadMode.ALWAYS)
    assert a.paths is None
    assert a.imported_by is None
    assert a.external is False
    assert a.notes == []
    a.notes.append("x")
    assert b.notes == []
