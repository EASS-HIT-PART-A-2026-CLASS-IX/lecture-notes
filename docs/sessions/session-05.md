# Session 05 – PostgreSQL Foundations for the Movie Service

- **Date:** Monday, Dec 1, 2025
- **Theme:** Graduate from local SQLite to production-colored PostgreSQL with Docker Compose, Alembic migrations, health checks, and Postgres-aware tests.

## Session Story
Session 04 proved the repository abstraction by persisting to SQLite. Session 05 keeps the exact HTTP contract but swaps SQLite for Postgres, adds connection protection, and wires health/CORS/trace IDs so future UIs (Streamlit, React) can plug in. By the end, every student can run, migrate, seed, and test against Postgres with disposable databases.

## Learning Objectives
- Provision Postgres with Docker Compose and manage credentials via `pydantic-settings`.
- Configure SQLModel + Alembic to target Postgres URLs (no SQLite leftovers).
- Add health checks, CORS, and trace IDs that survive container restarts.
- Seed/reset Postgres with Typer scripts and cache-safe pytest fixtures.
- Verify CRUD works end-to-end with the same FastAPI routes as Session 04.

## Deliverables (What You’ll Build)
- `docker-compose.yml` running Postgres with a persisted volume.
- `.env(.example)` entries for Postgres URLs and pool settings.
- `movie_service/app/database.py` tuned for psycopg + pooling.
- Alembic pointed at Postgres with an initial migration applied.
- Typer seed/reset script (`scripts/db.py`) plus pytest fixtures that create/drop throwaway Postgres databases.
- Updated health endpoint + CORS/trace middleware in `movie_service/app/main.py`.

## Toolkit Snapshot
- **PostgreSQL 16** – durable relational database.
- **psycopg 3** – sync driver for SQLModel/SQLAlchemy.
- **Docker Compose** – reproducible local Postgres.
- **Alembic** – migrations pointed at Postgres URLs.
- **pytest** – Postgres-aware fixtures for isolated tests.
- **Typer/Rich** – CLI helpers for seeds + ops automation.

## Before Class (JiTT)
0. **Workflow reminder:** copy `docs/workflows/ai-assisted/templates/feature-brief.md` per slice (Compose, env/settings, database module, Alembic, health/CORS, seeds/tests). Keep changes under the 150‑LOC limit from `docs/workflows/ai-assisted/README.md`.
1. Finish Session 04 and confirm SQLite tests pass: `uv run pytest movie_service/tests -v`.
2. Install Postgres + tooling:
   ```bash
   docker compose version
   uv add "psycopg[binary]" sqlalchemy-utils
   ```
3. Create `docker-compose.yml` for Postgres:
   ```yaml
   services:
     db:
       image: postgres:16
       environment:
         POSTGRES_USER: movie
         POSTGRES_PASSWORD: movie
         POSTGRES_DB: movies
       ports: ["5432:5432"]
       volumes: [pgdata:/var/lib/postgresql/data]
   volumes:
     pgdata:
   ```
4. Extend `.env.example` / `.env`:
   ```ini
   MOVIE_DATABASE_URL="postgresql+psycopg://movie:movie@localhost:5432/movies"
   MOVIE_DATABASE_URL_TEST="postgresql+psycopg://movie:movie@localhost:5432/postgres"
   MOVIE_DATABASE_ECHO=false
   MOVIE_POOL_SIZE=5
   MOVIE_POOL_TIMEOUT=30
   ```
5. Start Postgres and verify connectivity:
   ```bash
   docker compose up -d db
   pg_isready -h localhost -p 5432 -d movies -U movie
   ```
6. Point Alembic at Postgres (details in Lab 1) and run `uv run alembic upgrade head` once to ensure the DB matches Session 04 models.

## Session Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Recap & intent | 10 min | Discussion | Why SQLite dies under concurrency; Postgres expectations. |
| Postgres primer | 20 min | Talk + board | URLs, pools, Alembic env vars, Compose. |
| **Part B – Lab 1** | **45 min** | **Guided coding** | **Swap SQLite → Postgres, health/CORS/trace.** |
| Break | 10 min | — | Logs + pgcli checks. |
| **Part C – Lab 2** | **45 min** | **Guided testing** | **Seeds, pytest fixtures, migrations.** |
| Wrap-up | 10 min | Q&A | Checklist + preview of Session 06. |

## Lab 1 – Move FastAPI to Postgres (45 min)
Goal: configure Postgres URLs, wire engine/pooling, align Alembic, and prove the app still serves the same CRUD contract.

> Stay slice-by-slice: env/settings → database module → Alembic → FastAPI wiring → smoke test.

### Step 0 – Boot Postgres
```bash
docker compose up -d db
pg_isready -h localhost -p 5432 -d movies -U movie
docker compose logs db | tail
```

### Step 1 – Settings for Postgres
`movie_service/app/config.py`
````python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Movie Service"
    database_url: str = "postgresql+psycopg://movie:movie@localhost:5432/movies"
    database_url_test: str | None = None
    database_echo: bool = False
    pool_size: int = 5
    pool_timeout: int = 30

    model_config = SettingsConfigDict(env_prefix="MOVIE_", env_file=".env", extra="ignore")
````

### Step 2 – Database module (psycopg + pooling)
`movie_service/app/database.py`
````python
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

from . import models  # ensure metadata is loaded
from .config import Settings

settings = Settings()
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.pool_size,
    pool_timeout=settings.pool_timeout,
    pool_pre_ping=True,
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
````

### Step 3 – Alembic on Postgres
1. If new: `uv run alembic init migrations`.
2. In `alembic.ini`, remove any hard-coded `sqlalchemy.url`; keep `script_location = migrations`.
3. `migrations/env.py` excerpt (replace SQLite logic):
   ````python
   from logging.config import fileConfig

   from alembic import context
   from sqlalchemy import engine_from_config, pool
   from sqlmodel import SQLModel

   from movie_service.app import models  # noqa: F401
   from movie_service.app.config import Settings

   config = context.config
   settings = Settings()
   config.set_main_option("sqlalchemy.url", settings.database_url)

   if config.config_file_name is not None:
       fileConfig(config.config_file_name)

   target_metadata = SQLModel.metadata


   def run_migrations_offline() -> None:
       url = config.get_main_option("sqlalchemy.url")
       context.configure(
           url=url,
           target_metadata=target_metadata,
           literal_binds=True,
           dialect_opts={"paramstyle": "named"},
       )
       with context.begin_transaction():
           context.run_migrations()


   def run_migrations_online() -> None:
       connectable = engine_from_config(
           config.get_section(config.config_ini_section, {}),
           prefix="sqlalchemy.",
           poolclass=pool.NullPool,
       )
       with connectable.connect() as connection:
           context.configure(connection=connection, target_metadata=target_metadata)
           with context.begin_transaction():
               context.run_migrations()


   if context.is_offline_mode():
       run_migrations_offline()
   else:
       run_migrations_online()
   ````
4. Commands:
   ```bash
   uv run alembic revision --autogenerate -m "switch to postgres"
   uv run alembic upgrade head
   uv run alembic current
   ```

### Step 4 – FastAPI wiring (CORS + trace IDs + health)
`movie_service/app/main.py` excerpt:
````python
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine
from .dependencies import RepositoryDep, SettingsDep
from .models import MovieCreate, MovieRead

app = FastAPI(title="Movie Service", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:5173"],
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
Reuse the Session 04 CRUD routes; only the engine/middleware changed.

### Step 5 – Smoke test
```bash
uv run uvicorn movie_service.app.main:app --reload
curl -i -H "X-Trace-Id: smoke-1" http://localhost:8000/healthz
curl http://localhost:8000/movies
```
Expect `{"status": "ok", "database": "postgres"}` and empty movie list on a clean DB.

## Lab 2 – Seeds, Fixtures, Regression (45 min)
Goal: seed Postgres safely and keep tests hermetic with throwaway databases.

### Step 1 – Typer seed/reset script
`scripts/db.py` (describe; create during lab):
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
        if repo.list():
            typer.echo("Database already seeded; skipping.")
            return
        for idx in range(sample):
            repo.create(MovieCreate(title=f"Sample {idx+1}", year=2010 + idx, genre="sci-fi"))
    typer.echo(f"Seeded {sample} movies.")


if __name__ == "__main__":
    app()
````
Run: `uv run python scripts/db.py bootstrap --sample 3`.

### Step 2 – Postgres pytest fixtures (throwaway DBs)
`movie_service/tests/conftest.py` excerpt:
````python
import uuid

import psycopg
import pytest
from sqlmodel import SQLModel, Session, create_engine, delete

from movie_service.app.dependencies import get_repository
from movie_service.app.main import app
from movie_service.app.models import Movie
from movie_service.app.repository_db import MovieRepository

ADMIN_URL = "postgresql://movie:movie@localhost:5432/postgres"
DB_TEMPLATE = "postgresql+psycopg://movie:movie@localhost:5432/{db_name}"


def _create_test_db() -> str:
    name = f"movies_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    return DB_TEMPLATE.format(db_name=name)


def _drop_test_db(url: str) -> None:
    name = url.rsplit("/", 1)[-1]
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s", (name,))
        conn.execute(f'DROP DATABASE IF EXISTS "{name}"')


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
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def override_repo(session):
    app.dependency_overrides[get_repository] = lambda: MovieRepository(session)
    yield
    app.dependency_overrides.pop(get_repository, None)
    session.exec(delete(Movie))
    session.commit()
````  
Each test module gets its own database; teardown drops the DB even if tests fail.

### Step 3 – Regression commands
```bash
uv run alembic upgrade head
uv run python scripts/db.py bootstrap --sample 3
uv run pytest movie_service/tests -v
```

## Wrap-Up & Success Criteria
- [ ] Postgres container healthy (`docker compose ps`, `pg_isready`).
- [ ] `/healthz` returns Postgres status + echoes `X-Trace-Id`.
- [ ] Alembic `upgrade head` succeeds against Postgres URL.
- [ ] Seed script adds movies; reruns are idempotent.
- [ ] Pytest uses throwaway Postgres DBs (no writes to dev DB).
- [ ] README/docs updated with Compose/Alembic/seed/test commands.

## Session 06 Preview – UI Layer
| Component | Session 05 (Postgres) | Session 06 (UI) | Change? |
| --- | --- | --- | --- |
| Backend | FastAPI + Postgres + CORS/trace IDs | Reused verbatim | None |
| Dependencies | psycopg, sqlmodel | + streamlit, typer, rich, httpx, pandas | Add |
| Scripts | Seed/reset | Add UI-focused Typer commands | Extend |
| Health | `/healthz` w/ trace IDs | Reused on UI calls | None |
| Tests | Postgres DB per run | Same fixtures reused | None |

Action items before Session 06:
1. Ensure `docker compose ps` shows `db` healthy.
2. `curl http://localhost:8000/healthz` returns status and trace header.
3. Install UI deps: `uv add streamlit rich typer httpx pandas`.
4. Keep seed + pytest commands handy for demos.

## Troubleshooting
- **`psycopg.OperationalError: connection refused`** → ensure Docker Desktop/Colima is running and port 5432 is free; restart with `docker compose down && docker compose up -d`.
- **`permission denied to create database`** → grant `CREATEDB` to the `movie` role: `docker compose exec db psql -c "ALTER ROLE movie CREATEDB;"`.
- **Alembic still targets SQLite** → delete hard-coded URLs in `alembic.ini` and verify `Settings().database_url` points to Postgres.
- **Tests hang on drop** → terminate active connections before `DROP DATABASE` (see `_drop_test_db`).
- **CORS blocked** → ensure `allow_origins` includes `http://localhost:8501` and `http://localhost:5173`.
