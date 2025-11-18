# Session 05 – PostgreSQL Foundations for the Movie Service

- **Date:** Monday, Dec 1, 2025
- **Theme:** Graduate from local SQLite to production-colored PostgreSQL with Docker Compose, Alembic migrations, connection health checks, and Postgres-aware tests.

## Session Story
Session 04 proved the repository abstraction by persisting to SQLite. Session 05 keeps the same FastAPI surface but swaps the backing store for PostgreSQL, adds connection-pool guardrails, and teaches every team how to run, migrate, and test against the database they’ll ship to staging and Exercise 3. Students leave with Docker Compose running Postgres, updated configs + migrations, health endpoints with trace IDs, and pytest fixtures that create/tear down disposable Postgres databases.

## Learning Objectives
- Provision PostgreSQL locally with Docker Compose and manage credentials via `pydantic-settings`.
- Point SQLModel, Alembic, and uv-based scripts at Postgres URLs instead of SQLite.
- Implement connection pooling, CORS, and health checks that prove DB reachability.
- Seed and reset Postgres safely with Typer/uv scripts.
- Write pytest fixtures that create isolated Postgres databases per run.

## Deliverables (What You’ll Build)
- `docker-compose.yml` running Postgres (plus optional admin tools).
- `.env(.example)` entries for `MOVIE_DATABASE_URL`, pool settings, and optional test URLs.
- `movie_service/app/database.py` configured for psycopg + pooling.
- Alembic migrations targeted at Postgres types.
- Seed + diagnostic scripts (Typer CLI) connected to the Postgres engine.
- pytest fixtures that create/drop throwaway Postgres databases (e.g., `movies_test_<uuid>`).

## Toolkit Snapshot
- **PostgreSQL 16** – production-grade relational database with concurrency + JSONB.
- **psycopg 3** – default sync driver for SQLModel/SQLAlchemy.
- **Docker Compose** – standard way to run Postgres consistently on every laptop.
- **Alembic** – captures schema history as revisions before EX3 deployments.
- **pytest** – integration tests now talk to real Postgres databases.
- **Typer/Rich** – optional CLI helpers for seeds + ops automation.

## Before Class (JiTT)
0. **Workflow reminder:** open `docs/workflows/ai-assisted/templates/feature-brief.md` and copy one per slice (Docker Compose, settings/env, database module, Alembic wiring, health/CORS, seed/tests). Stick to ≤150 LOC chunks and capture verification commands so Codex + reviewers stay aligned.
1. Finish Session 04 and ensure SQLite tests still pass.
2. Install Docker Desktop (or Colima) and confirm `docker compose version` works.
3. Add psycopg: `uv add "psycopg[binary]"` and verify with `uv run python -c "import psycopg"`.
4. Create `docker-compose.yml`:
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
5. Update `.env.example` / `.env`:
   ```ini
   MOVIE_DATABASE_URL="postgresql+psycopg://movie:movie@localhost:5432/movies"
   MOVIE_DB_HOST="localhost"
   MOVIE_DB_NAME="movies"
   MOVIE_DB_USER="movie"
   MOVIE_DB_PASSWORD="movie"
   ```
6. Start the database: `docker compose up -d db` and verify with `pgcli postgresql://movie:movie@localhost:5432/movies -c "SELECT 1;"`.
7. Run `uv run alembic upgrade head` so the Postgres schema matches the SQLite models before class starts.

## Session Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Recap & intent | 10 min | Discussion | Why SQLite won’t survive concurrent clients; Postgres expectations. |
| Postgres architecture primer | 20 min | Talk + whiteboard | Connection strings, pools, Alembic env vars, Docker Compose. |
| **Part B – Lab 1** | **45 min** | **Guided coding** | **Provision Postgres + migrate SQLModel + health checks.** |
| Break | 10 min | — | Encourage pgcli exploration, share `docker compose` tips. |
| **Part C – Lab 2** | **45 min** | **Guided testing** | **Seeds, fixtures, Alembic scripts, multi-DB strategy.** |
| Wrap-up & Streamlit preview | 10 min | Q&A | How Session 06’s UI builds on this backend. |

## Lab 1 – Provision Postgres + migrate SQLModel (45 min)
Goal: replace SQLite-specific assumptions with Postgres-friendly config and confirm CRUD still works.

> Use individual briefs for Docker Compose + env vars, config/database updates, Alembic changes, and FastAPI wiring. Generate/review in that order so each chunk stays within the AI-assisted workflow guardrails.

### Step 0 – Boot Postgres
```bash
docker compose up -d db
pg_isready -h localhost -p 5432 -d movies -U movie
```
If the readiness probe fails, inspect `docker compose logs db` before proceeding.

### Step 1 – Update settings
`movie_service/app/config.py`
````python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Movie Service"
    database_url: str = "postgresql+psycopg://movie:movie@localhost:5432/movies"
    database_echo: bool = False
    pool_size: int = 5
    pool_timeout: int = 30

    model_config = SettingsConfigDict(env_prefix="MOVIE_", env_file=".env", extra="ignore")
````
Add `MOVIE_DATABASE_URL_TEST` later for pytest.

### Step 2 – Configure the Postgres engine
`movie_service/app/database.py`
````python
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
````
`pool_pre_ping=True` protects the app when the container restarts or idle connections go stale.

### Step 3 – Align Alembic with Postgres
`migrations/env.py` excerpt:
````python
from movie_service.app.database import engine
from movie_service.app.config import Settings
from sqlmodel import SQLModel

settings = Settings()

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
````
Commands:
```bash
uv run alembic revision --autogenerate -m "migrate to postgres"
uv run alembic upgrade head
```
Inspect the revision to confirm Postgres types (serial, timestamptz, etc.).

### Step 4 – Add health + middleware support
`movie_service/app/main.py` snippet:
````python
import uuid

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine
from .dependencies import RepositoryDep, SettingsDep
from .models import MovieCreate, MovieRead

app = FastAPI(title="Movie Service", version="0.4.0")
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
    trace_id = request.headers.get("X-Trace-Id") or f"req-{uuid.uuid4().hex[:8]}"
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "postgres"}
````
Reuse the existing movie routes from Session 04; CRUD logic stays unchanged.

### Step 5 – Smoke test against Postgres
```bash
uv run uvicorn movie_service.app.main:app --reload
curl http://localhost:8000/healthz -H "X-Trace-Id: test-123" -v
curl http://localhost:8000/movies
```
Successful responses prove FastAPI, SQLModel, Alembic, and CORS are now Postgres-aware.

## Lab 2 – Seeds, fixtures, and safety rails (45 min)
Goal: treat Postgres as the default datastore for dev + tests.

> Continue the slice-by-slice habit: one brief for the Typer seed script, another for pytest fixtures, etc. Annotate diffs before moving to the next segment.

### Step 1 – Typer seed script
`scripts/db.py`
````python
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


if __name__ == "__main__":
    app()
````
Run `uv run python scripts/db.py bootstrap --sample 3`.

### Step 2 – Test database strategy
`movie_service/tests/conftest.py`
````python
import uuid

import psycopg
import pytest
from sqlmodel import SQLModel, Session, create_engine

from movie_service.app.dependencies import get_repository
from movie_service.app.main import app
from movie_service.app.repository_db import MovieRepository

DB_TEMPLATE = "postgresql+psycopg://movie:movie@localhost:5432/{db_name}"
ADMIN_URL = "postgresql://movie:movie@localhost:5432/postgres"


def _create_test_db() -> str:
    db_name = f"movies_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {db_name}")
    return DB_TEMPLATE.format(db_name=db_name)


def _drop_test_db(url: str) -> None:
    db_name = url.rsplit("/", 1)[-1]
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{db_name}'"
        )
        conn.execute(f"DROP DATABASE IF EXISTS {db_name}")


@pytest.fixture()
def engine_url():
    url = _create_test_db()
    try:
        yield url
    finally:
        _drop_test_db(url)


@pytest.fixture()
def session(engine_url):
    engine = create_engine(engine_url)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def override_repo(session):
    app.dependency_overrides[get_repository] = lambda: MovieRepository(session)
    yield
    app.dependency_overrides.pop(get_repository, None)
````
These fixtures provision a clean database for every test session and remove it afterward.

### Step 3 – Document and monitor
- Add `docs/runbooks/postgres.md` (or README section) covering Docker commands, credentials, and troubleshooting.
- Capture `pg_dump` + restore commands for backups.
- Log `db_host`, `db_name`, and the trace ID when `/healthz` fails; these details will feed Session 07 diagnostics.

### Step 4 – Regression checks
- `docker compose ps` shows the Postgres container running.
- `uv run pytest -q` creates/drops databases cleanly.
- `uv run alembic upgrade head` targets the Postgres URL.

## Optional Lab – Text-to-SQL PoC (30 min)
Use only if time allows; it showcases how to bolt a local LLM onto the hardened backend.

1. Run a local OpenAI-compatible model (e.g., `llama-server`).
2. Extend `movie_service/app/config.py` with `llm_base_url`, `llm_api_key`, and `llm_model` defaults and mirror them in `.env.example`.
3. Create `movie_service/app/llm.py`:
   ````python
   from openai import OpenAI

   from .config import Settings

   settings = Settings()
   client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

   TEXT2SQL_SYSTEM_PROMPT = """You are a PostgreSQL SQL generator for the movies table...
   Only return SELECT statements with LIMIT 50 unless told otherwise.""".strip()


   def generate_sql_from_nl(question: str) -> str:
       response = client.chat.completions.create(
           model=settings.llm_model,
           messages=[
               {"role": "system", "content": TEXT2SQL_SYSTEM_PROMPT},
               {"role": "user", "content": question},
           ],
           temperature=0,
       )
       return (response.choices[0].message.content or "").strip("`")
   ````
4. Guard execution in `movie_service/app/text2sql.py` (regex-allow only SELECT, block destructive verbs) and run the SQL via a SQLModel session.
5. Mount the feature under `/admin/sql-assistant` with a simple POST route that returns `{ "sql": ..., "rows": [...] }` or a validation error.

## Wrap-Up & Success Criteria
- [ ] Dockerized Postgres is running locally with a persistent volume and health checks.
- [ ] FastAPI CRUD + `/healthz` talk to Postgres via SQLModel + Alembic migrations.
- [ ] pytest fixtures create/destroy dedicated Postgres databases without manual cleanup.
- [ ] Typer/uv scripts seed + reset data safely.
- [ ] Runbook/README documents the workflow so Streamlit (Session 06) can plug in immediately.

## Session 06 Preview – Building User Interfaces
| Component | Session 05 (Current) | Session 06 (UI Layer) | Change? |
| --- | --- | --- | --- |
| FastAPI backend | Postgres, trace IDs, CORS | Reused verbatim | None |
| Streamlit dashboard | — | New dashboard hitting `/movies` | Add `frontend/dashboard.py` |
| Typer CLI | Seeds only | Adds admin UX commands | Extend scripts |
| HTTP client | — | `frontend/client.py` (httpx wrapper) | New |
| Dependencies | psycopg, sqlmodel | + streamlit, typer, rich, httpx, pandas | Install |

Action items before Session 06:
1. Ensure `docker compose ps` shows `db` healthy.
2. Confirm `/healthz` returns `{"status": "ok", "database": "postgres"}` and echoes trace IDs.
3. Install UI deps: `uv add streamlit rich typer httpx pandas`.
4. Capture screenshots/logs of health + seed commands for reference during the UI lab.

## Troubleshooting
- **`psycopg.OperationalError: connection refused`** → make sure Docker Desktop is running and port 5432 is free; restart with `docker compose down && docker compose up -d`.
- **`permission denied to create database`** → connect as the `postgres` superuser or grant `CREATEDB` to the `movie` role: `docker compose exec db psql -c "ALTER ROLE movie CREATEDB;"`.
- **Alembic cannot find tables** → verify `MOVIE_DATABASE_URL` is exported when running migrations and that `movie_service.app.models` is imported in `env.py`.
- **Tests hang on drop** → terminate active connections before `DROP DATABASE` (see `_drop_test_db`).

## AI Prompt Seeds
- “Given a SQLModel app currently on SQLite, write the code/commands to migrate it to PostgreSQL with Alembic, Docker Compose, and health checks.”
- “Generate pytest fixtures that create/destroy a temporary PostgreSQL database per test module using psycopg.”
- “Draft a Typer CLI command that seeds PostgreSQL with sample movies using SQLModel sessions.”
