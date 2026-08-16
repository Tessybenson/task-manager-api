# Task Management API

A FastAPI backend for a Trello/Asana-style task manager: multiple users, shared
projects, role-based permissions, and filterable/paginated task lists.

## Stack

- **FastAPI** — routing, validation, OpenAPI docs
- **SQLAlchemy 2.0** — ORM (SQLite for dev, Postgres for prod — same models, no code changes)
- **Alembic** — schema migrations
- **Pydantic v2** — request/response schemas, kept separate from the DB models
- **passlib[bcrypt]** — password hashing
- **python-jose** — JWT issuing/verification
- **pytest + httpx (FastAPI TestClient)** — automated tests

## Project layout

```
app/
  main.py            FastAPI app, router registration
  database.py         engine/session setup, get_db dependency
  models.py           SQLAlchemy ORM models (User, Project, ProjectMember, Task)
  schemas.py           Pydantic request/response models
  auth.py              password hashing + JWT helpers
  dependencies.py       get_current_user + RBAC guards (require_member/editor/owner)
  routers/
    auth.py            POST /auth/register, /auth/login
    projects.py         project CRUD + member management
    tasks.py            task CRUD, assignment, filtering, pagination
alembic/               migrations (env.py wired to DATABASE_URL, one initial revision)
tests/                 16 pytest tests across auth/projects/tasks
```

## Data model & permissions

- **User** — id, email, hashed_password, created_at
- **Project** — id, name, owner_id, created_at
- **ProjectMember** — (project_id, user_id) → role (`owner` / `editor` / `viewer`), unique per pair
- **Task** — id, project_id, title, description, status (`todo` / `in_progress` / `done`), assignee_id, due_date, created_at

Creating a project automatically makes you an `owner` member of it. Permission
checks are centralized in `dependencies.py`:

| Action                         | Required role            |
|---------------------------------|---------------------------|
| View project / list tasks       | any member                |
| Update project, create/edit/delete tasks, assign tasks | `editor` or `owner` |
| Delete project, manage members  | `owner`                   |

Anyone who isn't a member of a project gets `403` on it (not `404`, so a
member always knows the project exists but a non-member is simply refused —
adjust `require_member` if you'd rather hide existence entirely).

## Setup (local dev, SQLite)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# apply migrations (creates task_manager.db)
alembic upgrade head

uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive OpenAPI docs.

> Note: `app/main.py` also calls `Base.metadata.create_all()` on startup as a
> dev convenience so the app "just works" without running migrations first.
> In a real deployment, drop that and rely solely on `alembic upgrade head`.

## Running with Docker (API + Postgres)

```bash
docker compose up --build
```

This starts Postgres, waits for it to be healthy, runs `alembic upgrade head`,
then starts the API on http://localhost:8000.

## Running tests

```bash
pytest -v
```

Tests run against their own SQLite file (`test.db`), with the schema created
and dropped fresh for every test function via a `setup_db` fixture, so tests
don't interfere with each other or with your dev database. 16 tests cover:
registration/login/token validation, project CRUD and RBAC (owner vs. editor
vs. viewer, non-member access), and task CRUD, assignment, status/date
filtering, and pagination.

## Example flow

```bash
# 1. Register
curl -X POST localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "supersecret1"}'

# 2. Log in (note: form-encoded, OAuth2 password flow)
curl -X POST localhost:8000/auth/login \
  -d "username=alice@example.com&password=supersecret1"
# -> {"access_token": "...", "token_type": "bearer"}

# 3. Create a project
curl -X POST localhost:8000/projects \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Website Redesign"}'

# 4. Create a task
curl -X POST localhost:8000/projects/<project_id>/tasks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Design homepage", "status": "todo", "due_date": "2026-09-01"}'

# 5. Filter + paginate
curl "localhost:8000/projects/<project_id>/tasks?status=todo&page=1&page_size=10" \
  -H "Authorization: Bearer <token>"
```

## Design notes / trade-offs

- **UUID primary keys** via a custom `GUID` `TypeDecorator` (`app/models.py`)
  that stores native `UUID` on Postgres and `CHAR(36)` on SQLite, so the exact
  same model definitions work for local dev and production without an
  if/else scattered through the codebase.
- **Schemas are separate from ORM models** — nothing in `schemas.py` imports
  `Column`/`relationship`, and `UserOut` deliberately excludes
  `hashed_password` so it can never leak through the API even if a route
  accidentally returns the raw ORM object.
- **RBAC is centralized**, not duplicated per-route: every route calls one of
  `require_member` / `require_editor_or_owner` / `require_owner` from
  `dependencies.py` rather than re-implementing role checks inline.
- **Pagination** is offset/limit based (`page`, `page_size`) with a `total`
  count returned alongside `items`, which is simple to reason about at this
  scale; a cursor-based approach would be the next step if task lists grew
  very large.

## Stretch goals implemented

- **Dockerized** (`Dockerfile` + `docker-compose.yml`) — API + Postgres, with
  the API container waiting on Postgres's healthcheck and running Alembic
  migrations before serving traffic.
