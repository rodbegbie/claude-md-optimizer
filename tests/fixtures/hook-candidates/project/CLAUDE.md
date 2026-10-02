# Tidepool

Python library for parsing tide tables published by harbour authorities.

## Commands

- `uv run pytest` runs the tests.
- `uv run python -m tidepool.cli fetch <port>` downloads a table.

## Workflow

- Always run `ruff check` after each edit.
- Always run `ruff format` before finishing a task.
- Never commit without running `pytest` first.
- Never edit files under `tidepool/_generated/`; regenerate them instead.
- Run `mypy tidepool` before every commit.

## Design notes

- Times are stored in UTC and converted only at the display edge.
- Each harbour authority gets its own parser class in `tidepool/parsers/`.
- Parsers return `TideTable` objects; they never print or log directly.
