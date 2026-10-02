# Scenario: enforce-with-hooks

## Fixture

`tests/fixtures/hook-candidates/project/` (Tidepool, a CLAUDE.md
Workflow section with "Always run `ruff check` after each edit", "Never
commit without running `pytest` first" and "Never edit files under
`tidepool/_generated/`").

## Prompt

```text
Make Claude always do these.
```

## Must advise

- Use hooks in settings (for example PostToolUse for `ruff check` after
  edits, PreToolUse to block edits under `tidepool/_generated/` or
  commits before `pytest`) for rules that must happen every time.
- State that CLAUDE.md instructions are advisory and not enforced.

## Must not advise

- Claiming that stronger CLAUDE.md wording, capitals, "IMPORTANT" or
  "MUST" will guarantee compliance.
- Offering more emphatic CLAUDE.md rules as the only mechanism, with no
  mention of hooks.
