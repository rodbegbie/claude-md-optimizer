# Scenario: explain-context-cost

## Fixture

`tests/fixtures/oversized/project/` (Harbourlight, a single 260-line
CLAUDE.md with about 25 topic sections such as Bookings, Pricing,
Deployment and Payments).

## Prompt

```text
Why is my context so big?
```

## Must advise

- Get each CLAUDE.md file under about 200 lines (the file is 260).
- Move path-specific or occasional sections (for example Payments,
  Manifests, Deployment, Frontend) into path-scoped rules with `paths:`
  frontmatter, nested CLAUDE.md files or skills.
- Check what actually loaded with `/context`.

## Must not advise

- Stating that CLAUDE.md is re-injected on every request.
- Stating that cost compounds per turn, including phrasing such as
  "tokens x turns", "after 30 turns" or any cumulative multiple of the
  file size.
- Presenting a fixed limit of 150, 100 or 50 lines as official
  guidance.
