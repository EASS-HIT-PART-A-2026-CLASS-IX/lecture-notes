# Session 04 – Persisting the Movie Service (SQLite + SQLModel)

- **Date:** Monday, Nov 24, 2025
- **Theme:** Replace the in-memory repository with a real SQLite database using SQLModel, per-request sessions, and database-aware tests.

## Session Story
You begin exactly where Session 03 ended: a FastAPI app that forgets every movie as soon as the process restarts. In this session you will (1) teach FastAPI how to talk to SQLite through SQLModel, (2) rewire the repository and routes so every CRUD action persists real rows, and (3) wrap that work in tests, migrations, and a tiny seed script. The entire flow is intentionally linear so newer students can focus on one idea at a time before seeing how everything fits together.

## Learning Objectives
- Model movie data with SQLModel and generate the corresponding SQLite tables.
- Configure a database engine + session dependency for FastAPI using uv-managed settings.
- Rewrite the repository layer so every CRUD operation touches the database.
- Seed data and run migrations (Alembic) without leaving the `hello-uv` workspace.
- Update pytest fixtures to spin up an isolated database per test file.

## What You’ll Build
- `movie_service/app/models.py` holding SQLModel definitions (`Movie`, `MovieCreate`, `MovieRead`) plus a simple `MovieUpdate` stub you can expand during Session 05.
- `movie_service/app/database.py` that exposes `engine`, `get_session`, and an `init_db()` helper.
- `movie_service/app/repository_db.py` that performs create/list/get/delete via SQLModel sessions.
- Updated FastAPI endpoints wired to the new repository while preserving the HTTP contract from Session 03.
- Alembic migration script plus a seed helper for local data.
- pytest fixtures that create/drop the SQLite schema in a temporary directory so tests stay deterministic.

### Persistence Runway (Prep for EX3)
- Session 03 already satisfied the EX1 brief (HTTP contract, validation, tests, Docker). Today we **extend that same service with SQLModel + SQLite** so the data finally survives process restarts and teams rehearse the upgrade path they must finish before EX3.
- Make the expectation explicit: EX3 combines at least three cooperating services (FastAPI backend, persistence layer, and a UI/automation interface—with many teams adding a fourth AI or background worker). This lab is where the backend learns how to talk to its dedicated database service.
- Position this as a gradual mastery track: students can keep EX1 submissions in-memory if they need to prioritize fundamentals, while advanced teams can merge today’s DB layer immediately to reduce EX3 stress.
- Emphasize architecture boundaries: **Session 03 kept storage behind a repository interface** for exactly this reason. All new database touch points stay inside `repository_db.py` / `database.py`, so future swaps (Session 05’s PostgreSQL stretch, Session 07 diagnostics, Session 08 AI tools) stay surgical.

## Prerequisites

**Before starting, verify your Session 03 baseline works:**

```bash
cd hello-uv
uv run pytest movie_service/tests -v  # Should see 13 passing tests
uv run uvicorn movie_service.app.main:app --reload  # Server starts cleanly
curl http://localhost:8000/movies  # Returns empty array or existing movies
```

If any command fails, revisit Session 03 before proceeding. Session 04 builds on top of that exact codebase.

Complete these before students arrive so the first lab can jump straight into coding. Run every command from the `hello-uv/` workspace root unless noted otherwise.

1. **Install extra dependencies** inside `hello-uv`:
   ```bash
   uv add sqlmodel alembic sqlalchemy-utils
   ```
2. **Create a database directory** (ignored by Git):
   ```bash
   mkdir -p data
   echo "data/" >> .gitignore  # if not already present
   ```
3. **Update `.env.example`** with the database URL and Alembic env:
   ```ini
   MOVIE_DATABASE_URL="sqlite:///data/movies.db"
   MOVIE_ALEMBIC_CONFIG="alembic.ini"
   ```
   Copy changes to `.env` if needed.
4. **Verify SQLModel import works:**
   ```bash
   uv run python -c "import sqlmodel; print('SQLModel', sqlmodel.__version__)"
   ```

## Toolkit Snapshot
- **SQLModel** – ORM from the FastAPI author combining Pydantic models with SQLAlchemy-powered persistence.
- **SQLite** – file-based relational database; zero configuration, perfect for local development and tests.
- **SQLAlchemy** – battle-tested database toolkit that SQLModel builds on for engine/session management.
- **Alembic** – migration framework that captures schema changes and upgrades databases safely.
- **pytest** – reused from Session 03, now paired with temporary SQLite fixtures for deterministic DB tests.
- **uv** – still handles Python/dep installs; now also runs Alembic commands and seed scripts.

## Session Agenda

| Time | Activity | Focus |
| --- | --- | --- |
| 10 min | Recap & intent | Explain why in-memory repos do not persist data. |
| 20 min | Data modeling primer | SQLModel basics, relationships, auto-generated tables. |
| 45 min | **Lab 1: Wire SQLite** | Settings, engine, SQLModel classes, repository rewrite. |
| 10 min | Break | — |
| 45 min | **Lab 2: Database tests + migrations** | pytest fixtures, Alembic init, seed script. |
| 10 min | Wrap-up | Checklist + preview of async/ORM enhancements. |

## Core Concepts

### 1. SQLModel = Pydantic + SQLAlchemy
SQLModel sits between familiar Pydantic models and SQLAlchemy's database engine, so you keep type hints and validation while gaining persistence.
- Inherit from `SQLModel`; specify `table=True` for persisted tables.
- Use `Field(default=None, primary_key=True)` for ids; reuse `Field(ge=..., le=...)` for validation just like Session 03.
- Create lightweight Pydantic schemas (`MovieCreate`, `MovieRead`) by reusing the same base class.
- **Key insight:** `MovieBase` holds shared fields, `Movie(table=True)` is the SQLAlchemy-tracked table, and `MovieRead` is the Pydantic response model. This keeps validation (Pydantic) separate from persistence (SQLAlchemy).

### 2. Database Engine & Sessions
An engine is the shared “wire” to SQLite; a session is a short-lived unit of work that FastAPI opens per request and automatically closes.
- `engine = create_engine(database_url, echo=False, connect_args={"check_same_thread": False})` for SQLite.
- Provide sessions with `Session(engine)` inside a dependency generator (FastAPI closes it automatically).
- One request = one session; repository functions receive the session via dependency injection.

### 3. Repository Layer Swap
Instead of dict lookups, the repository now issues SQL queries but keeps the same interface so routes do not change.
- Replace the in-memory dictionary with SQL queries (`session.exec(select(Movie)).all()`).
- Keep the FastAPI routes untouched—only the dependency wiring changes.
- Add helper methods for `update` so Session 05 can introduce PUT/PATCH quickly.

### 4. Testing with Temporary Databases
Temporary SQLite files keep each test hermetic: build tables at the start of a module, drop them afterward, and never leak data across runs.
- Use Python’s `tempfile.TemporaryDirectory` or `pytest` tmp_path fixtures.
- Create an engine pointing to `sqlite://` (in-memory) or `sqlite:///tmp/test.db`.
- Create tables before each test module, drop after, ensuring no cross-test leakage.

### 5. Alembic + Seeds
Alembic versions the schema; a seed script fills predictable starter rows so dev and tests stay in sync.
- `alembic init` scaffolds migrations driven by SQLModel metadata.
- A tiny seed script demonstrates how to reuse the same session dependency outside FastAPI.
- Even if you skip Alembic locally, capture the steps for your repo (it becomes essential prep for EX3, and ambitious EX1 teams can treat it as a stretch goal).

## Part A – Theory Highlights
1. **State diagram:** Request enters FastAPI → dependency `get_session()` opens DB session → repository issues SQLModel operations → session commits/rollbacks → response serialized via Pydantic.
2. **SQLite trade-offs:** file-based, zero config, ideal for laptops/tests. Later we can point the same SQLModel code at Postgres.
3. **Transactions:** Use `session.add()` + `session.commit()` in repository methods, followed by `session.refresh()` to populate generated IDs.
4. **Migrations:** Alembic stores schema history; every structural change (new column) gets its own revision.

## Part B – Lab 1: Wire SQLite (45 minutes)

> Goal: replace the toy in-memory repository with a SQLite-backed SQLModel stack while keeping the HTTP contract untouched.  
> Files you’ll edit: `movie_service/app/config.py`, `database.py`, `models.py`, `repository_db.py`, `dependencies.py`, `main.py`.  
> Success check: restart the server, hit `/movies`, and see the rows you created earlier still present.

### Step 1: Update Settings
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

### Step 2: Create `database.py`
`movie_service/app/database.py`
````python
from typing import Generator

from sqlmodel import SQLModel, create_engine, Session

from .config import Settings

settings = Settings()
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},  # needed for SQLite + threads
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
````
Run `uv run python - <<'PY'` to create the initial database file:
```bash
uv run python - <<'PY'
from movie_service.app.database import init_db
init_db()
print("Created data/movies.db")
PY
```
Running the helper once up front saves students from a confusing "no such table" error when they hit the POST endpoint for the first time.

### Step 3: Define SQLModel classes
`movie_service/app/models.py`
````python
# filepath: movie_service/app/models.py
from typing import Optional

from sqlmodel import SQLModel, Field
from pydantic import model_validator


class MovieBase(SQLModel):
    """Shared fields for create/read models.
    
    Inherits from SQLModel (not BaseModel) so we can reuse these
    fields in both the table definition and Pydantic response models.
    """
    title: str
    year: int = Field(ge=1900, le=2100)
    genre: str


class Movie(MovieBase, table=True):
    """SQLAlchemy-tracked table definition.
    
    The `table=True` parameter tells SQLModel to create a database table.
    SQLAlchemy will auto-generate the `id` primary key when we insert rows.
    """
    id: Optional[int] = Field(default=None, primary_key=True)


class MovieCreate(MovieBase):
    """Incoming payload with validation + normalization.
    
    Same validator from Session 03 carries forward unchanged—
    proof that validation rules survive persistence layer swaps.
    """

    @model_validator(mode="after")
    def normalize_genre(self) -> "MovieCreate":
        """Title-case the genre: 'sci-fi' → 'Sci-Fi'."""
        self.genre = self.genre.title()
        return self


class MovieRead(MovieBase):
    """Response model for API endpoints.
    
    Separated from `Movie` because:
    - API responses should be Pydantic models (fast serialization)
    - Table models need SQLAlchemy tracking (session.add/commit)
    - Keeps concerns separated (HTTP vs persistence)
    """
    id: int
````

**Migration note:** Session 03 used `Movie` for both domain logic and responses. We now split it into `Movie` (table) and `MovieRead` (response), but the HTTP contract stays identical—FastAPI serializes `Movie` instances into `MovieRead` automatically.

### Step 4: Database-backed repository
`movie_service/app/repository_db.py`
````python
# filepath: movie_service/app/repository_db.py
from typing import Sequence

from sqlmodel import Session, select

from .models import Movie, MovieCreate


class MovieRepository:
    """SQLite-backed storage for movies.
    
    Compare to Session 03's in-memory version:
    - `list()` was `return list(self._items.values())`
      Now: `return self.session.exec(select(Movie)).all()`
    - `create()` was `movie = Movie(...); self._items[movie.id] = movie`
      Now: `session.add(record); session.commit(); session.refresh(record)`
    - `get()` was `return self._items.get(movie_id)`
      Now: `return self.session.get(Movie, movie_id)`
    - `delete()` was `self._items.pop(movie_id, None)`
      Now: `session.delete(record); session.commit()`
    
    The function signatures stayed identical—only the internals changed.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> Sequence[Movie]:
        """Get all movies.
        
        Changed from `list[Movie]` to `Sequence[Movie]` because SQLModel's
        `.all()` returns a sequence. Routes still work because FastAPI
        serializes sequences into JSON arrays automatically.
        """
        return self.session.exec(select(Movie)).all()

    def create(self, payload: MovieCreate) -> Movie:
        """Add a new movie and return it with assigned ID.
        
        `model_validate` converts the Pydantic `MovieCreate` into the
        SQLModel `Movie` table class so SQLAlchemy can track it.
        `refresh` populates the auto-generated `id` after commit.
        """
        record = Movie.model_validate(payload)  # copy into SQLModel
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get(self, movie_id: int) -> Movie | None:
        """Get a movie by ID, or None if not found.
        
        `session.get(Model, pk)` is SQLAlchemy shorthand for
        `session.exec(select(Movie).where(Movie.id == movie_id)).first()`.
        """
        return self.session.get(Movie, movie_id)

    def delete(self, movie_id: int) -> None:
        """Remove a movie by ID.
        
        Must commit to persist the deletion to the database file.
        """
        record = self.get(movie_id)
        if record:
            self.session.delete(record)
            self.session.commit()
````

`Movie.model_validate(payload)` converts the incoming request object into the SQLModel table class so SQLAlchemy can track it and populate the autogenerated primary key.

### Step 5: Dependency wiring
`movie_service/app/dependencies.py`
````python
from collections.abc import Generator
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

### Step 6: FastAPI routes (reuse Session 03 handlers)
No major changes besides importing `MovieRead` for response models and `MovieCreate` for payloads:
`movie_service/app/main.py`
````python
from fastapi import FastAPI, HTTPException, status

from .dependencies import RepositoryDep, SettingsDep
from .models import MovieRead, MovieCreate

app = FastAPI(title="Movie Service", version="0.2.0")


@app.get("/health", tags=["diagnostics"])
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/movies", response_model=list[MovieRead], tags=["movies"])
def list_movies(repository: RepositoryDep) -> list[MovieRead]:
    return list(repository.list())


@app.post(
    "/movies",
    response_model=MovieRead,
    status_code=status.HTTP_201_CREATED,
    tags=["movies"],
)
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

### Step 7: Manual smoke test
```bash
uv run uvicorn movie_service.app.main:app --reload
curl -X POST http://localhost:8000/movies \
  -H "Content-Type: application/json" \
  -d '{"title": "Inception", "year": 2010, "genre": "sci-fi"}'
curl http://localhost:8000/movies
```
Observe that records persist after restarting the server because they now live in `data/movies.db`.

> ✅ Lab 1 complete when: POST returns `201`, `/movies` echoes the new record, and the same record appears after you restart uvicorn.

## Part C – Lab 2: Tests, Migrations, Seeds (45 minutes)

> Goal: prove the database-backed service is safe to refactor by adding hermetic pytest fixtures, an Alembic migration, and a repeatable seed script.  
> Files you’ll edit: `movie_service/tests/conftest.py`, Alembic `env.py` + `alembic.ini`, and `movie_service/scripts/seed_db.py`.  
> Success check: `uv run pytest movie_service/tests -v` passes, `uv run alembic upgrade head` applies cleanly, and the seed script prints that it inserted two movies.

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
    """Swap FastAPI's repository dependency for the test session."""
    app.dependency_overrides[get_repository] = lambda: MovieRepository(session)
    yield
    app.dependency_overrides.pop(get_repository, None)
    session.exec(delete(Movie))
    session.commit()


@pytest.fixture()
def client():
    return TestClient(app)
````
By overriding `app.dependency_overrides`, every TestClient call receives the in-memory session so test runs stay hermetic—no writes go to `data/movies.db`.

### Step 2: Reuse the Session 03 tests
Most assertions stay the same. Keep them in `movie_service/tests/test_movies.py`; the fixtures now ensure each test runs against a blank SQLite database.

### Alembic 101 (Zero-Experience Primer)
Think of Alembic as Git for your database schema: every change gets a revision file, environments move "forward" with `upgrade`, and you always know which version a database is running. Instead of manually running `CREATE TABLE` statements, you record each structural change as a **revision** so every developer (and CI) can reproduce the same database.

- **Vocabulary cheat sheet**
  - **Revision** – one Python file under `migrations/versions/` that knows how to `upgrade()` and `downgrade()` a specific change.
  - **Head** – the newest revision in the timeline. `upgrade head` moves your database to the latest schema; `downgrade -1` rolls back one step.
  - **Autogenerate** – Alembic inspects `SQLModel.metadata` and suggests the SQL needed to match your models.
  - **Why bother?** – Lets teams coordinate schema changes without manually syncing SQL scripts. Essential for EX3 where you'll deploy to Azure with versioned migrations.
  
- **What `alembic init migrations` creates**
  ````text
  alembic.ini
  migrations/
  ├── env.py          # wires SQLModel metadata into Alembic
  ├── README          # short usage notes
  ├── script.py.mako  # template Alembic uses for new revisions
  └── versions/       # empty folder where revisions land
  ````
- **Workflow you’ll repeat**
  1. Update or add SQLModel classes.
  2. Run `uv run alembic revision --autogenerate -m "describe change"`.
  3. Inspect the generated file (it mirrors SQL `CREATE/ALTER TABLE` statements).
  4. Apply it with `uv run alembic upgrade head`. Your SQLite file now matches the models.
  5. (Optional) check status with `uv run alembic current` which prints the active revision.

### Step 3: Alembic initialization
1. **Scaffold Alembic**
   ```bash
   uv run alembic init migrations
   ```
   This creates `alembic.ini` plus the `migrations/` folder shown in the primer above.

2. **Point Alembic at your SQLite URL + SQLModel metadata**
   
   Edit `alembic.ini` to use your environment variable:
   ```ini
   # Replace the static sqlalchemy.url line with:
   # sqlalchemy.url = driver://user:pass@localhost/dbname
   
   # Comment out or remove the above, then Alembic will read from env.py
   ```
   
   Edit `migrations/env.py` to connect to your engine and metadata:
   ````python
   # filepath: migrations/env.py
   from logging.config import fileConfig
   from sqlalchemy import engine_from_config, pool
   from alembic import context
   
   # Import your SQLModel metadata
   from sqlmodel import SQLModel
   from movie_service.app import models  # noqa: F401 - registers tables
   from movie_service.app.config import Settings
   
   config = context.config
   
   # Override sqlalchemy.url with your settings
   settings = Settings()
   config.set_main_option("sqlalchemy.url", settings.database_url)
   
   if config.config_file_name is not None:
       fileConfig(config.config_file_name)
   
   target_metadata = SQLModel.metadata
   
   # ...existing code for run_migrations_offline and run_migrations_online...
   ````

3. **Generate the first revision (create the `movie` table)**
   ```bash
   uv run alembic revision --autogenerate -m "create movies"
   ```
   Open the new file under `migrations/versions/` to see the SQL it plans to run. It will look similar to:
   ````python
   def upgrade() -> None:
       op.create_table(
           "movie",
           sa.Column("id", sa.Integer(), primary_key=True),
           sa.Column("title", sa.String(), nullable=False),
           sa.Column("year", sa.Integer(), nullable=False),
           sa.Column("genre", sa.String(), nullable=False),
       )
   ````

4. **Apply the revision to your dev database**
   ```bash
   uv run alembic upgrade head
   uv run alembic current  # optional: prints the revision hash now stored in data/movies.db
   ```
   At this point `data/movies.db` contains a `movie` table that matches the SQLModel definitions.

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
Run via:
```bash
uv run python -m movie_service.scripts.seed_db
```
`Session(engine)` keeps the connection alive for the `with` block; calling `next(get_session())` would exit the generator context immediately and leave you with a closed session.

## Wrap-Up Checklist
- [ ] `data/movies.db` exists and persists records between server restarts.
- [ ] `uv run pytest movie_service/tests -v` passes using the new fixtures.
- [ ] Alembic migration runs cleanly (`uv run alembic upgrade head`).
- [ ] Seed script inserts sample movies.
- [ ] README or docs updated with new commands.

## Next Steps
- Add `PUT /movies/{id}` using `MovieUpdate`.
- Introduce pagination + filtering at the SQL layer.
- Prepare for Postgres by moving `database_url` into `.env` per environment.
- Revisit Dockerfile (Session 05) to include SQLite volume mounts or alternative databases.

## Facilitation Tips for Newer Students
- Open each file together before typing so everyone can see where the new code lives (config → database → models → repository → routes).
- After Step 2, pause and confirm the SQLite file exists to prevent cascading errors during POST tests.
- Keep pytest green by running `uv run pytest movie_service/tests -k movies` after wiring the fixtures, then expand to `-v` once everything passes.
- For Alembic, show the generated revision and highlight the mirrored SQL columns; this keeps the migration step from feeling like magic.
- End the session by re-running the seed script and `/movies` curl so students leave with a visible success moment.

## Troubleshooting
- **`sqlite3.OperationalError: attempt to write a readonly database`** → ensure the `data/` directory is writable and not tracked by Git.
- **`check_same_thread` errors** → confirm `connect_args={"check_same_thread": False}` is set on SQLite engines used by FastAPI and tests.
- **Alembic cannot locate metadata** → import `SQLModel.metadata` in `env.py` and reference `engine` directly.
- **Tests still mutate the real database** → ensure the `override_repository` fixture sets `app.dependency_overrides[get_repository]` before the `TestClient` fixture runs.

## Success Criteria
- You can explain how FastAPI obtains a database session per request.
- You can create/list/get/delete records backed by SQLite.
- Tests run against an isolated database (no flakiness between runs).
- Alembic migrations capture schema changes.
- Seed script populates predictable starter data.

If any box is unchecked, pair with a mentor before Session 05.

## AI Prompt Seeds

- "Convert these Pydantic models + dict repository into SQLModel classes with a SQLite-backed repository; keep the FastAPI route signatures identical."
- "Write pytest fixtures that spin up a temporary SQLite database, override FastAPI dependencies, and keep each test hermetic."
- "Draft an Alembic workflow (init, revision, upgrade) and a Typer/uv command list so students can recreate the migration + seed steps from the session."
