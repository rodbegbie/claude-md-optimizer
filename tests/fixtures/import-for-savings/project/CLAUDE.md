# Ledgerly

Personal finance CLI that imports bank CSVs and produces monthly summaries.

## Commands

- `uv run pytest` runs the tests.
- `uv run ledgerly import statements/` loads every CSV in a folder.
- `uv run ruff format .` formats the code.

## Conventions

Our coding conventions are long, so I split them into an imported file to save
context. Claude loads it on demand when it is relevant.

@docs/conventions.md

## Notes

- Amounts are stored as integer pence, never floats.
- Bank CSV formats differ; each parser lives in `ledgerly/parsers/`.
