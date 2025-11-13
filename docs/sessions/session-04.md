# Session 04 – Persisting the Movie Service (SQLite + SQLModel)

- **Date:** Monday, Nov 24, 2025
- **Theme:** Replace the in-memory repository with a real SQLite database using SQLModel, per-request sessions, and database-aware tests.

## Learning Objectives
- Model movie data with SQLModel and generate the corresponding SQLite tables.
- Configure a database engine + session dependency for FastAPI using uv-managed settings.
- Rewrite the repository layer so every CRUD operation touches the database.
- Seed data and run migrations (Alembic) without leaving the `hello-uv` workspace.
- Update pytest fixtures to spin up an isolated database per test file.

## What You’ll Build
- `movie_service/app/models.py` holding SQLModel definitions (`Movie`, `MovieCreate`, `MovieRead`, `MovieUpdate`).
- `movie_service/app/database.py` that exposes `engine`, `get_session`, and an `init_db()` helper.
- `movie_service/app/repository_db.py` that performs create/list/get/delete via SQLModel sessions.
- Updated FastAPI endpoints wired to the new repository while preserving the HTTP contract from Session 03.
- Alembic migration script plus a seed helper for local data.
- pytest fixtures that create/drop the SQLite schema in a temporary directory so tests stay deterministic.

## Prerequisites

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
- Inherit from `SQLModel`; specify `table=True` for persisted tables.
- Use `Field(default=None, primary_key=True)` for ids; reuse `Field(ge=..., le=...)` for validation just like Session 03.
- Create lightweight Pydantic schemas (`MovieCreate`, `MovieRead`) by reusing the same base class.

### 2. Database Engine & Sessions
- `engine = create_engine(database_url, echo=False, connect_args={"check_same_thread": False})` for SQLite.
- Provide sessions with `Session(engine)` inside a dependency generator (FastAPI closes it automatically).
- One request = one session; repository functions receive the session via dependency injection.

### 3. Repository Layer Swap
- Replace the in-memory dictionary with SQL queries (`session.exec(select(Movie)).all()`).
- Keep the FastAPI routes untouched—only the dependency wiring changes.
- Add helper methods for `update` so Session 05 can introduce PUT/PATCH quickly.

### 4. Testing with Temporary Databases
- Use Python’s `tempfile.TemporaryDirectory` or `pytest` tmp_path fixtures.
- Create an engine pointing to `sqlite://` (in-memory) or `sqlite:///tmp/test.db`.
- Create tables before each test module, drop after, ensuring no cross-test leakage.

### 5. Alembic + Seeds
- `alembic init` scaffolds migrations driven by SQLModel metadata.
- A tiny seed script demonstrates how to reuse the same session dependency outside FastAPI.
- Even if you skip Alembic locally, document the steps for EX1.

## Part A – Theory Highlights
1. **State diagram:** Request enters FastAPI → dependency `get_session()` opens DB session → repository issues SQLModel operations → session commits/rollbacks → response serialized via Pydantic.
2. **SQLite trade-offs:** file-based, zero config, ideal for laptops/tests. Later we can point the same SQLModel code at Postgres.
3. **Transactions:** Use `session.add()` + `session.commit()` in repository methods, followed by `session.refresh()` to populate generated IDs.
4. **Migrations:** Alembic stores schema history; every structural change (new column) gets its own revision.

## Part B – Lab 1: Wire SQLite (45 minutes)

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
from contextlib import contextmanager
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

### Step 3: Define SQLModel classes
`movie_service/app/models.py`
````python
from typing import Optional

from sqlmodel import SQLModel, Field


class MovieBase(SQLModel):
    title: str
    year: int = Field(ge=1900, le=2100)
    genre: str


class Movie(MovieBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class MovieCreate(MovieBase):
    pass


class MovieRead(MovieBase):
    id: int
````
Add `MovieUpdate` later when you introduce PUT/PATCH.

### Step 4: Database-backed repository
`movie_service/app/repository_db.py`
````python
from typing import Sequence

from sqlmodel import Session, select

from .models import Movie, MovieCreate


class MovieRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> Sequence<Movie]:
        return self.session.exec(select(Movie)).all()

    def create(self, payload: MovieCreate) -> Movie:
        record = Movie.model_validate(payload, update={})  # copy into SQLModel
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
````

### Step 5: Dependency wiring
`movie_service/app/dependencies.py`
````python
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends

from .config import Settings
from .database import get_session
from .repository_db import MovieRepository


def get_settings() -> Settings:
    return Settings()


def get_repository(session=Depends(get_session)) -> MovieRepository:
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

## Part C – Lab 2: Tests, Migrations, Seeds (45 minutes)

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

### Step 3: Alembic initialization
```bash
uv run alembic init migrations
```
Update `alembic.ini` to use `MOVIE_DATABASE_URL`, then edit `migrations/env.py`:
````python
from sqlmodel import SQLModel

from movie_service.app import models  # noqa: F401 - ensures models register tables
from movie_service.app.database import engine

target_metadata = SQLModel.metadata
````
Generate the first migration:
```bash
uv run alembic revision --autogenerate -m "create movies"
uv run alembic upgrade head
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
