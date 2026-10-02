# Recipe Box

A small Flask app for storing and scaling family recipes.

## Project structure

```text
recipe-box/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes/
│   │   ├── recipes.py
│   │   └── auth.py
│   ├── templates/
│   │   ├── base.html
│   │   └── recipe_detail.html
│   └── static/
│       └── app.css
├── migrations/
├── tests/
│   ├── test_models.py
│   └── test_routes.py
├── pyproject.toml
└── README.md
```

## Dependencies

- flask 3.0.3
- flask-sqlalchemy 3.1.1
- flask-login 0.6.3
- flask-migrate 4.0.7
- alembic 1.13.2
- jinja2 3.1.4
- pytest 8.3.2
- ruff 0.6.2

## Architecture

Recipe Box is a classic server-rendered Flask application. The app factory in
`app/__init__.py` creates the Flask instance, wires up SQLAlchemy and
Flask-Login, and registers two blueprints. The `recipes` blueprint handles
listing, creating, editing and scaling recipes, while the `auth` blueprint
handles login and registration. Models live in a single `models.py` module and
use SQLAlchemy declarative classes. Templates extend `base.html` and render
everything on the server; there is no JavaScript framework. Data is stored in
SQLite in development and Postgres in production.

## Commands

- `uv run flask --app app run --debug` starts the dev server on port 5000.
- `uv run pytest` runs the test suite against an in-memory SQLite database.
- `uv run flask --app app db migrate -m "message"` generates a migration.

## Gotchas

- Ingredient quantities are stored as fractions in `Ingredient.quantity_num`
  and `quantity_den`; never store floats, scaling breaks on 1/3 cups.
- The test client needs `SERVER_NAME` unset or url_for fails in tests.
