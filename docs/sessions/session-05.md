# Session 05 – Multi-DB Modes + Postgres Hardening

- **Date:** Monday, 30/03/2026
- **Theme:** Keep the FastAPI contract stable while making the repository facade run in three modes: in-memory, SQLite, and Postgres. Add health/CORS/trace protections and keep migrations/tests working regardless of backend.

## Session Story
Session 03 shipped the in-memory backend; Session 04 swapped in SQLite + Alembic without touching routes. Session 05 makes that abstraction explicit: you choose the datastore via config, keep the same models/routes, and prove the same migrations/tests run against SQLite (offline) and Postgres (compose). Memory stays available for ultra-fast unit tests. The outcome is a single codebase that can run everywhere—from ephemeral tests to classroom laptops to production-colored Postgres.

## Learning Objectives
- Expose a `db_mode` switch (memory | sqlite | postgres) with sensible defaults so environments pick their own backend without code edits.
- Drive SQLModel/Alembic from environment URLs and keep the migration history identical across SQLite and Postgres.
- Maintain the repository facade so FastAPI routes never import storage-specific classes.
- Add health, CORS, and trace ID middleware that works in every mode.
- Seed and test against all backends with repeatable commands.

## Deliverables (What You’ll Build)
- Env-driven settings (`MOVIE_DB_MODE`, `MOVIE_DATABASE_URL_SQLITE`, `MOVIE_DATABASE_URL_POSTGRES`, `MOVIE_DATABASE_URL_TEST`, pool flags) captured in `.env.example`, plus a computed `database_url` property.
- `docker-compose.yml` (provided in repo root) for Postgres with a persisted volume.
- `movie_service/app/database.py` that resolves the correct engine per mode (memory → no engine, sqlite → file path + `check_same_thread`, postgres → psycopg + pooling).
- `movie_service/app/dependencies.py` with a repository factory/protocol that returns the in-memory repository or the SQLModel-backed repository without changing route signatures.
- Alembic configured to read URLs from settings; the same migration set applies to SQLite and Postgres.
- Typer/Rich CLI for seeding/resetting the chosen backend.
- Pytest fixtures that default to memory, can target SQLite files, and optionally spin up throwaway Postgres DBs.

## Toolkit Snapshot
- **FastAPI** + **SQLModel** – shared models for API + persistence.
- **Alembic** – migration history that points at the active `MOVIE_DATABASE_URL`.
- **psycopg 3** – Postgres driver; only used when `db_mode=postgres`.
- **Docker Compose** – reproducible Postgres for local/dev demos.
- **pytest** – fixtures per mode; dependency overrides for repositories.
- **Typer/Rich** – CLI UX for seeds/resets regardless of backend.

## Before Class (JiTT)
0. Workflow reminder: keep briefs per slice under the 150‑LOC limit in `docs/workflows/ai-assisted/README.md`.
1. Finish Session 04 and confirm SQLite path is green: `uv run pytest movie_service/tests -v`.
2. Add Postgres + tooling (needed only for postgres mode):
   ```bash
   docker compose version
   uv add "psycopg[binary]" rich typer
   ```
   Add `sqlalchemy-utils` only if you rely on its Postgres helpers for throwaway DB creation.
3. Extend env templates:
   ```ini
   MOVIE_DB_MODE="sqlite"  # options: memory | sqlite | postgres
   MOVIE_DATABASE_URL_SQLITE="sqlite:///./data/movies.db"
   MOVIE_DATABASE_URL_POSTGRES="postgresql+psycopg://movie:movie@localhost:5432/movies"
   MOVIE_DATABASE_URL_TEST="sqlite:///./data/movies-test.db"  # override per test run
   MOVIE_DATABASE_ECHO=false
   MOVIE_POOL_SIZE=5
   MOVIE_POOL_TIMEOUT=30
   ```
   Keep `MOVIE_DATABASE_URL` as a computed property in code (see Lab 1).
   `.env.example` includes these keys; copy it to `.env` and adjust paths before class.
4. Create/confirm writable `data/` directory and ignore it in git.
5. (Optional) Start Postgres for the postgres path:
   Compose file lives at repo root (`docker-compose.yml`).
   ```bash
   docker compose up -d db
   pg_isready -h localhost -p 5432 -d movies -U movie
   ```
6. Smoke imports:
   ```bash
   uv run python - <<'PY'
   import sqlmodel, psycopg, typer  # noqa: F401
   print("SQLModel + psycopg + Typer ready")
   PY
   ```
7. Baseline: `uv run pytest movie_service/tests -v` should still pass in default memory/sqlite mode before class.

## Session Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Recap & intent | 10 min | Discussion | Why we keep three storage modes; how the facade prevents churn. |
| **Part A – Mode switch design** | 20 min | Board + talk | Settings + dependency diagram for memory/sqlite/postgres. |
| **Part B – Lab 1** | **45 min** | **Guided build** | **Wire config + dependencies for multi-DB, add health/CORS/trace.** |
| Break | 10 min | — | Confirm URLs + logs per mode. |
| **Part C – Lab 2** | **45 min** | **Guided testing** | **Migrations, seeds, pytest matrix (memory/sqlite/postgres).** |
| Wrap-up | 10 min | Q&A | Checklist + next experiments. |

## Lab 1 – Wire Multi-DB Modes (45 min)
Goal: make the repository + dependency layer choose memory, SQLite, or Postgres based on settings while keeping the HTTP contract unchanged.

> Keep the interfaces identical: `RepositoryProtocol.list/create/get/delete` is the only shape routes see.

### Step 0 – (Optional) Boot Postgres
```bash
docker compose up -d db
pg_isready -h localhost -p 5432 -d movies -U movie
docker compose logs db | tail
```
`docker-compose.yml` ships with `postgres:15-alpine`, user/password `movie`, DB `movies`, and a persisted `pgdata` volume.

### Step 1 – Settings with a mode switch
`movie_service/app/config.py`
````python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Movie Service"
    db_mode: str = "sqlite"  # memory | sqlite | postgres
    database_url_sqlite: str = "sqlite:///./data/movies.db"
    database_url_postgres: str = "postgresql+psycopg://movie:movie@localhost:5432/movies"
    database_url_test: str | None = None
    database_echo: bool = False
    pool_size: int = 5
    pool_timeout: int = 30

    @property
    def database_url(self) -> str:
        if self.db_mode == "postgres":
            return self.database_url_postgres
        return self.database_url_sqlite

    model_config = SettingsConfigDict(env_prefix="MOVIE_", env_file=".env", extra="ignore")
````

### Step 2 – Engine + session factory per mode
`movie_service/app/database.py`
````python
from collections.abc import Generator
from contextlib import nullcontext
from typing import Annotated, Optional

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from .config import Settings


def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


def _build_engine(settings: Settings):
    if settings.db_mode == "memory":
        return None
    url = settings.database_url_test or settings.database_url
    kwargs: dict = {"echo": settings.database_echo}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    if url.startswith("postgresql"):
        kwargs.update(
            pool_size=settings.pool_size,
            pool_timeout=settings.pool_timeout,
            pool_pre_ping=True,
        )
    return create_engine(url, **kwargs)


engine = _build_engine(Settings())


def init_db() -> None:
    from . import models  # noqa: F401

    if engine:
        SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Optional[Session], None, None]:
    if engine is None:
        with nullcontext():
            yield None  # repository factory ignores session in memory mode
        return
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Optional[Session], Depends(get_session)]
````

### Step 3 – Repository facade (memory + SQLModel)
`movie_service/app/dependencies.py`
````python
from typing import Annotated, Protocol

from fastapi import Depends

from .database import SessionDep, SettingsDep
from .repository import MovieRepository as InMemoryRepository
from .repository_db import MovieRepository as SqlRepository


class MovieRepositoryProtocol(Protocol):
    def list(self, *, skip: int = 0, limit: int = 100): ...
    def create(self, payload): ...
    def get(self, movie_id: int): ...
    def delete(self, movie_id: int): ...


def get_repository(settings: SettingsDep, session: SessionDep) -> MovieRepositoryProtocol:
    if settings.db_mode == "memory":
        return InMemoryRepository()
    if session is None:
        raise RuntimeError("Database session required for non-memory modes")
    return SqlRepository(session)


RepositoryDep = Annotated[MovieRepositoryProtocol, Depends(get_repository)]
````

### Step 4 – Health/CORS/trace that works in every mode
`movie_service/app/main.py` excerpt:
````python
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine, SettingsDep
from .dependencies import RepositoryDep
from .models import MovieCreate, MovieRead

app = FastAPI(title="Movie Service", version="0.5.0")
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
def healthcheck(settings: SettingsDep) -> dict[str, str]:
    if engine:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    backend = settings.db_mode if engine else "memory"
    return {"status": "ok", "database": backend}
````  
Reuse the Session 03/04 CRUD routes unchanged; only the engine/middleware changed.

### Step 5 – Smoke test each mode
```bash
# Memory (fastest for demos/tests)
MOVIE_DB_MODE=memory uv run uvicorn movie_service.app.main:app --reload

# SQLite (offline durable)
MOVIE_DB_MODE=sqlite uv run uvicorn movie_service.app.main:app --reload

# Postgres (production-colored)
MOVIE_DB_MODE=postgres uv run uvicorn movie_service.app.main:app --reload
curl -i -H "X-Trace-Id: smoke-1" http://localhost:8000/healthz
curl http://localhost:8000/movies
```

## Lab 2 – Migrations, Seeds, Tests per Mode (45 min)
Goal: run the same migration/seed/test story regardless of backend.

> One migration history, multiple URLs. Never fork schemas per mode.

### Step 1 – Alembic points at settings
1. Ensure `alembic.ini` leaves `sqlalchemy.url` empty; `migrations/env.py` should read:
   ````python
   from sqlmodel import SQLModel

   from movie_service.app.config import Settings

   settings = Settings()
   config.set_main_option("sqlalchemy.url", settings.database_url)
   target_metadata = SQLModel.metadata
   ````
2. Commands per backend:
   ```bash
   MOVIE_DB_MODE=sqlite uv run alembic upgrade head
   MOVIE_DB_MODE=postgres uv run alembic upgrade head
   ```

### Step 2 – Typer seed/reset that respects the mode
`scripts/db.py` excerpt (new Typer CLI; replaces the Session 04 `seed_db` helper):
````python
import typer
from sqlmodel import Session

from movie_service.app.config import Settings
from movie_service.app.database import engine, init_db
from movie_service.app.models import MovieCreate
from movie_service.app.repository import MovieRepository as MemoryRepo
from movie_service.app.repository_db import MovieRepository as DbRepo

app = typer.Typer(help="Database utilities")


@app.command()
def bootstrap(sample: int = 5) -> None:
    settings = Settings()
    if settings.db_mode == "memory":
        repo = MemoryRepo()
        for idx in range(sample):
            repo.create(MovieCreate(title=f"Sample {idx+1}", year=2010 + idx, genre="sci-fi"))
        typer.echo("Seeded in-memory repo (non-persistent).")
        return

    init_db()
    with Session(engine) as session:
        repo = DbRepo(session)
        if repo.list():
            typer.echo("Database already seeded; skipping.")
            return
        for idx in range(sample):
            repo.create(MovieCreate(title=f"Sample {idx+1}", year=2010 + idx, genre="sci-fi"))
        session.commit()
    typer.echo(f"Seeded {sample} movies in {settings.db_mode}.")


if __name__ == "__main__":
    app()
````
Place this file at `scripts/db.py` in your project root (or under `movie_service/scripts/db.py` if you keep scripts inside the package); adjust imports to match your layout.
Run: `MOVIE_DB_MODE=sqlite uv run python scripts/db.py bootstrap --sample 3` (swap to postgres as needed).

### Step 3 – pytest matrix
- **Memory (default):**
  ```bash
  MOVIE_DB_MODE=memory uv run pytest movie_service/tests -v
  ```
- **SQLite (temp file per test module):** reuse Session 04 fixtures; ensure `database_url_test` points to a temp path and drop the file in teardown.
- **Postgres (optional):** reuse the throwaway DB fixture from below; ensure the `movie` role has `CREATEDB`.

`movie_service/tests/conftest.py` excerpt for Postgres:
````python
import uuid

import psycopg
import pytest
from sqlmodel import SQLModel, Session, create_engine

from movie_service.app.dependencies import get_repository
from movie_service.app.main import app
from movie_service.app.models import Movie
from movie_service.app.repository_db import MovieRepository

ADMIN_URL = "postgresql://movie:movie@localhost:5432/postgres"
DB_TEMPLATE = "postgresql+psycopg://movie:movie@localhost:5432/{db_name}"
````  
(Use the same create/drop helpers from Session 04; swap URL based on `MOVIE_DB_MODE`.)

### Step 4 – Regression commands
```bash
MOVIE_DB_MODE=sqlite uv run alembic upgrade head
MOVIE_DB_MODE=sqlite uv run python scripts/db.py bootstrap --sample 3
MOVIE_DB_MODE=memory uv run pytest movie_service/tests -v
MOVIE_DB_MODE=postgres uv run pytest movie_service/tests -v  # optional if Postgres running
```

## Wrap-Up & Success Criteria
- [ ] `MOVIE_DB_MODE` toggles between memory/sqlite/postgres without code changes.
- [ ] `/healthz` reports the active backend and echoes `X-Trace-Id`.
- [ ] Alembic `upgrade head` succeeds for SQLite and Postgres URLs.
- [ ] Seed script is idempotent per backend.
- [ ] Pytest passes in memory mode; optional runs green for SQLite/Postgres fixtures.
- [ ] README/docs updated with Compose/Alembic/seed/test commands per mode.

## Next steps
- Keep `docker compose ps` handy to ensure Postgres is healthy when using that mode.
- Add CI matrix jobs for memory + SQLite; gate Postgres behind an opt-in service job.
- Wire Streamlit/React clients to the CORS/trace-aware API once health checks pass.

## Troubleshooting
- **`psycopg.OperationalError: connection refused`** → ensure Docker Desktop/Colima is running and port 5432 is free; restart with `docker compose down && docker compose up -d`.
- **`permission denied to create database`** → grant `CREATEDB` to the `movie` role: `docker compose exec db psql -c "ALTER ROLE movie CREATEDB;"`.
- **Alembic still targets SQLite** → delete hard-coded URLs in `alembic.ini` and verify `Settings().database_url` points to the chosen backend.
- **Tests hang on drop** → terminate active connections before `DROP DATABASE` (see `_drop_test_db`).
- **CORS blocked** → ensure `allow_origins` includes `http://localhost:8501` and `http://localhost:5173`.
