# Scenario: audit-clean-file

## Fixture

`tests/fixtures/clean/project/` (Kettle, a short Go service whose
CLAUDE.md has only Commands, Gotchas and Conventions sections).

## Prompt

```text
Optimise my CLAUDE.md.
```

## Must advise

- The file is already in good shape and needs little or no change.
- Any suggested change is a small edit tied to a named existing line
  (for example a Gotchas bullet), not a new section.

## Must not advise

- Adding a directory-structure, "key files" or "critical paths"
  section.
- Adding a prohibitions or "do not" section, a domain glossary, or an
  "information recording principles" section.
- Adding a sub-documentation table or trigger index, or splitting the
  file into sub-documents, imports or rules files.
- Saying the file scores badly or has deficits only because a section
  is missing, or recommending a change whose only justification is
  raising a score.
- Rewriting existing lines into a different form (for example bullets
  to a table, or reordering sections) without a stated functional
  reason.
