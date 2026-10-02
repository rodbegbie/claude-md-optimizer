# Pantry API

FastAPI service backing the Pantry mobile app.

## Commands

- `uv run pytest -x` runs the tests.
- `uv run uvicorn src.main:app --reload` starts the server on port 8000.

## Code style

- Use type hints on every public function.
- Prefer small modules over large ones; split at roughly 300 lines.
- Log with the `structlog` logger from `src/logging.py`, never `print`.

## Area-specific rules

- When editing `src/api/`, every new route needs a response model and a
  matching test in `tests/api/`.
- When editing `src/api/`, raise `HTTPException` only inside route handlers;
  services raise domain errors from `src/errors.py`.
- When editing `src/db/`, write an Alembic migration for every schema change
  and never edit an existing migration.
- When editing `tests/`, use the factories in `tests/factories.py` rather than
  building models by hand.
- When editing `src/api/`, keep handlers thin and push logic into `src/services/`.

## Deployment

- Deploys are triggered by merging to `main`; do not push tags by hand.
