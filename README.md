# claude-md-optimizer

A Claude Code skill that audits the instruction files Claude Code loads
(`CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/`, `@` imports and
`MEMORY.md`) and helps you move each piece of content to where it works best.

This fork of [geuneda/claude-md-optimizer][upstream] is reworked to follow
Anthropic's current [memory][memory] and [best practices][anthropic] docs.

## What it does

- Finds every file Claude Code would load for a project, with its load mode:
  always, conditional (`paths:` rules), on demand, dormant, excluded or
  skipped.
- Runs checks and tags each finding by where it comes from. A `docs` finding
  cites an Anthropic page. A `heuristic` finding is this tool's own judgement
  and is offered as a suggestion.
- Lists the limits it could not confirm in Anthropic's docs as unverified,
  rather than stating them as fact.
- Scores the result from 0 to 100. The score starts at 100 and only goes
  down. It is this tool's own measure, not an Anthropic metric.
- Proposes changes against named lines, applies only what you approve, and
  moves content verbatim.

## Installation

Clone the repo into your skills directory:

```bash
git clone https://github.com/rodbegbie/claude-md-optimizer.git /tmp/cmo
cp -R /tmp/cmo/claude-md-optimizer ~/.claude/skills/
```

The skill directory is `claude-md-optimizer/`. It needs Python 3.13 or later
and has no runtime dependencies.

## Usage

In Claude Code, say something like:

```text
Optimize my CLAUDE.md
```

The skill runs the analyser, reads the always-on files itself, and proposes
changes one at a time. It ends by asking you to run `/context` in a new
session to check the Memory files list.

You can also run the analyser directly. Add `--json` for machine-readable
output:

```bash
python3 ~/.claude/skills/claude-md-optimizer/scripts/analyze_claude_md.py \
  /path/to/project
```

## Example output

Paths are shortened and long lines wrapped here.

```text
============================================================
  CLAUDE.md Optimization Report
============================================================

  Context load (estimated tokens):
    Always-on:   ~422
    Conditional: ~0
    On demand:   ~0

    always  project  60 lines  ~422 tokens  /project/CLAUDE.md

  Unverified limits: COMBINED_LINES

------------------------------------------------------------
  Backed by Anthropic docs (2):
    [issue] derivable-content: /project/CLAUDE.md:7 looks like a
        directory tree. Claude can read this from the code or
        config, so it can usually be cut.
        Docs: https://code.claude.com/docs/en/best-practices

  Heuristics (this tool's own judgement) (4):
    [suggestion] code-block-long: /project/CLAUDE.md:7 contains a
        code block of 18 lines (over 5).

------------------------------------------------------------
  Deductions:
    code-block-long: 1 finding(s), -1
    derivable-content: 2 finding(s), -4

  Score: 90/100 (starts at 100; only deductions apply)
============================================================
```

## What counts as documented

Anthropic recommends under 200 lines per `CLAUDE.md` file. `MEMORY.md`
loads its first 200 lines or 25KB. Every other threshold in the analyser is
a heuristic and is tagged that way. The full list of rules, check ids and
unverified items is in
[`references/optimization-rules.md`](claude-md-optimizer/references/optimization-rules.md).

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Credits

Originally written by geuneda. Research sources: [Anthropic][anthropic],
[HumanLayer][humanlayer], [Arize][arize] and [Dometrain][dometrain].

## License

MIT. See [LICENSE](LICENSE).

[upstream]: https://github.com/geuneda/claude-md-optimizer
[memory]: https://code.claude.com/docs/en/memory
[anthropic]: https://code.claude.com/docs/en/best-practices
[humanlayer]: https://www.humanlayer.dev/blog/writing-a-good-claude-md
[arize]: https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/
[dometrain]: https://dometrain.com/blog/creating-the-perfect-claudemd-for-claude-code/
