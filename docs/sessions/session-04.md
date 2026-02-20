# Session 04 – Persisting the Movie Service (SQLite + SQLModel)

- **Date:** Monday, 23/03/2026
- **Theme:** Replace the in-memory repository with SQLite + SQLModel, wire FastAPI to real sessions, and back everything with migrations + tests.

## Session Story
Session 03 shipped the Movie Service with in-memory storage. Session 04 keeps the same HTTP contract but persists to SQLite through SQLModel, proving the repository abstraction, adding Alembic migrations, and hardening pytest fixtures so every test runs in a throwaway database. Students leave with durable data, migrations, and a repeatable seed script they can trust in later sessions.

## Instructor Notes
- `uv run pytest movie_service/tests -v` (baseline still green)
- Ensure `.gitignore` ignores `data/` but keeps Alembic revisions tracked (do not ignore `migrations/versions/`; keep `migrations/env.py` and `migrations/script.py.mako` in version control)
- Generate the initial Alembic revision before running `init_db()`; if `data/movies.db` already exists, delete it so `alembic revision --autogenerate` emits the `create_table`
- `uv run alembic upgrade head` and confirm `data/movies.db` timestamps change (this creates the SQLite file)
- `uv run python -m movie_service.scripts.seed_db` twice to verify idempotent seeding
- Smoke `uv run uvicorn movie_service.app.main:app --reload` then `curl http://localhost:8000/health` and `curl http://localhost:8000/movies`
- Ensure the `data/` folder is writable on classroom machines

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
   uv add sqlmodel alembic
   ```
3. Create a writable data directory and ignore it:
   ```bash
   mkdir -p data
   grep -qx 'data/' .gitignore || printf "\n# SQLite data\ndata/\n" >> .gitignore
   ```
4. Extend `.env.example` and `.env` (relative path is fine for local dev):
   ```ini
   MOVIE_DATABASE_URL="sqlite:///./data/movies.db"
   ```
5. Smoke-test imports:
   ```bash
   uv run python - <<'PY'
   import sqlmodel, alembic  # noqa: F401
   print("SQLModel + Alembic ready")
   PY
   ```

## Migration Quickstart (from Session 03)
- Start clean: `uv run pytest movie_service/tests -v` and tag/branch `session-03-complete`.
- Add deps + data dir + env: `uv add sqlmodel alembic`; ensure `data/` exists/ignored and `.env(.example)` has `MOVIE_DATABASE_URL="sqlite:///./data/movies.db"`.
- Swap storage: follow Lab 1 to add `database.py`, update `config.py`, define SQLModel models, drop in `repository_db.py`, and wire `dependencies.py` + `main.py` (keep the HTTP contract identical).
- Tests: use the DB-aware fixtures in Lab 2 Step 1 and rerun the existing `movie_service/tests/test_movies.py`.
- Migrations: `uv run alembic init migrations`, edit `alembic.ini` + `migrations/env.py`, delete any pre-created `data/movies.db`, then `uv run alembic revision --autogenerate -m "create movies"` and `uv run alembic upgrade head`.
- Seeds: run `uv run python -m movie_service.scripts.seed_db` twice to confirm idempotency.
- Smoke: `uv run uvicorn movie_service.app.main:app --reload`, then `curl /health` and `/movies`.
- Commit/tag when green to mark the Session 04 baseline.

## Session Agenda
| Time | Activity | Focus |
| --- | --- | --- |
| 10 min | Recap & intent | Why the repo abstraction makes the DB swap easy. |
| 20 min | Data modeling primer | SQLModel basics, table vs response models, migrations. |
| 45 min | **Lab 1** | **Database wiring + CRUD rewrite.** |
| 10 min | Break | Encourage quick SQLite browser checks (e.g., DBeaver/DB Browser). |
| 45 min | **Lab 2** | **Tests, Alembic, seed scripts.** |
| 10 min | Wrap-up | Checklist + Q&A. |

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
    database_url: str = "sqlite:///./data/movies.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MOVIE_",
        extra="ignore",
    )
````

### Step 2: Create the database module
`movie_service/app/database.py`
````python
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from .config import Settings


def get_settings() -> Settings:
    """Dependency for accessing application settings."""
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]

# Create engine using settings
settings = get_settings()
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)


def init_db() -> None:
    """Initialize database tables. Import models before calling this."""
    from . import models  # noqa: F401
    
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Provide a database session for dependency injection."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
````

Run the helper once so the database file exists (run from the project root). If you call this before creating the initial Alembic revision, delete `data/movies.db` before `alembic revision --autogenerate` so the migration emits the table:
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

from pydantic import field_validator
from sqlmodel import Field, SQLModel


class MovieBase(SQLModel):
    """Base model with shared movie fields."""
    
    title: str = Field(min_length=1, max_length=200)
    year: int = Field(ge=1888, le=2100)  # 1888 = first film ever made
    genre: str = Field(min_length=1, max_length=50)


class Movie(MovieBase, table=True):
    """Database model for movies."""
    
    __tablename__ = "movies"
    
    id: Optional[int] = Field(default=None, primary_key=True)


class MovieCreate(MovieBase):
    """Schema for creating a new movie."""
    
    @field_validator("genre")
    @classmethod
    def normalize_genre(cls, v: str) -> str:
        """Normalize genre to title case."""
        return v.strip().title()
    
    @field_validator("title")
    @classmethod
    def normalize_title(cls, v: str) -> str:
        """Strip whitespace from title."""
        return v.strip()


class MovieRead(MovieBase):
    """Schema for reading a movie."""
    
    id: int


class MovieUpdate(SQLModel):
    """Schema for updating a movie (all fields optional)."""
    
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    year: Optional[int] = Field(default=None, ge=1888, le=2100)
    genre: Optional[str] = Field(default=None, min_length=1, max_length=50)
    
    @field_validator("genre")
    @classmethod
    def normalize_genre(cls, v: Optional[str]) -> Optional[str]:
        """Normalize genre to title case if provided."""
        return v.strip().title() if v else None
    
    @field_validator("title")
    @classmethod
    def normalize_title(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace from title if provided."""
        return v.strip() if v else None
````

`MovieUpdate` is ready for a future `PUT/PATCH` route; the contract today stays list/create/get/delete.

### Step 4: Database-backed repository
`movie_service/app/repository_db.py`
````python
from typing import Optional

from sqlmodel import Session, select

from .models import Movie, MovieCreate


class MovieRepository:
    """SQLite-backed storage for movies with proper session handling."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, *, skip: int = 0, limit: int = 100) -> list[Movie]:
        """List all movies with pagination support."""
        statement = select(Movie).offset(skip).limit(limit)
        return list(self.session.exec(statement).all())

    def create(self, payload: MovieCreate) -> Movie:
        """Create a new movie and persist to database."""
        record = Movie.model_validate(payload)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get(self, movie_id: int) -> Optional[Movie]:
        """Retrieve a movie by ID."""
        return self.session.get(Movie, movie_id)

    def delete(self, movie_id: int) -> bool:
        """Delete a movie by ID. Returns True if deleted, False if not found."""
        record = self.get(movie_id)
        if record is None:
            return False
        self.session.delete(record)
        self.session.commit()
        return True

    def delete_all(self) -> int:
        """Delete all movies and return count. Use with caution."""
        statement = select(Movie)
        records = self.session.exec(statement).all()
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

from .database import SessionDep
from .repository_db import MovieRepository


def get_repository(session: SessionDep) -> MovieRepository:
    """Dependency for accessing the movie repository."""
    return MovieRepository(session)


RepositoryDep = Annotated[MovieRepository, Depends(get_repository)]
````

`movie_service/app/main.py`
````python
from fastapi import FastAPI, HTTPException, status

from .database import SettingsDep
from .dependencies import RepositoryDep
from .models import MovieCreate, MovieRead

app = FastAPI(
    title="Movie Service",
    version="0.2.0",
    description="A service for managing movie data with SQLite persistence",
)


@app.get("/health", tags=["diagnostics"])
def health(settings: SettingsDep) -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "app": settings.app_name}


@app.get("/movies", response_model=list[MovieRead], tags=["movies"])
def list_movies(
    repository: RepositoryDep,
    skip: int = 0,
    limit: int = 100,
) -> list[MovieRead]:
    """List all movies with optional pagination."""
    return repository.list(skip=skip, limit=limit)


@app.post(
    "/movies",
    response_model=MovieRead,
    status_code=status.HTTP_201_CREATED,
    tags=["movies"],
)
def create_movie(payload: MovieCreate, repository: RepositoryDep) -> MovieRead:
    """Create a new movie."""
    return repository.create(payload)


@app.get("/movies/{movie_id}", response_model=MovieRead, tags=["movies"])
def read_movie(movie_id: int, repository: RepositoryDep) -> MovieRead:
    """Retrieve a specific movie by ID."""
    movie = repository.get(movie_id)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found",
        )
    return movie


@app.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["movies"])
def delete_movie(movie_id: int, repository: RepositoryDep) -> None:
    """Delete a specific movie by ID."""
    deleted = repository.delete(movie_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id {movie_id} not found",
        )
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
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from movie_service.app import models  # noqa: F401
from movie_service.app.database import get_session
from movie_service.app.main import app


@pytest.fixture(name="engine")
def engine_fixture(tmp_path):
    """Create a temporary SQLite database for testing."""
    test_db = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{test_db}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    # Cleanup: drop all tables and dispose engine
    SQLModel.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine) -> Generator[Session, None, None]:
    """Provide a SQLModel session connected to the test database."""
    with Session(engine) as session:
        yield session
        # Rollback any uncommitted changes
        session.rollback()


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """Provide a test client with overridden dependencies."""
    
    def get_session_override() -> Generator[Session, None, None]:
        yield session
    
    app.dependency_overrides[get_session] = get_session_override
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup: remove override
    app.dependency_overrides.clear()
````

### Step 2: Reuse Session 03 tests
Keep the assertions in `movie_service/tests/test_movies.py`; the fixtures already isolate each test file. Run them:
```bash
uv run pytest movie_service/tests -v
```

### Step 3: Alembic workflow
> Run this step before using `init_db()` or any command that creates `data/movies.db`. If you already created the file, delete it so `alembic revision --autogenerate` emits the `create_table`.

1. Scaffold Alembic:
   ```bash
   uv run alembic init migrations
   ```
2. Keep revision files tracked (do **not** ignore `migrations/versions/`; commit generated files so others can run upgrades).
3. Update `alembic.ini` to remove the hard-coded `sqlalchemy.url` (env.py will set it). Leave `script_location = migrations`.
4. Edit `migrations/env.py`:
   ````python
   # filepath: migrations/env.py
   from logging.config import fileConfig

   from alembic import context
   from sqlalchemy import engine_from_config, pool
   from sqlmodel import SQLModel

   # Import all models to ensure they're registered with SQLModel metadata
   from movie_service.app import models  # noqa: F401
   from movie_service.app.config import Settings

   config = context.config

   # Get database URL from settings
   settings = Settings()
   if not config.get_main_option("sqlalchemy.url"):
       config.set_main_option("sqlalchemy.url", settings.database_url)

   # Interpret the config file for Python logging
   if config.config_file_name is not None:
       fileConfig(config.config_file_name)

   target_metadata = SQLModel.metadata


   def run_migrations_offline() -> None:
       """Run migrations in 'offline' mode."""
       url = config.get_main_option("sqlalchemy.url")
       context.configure(
           url=url,
           target_metadata=target_metadata,
           literal_binds=True,
           dialect_opts={"paramstyle": "named"},
           render_as_batch=True,  # Required for SQLite ALTER TABLE
       )

       with context.begin_transaction():
           context.run_migrations()


   def run_migrations_online() -> None:
       """Run migrations in 'online' mode."""
       connectable = engine_from_config(
           config.get_section(config.config_ini_section, {}),
           prefix="sqlalchemy.",
           poolclass=pool.NullPool,
       )

       with connectable.connect() as connection:
           context.configure(
               connection=connection,
               target_metadata=target_metadata,
               render_as_batch=True,  # Required for SQLite ALTER TABLE
           )

           with context.begin_transaction():
               context.run_migrations()


   if context.is_offline_mode():
       run_migrations_offline()
   else:
       run_migrations_online()
   ````

5. Generate and apply the initial revision:
   ```bash
   uv run alembic revision --autogenerate -m "create movies"
   uv run alembic upgrade head
   uv run alembic current  # optional sanity check
   ```

### Step 4: Seed script
`movie_service/scripts/seed_db.py`
````python
"""Seed the database with initial movie data."""

from sqlmodel import Session, select

from movie_service.app.database import engine, init_db
from movie_service.app.models import Movie, MovieCreate
from movie_service.app.repository_db import MovieRepository


def seed_movies() -> None:
    """Seed the database with sample movies if empty."""
    # Ensure tables exist
    init_db()
    
    with Session(engine) as session:
        # Check if database already has data
        statement = select(Movie)
        existing_movies = session.exec(statement).first()
        
        if existing_movies:
            print("Database already contains movies. Skipping seed.")
            return
        
        # Seed initial movies
        repo = MovieRepository(session)
        movies = [
            MovieCreate(title="Arrival", year=2016, genre="sci-fi"),
            MovieCreate(title="The Martian", year=2015, genre="sci-fi"),
            MovieCreate(title="Interstellar", year=2014, genre="sci-fi"),
        ]
        
        for movie_data in movies:
            repo.create(movie_data)
        
        print(f"Successfully seeded {len(movies)} movies.")


if __name__ == "__main__":
    seed_movies()
````

### Step 5: Verification checklist
- `uv run pytest movie_service/tests -v`
- `uv run alembic upgrade head`
- `uv run python -m movie_service.scripts.seed_db` (run twice to verify idempotency)
- Data persists in `data/movies.db` across uvicorn restarts
- README/docs updated with the new commands
- `.gitignore` contains `data/` and migration revision files are tracked (do not ignore `migrations/versions/`)

## Next steps
- Install Docker Desktop and verify `docker compose version` if you plan to run Postgres locally.
- Commit/tag this checkpoint (e.g., `session-04-complete`) for easy rollback.
- Capture current `.env` values so you can swap URLs cleanly when changing databases.
- Rerun `uv run pytest -v` to ensure a clean baseline before extending the stack.

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
