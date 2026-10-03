# AGENTS.md

This file provides guidance to coding agents (including Claude Code) when
working with code in this repository.

## What this repo is

A Claude Code skill (`claude-md-optimizer/`) that audits `CLAUDE.md` files,
plus a Python analyser it runs. This is Rod's fork of geuneda's upstream; work
here is fork-only, not for upstream PRs. The skill is being reworked to match
Anthropic's current memory docs.

The skill directory is the shippable unit: `SKILL.md` is the prompt,
`references/optimization-rules.md` holds the rules, and `scripts/` holds the
analyser.

## Commands

Python 3.13+, managed with `uv`. There are no runtime dependencies.

```bash
uv sync                                  # install pytest and ruff
uv run pytest                            # full suite
uv run pytest tests/test_limits.py       # one file
uv run pytest tests/test_model.py::test_name   # one test
uv run ruff check . && uv run ruff format --check .
python3 claude-md-optimizer/scripts/analyze_claude_md.py <project-dir> [--json]
```

`pytest` puts `claude-md-optimizer/scripts` on `pythonpath`, so tests import
`claude_md.*` directly.

## Architecture

`scripts/analyze_claude_md.py` is the CLI entry point and is mid-migration.
It still holds the legacy per-file checks (`analyze_file`, regex pattern
lists, `calculate_score`) and is excluded from ruff in `pyproject.toml`
(remove the exclusion when the rework retires it). Its helpers have been
moved into the `claude_md` package, so edit the package, not the copies the
script still carries.

The `claude_md` package models what Claude Code actually loads:

- `discovery.py`: `discover()` walks managed, user, ancestor, project, local,
  rules, nested, `@import` and auto-memory files. It returns `LoadedFile`s in
  load order. It also handles `.claude/settings.json` excludes, git
  worktree-to-main-repo mapping, and `AGENTS.md` as a fallback that only loads
  when no `CLAUDE.md` exists at or above the working directory.
- `model.py`: `Scope` (where a file came from), `LoadMode` (always,
  conditional via `paths:` frontmatter, on-demand, excluded, dormant,
  skipped), `LoadedFile`, and `totals()`.
- `limits.py`: documented limits as `Limit(value, verified, source)`.
  Anything not confirmed by Anthropic's docs has `verified=False` and is
  surfaced as "unverified" in the report. Do not state a limit as fact unless
  it is verified.
- `text.py`: token estimate, HTML-comment stripping, frontmatter and `paths:`
  parsing.

The main script analyses only the `ALWAYS`-loaded files for scoring, but
reports all of them.

## Tests

- `tests/test_*.py` drive the analyser through the CLI. The `tree` fixture
  builds a file tree in `tmp_path`, and `run_cli` runs the script with `HOME`
  set to `tmp_path/home`. Always pass a project subdirectory such as
  `root / "project"`, never `tmp_path` itself, or the fake home is analysed as
  project content.
- `tests/fixtures/<name>/{project/,expected.json}` are sample projects;
  `test_fixtures_wellformed.py` validates their shape.
- `tests/scenarios/` are manual, agent-run checks of the skill's advice, not
  pytest. Follow the run and isolation protocol in `tests/scenarios/README.md`
  exactly (fresh subagent, explicit skill path, `HOME` override, 3 reps).
- `test_known_bugs.py` pins fixed discovery bugs.

## Repo conventions

- Markdown must be markdownlint-clean (lines under 80 characters, blank lines
  around blocks).
- Phase plans, specs and baselines live only on branch
  `planning/claude-md-optimizer-rework`. Never merge them to `main`.
- Work is phased, and each phase ends in a draft PR to `main` on the fork (see
  "GitHub: fork only" below).
- `git push` runs Entire's hook. The first branch push is often rejected;
  confirm the remote did not move, retry once, and never force.
- `.claude/`, `.codex/` and `.entire/` configs are tracked and belong to the
  Entire integration. `.agent-traces/` and `.private-journal/` are not.

## GitHub: fork only

- Every GitHub interaction MUST happen on Rod's fork,
  `rodbegbie/claude-md-optimizer`. That covers PRs, issues, comments, reviews,
  labels, releases and repo settings.
- NEVER open a PR or an issue, or post anything else, on the upstream repo
  (`geuneda/claude-md-optimizer`). This work is fork-only and is not for
  upstream.
- Always pass `--repo rodbegbie/claude-md-optimizer` to `gh`, because `gh`
  defaults to upstream after forking. Check the target repo before any `gh`
  command that writes.
- The `upstream` remote is read-only. Never push to it. Push branches to
  `origin` and open PRs against `main` on the fork.

<!-- entire-agent:begin -->
Read .entire/agent-guide.md for this repository's workflow, source inspection, and verification guidance.
@.entire/agent-guide.md
<!-- entire-agent:end -->
