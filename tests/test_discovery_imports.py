import pytest
from claude_md.discovery import discover
from claude_md.model import LoadMode, Scope


@pytest.fixture
def layout(tmp_path):
    root = tmp_path.resolve()
    home = root / "home"
    project = root / "outer" / "proj"
    home.mkdir()
    project.mkdir(parents=True)
    return root, home, project


def write(path, content="x\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def found(root, files):
    return [f for f in files if f.path.is_relative_to(root)]


def imports(root, files):
    return [f for f in found(root, files) if f.scope == Scope.IMPORT]


def by_name(root, files, name):
    return next(f for f in found(root, files) if f.path.name == name)


def test_import_counts_as_own_file(layout):
    root, home, project = layout
    claude = write(project / "CLAUDE.md", "see @docs/a.md\n")
    write(project / "docs" / "a.md", "alpha\n")
    files = found(root, discover(project, home))
    assert [f.path.name for f in files] == ["CLAUDE.md", "a.md"]
    imported = files[1]
    assert imported.scope == Scope.IMPORT
    assert imported.mode == LoadMode.ALWAYS
    assert imported.imported_by == claude
    assert imported.external is False
    assert imported.order == files[0].order + 1
    assert imported.raw == "alpha\n"


def test_nested_imports_expand(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@a.md\n")
    a = write(project / "a.md", "@b.md\n")
    b = write(project / "b.md", "end\n")
    files = imports(root, discover(project, home))
    assert [f.path for f in files] == [a, b]
    assert files[1].imported_by == a


def test_circular_import_terminates_and_notes(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@a.md\n")
    write(project / "a.md", "@b.md\n")
    write(project / "b.md", "@a.md\n")
    files = discover(project, home)
    assert [f.path.name for f in imports(root, files)] == ["a.md", "b.md"]
    assert by_name(root, files, "b.md").notes == ["circular import: @a.md"]


def test_self_import_is_circular(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@CLAUDE.md\n")
    files = found(root, discover(project, home))
    assert len(files) == 1
    assert files[0].notes == ["circular import: @CLAUDE.md"]


def test_external_import_flagged(layout):
    root, home, project = layout
    outside = write(root / "shared" / "ext.md")
    write(project / "CLAUDE.md", f"@{outside}\n@inside.md\n")
    write(project / "inside.md")
    files = {f.path.name: f for f in imports(root, discover(project, home))}
    assert files["ext.md"].external is True
    assert files["inside.md"].external is False


def test_external_flag_follows_the_chain(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", f"@{root}/shared/one.md\n")
    write(root / "shared" / "one.md", "@two.md\n")
    write(root / "shared" / "two.md")
    files = {f.path.name: f for f in imports(root, discover(project, home))}
    assert files["one.md"].external is True
    assert files["two.md"].external is True


def test_user_file_import_is_not_external(layout):
    root, home, project = layout
    user = write(home / ".claude" / "CLAUDE.md", "@~/notes.md\n")
    write(home / "notes.md")
    files = imports(root, discover(project, home))
    assert [(f.imported_by, f.external) for f in files] == [(user, False)]


def test_same_import_from_project_file_is_external(layout):
    root, home, project = layout
    write(home / "notes.md")
    write(project / "CLAUDE.md", "@~/notes.md\n")
    files = imports(root, discover(project, home))
    assert [f.external for f in files] == [True]


def test_import_in_code_block_ignored(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "```\n@a.md\n```\n~~~\n@a.md\n~~~\n")
    write(project / "a.md")
    files = discover(project, home)
    assert imports(root, files) == []
    assert by_name(root, files, "CLAUDE.md").notes == []


def test_import_after_code_block_still_expands(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "```\n@a.md\n```\n@b.md\n")
    write(project / "a.md")
    write(project / "b.md")
    files = imports(root, discover(project, home))
    assert [f.path.name for f in files] == ["b.md"]


def test_import_in_inline_code_ignored(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "use `@a.md` and ``@a.md`` here\n")
    write(project / "a.md")
    assert imports(root, discover(project, home)) == []


def test_missing_import_target_is_noted(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@docs/nope.md and @gone.md and @docs/dir\n")
    (project / "docs" / "dir").mkdir(parents=True)
    files = discover(project, home)
    assert imports(root, files) == []
    assert by_name(root, files, "CLAUDE.md").notes == [
        "import target missing: @docs/nope.md",
        "import target missing: @gone.md",
        "import target missing: @docs/dir",
    ]


def test_mention_ignored_silently(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "ping @mention and @alice, please\n")
    files = discover(project, home)
    assert by_name(root, files, "CLAUDE.md").notes == []


def test_email_address_is_not_an_import(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "mail user@example.com or me@a.md\n")
    write(project / "a.md")
    files = discover(project, home)
    assert imports(root, files) == []
    assert by_name(root, files, "CLAUDE.md").notes == []


def test_relative_import_resolves_from_importing_file(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@docs/a.md\n")
    write(project / "docs" / "a.md", "@b.md\n")
    b = write(project / "docs" / "b.md")
    write(project / "b.md")
    files = imports(root, discover(project, home))
    assert [f.path for f in files] == [project / "docs" / "a.md", b]


def test_tilde_uses_passed_home(layout):
    root, home, project = layout
    target = write(home / "prefs.md")
    write(project / "CLAUDE.md", "@~/prefs.md\n")
    files = imports(root, discover(project, home))
    assert [f.path for f in files] == [target]


def test_absolute_path_import(layout):
    root, home, project = layout
    target = write(root / "abs" / "x.md")
    write(project / "CLAUDE.md", f"@{target}\n")
    assert [f.path for f in imports(root, discover(project, home))] == [target]


def test_fifth_hop_not_loaded_and_depth_noted(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@f1.md\n")
    for i in range(1, 6):
        write(project / f"f{i}.md", f"@f{i + 1}.md\n")
    write(project / "f6.md")
    files = discover(project, home)
    names = [f.path.name for f in imports(root, files)]
    assert names == ["f1.md", "f2.md", "f3.md", "f4.md"]
    assert by_name(root, files, "f4.md").notes == ["import depth limit reached: @f5.md"]
    assert by_name(root, files, "f3.md").notes == []


def test_trailing_punctuation_stripped(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "see @docs/x.md.\nalso @docs/y.md), ok\n")
    write(project / "docs" / "x.md")
    write(project / "docs" / "y.md")
    files = imports(root, discover(project, home))
    assert [f.path.name for f in files] == ["x.md", "y.md"]


def test_punctuation_kept_when_file_exists_with_it(layout):
    root, home, project = layout
    target = write(project / "odd.md.")
    write(project / "CLAUDE.md", "@odd.md.\n")
    assert [f.path for f in imports(root, discover(project, home))] == [target]


def test_conditional_rule_imports_not_expanded(layout):
    root, home, project = layout
    rule = "---\npaths:\n  - src/**\n---\n@../../a.md\n"
    write(project / ".claude" / "rules" / "r.md", rule)
    write(project / "a.md")
    files = discover(project, home)
    assert imports(root, files) == []
    assert by_name(root, files, "r.md").mode == LoadMode.CONDITIONAL


def test_unconditional_rule_imports_expand(layout):
    root, home, project = layout
    rule = write(project / ".claude" / "rules" / "r.md", "@../../a.md\n")
    a = write(project / "a.md")
    files = imports(root, discover(project, home))
    assert [(f.path, f.imported_by) for f in files] == [(a, rule)]


def test_nested_claude_md_imports_not_expanded(layout):
    root, home, project = layout
    write(project / "CLAUDE.md")
    write(project / "sub" / "CLAUDE.md", "@a.md\n")
    write(project / "sub" / "a.md")
    assert imports(root, discover(project, home)) == []


def test_imported_file_appears_once(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@.claude/rules/r.md\n")
    write(project / ".claude" / "rules" / "r.md")
    files = found(root, discover(project, home))
    matches = [f for f in files if f.path.name == "r.md"]
    assert len(matches) == 1
    assert matches[0].scope == Scope.IMPORT


def test_same_file_imported_twice_yields_one_entry(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@a.md\n@a.md\n")
    write(project / "a.md")
    assert len(imports(root, discover(project, home))) == 1


def test_imported_file_order_follows_importer(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@a.md\n")
    write(project / "a.md", "@b.md\n")
    write(project / "b.md")
    write(project / "CLAUDE.local.md")
    files = found(root, discover(project, home))
    names = [f.path.name for f in files]
    assert names == ["CLAUDE.md", "a.md", "b.md", "CLAUDE.local.md"]
    assert [f.order for f in files] == sorted(f.order for f in files)
    assert files[1].order == files[0].order + 1
    assert files[2].order == files[1].order + 1


def test_oversized_import_is_skipped(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@big.md\n")
    write(project / "big.md", "a" * (4 * 1024 * 1024 + 1))
    files = imports(root, discover(project, home))
    assert [f.mode for f in files] == [LoadMode.SKIPPED]
    assert files[0].notes == ["skipped: larger than 4 MiB"]


def chain_of_six(project, root_lines):
    write(project / "CLAUDE.md", root_lines)
    for i in range(1, 6):
        write(project / f"f{i}.md", f"@f{i + 1}.md\n")
    write(project / "f6.md")


@pytest.mark.parametrize("lines", ["@f1.md\n@f4.md\n", "@f4.md\n@f1.md\n"])
def test_shallower_reach_expands_depth_limited_file(layout, lines):
    root, home, project = layout
    chain_of_six(project, lines)
    files = discover(project, home)
    names = [f.path.name for f in imports(root, files)]
    assert sorted(names) == [f"f{i}.md" for i in range(1, 7)]
    assert len(names) == len(set(names))
    assert by_name(root, files, "f4.md").notes == []
    assert [f.order for f in files] == list(range(len(files)))


def test_deep_reach_after_shallow_does_not_reexpand(layout):
    root, home, project = layout
    chain_of_six(project, "@f4.md\n@f1.md\n")
    files = discover(project, home)
    names = [f.path.name for f in imports(root, files)]
    assert names == ["f4.md", "f5.md", "f6.md", "f1.md", "f2.md", "f3.md"]
    assert all(f.notes == [] for f in imports(root, files))


def test_diamond_loads_once_without_circular_note(layout):
    root, home, project = layout
    write(project / "CLAUDE.md", "@a.md\n@b.md\n")
    write(project / "a.md", "@c.md\n")
    write(project / "b.md", "@c.md\n")
    write(project / "c.md")
    files = imports(root, discover(project, home))
    assert [f.path.name for f in files] == ["a.md", "c.md", "b.md"]
    assert all(f.notes == [] for f in files)
