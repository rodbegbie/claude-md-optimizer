# Skill-behaviour scenarios

Manual tests of what the claude-md-optimizer skill advises. Each
scenario file holds a fixture, a prompt and a rubric of lines to tick
or fail.

## Run protocol

1. Each run uses a fresh subagent with no prior context.
2. The subagent's working directory is
   `tests/fixtures/<fixture>/project/` of the checkout under test.
3. Tell the subagent to read `<checkout>/claude-md-optimizer/SKILL.md`
   and follow that skill, using the files in that checkout. Give the
   explicit path. Never use the installed copy at `~/.claude/skills`,
   which may be missing or stale.
4. Give the subagent the scenario's Prompt verbatim, and tell it not to
   modify any files (advice only).
5. Do 3 repetitions per scenario. Record each repetition's advice
   verbatim, and tick or fail every rubric line.
6. Record results in a baseline document on the planning branch, not in
   this repository's main line.
