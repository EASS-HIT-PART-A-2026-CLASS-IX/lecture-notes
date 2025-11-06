# Session 05 – Movie Service Persistence with SQLite

- **Date:** Monday, Dec 1, 2025
- **Theme:** Replace the in-memory repository with SQLModel + SQLite, add migrations, and keep tests green.

## Learning Objectives
- Model movies and ratings with SQLModel, including relationships and uniqueness constraints.
- Run Alembic migrations to manage schema changes and seed baseline data.
- Implement repository functions that use dependency-injected sessions, respecting trace identifiers (IDs) and validation rules.
- Write tests that spin up a temporary SQLite database per test (fixtures preview for Session 07).

## Before Class – Persistence Preflight (Just-in-Time Teaching, JiTT)
- Install dependencies:
  ```bash
  uv add "sqlmodel==0.0.22" "alembic==1.*" "typer==0.*"
  ```
- Create `alembic.ini` with `uv run alembic init migrations` if you want to peek ahead; note blockers for class.
- Review SQLite basics (3-minute cheat sheet linked in the Learning Management System (LMS)) and write down one question about indexes or foreign keys.
- Optional: run the micro demo “SQLModel in-memory insert/select (5 lines)” from the quick-demos list so students arrive warmed up.

## Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Recap & intent | 7 min | Discussion | What worked when adding pagination or feature flags to Exercise 1 (EX1)? Any SQLite fears? |
| SQLModel primer | 20 min | Talk + notebook | Tables, models, relationships, ordering, uniqueness. |
| Micro demo: SQLModel insert/select | 3 min | Live demo (≤120 s) | `Session.add`, `Session.exec`, `.all()` in 5 lines. |
| Alembic workflow | 15 min | Talk + whiteboard | `env.py`, autogenerate, upgrade/downgrade, seeding. |
| **Part B – Lab 1** | **45 min** | **Guided coding** | **Wire SQLModel engine, models, migrations.** |
| Break | 10 min | — | Launch the shared [10-minute timer](https://e.ggtimer.com/10minutes). |
| **Part C – Lab 2** | **45 min** | **Guided testing** | **Repository + FastAPI integration tests, fixtures preview.** |
| Wrap-up & EX1 milestone | 10 min | Questions and Answers (Q&A) | Next steps: indexes, seeding CLI, Alembic discipline. |

## Part A – Theory Highlights
1. **Zoom on `sqlmodel.SQLModel`:** inherits from `pydantic.BaseModel` for validation and `DeclarativeMeta` for SQLAlchemy features. Highlight `table=True` for tables vs. plain models for payloads.
2. **Relationships:** `Relationship(back_populates=...)`, `Field(foreign_key="ratings.movie_id")`. Stress lazy vs eager loading and why we’ll use `selectinload` later.
3. **Uniqueness/indexes:** `Field(index=True, unique=True)` for movie titles or slug fields.
4. **Alembic autogenerate:** show the flow `alembic revision --autogenerate -m "create tables"` → inspect diff → `alembic upgrade head`. Reinforce that Alembic is SQLAlchemy’s migration tool and still requires manual review of generated scripts.
5. **Trace identifiers (IDs) & logging:** reuse request-level `X-Trace-Id` when logging database (DB) actions to keep observability consistent.
6. **Storage decision cheat sheet:** reinforce that SQLModel makes it easy to swap engines. Use SQLite during Sessions 03–05 for a lightweight transactional store, graduate to Postgres once you need concurrent writers or cloud backups, lean on Redis (Session 10) for sub-millisecond caches/rate limiting, and reach for DuckDB when the team needs analytics on local parquet/CSV data. Share the DuckDB deep dive from CodeCut (<https://codecut.ai/deep-dive-into-duckdb-data-scientists/>) so students see why columnar OLAP engines feel different.

## Part B – Hands-on Lab 1 (45 Minutes)

### Lab timeline
- **Minutes 0–10** – Configure the SQLite engine and verify `movies.db` creation.
- **Minutes 10–25** – Model tables with SQLModel (movies + ratings).
- **Minutes 25–35** – Generate and apply the first Alembic migration.
- **Minutes 35–45** – Update repository + dependencies and run `uv run python scripts/db.py migrate`.
### 1. Configure the database engine (`app/db.py`)
```python
from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///./movies.db"
engine = create_engine(DATABASE_URL, echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
```
Call `init_db()` once from a command-line interface (CLI) (below) or during startup for development.

### 2. Define models (`app/models.py`)
```mermaid
erDiagram
    MOVIE ||--o{ RATING : "has many"
    MOVIE {
        int id PK
        string title UNIQUE
        int year
        string genre
    }
    RATING {
        int id PK
        int movie_id FK
        int score
    }
```

`PK` denotes a primary key and `FK` denotes a foreign key in the entity diagram above.

```python
from __future__ import annotations

from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Movie(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, unique=True)
    year: int = Field(ge=1900, le=2100)
    genre: str = Field(default="Unknown", index=True)

    ratings: list["Rating"] = Relationship(back_populates="movie")


class Rating(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movie.id")
    score: int = Field(ge=1, le=5)

    movie: Movie = Relationship(back_populates="ratings")
```

### 3. Create Alembic migration
```bash
uv run alembic init migrations
```
Adjust `env.py` to import `SQLModel.metadata`:
```python
from app.models import SQLModel

# inside run_migrations_online
with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=SQLModel.metadata)
```
Generate first migration:
```bash
uv run alembic revision --autogenerate -m "create movie and rating tables"
uv run alembic upgrade head
```
Encourage students to open the migration file and inspect the generated SQL.

### 4. Update repository to use SQLModel (`app/repository.py`)
```python
from collections.abc import Iterable
from typing import Optional

from sqlmodel import Session, select

from .models import Movie, Rating


class MovieRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> Iterable[Movie]:
        statement = select(Movie).order_by(Movie.title)
        return self.session.exec(statement).all()

    def create(self, *, title: str, year: int, genre: str) -> Movie:
        movie = Movie(title=title, year=year, genre=genre.title())
        self.session.add(movie)
        self.session.commit()
        self.session.refresh(movie)
        return movie

    def get(self, movie_id: int) -> Optional[Movie]:
        return self.session.get(Movie, movie_id)

    def add_rating(self, movie_id: int, score: int) -> Rating:
        rating = Rating(movie_id=movie_id, score=score)
        self.session.add(rating)
        self.session.commit()
        self.session.refresh(rating)
        return rating
```

### 5. Inject session into FastAPI (`app/dependencies.py`)
```python
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends

from .db import get_session
from .repository import MovieRepository


def get_repository() -> Generator[MovieRepository, None, None]:
    with get_session() as session:
        yield MovieRepository(session)

RepositoryDep = Annotated[MovieRepository, Depends(get_repository)]
```
Update FastAPI endpoints (from Session 03) to use the new repository methods. Log `trace_id` alongside `movie_id` when writing to the DB.

### 6. CLI utilities (`scripts/db.py`)
```python
import typer

from app.db import init_db

app = typer.Typer()


@app.command()
def migrate() -> None:
    init_db()
    typer.echo("Database ready")


if __name__ == "__main__":
    app()
```
Run `uv run python scripts/db.py migrate` to create local tables quickly.

> 🎉 **Quick win:** Seeing “Database ready” means your SQLModel metadata and Alembic migration are in sync—no more in-memory data loss.

## Part C – Hands-on Lab 2 (45 Minutes)

### Lab timeline
- **Minutes 0–10** – Build temporary SQLite fixture and override dependencies.
- **Minutes 10–25** – Write repository/API tests using the fixture.
- **Minutes 25–35** – Validate ratings relationship + commit/rollback behavior.
- **Minutes 35–45** – Practice Alembic downgrade/upgrade cycle and discuss seeding strategies.
### 1. Temporary DB fixture (preview)
Create `tests/conftest.py`:
```python
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.dependencies import get_repository
from app.repository import MovieRepository

TEST_DB = "sqlite:///./test_movies.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})


@pytest.fixture(autouse=True)
def _clean_db() -> Generator[None, None, None]:
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def repository(monkeypatch) -> MovieRepository:
    def _override_repo():
        with Session(engine) as session:
            yield MovieRepository(session)

    monkeypatch.setattr("app.dependencies.get_repository", _override_repo)
    with Session(engine) as session:
        yield MovieRepository(session)
```

### 2. Rewrite tests to cover DB operations
`tests/test_movies.py`:
```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_movie_persists_and_lists(repository):
    response = client.post(
        "/movies",
        json={"title": "Arrival", "year": 2016, "genre": "sci-fi"},
        headers={"X-Trace-Id": "sql-demo"},
    )
    assert response.status_code == 201

    list_response = client.get("/movies")
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Arrival"


def test_add_rating_creates_relationship(repository):
    create = client.post(
        "/movies",
        json={"title": "Dune", "year": 2021, "genre": "sci-fi"},
    ).json()

    rating = repository.add_rating(movie_id=create["id"], score=5)
    assert rating.score == 5
    assert rating.movie_id == create["id"]
```
Run `uv run pytest -q` and call out that autouse fixtures reset the DB per test (Session 07 will formalize fixtures and factories).

> 🎉 **Quick win:** Green pytest output means your migrations + fixtures are stable—capture the command in your README before moving on.

### 3. Alembic downgrade drill
```bash
uv run alembic downgrade -1
uv run alembic upgrade head
```
Explain how to recover from broken migrations.

### 4. Optional stretch – uniqueness guard
Add a unique constraint check and raise HTTP 409 in the FastAPI route; note this as EX1 stretch.

## Wrap-up & Next Steps
- ✅ SQLModel models, Alembic migrations, FastAPI integration, and test coverage across the DB boundary.
- Next: integrate metrics/logging (Session 07), add richer queries (`selectinload`), add seeded data via CLI, and explore read/write splitting as a thought experiment.
- Encourage updating documentation (`docs/contracts/data-model.md`) with ER diagrams and constraints.
- Point students to [docs/exercises.md](../exercises.md#ex2--friendly-interface) so they can plan the data requirements their user interface (UI) deliverable for Exercise 2 (EX2) must satisfy.

## Troubleshooting
- **`sqlite3.OperationalError: no such table`** → ensure migrations ran (`uv run alembic upgrade head`).
- **“SQLite objects created in a thread can only be used in that same thread”** → include `connect_args={"check_same_thread": False}` for tests.
- **Alembic autogenerate misses changes** → verify models are imported in `env.py` and metadata is accurate.

### Common pitfalls
- **Forgetting to commit sessions** – always call `session.commit()` before returning models, otherwise changes vanish.
- **Migrations out of sync** – if Alembic complains, regenerate `env.py` imports or delete stray `.pyc` in `migrations/`.
- **Fixture state collisions** – ensure each test uses fresh `Session(engine)` context to avoid shared connections.

## Student Success Criteria

By the end of Session 05, every student should be able to:

- [ ] Model movies/ratings with SQLModel and run Alembic migrations.
- [ ] Replace the in-memory repository with SQLite-backed CRUD operations.
- [ ] Execute pytest suites that rely on temporary SQLite fixtures.

**If a student is missing a checkbox, schedule a persistence clinic before Session 06.**

## AI Prompt Seeds
- “Generate SQLModel models for movies and ratings with a relationship and uniqueness on title.”
- “Write an Alembic migration that creates movie/rating tables with indexes.”
- “Suggest pytest fixtures for SQLite databases that reset state per test.”
