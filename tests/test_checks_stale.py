import json
import os
from pathlib import Path

import pytest
from claude_md import checks  # noqa: F401
from claude_md.checks.stale import stale_reference
from claude_md.discovery import discover
from claude_md.findings import REGISTRY, Context, run_checks
from claude_md.model import LoadedFile, LoadMode, Scope

FIXTURES = Path(__file__).parent / "fixtures"
BANNED = ["per request", "every request", "each request", "per turn", "turns"]
BANNED += ["compound", "session cost"]


def run(
    tmp_path: Path,
    text: str,
    *,
    mode: LoadMode = LoadMode.ALWAYS,
    scope: Scope = Scope.PROJECT,
    name: str = "CLAUDE.md",
):
    file = LoadedFile(tmp_path / name, scope, mode, 0, text, text)
    return stale_reference([file], Context(tmp_path, tmp_path / "home"))


def lines(found) -> list[int]:
    return [f.line for f in found]


def write(root: Path, rel: str, content: str = "x") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_registered_as_heuristic():
    spec = REGISTRY["stale-reference"]
    assert spec.source.kind == "heuristic"
    assert spec.source.url is None
    assert (spec.weight, spec.cap) == (2, 4)


def test_missing_path_flagged(tmp_path):
    found = run(tmp_path, "# P\n\nSee `src/missing.py` for retries.\n")
    assert len(found) == 1
    assert found[0].check_id == "stale-reference"
    assert found[0].line == 3
    assert "src/missing.py" in found[0].message
    assert str(tmp_path) in found[0].message
    assert "remove" in found[0].fix
    assert not any(b in found[0].message.lower() for b in BANNED)


def test_existing_path_ok(tmp_path):
    write(tmp_path, "src/app.py")
    (tmp_path / "pkg").mkdir()
    text = "`src/app.py` `./src/app.py` `pkg/` `src/app.py:12` `app.py`\n"
    assert run(tmp_path, text) == []


def test_bare_filename_found_anywhere_in_project(tmp_path):
    write(tmp_path, "deep/er/settings.yaml")
    assert run(tmp_path, "Edit `settings.yaml`.\n") == []
    assert lines(run(tmp_path, "Edit `nowhere.yaml`.\n")) == [1]


def test_bare_js_name_is_not_a_file(tmp_path):
    assert run(tmp_path, "Built with `next.js` and `Node.js`.\n") == []


def test_missing_directory_under_existing_dir_flagged(tmp_path):
    (tmp_path / "src").mkdir()
    assert lines(run(tmp_path, "See `src/gone` and `text/plain`.\n")) == [1]


def test_resolves_relative_to_mentioning_file(tmp_path):
    write(tmp_path, "skill/scripts/run.py")
    write(tmp_path, "skill/SKILL.md")
    text = "Run `scripts/run.py` then `scripts/nope.py`.\n"
    found = run(tmp_path, text, name="skill/SKILL.md")
    assert len(found) == 1
    assert "scripts/nope.py" in found[0].message


def test_one_finding_per_token_per_line(tmp_path):
    text = "`a/x.py` and `a/x.py` and `b/y.py`\n`a/x.py`\n"
    assert lines(run(tmp_path, text)) == [1, 1, 2]


def test_missing_npm_script_flagged(tmp_path):
    write(tmp_path, "package.json", json.dumps({"scripts": {"build": "tsc"}}))
    text = "- `npm run build`\n- `npm run nope`\n- `npm run --if-present gone`\n"
    found = run(tmp_path, text)
    assert lines(found) == [2, 3]
    assert "nope" in found[0].message
    assert "package.json" in found[0].message


def test_pnpm_and_yarn_builtins_not_flagged(tmp_path):
    write(tmp_path, "package.json", json.dumps({"scripts": {"build": "tsc"}}))
    text = "`pnpm install` `yarn add x` `pnpm test` `yarn dev` `pnpm lint` `yarn`\n"
    text += "`pnpm run build` `yarn build` `pnpm -r build`\n"
    assert run(tmp_path, text) == []


def test_pnpm_and_yarn_missing_script_flagged(tmp_path):
    write(tmp_path, "package.json", json.dumps({"scripts": {"build": "tsc"}}))
    found = run(tmp_path, "`pnpm gen` and `yarn run seed`\n")
    assert [("gen" in f.message, "seed" in f.message) for f in found] == [
        (True, False),
        (False, True),
    ]


def test_binaries_from_dependencies_not_flagged(tmp_path):
    pkg = {"scripts": {}, "devDependencies": {"vitest": "1"}}
    write(tmp_path, "package.json", json.dumps(pkg))
    assert run(tmp_path, "`pnpm vitest`\n") == []


def test_workspaces_skip_script_checks(tmp_path):
    pkg = {"scripts": {}, "workspaces": ["packages/*"]}
    write(tmp_path, "package.json", json.dumps(pkg))
    assert run(tmp_path, "`npm run web:dev`\n") == []


def test_no_package_json_skips_npm_check(tmp_path):
    assert run(tmp_path, "`npm run nope` `pnpm gen` `yarn seed`\n") == []


def test_malformed_package_json_skipped(tmp_path):
    for bad in ("{not json", "[]", '{"scripts": 3}'):
        write(tmp_path, "package.json", bad)
        assert run(tmp_path, "`npm run nope`\n") == []


def test_missing_make_target_flagged(tmp_path):
    write(tmp_path, "Makefile", ".PHONY: lint\n\nbuild: deps\n\tgo build\nlint:\n\tv\n")
    found = run(tmp_path, "`make build` `make lint` `make deploy`\n")
    assert len(found) == 1
    assert "deploy" in found[0].message
    assert "Makefile" in found[0].message


def test_make_skipped_when_unverifiable(tmp_path):
    assert run(tmp_path, "`make deploy`\n") == []
    write(tmp_path, "Makefile", "include other.mk\nbuild:\n\ttrue\n")
    assert run(tmp_path, "`make deploy`\n") == []
    write(tmp_path, "Makefile", "%.o: %.c\n\tcc\nbuild:\n\ttrue\n")
    assert run(tmp_path, "`make deploy`\n") == []
    write(tmp_path, "Makefile", "build:\n\ttrue\n")
    assert run(tmp_path, "`make -C sub deploy` `make $T` `make A=1 build`\n") == []


def test_glob_and_url_skipped(tmp_path):
    text = (
        "`src/**/*.ts` `docs/?.md` `src/[a-z].py` `https://example.com/a/b.json`\n"
        "`~/.claude/CLAUDE.md` `/etc/hosts` `/usr/local/missing.py` `../up/x.py`\n"
        "`<name>/file.py` `$HOME/x.py` `{a,b}/c.py` `src/...` `@scope/pkg`\n"
        "`example.com/a/b` `a\\b.py` `C:/x/y.py`\n"
    )
    assert run(tmp_path, text) == []


def test_absolute_path_inside_project_checked(tmp_path):
    assert lines(run(tmp_path, f"`{tmp_path}/gone.py`\n")) == [1]


def test_generated_and_local_paths_skipped(tmp_path):
    text = (
        "`node_modules/x/index.js` `dist/app.js` `build/out.js` `.venv/bin/python`\n"
        "`.env.local` `settings.local.json` `coverage/lcov.info` `src/__pycache__/x.py`\n"
    )
    assert run(tmp_path, text) == []


def test_fenced_code_skipped(tmp_path):
    text = "```bash\nnpm run nope\ncat `src/missing.py`\n```\n\n~~~\n`a/b.py`\n~~~\n"
    write(tmp_path, "package.json", json.dumps({"scripts": {}}))
    assert run(tmp_path, text) == []


def test_only_loaded_project_files(tmp_path):
    text = "`src/missing.py`\n"
    assert run(tmp_path, text, mode=LoadMode.ON_DEMAND) == []
    assert run(tmp_path, text, scope=Scope.USER) == []
    assert run(tmp_path, text, scope=Scope.ANCESTOR) == []
    assert lines(run(tmp_path, text, mode=LoadMode.CONDITIONAL)) == [1]
    assert lines(run(tmp_path, text, scope=Scope.NESTED)) == [1]


def test_odd_paths_do_not_raise(tmp_path):
    long = "a/" + "b" * 5000 + ".py"
    nul = "src/\x00x.py"
    assert run(tmp_path, f"`{long}` `{nul}` `{'a/' * 3000}x.py`\n") is not None


def test_symlink_loop_and_outside_link_do_not_raise(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    os.symlink(project / "loop", project / "loop")
    os.symlink(outside, project / "escape")
    text = "`loop/x.py` `escape/y.py` `gone.py`\n"
    file = LoadedFile(
        project / "CLAUDE.md", Scope.PROJECT, LoadMode.ALWAYS, 0, text, text
    )
    found = stale_reference([file], Context(project, tmp_path / "home"))
    assert lines(found) == [1]
    assert "gone.py" in found[0].message


def run_fixture(name: str, tmp_path: Path):
    project = FIXTURES / name / "project"
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    files = discover(project, home, tmp_path / "managed")
    found = run_checks(files, Context(project, home))
    return [f for f in found if f.check_id == "stale-reference"]


def test_fixture_stale_refs_flags_missing_only(tmp_path):
    found = run_fixture("stale-refs", tmp_path)
    assert sorted(f.line for f in found) == [8, 14]
    text = " ".join(f.message for f in found)
    assert "nope" in text
    assert "src/missing.py" in text
    assert "templates.ts" not in text


def test_fixtures_excluding_id_do_not_flag(tmp_path):
    for expected in FIXTURES.glob("*/expected.json"):
        data = json.loads(expected.read_text())
        if "stale-reference" in data["must_exclude"]:
            assert run_fixture(expected.parent.name, tmp_path) == [], (
                expected.parent.name
            )


def test_local_conventions_and_suffix_patterns_skipped(tmp_path):
    text = "`.private-journal/` `.claude/CLAUDE.md` `_test.go` `MEMORY.md`\n"
    assert run(tmp_path, text) == []


@pytest.mark.parametrize(
    "command",
    [
        "yarn plugin",
        "yarn npm",
        "yarn constraints",
        "yarn explain",
        "yarn unplug",
        "pnpm root",
        "pnpm view",
        "pnpm recursive",
    ],
)
def test_more_pnpm_yarn_builtins_not_flagged(tmp_path, command):
    write(tmp_path, "package.json", json.dumps({"scripts": {"build": "tsc"}}))
    assert run(tmp_path, f"`{command}`\n") == []


def test_path_missing_from_project_and_file_directory_flagged(tmp_path):
    write(tmp_path, "skill/scripts/run.py")
    found = run(tmp_path, "`scripts/gone.py`\n", name="skill/SKILL.md")
    assert lines(found) == [1]
    assert str(tmp_path / "skill") in found[0].message
