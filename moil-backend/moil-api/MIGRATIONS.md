# Database migrations (Alembic)

**What it is.** A migration file is a numbered, saved instruction such as "add table X" or "add column Y". Alembic runs the files in order and
remembers in the database (table `alembic_version`) which ones already ran. This is how a real deployment database (PostgreSQL) is built and
changed safely, without deleting data.

**Two modes (setting `AUTO_CREATE_TABLES` in `.env`):**
| Mode | Setting | Who creates tables | Use for |
|---|---|---|---|
| Local | `true` (the default) | the API itself, when it starts (as before) | your laptop with `moil.db` |
| Deployment | `false` | Alembic only: `python -m alembic upgrade head` | Docker, PostgreSQL, any shared server |

Do not mix them on one database. Do NOT run `upgrade` on your local `moil.db`: its tables already exist.

## One-time setup (already described in HOW-TO-APPLY.txt)
`pip install alembic`, then `python -m scripts.make_baseline`. This writes `alembic/versions/0001_baseline.py` for the 24+ current tables.

## When you change a table or add a new one (every future patch)
1. Change `app/models/__init__.py`.
2. Make a migration file:  `python -m alembic revision --autogenerate -m "describe the change"`
3. Open the new file in `alembic/versions/` and read it: it should contain only what you changed.
4. `python -m pytest` runs `test_migrations`, which fails if the models and the migrations disagree.
5. On a deployment database: `python -m alembic upgrade head`.

## Useful commands (run in the backend folder)
- `python -m alembic current`    which migration this database is at
- `python -m alembic history`    list all migrations
- `python -m alembic upgrade head`   apply everything missing
- `python -m alembic downgrade -1`   undo the last one (read it first; undoing a table drop loses its data)

## SQLite note
SQLite cannot alter most things in place, so Alembic runs in "batch mode" (it rebuilds the table). That is already switched on in `alembic/env.py`.
