# Session 05 – PostgreSQL Foundations for the Movie Service

- **Date:** Monday, Dec 1, 2025
- **Theme:** Graduate from local SQLite files to a production-ready PostgreSQL instance with Alembic migrations, health checks, and test fixtures.

## Session Story
Session 04 proved the repository abstraction works by persisting to SQLite. Session 05 turns that prototype into a production-ready persistence layer: we provision PostgreSQL with Docker Compose, update SQLModel + Alembic settings, introduce connection pools, and teach pytest how to spin up an isolated Postgres database per run. When the dust settles, every request hits a real database just like it will in staging and Exercise 3 (EX3), and the rest of the stack (Streamlit in Session 06, React/Vite in Session 07) can trust the API under load.

## Learning Objectives
- Run PostgreSQL locally with Docker Compose and manage credentials/env vars via `pydantic-settings`.
- Update SQLModel/Alembic configuration (engines, metadata, migrations) to target Postgres instead of SQLite.
- Implement health checks, seed scripts, and connection pooling best practices for async/sync FastAPI apps.
- Write pytest fixtures that create/tear down Postgres schemas so integration tests stay deterministic.

## What You’ll Build
- `docker-compose.yml` service for PostgreSQL + admin tools (`pgAdmin`, `pgcli`).
- Updated `.env(.example)` entries for `MOVIE_DATABASE_URL`, `MOVIE_DB_HOST`, etc.
- `movie_service/app/database.py` pointing SQLModel/Alembic to Postgres with pooling options.
- Alembic migration targeting Postgres types (UUIDs, timestamps) plus a repeatable seed command.
- Test utilities that provision a throwaway Postgres database (`movies_test_<uuid>`) before each test module.

## Prerequisites
1. Complete Session 04 with SQLite + SQLModel working end-to-end.
2. Install Docker Desktop (or Colima) and ensure `docker compose version` works.
3. Install Postgres tooling inside `hello-uv`:
   ```bash
   uv add "psycopg[binary]"
   ```
4. Confirm `uv run python -c "import psycopg"` succeeds. If not, reinstall `psycopg[binary]` and ensure OpenSSL/libpq dependencies exist (Homebrew covers this on macOS).

### Pre-class Setup (JiTT)
1. Create `docker-compose.yml` with a `postgres` service:
   ```yaml
   services:
     db:
       image: postgres:16
       environment:
         POSTGRES_USER: movie
         POSTGRES_PASSWORD: movie
         POSTGRES_DB: movies
       ports:
         - "5432:5432"
       volumes:
         - pgdata:/var/lib/postgresql/data
   volumes:
     pgdata:
   ```
2. Update `.env.example`:
   ```ini
   MOVIE_DATABASE_URL="postgresql+psycopg://movie:movie@localhost:5432/movies"
   MOVIE_DB_HOST="localhost"
   MOVIE_DB_NAME="movies"
   MOVIE_DB_USER="movie"
   MOVIE_DB_PASSWORD="movie"
   ```
3. Start the database and verify connectivity:
   ```bash
   docker compose up -d db
   pgcli postgresql://movie:movie@localhost:5432/movies -c "SELECT 1;"
   ```
4. Run `uv run alembic upgrade head` to migrate SQLite changes into Postgres before class.

## Toolkit Snapshot
- **PostgreSQL 16** – production-grade relational database, supporting concurrency, JSONB, and extensions.
- **psycopg 3** – async-friendly Postgres driver that SQLModel/SQLAlchemy leverage.
- **Alembic** – migration orchestrator; now configured for Postgres schemas, sequences, and UUIDs.
- **Docker Compose** – spins up Postgres + admin tools consistently across laptops.
- **pytest** – still the main harness, now paired with Postgres-specific fixtures or `testcontainers` (optional stretch).
- **Rich/Typer** – reused for migration + seed scripts, ensuring developers can manage Postgres without manual SQL.

## Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Recap & intent | 10 min | Discussion | Why SQLite isn’t enough for EX3; Postgres expectations. |
| Postgres architecture primer | 20 min | Talk + whiteboard | Connection strings, pooling, Alembic config, Docker Compose. |
| **Part B – Lab 1** | **45 min** | **Guided coding** | **Provision Postgres + migrate SQLModel + health checks.** |
| Break | 10 min | — | Encourage pgcli exploration, share `docker compose` tips. |
| **Part C – Lab 2** | **45 min** | **Guided testing** | **Seeds, fixtures, Alembic scripts, multi-db strategy.** |
| Wrap-up & Streamlit preview | 10 min | Q&A | How Session 06’s UI benefits from a hardened DB. |

## Part A – Theory Highlights
1. **Why Postgres now?** Concurrency, transactions, row-level security, JSONB columns, and the ability to mirror production before EX3. SQLite is great for local dev but single-writer constraints will hurt once Streamlit/React clients join.
2. **Connection management:** prefer a single global engine with `pool_size` tuned for your workload. Discuss `asyncpg` vs synchronous psycopg; we’ll stick to sync for now.
3. **Migrations + environments:** keep `.env` authoritative, but drive migrations via Alembic env variables—not hardcoded strings. Introduce `MOVIE_DATABASE_URL_TEST` for pytest.
4. **Testing strategy:** options include `pytest-postgresql`, `testcontainers`, or manual create/drop logic via psycopg. Today we’ll implement a deterministic create/drop scheme using unique database names.
5. **Observability readiness:** Postgres exposes statistics via `pg_stat_activity`; we’ll hook those metrics to Logfire/Grafana later, but today’s focus is ensuring logs include DB host/DB name on connection failures.

## Part B – Lab 1: Provision Postgres + migrate SQLModel (45 minutes)
Goal: replace SQLite-specific assumptions with Postgres-friendly config and confirm CRUD still works.

### Step 0 – Boot Postgres
```bash
docker compose up -d db
pg_isready -h localhost -p 5432 -d movies -U movie
```
If the command fails, run `docker compose logs db` and fix credentials before moving on.

### Step 1 – Update settings
`movie_service/app/config.py`:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Movie Service"
    database_url: str = "postgresql+psycopg://movie:movie@localhost:5432/movies"
    database_echo: bool = False
    pool_size: int = 5
    pool_timeout: int = 30

    model_config = SettingsConfigDict(env_prefix="MOVIE_", env_file=".env", extra="ignore")
```
Add `MOVIE_DATABASE_URL_TEST` later for pytest.

### Step 2 – Configure the Postgres engine
`movie_service/app/database.py`:
```python
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from .config import Settings

settings = Settings()
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.pool_size,
    pool_pre_ping=True,
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```
> ✅ `pool_pre_ping` guards against stale connections when containers restart.

### Step 3 – Align Alembic with Postgres
`alembic/env.py` excerpt:
```python
from movie_service.app.database import engine
from sqlmodel import SQLModel

def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=SQLModel.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=SQLModel.metadata)
        with context.begin_transaction():
            context.run_migrations()
```
Run:
```bash
uv run alembic revision --autogenerate -m "migrate to postgres"
uv run alembic upgrade head
```
Inspect the migration to verify Postgres-specific types (serial primary keys, timestamps).

### Step 4 – Build a health endpoint with trace support
`movie_service/app/main.py` snippet:
```python
import uuid
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine

app = FastAPI(title="Movie Service", version="0.4.0")

# Add CORS for upcoming UI clients (Session 06+)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit (Session 06)
        "http://localhost:5173",  # Vite (Session 07)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    """Add or preserve X-Trace-Id for request tracing.
    
    Session 06's Streamlit client and Session 07's Vite client
    will send this header. If missing, we generate one.
    """
    trace_id = request.headers.get("X-Trace-Id") or f"req-{uuid.uuid4().hex[:8]}"
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    """Health check with database connectivity test.
    
    Returns trace ID so clients can correlate logs.
    """
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "postgres"}


# ...existing movie routes below...
```
Run `uv run uvicorn movie_service.app.main:app --reload` and hit `/healthz` + `/movies` to confirm Postgres-backed CRUD works.

Test trace ID propagation:
```bash
curl -H "X-Trace-Id: test-123" http://localhost:8000/healthz -v
# Should see X-Trace-Id: test-123 in response headers
```

## Part C – Lab 2: Seeds, fixtures, and safety rails (45 minutes)
Goal: treat Postgres as the default datastore for dev + tests.

### Step 1 – Seed script for Postgres
`scripts/db.py`:
```python
import typer
from sqlmodel import Session

from movie_service.app.database import engine, init_db
from movie_service.app.models import MovieCreate
from movie_service.app.repository_db import MovieRepository

app = typer.Typer(help="Database utilities")


@app.command()
def bootstrap(sample: int = 5) -> None:
    init_db()
    with Session(engine) as session:
        repo = MovieRepository(session)
        for idx in range(sample):
            repo.create(MovieCreate(title=f"Sample {idx}", year=2000 + idx, genre="sci-fi"))
    typer.echo("Seed complete")
```
Run `uv run python scripts/db.py bootstrap --sample 3`.

### Step 2 – Test database strategy
Create `tests/conftest.py` snippet:
```python
import uuid

import psycopg
import pytest
from sqlmodel import SQLModel, create_engine, Session

from movie_service.app.dependencies import get_repository
from movie_service.app.repository_db import MovieRepository

DB_TEMPLATE = "postgresql+psycopg://movie:movie@localhost:5432/{db_name}"


def _create_test_db() -> str:
    db_name = f"movies_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect("postgresql://movie:movie@localhost:5432/postgres", autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {db_name}")
    return DB_TEMPLATE.format(db_name=db_name)


def _drop_test_db(url: str) -> None:
    db_name = url.rsplit("/", 1)[-1]
    with psycopg.connect("postgresql://movie:movie@localhost:5432/postgres", autocommit=True) as conn:
        conn.execute(
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db_name}'"
        )
        conn.execute(f"DROP DATABASE IF EXISTS {db_name}")


@pytest.fixture
def session_url() -> str:
    url = _create_test_db()
    try:
        yield url
    finally:
        _drop_test_db(url)


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch, session_url: str) -> MovieRepository:
    engine = create_engine(session_url)
    SQLModel.metadata.create_all(engine)

    def _override_repo():
        with Session(engine) as session:
            yield MovieRepository(session)

    monkeypatch.setattr("movie_service.app.dependencies.get_repository", _override_repo)
    with Session(engine) as session:
        yield MovieRepository(session)
```
Run `uv run pytest -q` and confirm each test creates/destroys its own database.

### Step 3 – Document and monitor
- Add `docs/runbooks/postgres.md` (or README section) describing `docker compose` commands, credentials, and troubleshooting tips.
- Configure Logfire (or simple logging) to include `db_host`, `db_name`, and pool statistics.
- Capture `pg_dump` instructions for backups; emphasize storing migrations/seed data alongside code.

> 🎉 **Quick win:** When pytest, Alembic, and `/healthz` all succeed against Postgres, the backend is production-colored and ready for Session 06’s Streamlit UI.

## Wrap-up & Next Steps
- ✅ Postgres replaces SQLite locally; migrations and seeds run through Typer/uv.
- 📌 Update CI to run `docker compose up -d db && uv run pytest` so pull requests always hit Postgres.

## Session 06 Preview – What's Coming:

**Building User Interfaces:**

With Postgres hardened, Session 06 adds **two** UI layers:
1. **Streamlit dashboard** – Python-native, perfect for data exploration and admin tasks
2. **Typer CLI** – Terminal commands for seeding, wiping, and ops workflows

| Component | Session 05 (Current) | Session 06 (UI Layer) | Changes? |
|-----------|---------------------|----------------------|----------|
| FastAPI | Postgres backend | SAME, now with CORS enabled | ✅ Already setup |
| `main.py` | Has X-Trace-Id middleware | Clients send trace IDs | ✅ Already setup |
| New: `frontend/client.py` | Doesn't exist | httpx wrapper for API | 🆕 NEW |
| New: `frontend/dashboard.py` | Doesn't exist | Streamlit UI | 🆕 NEW |
| New: `scripts/ui.py` | Doesn't exist | Typer admin CLI | 🆕 NEW |
| Dependencies | psycopg, sqlmodel | + streamlit, typer, rich | 🆕 NEW |

**Key insight:** Session 06 only *adds* frontend code. Your FastAPI + Postgres backend runs unchanged, proving the API contract from Session 03 → Session 05 is solid.

**Action items before Session 06:**
1. Verify `docker compose ps` shows `db` container running
2. Confirm `/healthz` returns `{"status": "ok", "database": "postgres"}`
3. Test trace ID: `curl -H "X-Trace-Id: test" http://localhost:8000/healthz -v`
4. Install UI deps: `uv add streamlit rich typer httpx pandas`

🔜 Session 06 builds Streamlit dashboards and Typer UX on top of this database; Session 07 brings full TypeScript/Vite clients plus expanded testing/logging.

## Troubleshooting
- **`psycopg.OperationalError: connection refused`** → ensure Docker Desktop is running and port 5432 isn’t taken; restart with `docker compose down && docker compose up -d`.
- **`permission denied to create database`** → connect as the `postgres` superuser or grant `CREATEDB` to `movie` role: `ALTER ROLE movie CREATEDB;`.
- **Alembic fails with `No such table`** → check that `MOVIE_DATABASE_URL` is exported when running migrations; avoid mixing SQLite + Postgres URLs.
- **Tests hang on DB drop** → make sure you terminate active connections before `DROP DATABASE` (see `_drop_test_db`).

## Student Success Criteria
- [ ] Dockerized Postgres is running locally with persistent volume + health checks.
- [ ] FastAPI CRUD + `/healthz` talk to Postgres via SQLModel + Alembic migrations.
- [ ] pytest fixtures spin up and tear down dedicated Postgres databases without manual cleanup.
- [ ] Runbook/README documents the new workflow so Streamlit (Session 06) can reuse it immediately.

Schedule mentoring time before Session 06 if any box is unchecked.

## AI Prompt Seeds
- “Given a SQLModel app currently on SQLite, write the code/commands to migrate it to PostgreSQL with Alembic, Docker Compose, and health checks.”
- “Generate pytest fixtures that create/destroy a temporary PostgreSQL database per test module using psycopg.”
- “Draft a Typer CLI command that seeds PostgreSQL with sample movies using SQLModel sessions.”
