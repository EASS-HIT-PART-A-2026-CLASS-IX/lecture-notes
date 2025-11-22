# Session 04 – Persisting the Movie Service (SQLite + SQLModel)

- **Date:** Monday, November 24, 2025
- **Theme:** Replace the in-memory repository with SQLite + SQLModel, wire FastAPI to real sessions, and back everything with migrations + tests.

## Session Story
Session 03 shipped the Movie Service with in-memory storage. Session 04 keeps the same HTTP contract but persists to SQLite through SQLModel, proving the repository abstraction, adding Alembic migrations, and hardening pytest fixtures so every test runs in a throwaway database. Students leave with durable data, migrations, and a repeatable seed script they can trust in later sessions.

## Instructor Notes
- `uv run pytest movie_service/tests -v` (baseline still green)
- Create the SQLite file once:
  ```bash
  uv run python - <<'PY'
  from movie_service.app.database import init_db
  init_db()
  print('Created data/movies.db')
  PY
  ```
- `uv run alembic upgrade head` and confirm `data/movies.db` timestamps change
- `uv run python -m movie_service.scripts.seed_db` twice to verify idempotent seeding
- Smoke `uv run uvicorn movie_service.app.main:app --reload` then `curl http://localhost:8000/health` and `curl http://localhost:8000/movies`
- Ensure `.gitignore` contains `data/` and the folder is writable on classroom machines

## Learning Objectives
- Model movie data with SQLModel tables while keeping request/response schemas intact.
- Configure a SQLite engine and FastAPI dependency that hands out scoped SQLModel sessions.
- Replace the dict-backed repository with SQLModel CRUD without changing the routes.
- Run pytest against isolated SQLite files to prevent cross-test contamination.
- Capture schema history with Alembic and seed working data via uv scripts.

## Deliverables (What You’ll Build)
- `movie_service/app/models.py` SQLModel definitions (`Movie`, `MovieCreate`, `MovieRead`, `MovieUpdate`).
- `movie_service/app/database.py` with `engine`, `get_session`, and `init_db()` helpers.
- `movie_service/app/repository_db.py` backed by SQLModel sessions for CRUD.
- FastAPI routes that still satisfy the Session 03 HTTP contract while persisting rows.
- Alembic scaffolding + initial migration and `movie_service/scripts/seed_db.py`.
- pytest fixtures that create/destroy temp SQLite databases per test file.

## Toolkit Snapshot
- **SQLModel** – Pydantic + SQLAlchemy hybrid that keeps request/response models close to table definitions.
- **SQLite** – file-based relational database that requires zero services for local dev.
- **SQLAlchemy/Alembic** – connection management + migrations.
- **pytest** – hermetic tests with dependency overrides.
- **uv** – dependency manager + runner for scripts, migrations, and uvicorn.

## Before Class (JiTT)
0. **Workflow reminder:** copy `docs/workflows/ai-assisted/templates/feature-brief.md` for each slice (settings, database, models, repository, tests, Alembic/seed). Keep each change under the 150‑LOC guardrail in `docs/workflows/ai-assisted/README.md`.
1. Baseline: from the Session 03 code, run `uv run pytest movie_service/tests -v` and fix any failures. Commit/tag as `session-03-complete` so you can roll back easily.
2. Install the new dependencies inside `hello-uv`:
   ```bash
   uv add sqlmodel alembic sqlalchemy-utils
   ```
3. Create a writable data directory and ignore it:
   ```bash
   mkdir -p data
   grep -qx 'data/' .gitignore || printf "\n# SQLite data\ndata/\n" >> .gitignore
   ```
4. Extend `.env.example` and `.env`:
   ```ini
   MOVIE_DATABASE_URL="sqlite:///data/movies.db"
   ```
5. Smoke-test imports:
   ```bash
   uv run python - <<'PY'
   import sqlmodel, alembic  # noqa: F401
   print("SQLModel + Alembic ready")
   PY
   ```

## Session Agenda
| Time | Activity | Focus |
| --- | --- | --- |
| 10 min | Recap & intent | Why the repo abstraction makes the DB swap easy. |
| 20 min | Data modeling primer | SQLModel basics, table vs response models, migrations. |
| 45 min | **Lab 1** | **Database wiring + CRUD rewrite.** |
| 10 min | Break | Encourage quick sqlite browser checks. |
| 45 min | **Lab 2** | **Tests, Alembic, seed scripts.** |
| 10 min | Wrap-up | Checklist + preview of Session 05 (Postgres). |

## Lab 1 – Persist CRUD with SQLModel (45 min)
Goal: move the repository + routes from in-memory storage to SQLite without touching the FastAPI contract.

> Stay disciplined: one brief per subsystem (config, database, models, repository, routes). Generate → review → split before moving on so diffs stay small.

### Step 1: Configure Settings
`movie_service/app/config.py`
````python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Movie Service"
    default_page_size: int = 20
    feature_preview: bool = False
    database_url: str = "sqlite:///data/movies.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MOVIE_",
        extra="ignore",
    )
````

### Step 2: Create the database module
`movie_service/app/database.py`
````python
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

from .config import Settings
from . import models  # ensures SQLModel metadata includes Movie before create_all

settings = Settings()
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},  # SQLite + threads
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
````
Run the helper once so the database file exists (run from the project root):
```bash
uv run python - <<'PY'
from movie_service.app.database import init_db
init_db()
print("Created data/movies.db")
PY
```

### Step 3: Define SQLModel classes
`movie_service/app/models.py`
````python
from typing import Optional

from pydantic import model_validator
from sqlmodel import Field, SQLModel


class MovieBase(SQLModel):
    title: str
    year: int = Field(ge=1900, le=2100)
    genre: str


class Movie(MovieBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class MovieCreate(MovieBase):

    @model_validator(mode="after")
    def normalize_genre(self) -> "MovieCreate":
        self.genre = self.genre.title()
        return self


class MovieRead(MovieBase):
    id: int


class MovieUpdate(SQLModel):
    title: Optional[str] = None
    year: Optional[int] = Field(default=None, ge=1900, le=2100)
    genre: Optional[str] = None
````
`MovieUpdate` is ready for a future `PUT/PATCH` route; the contract today stays list/create/get/delete.

### Step 4: Database-backed repository
`movie_service/app/repository_db.py`
````python
from sqlmodel import Session, select

from .models import Movie, MovieCreate


class MovieRepository:
    """SQLite-backed storage for movies."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Movie]:
        return list(self.session.exec(select(Movie)))

    def create(self, payload: MovieCreate) -> Movie:
        record = Movie.model_validate(payload)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get(self, movie_id: int) -> Movie | None:
        return self.session.get(Movie, movie_id)

    def delete(self, movie_id: int) -> None:
        record = self.get(movie_id)
        if record:
            self.session.delete(record)
            self.session.commit()

    def delete_all(self) -> int:
        records = self.session.exec(select(Movie)).all()
        count = len(records)
        for record in records:
            self.session.delete(record)
        self.session.commit()
        return count
````

### Step 5: Dependency wiring + routes
`movie_service/app/dependencies.py`
````python
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from .config import Settings
from .database import get_session
from .repository_db import MovieRepository


def get_settings() -> Settings:
    return Settings()


def get_repository(session: Session = Depends(get_session)) -> MovieRepository:
    return MovieRepository(session)


SettingsDep = Annotated[Settings, Depends(get_settings)]
RepositoryDep = Annotated[MovieRepository, Depends(get_repository)]
````

`movie_service/app/main.py`
````python
from fastapi import FastAPI, HTTPException, status

from .dependencies import RepositoryDep, SettingsDep
from .models import MovieCreate, MovieRead

app = FastAPI(title="Movie Service", version="0.2.0")


@app.get("/health", tags=["diagnostics"])
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/movies", response_model=list[MovieRead], tags=["movies"])
def list_movies(repository: RepositoryDep) -> list[MovieRead]:
    return list(repository.list())


@app.post("/movies", response_model=MovieRead, status_code=status.HTTP_201_CREATED, tags=["movies"])
def create_movie(payload: MovieCreate, repository: RepositoryDep) -> MovieRead:
    return repository.create(payload)


@app.get("/movies/{movie_id}", response_model=MovieRead, tags=["movies"])
def read_movie(movie_id: int, repository: RepositoryDep) -> MovieRead:
    movie = repository.get(movie_id)
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie


@app.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["movies"])
def delete_movie(movie_id: int, repository: RepositoryDep) -> None:
    movie = repository.get(movie_id)
    if movie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    repository.delete(movie_id)
````

### Step 6: Manual smoke test
```bash
uv run uvicorn movie_service.app.main:app --reload
curl -X POST http://localhost:8000/movies \
  -H "Content-Type: application/json" \
  -d '{"title": "Inception", "year": 2010, "genre": "sci-fi"}'
curl http://localhost:8000/movies
```
Run after `init_db()` or `uv run alembic upgrade head`; records should persist in `data/movies.db` across restarts.

## Lab 2 – Tests, Migrations, Seeds (45 min)
Goal: prove the database-backed service is safe to refactor by adding hermetic pytest fixtures, an Alembic migration, and a repeatable seed script.

> Keep the briefs flowing: fixtures → Alembic → seed script. Commit between each chunk to avoid giant diffs.

### Step 1: Database-aware pytest fixtures
`movie_service/tests/conftest.py`
````python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, delete

from movie_service.app.dependencies import get_repository
from movie_service.app.main import app
from movie_service.app.models import Movie
from movie_service.app.repository_db import MovieRepository


@pytest.fixture()
def engine(tmp_path):
    test_db = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{test_db}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(autouse=True)
def override_repository(session):
    app.dependency_overrides[get_repository] = lambda: MovieRepository(session)
    yield
    app.dependency_overrides.pop(get_repository, None)
    session.exec(delete(Movie))
    session.commit()


@pytest.fixture()
def client(override_repository):
    return TestClient(app)
````

### Step 2: Reuse Session 03 tests
Keep the assertions in `movie_service/tests/test_movies.py`; the fixtures already isolate each test file. Run them:
```bash
uv run pytest movie_service/tests -v
```

### Step 3: Alembic workflow
1. Scaffold Alembic:
   ```bash
   uv run alembic init migrations
   ```
2. Update `alembic.ini` to remove the hard-coded `sqlalchemy.url` (env.py will set it). Leave `script_location = migrations`.
3. Edit `migrations/env.py`:
   ````python
   from logging.config import fileConfig

   from alembic import context
   from sqlalchemy import engine_from_config, pool
   from sqlmodel import SQLModel

   from movie_service.app import models  # noqa
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
           render_as_batch=True,  # needed for SQLite ALTER TABLE
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
           context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
           with context.begin_transaction():
               context.run_migrations()


   if context.is_offline_mode():
       run_migrations_offline()
   else:
       run_migrations_online()
   ````
4. Generate and apply the initial revision:
   ```bash
   uv run alembic revision --autogenerate -m "create movies"
   uv run alembic upgrade head
   uv run alembic current  # optional sanity check
   ```

### Step 4: Seed script
`movie_service/scripts/seed_db.py`
````python
from sqlmodel import Session

from movie_service.app.database import engine, init_db
from movie_service.app.models import MovieCreate
from movie_service.app.repository_db import MovieRepository

init_db()
with Session(engine) as session:
    repo = MovieRepository(session)
    if repo.list():
        print("Database already seeded")
    else:
        repo.create(MovieCreate(title="Arrival", year=2016, genre="sci-fi"))
        repo.create(MovieCreate(title="The Martian", year=2015, genre="sci-fi"))
        print("Seeded two movies")
````
Run via `uv run python -m movie_service.scripts.seed_db`.

### Step 5: Verification checklist
- `uv run pytest movie_service/tests -v`
- `uv run alembic upgrade head`
- `uv run python -m movie_service.scripts.seed_db`
- Data persists in `data/movies.db` across uvicorn restarts.
- README/docs updated with the new commands and `.gitignore` contains `data/`.

## Session 05 Preview – Moving to PostgreSQL
| Component | Session 04 (SQLite) | Session 05 (Postgres) | Change? |
| --- | --- | --- | --- |
| `database.py` | `sqlite:///data/movies.db` | `postgresql+psycopg://...` | URL swap |
| `config.py` | Basic settings | Adds pool + echo flags | Minor tweaks |
| `models.py` | SQLModel classes | Reused verbatim | None |
| `repository_db.py` | SQLite session | Reused verbatim | None |
| Alembic | SQLite URL | Points to Postgres | Config update |
| Tests | Temp SQLite | Temp Postgres DBs | New fixtures |
| Workflow | `uv run uvicorn` | `docker compose up` + uvicorn | Add service |

Action items before Session 05:
1. Install Docker Desktop and verify `docker compose version`.
2. Commit/tag Session 04 (`session-04-complete`).
3. Capture current `.env` values—you’ll swap URLs in Session 05.
4. Rerun `uv run pytest -v` to ensure a clean baseline.

## Facilitation Tips
- Open each target file before coding so everyone understands where the changes land.
- After Step 2, confirm `data/movies.db` exists; failing to do so causes confusing POST errors later.
- Encourage `uv run pytest movie_service/tests -k movies` mid-lab to keep failures tight.
- When introducing Alembic, show the generated revision file and connect it to the SQL it would run.
- Close by re-running the seed script + `/movies` curl so students see durable data.

## Troubleshooting
- **`sqlite3.OperationalError: attempt to write a readonly database`** → ensure `data/` is writable and ignored by Git.
- **`check_same_thread` errors** → confirm `connect_args={"check_same_thread": False}` is present anywhere FastAPI or tests create SQLite engines.
- **Alembic cannot locate metadata** → import `movie_service.app.models` in `env.py` and ensure `SQLModel.metadata` is referenced.
- **Tests mutate the real database** → verify the dependency override fixture runs before `TestClient` is instantiated.

## AI Prompt Seeds
- “Convert these Pydantic models + dict repository into SQLModel classes with a SQLite-backed repository; keep FastAPI route signatures identical.”
- “Write pytest fixtures that spin up a temporary SQLite database, override FastAPI dependencies, and keep each test hermetic.”
- “Draft an Alembic workflow (init, revision, upgrade) and a Typer/uv command list so students can recreate today’s migration + seed steps.”
