# Session 03 – FastAPI Fundamentals (Movie Service v0)

- **Date:** Monday, Nov 17, 2025
- **Theme:** Build a complete FastAPI movie service with dependency injection, validation, and automated tests.

## Learning Objectives

By the end of this session, you will:
- Build REST API endpoints with FastAPI using proper HTTP methods and status codes
- Validate request/response data with Pydantic v2 models and custom validators
- Implement dependency injection to manage shared resources (settings, repositories)
- Write automated tests using pytest and TestClient
- Run the same application locally and in Docker containers

## What You'll Build

A working FastAPI backend that:
- Stores movies in memory with CRUD operations
- Validates all incoming data (year ranges, required fields)
- Returns proper HTTP status codes (200, 201, 404, 422)
- Includes comprehensive test coverage
- Runs identically on your machine and in Docker

### EX1 Baseline (In-Memory Only)

- This session **is the EX1 deliverable**: students leave class with a FastAPI backend, pytest suite, Docker packaging, and REST client scripts that satisfy the HTTP API portion of the exercise—even if data only lives in memory for now. Think of it as microservice #1 in the eventual EX3 stack.
- In-memory storage is intentional at this checkpoint; it keeps the focus on HTTP verbs, validation, dependency injection, and smoke testing. Everyone can demo the service (curl, REST Client, Docker) without juggling SQL yet.
- Preview the roadmap: **Session 04 adds SQLModel + SQLite** so the same API talks to a real database. That persistence layer becomes non‑negotiable before EX3, where teams will run at least three cooperating services (FastAPI backend, persistence, and a UI/automation surface).
- Encourage students to push this code to their EX1 repo immediately. Session 04’s DB changes layer on top of the same HTTP contract—they are not a different app, just service hardening that prepares the multi-service system you expect by the final exercise.
- **Architecture decision**: We use `Movie` as both the domain model and response model today. Session 04 will introduce `MovieRead` to distinguish SQLModel tables from API responses, but the HTTP contract stays identical.

## Live Build Strategy (No Pre-Solved Example)

- This session is the canonical FastAPI walkthrough for the whole course, so we now build the example entirely from the scripted steps below instead of keeping a separate `examples/fastapi-calculator/` folder.
- Treat this document as the live-coding script: copy/paste the code fences when time is tight, or narrate each block while students type. Everything here feeds directly into Sessions 04–07, so keeping it inline prevents drift.
- Want a rehearse-ready reference? Pair these steps with the REST Client snippets in `examples.http`—they hit the exact endpoints you create in Lab 1.
- Optional deep dives that truly need their own repos (for example the blockchain mini-demo) are cataloged in `examples/README.md`; they stay disconnected from the core FastAPI storyline on purpose.

## Prerequisites

Before class, complete these setup steps:

1. **Install Python 3.12 with uv:**
   ```bash
   # Install uv package manager
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install Python 3.12
   uv python install 3.12
   ```

2. **Create project workspace:**
   ```bash
   mkdir hello-uv && cd hello-uv
   git init
   ```

3. **Add dependencies:**
   ```bash
   uv add fastapi uvicorn pydantic pydantic-settings httpx pytest
   ```

4. **Create environment template:**
   Create `.env.example` with:
   ```ini
   MOVIE_APP_NAME="Movie Service"
   MOVIE_DEFAULT_PAGE_SIZE=20
   MOVIE_FEATURE_PREVIEW=false
   ```
   
   Copy to `.env` for local use:
   ```bash
   cp .env.example .env
   ```

5. **Verify setup:**
   ```bash
   uv run python -c "import fastapi, pydantic; print('Ready!')"
   ```

## Toolkit Snapshot
- **FastAPI** – async-ready web framework that maps HTTP verbs to Python functions and autogenerates OpenAPI docs.
- **uv** – Python/packaging manager from Astral; manages Python 3.12 installs, virtual envs, and dependency locking.
- **Pydantic v2** – data validation library; enforces request/response shapes via type hints and `Field` metadata.
- **pytest + TestClient** – testing framework plus FastAPI’s HTTP client for asserting status codes and payloads.
- **httpx** – modern HTTP library (sync/async) you can reuse for CLI checks or future integration tests.
- **Docker** – optional packaging step that proves the same FastAPI app runs outside your local Python setup.

## Session Agenda

| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Part A – Recap & intent | 5 min | Guided discussion | Surface wins from Session 02, confirm EX1 blockers, frame why FastAPI is today's focus. |
| Part A – FastAPI fundamentals | 15 min | Talk + board | Map HTTP verbs to path operations, highlight what `/docs` gives you for free. |
| Part A – Request flow walkthrough | 10 min | Diagram walkthrough | Trace HTTP → FastAPI → dependency injection → repository → response. |
| Part A – Live demo: docs + TestClient | 15 min | Live coding | Show how FastAPI auto-generates docs/tests before we build it ourselves. |
| Break | 10 min | — | Walk/stretch, reset terminals. |
| **Part B – Lab 1** | **45 min** | **Guided build** | **Scaffold config, models, repository, and routes for Movie Service v0.** |
| Break | 10 min | — | Hydrate, swap drivers. |
| **Part C – Lab 2** | **45 min** | **Guided testing** | **Pytest fixtures, TestClient, regression hunts, red→green loops.** |
| Docker deployment demo | 10 min | Live demo | Containerize the same app, compare local vs Docker runs. |
| Wrap-up & checklist | 10 min | Discussion + Q&A | Review deliverables, preview Session 04 (SQLite + SQLModel). |

## Part A – Theory & Live Demos (45 minutes)

**Talk track:**
- Kick off with a 60-second recap of Session 02's HTTP anatomy and connect it to today's goal: code the same contracts in FastAPI.
- Draw the request flow (client → FastAPI app → dependency injection → repository → response) before showing any code so students see where each file fits.
- Bounce between the board and the live server (`/docs`, `pytest`) so every concept immediately maps to feedback loops they'll use in Labs 1 and 2.

### 1. FastAPI Path Operations (15 min)

FastAPI maps HTTP methods to Python functions:

```python
@app.get("/movies")           # GET request - retrieve data
def list_movies(): ...

@app.post("/movies")          # POST request - create new resource
def create_movie(): ...

@app.get("/movies/{id}")      # GET with path parameter
def get_movie(id: int): ...

@app.delete("/movies/{id}")   # DELETE request - remove resource
def delete_movie(id: int): ...
```

**Status codes matter:**
- `200` - Successful GET/PUT/DELETE
- `201` - Resource created (POST)
- `204` - Success with no content (DELETE)
- `404` - Resource not found
- `422` - Validation error

### 2. Pydantic Models for Validation (10 min)

Pydantic automatically validates request/response data:

```python
from pydantic import BaseModel, Field

class MovieCreate(BaseModel):
    title: str
    year: int = Field(ge=1900, le=2100)  # Between 1900-2100
    genre: str
```

Benefits:
- Automatic type checking
- Clear error messages
- Self-documenting API
- Auto-generated OpenAPI docs

### 3. Dependency Injection (10 min)

Share resources across endpoints without globals:

```python
from fastapi import Depends

def get_repository():
    return MovieRepository()

@app.post("/movies")
def create_movie(
    payload: MovieCreate,
    repo: MovieRepository = Depends(get_repository)
):
    return repo.create(payload)
```

Why use DI:
- Easy to test (swap dependencies)
- No global state issues
- Clear dependencies in function signatures

### 4. Local Feedback Loops (10 min)

- Run the API with `uv run uvicorn movie_service.app.main:app --reload` for instant reloads.
- Keep pytest green: `uv run pytest movie_service/tests -q`.
- Use `curl` or `httpie` to hit endpoints exactly as your automated tests do.
- The faster the loop, the easier it is to spot regressions before moving on.

## Part B – Lab 1: Build the Movie API (45 minutes)

**Goals:** Ship an in-memory FastAPI service with health + CRUD endpoints, dependency injection, and clean separation between config, models, repositories, and routes.

**Facilitation tips:**
- Keep VS Code and the terminal side by side; pause after each file so students catch up before moving on.
- Continuously connect each file to the earlier request-flow diagram so the mental model stays intact.
- Remind the cohort that Session 04 swaps the repository for SQLModel, so investing in clean boundaries now pays off later.

Follow these steps to build a working FastAPI application from scratch.

### Step 1: Create Project Structure (5 min)

```bash
cd hello-uv
mkdir -p movie_service/{app,tests,scripts}
touch movie_service/__init__.py
touch movie_service/app/__init__.py
touch movie_service/tests/__init__.py
```

Your structure:
```
hello-uv/
├── .env
├── .env.example
├── pyproject.toml
└── movie_service/
    ├── __init__.py
    ├── app/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── models.py       # ← new in this session
    │   ├── repository.py
    │   ├── dependencies.py
    │   └── main.py
    ├── tests/
    │   └── __init__.py
    └── scripts/
```

### Step 2: Configure Settings (5 min)

Create `movie_service/app/config.py`:

````python
# filepath: movie_service/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    app_name: str = "Movie Service"
    default_page_size: int = 20
    feature_preview: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",           # Load from .env file
        env_prefix="MOVIE_",       # Only read MOVIE_* variables
        extra="ignore",            # Ignore unknown variables
    )
````

**What this does:**
- Loads configuration from `.env` file
- Reads variables starting with `MOVIE_` prefix
- Provides defaults if variables aren't set
- Type-checks all values

### Step 3: Define Pydantic Models (5 min)

Create `movie_service/app/models.py`:

````python
# filepath: movie_service/app/models.py
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class MovieBase(BaseModel):
    """Shared fields for create/read models."""
    title: str
    year: int = Field(ge=1900, le=2100)
    genre: str


class Movie(MovieBase):
    """Response model that includes the server-generated ID.
    
    Note: In Session 04, we'll split this into `Movie` (table) and 
    `MovieRead` (response), but the HTTP contract stays the same.
    """
    id: int


class MovieCreate(MovieBase):
    """Incoming payload with validation + normalization."""

    @model_validator(mode="after")
    def normalize_genre(self) -> "MovieCreate":
        """Title-case the genre: 'sci-fi' → 'Sci-Fi'.
        
        This validator will carry forward to Session 04's SQLModel version,
        demonstrating how validation rules survive persistence layer swaps.
        """
        self.genre = self.genre.title()
        return self
````

**Why split models from controllers:**
- Controllers (FastAPI routes) only care about IO contracts.
- Repositories reuse the same schemas without importing FastAPI.
- Future persistence swaps (Session 04) can reuse the same models.

### Step 4: Build the Repository (10 min)

Create `movie_service/app/repository.py`:

````python
# filepath: movie_service/app/repository.py
from __future__ import annotations

from typing import Dict

from .models import Movie, MovieCreate


class MovieRepository:
    """In-memory storage for movies.
    
    Session 04 will replace this implementation with SQLModel + SQLite,
    but the interface (list/create/get/delete) stays identical so routes
    don't need to change.
    """

    def __init__(self) -> None:
        self._items: Dict[int, Movie] = {}
        self._next_id = 1

    def list(self) -> list[Movie]:
        """Get all movies.
        
        Returns list for now; Session 04 changes to Sequence[Movie]
        to match SQLModel's query results.
        """
        return list(self._items.values())

    def create(self, payload: MovieCreate) -> Movie:
        """Add a new movie and return it with assigned ID.
        
        Session 04: This becomes `session.add()` + `session.commit()`,
        but the function signature stays the same.
        """
        movie = Movie(id=self._next_id, **payload.model_dump())
        self._items[movie.id] = movie
        self._next_id += 1
        return movie

    def get(self, movie_id: int) -> Movie | None:
        """Get a movie by ID, or None if not found.
        
        Session 04: Changes to `session.get(Movie, movie_id)`.
        """
        return self._items.get(movie_id)

    def delete(self, movie_id: int) -> None:
        """Remove a movie by ID.
        
        Session 04: Changes to `session.delete()` + `session.commit()`.
        """
        self._items.pop(movie_id, None)

    def clear(self) -> None:
        """Remove all movies (useful for tests).
        
        Session 04: Test fixtures will use separate test databases
        instead of clearing a shared repository.
        """
        self._items.clear()
        self._next_id = 1
````

**Key features:**
- Repository depends only on the domain models.
- Controllers can stay lean—no storage details leak into FastAPI handlers.
- Tests can import `MovieRepository` without touching FastAPI.

### Step 5: Wire Up Dependencies (5 min)

Create `movie_service/app/dependencies.py`:

````python
# filepath: movie_service/app/dependencies.py
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends

from .config import Settings
from .repository import MovieRepository

# Create singletons
_settings = Settings()
_repository = MovieRepository()


def get_settings() -> Settings:
    """Provide settings to endpoints."""
    return _settings


def get_repository() -> Generator[MovieRepository, None, None]:
    """Provide repository to endpoints."""
    yield _repository


# Type aliases for cleaner endpoint signatures
SettingsDep = Annotated[Settings, Depends(get_settings)]
RepositoryDep = Annotated[MovieRepository, Depends(get_repository)]
````

**Why this pattern:**
- One instance of Settings shared across all requests
- One instance of Repository shared across all requests
- Easy to swap implementations for testing
- Type hints make code self-documenting

### Step 6: Build the FastAPI App (15 min)

Create `movie_service/app/main.py`:

````python
# filepath: movie_service/app/main.py
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, status

from .dependencies import RepositoryDep, SettingsDep
from .models import Movie, MovieCreate

logger = logging.getLogger("movie-service")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

app = FastAPI(title="Movie Service", version="0.1.0")


@app.get("/health", tags=["diagnostics"])
def health(settings: SettingsDep) -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "app": settings.app_name}


@app.get("/movies", response_model=list[Movie], tags=["movies"])
def list_movies(repository: RepositoryDep) -> list[Movie]:
    """Get all movies."""
    return list(repository.list())


@app.post(
    "/movies",
    response_model=Movie,
    status_code=status.HTTP_201_CREATED,
    tags=["movies"],
)
def create_movie(
    payload: MovieCreate,
    repository: RepositoryDep,
) -> Movie:
    """Create a new movie."""
    movie = repository.create(payload)
    logger.info("movie.created id=%s title=%s", movie.id, movie.title)
    return movie


@app.get("/movies/{movie_id}", response_model=Movie, tags=["movies"])
def read_movie(movie_id: int, repository: RepositoryDep) -> Movie:
    """Get a specific movie by ID."""
    movie = repository.get(movie_id)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found",
        )
    return movie


@app.delete(
    "/movies/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["movies"],
)
def delete_movie(movie_id: int, repository: RepositoryDep) -> None:
    """Delete a movie by ID."""
    if repository.get(movie_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found",
        )
    repository.delete(movie_id)
    logger.info("movie.deleted id=%s", movie_id)
````

**Controller responsibility stays thin:** FastAPI handlers import the Pydantic models for type safety but let the repository enforce storage rules and business logic.

### Step 7: Run the API (5 min)

Start the server:
```bash
cd hello-uv
uv run uvicorn movie_service.app.main:app --reload
```

You'll see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

**Test it works:**

1. **Visit the docs:** Open `http://127.0.0.1:8000/docs` in your browser
   - See all endpoints with request/response schemas
   - Try creating a movie directly in the UI

2. **Test with curl:**
```bash
# Create a movie
curl -X POST http://localhost:8000/movies \
  -H "Content-Type: application/json" \
  -d '{"title": "Inception", "year": 2010, "genre": "sci-fi"}'

# List all movies
curl http://localhost:8000/movies

# Check health
curl http://localhost:8000/health
```

**Success criteria:**
- Server starts without errors
- `/docs` page loads and shows all endpoints
- Can create and retrieve movies

## Part C – Lab 2: Test Everything (45 minutes)

**Goals:** Turn pytest into a guardrail so every regression is caught before Docker or GitHub.

**Facilitation tips:**
- Start by running a single failing test to show how fast TestClient feedback arrives.
- Narrate the purpose of each fixture (state isolation, dependency overrides) before writing assertions.
- Celebrate the red→green moment, then immediately demonstrate how a removed validator is caught.

### Step 1: Create Test Fixtures (10 min)

Create `movie_service/tests/conftest.py`:

````python
# filepath: movie_service/tests/conftest.py
import pytest
from fastapi.testclient import TestClient

from movie_service.app.main import app
from movie_service.app.dependencies import get_repository


@pytest.fixture(autouse=True)
def clear_repository():
    """Clear repository before and after each test."""
    repo = next(get_repository())
    repo.clear()
    yield
    repo.clear()


@pytest.fixture
def client():
    """Provide a TestClient for making requests."""
    return TestClient(app)
````

**What fixtures do:**
- `clear_repository` - Prevents tests from affecting each other
- `client` - Lets you make HTTP requests to your app
- `autouse=True` - Runs automatically before every test

### Step 2: Write Comprehensive Tests (25 min)

Create `movie_service/tests/test_movies.py`:

````python
# filepath: movie_service/tests/test_movies.py

def test_health_includes_app_name(client):
    """Health endpoint returns status and app name."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Movie Service"


def test_create_movie_returns_201_and_payload(client):
    """Creating a movie returns 201 with normalized payload."""
    response = client.post(
        "/movies",
        json={"title": "The Matrix", "year": 1999, "genre": "sci-fi"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "The Matrix"
    assert payload["year"] == 1999
    assert payload["genre"] == "Sci-Fi"  # normalized by validator
    assert payload["id"] == 1


def test_movie_ids_increment(client):
    """Repository assigns sequential IDs."""
    first = client.post(
        "/movies",
        json={"title": "Blade Runner", "year": 1982, "genre": "sci-fi"},
    ).json()["id"]
    second = client.post(
        "/movies",
        json={"title": "Blade Runner 2049", "year": 2017, "genre": "sci-fi"},
    ).json()["id"]
    assert second == first + 1


def test_list_movies_returns_empty_array_initially(client):
    """Empty repository returns empty array."""
    response = client.get("/movies")
    assert response.status_code == 200
    assert response.json() == []


def test_list_movies_returns_created_movie(client):
    """Can retrieve movies after creating them."""
    client.post(
        "/movies",
        json={"title": "Dune", "year": 2021, "genre": "sci-fi"},
    )
    
    response = client.get("/movies")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 1
    assert movies[0]["title"] == "Dune"


def test_get_movie_by_id(client):
    """Can retrieve specific movie by ID."""
    create_response = client.post(
        "/movies",
        json={"title": "Arrival", "year": 2016, "genre": "sci-fi"},
    )
    movie_id = create_response.json()["id"]
    
    response = client.get(f"/movies/{movie_id}")
    assert response.status_code == 200
    movie = response.json()
    assert movie["title"] == "Arrival"
    assert movie["id"] == movie_id


def test_get_missing_movie_returns_404(client):
    """Requesting non-existent movie returns 404."""
    response = client.get("/movies/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found"


def test_delete_movie(client):
    """Can delete a movie and it's gone afterwards."""
    create_response = client.post(
        "/movies",
        json={"title": "Interstellar", "year": 2014, "genre": "sci-fi"},
    )
    movie_id = create_response.json()["id"]
    
    response = client.delete(f"/movies/{movie_id}")
    assert response.status_code == 204
    
    get_response = client.get(f"/movies/{movie_id}")
    assert get_response.status_code == 404


def test_delete_missing_movie_returns_404(client):
    """Deleting non-existent movie returns 404."""
    response = client.delete("/movies/9999")
    assert response.status_code == 404


def test_create_movie_rejects_year_too_old(client):
    """Year before 1900 is rejected with 422."""
    response = client.post(
        "/movies",
        json={"title": "Metropolis", "year": 1800, "genre": "sci-fi"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("year" in str(err).lower() for err in detail)


def test_create_movie_rejects_year_too_new(client):
    """Year after 2100 is rejected with 422."""
    response = client.post(
        "/movies",
        json={"title": "Future Film", "year": 2200, "genre": "sci-fi"},
    )
    assert response.status_code == 422


def test_create_movie_rejects_missing_title(client):
    """Missing required field returns 422."""
    response = client.post(
        "/movies",
        json={"year": 2020, "genre": "drama"},
    )
    assert response.status_code == 422
````

### Step 3: Run the Tests (5 min)

```bash
cd hello-uv
uv run pytest movie_service/tests -v
```

You should see:
```
test_health_includes_app_name PASSED
test_create_movie_returns_201_and_payload PASSED
test_movie_ids_increment PASSED
...
==================== 13 passed in 0.45s ====================
```

**If tests fail:**
1. Read the error message carefully
2. Check which assertion failed
3. Print the response: `print(response.json())`
4. Fix the code, rerun the test

### Step 4: Practice Red→Green Testing (5 min)

**Live demonstration of test-driven development:**

1. **Break something** - Comment out the genre validator:
   ```python
   # @model_validator(mode="after")
   # def normalize_genre(self):
   #     self.genre = self.genre.title()
   #     return self
   ```

2. **Run tests** - See them fail:
   ```bash
   uv run pytest movie_service/tests::test_create_movie_returns_201_and_payload -v
   ```
   Output: `AssertionError: assert 'sci-fi' == 'Sci-Fi'`

3. **Restore the validator** - Uncomment the code

4. **Run tests again** - See them pass

**The lesson:** Tests catch regressions immediately. Always run tests before committing code.

## Docker Deployment (10 minutes)

Run the exact same application in a container.

### Create Dockerfile

Create `movie_service/Dockerfile`:

````dockerfile
# filepath: movie_service/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv pip install --system fastapi uvicorn pydantic pydantic-settings httpx

# Copy application code
COPY movie_service ./movie_service

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "movie_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
````

### Build and Run

```bash
# Build the image (from hello-uv directory)
docker build -t movie-service -f movie_service/Dockerfile .

# Run the container
docker run --rm -p 8000:8000 --name movie-service movie-service
```

**Test it:**
- Visit `http://127.0.0.1:8000/docs`
- Same API, same behavior, different environment
- Stop with Ctrl+C

**Key insight:** Docker ensures your app runs the same way everywhere—your laptop, a teammate's machine, production servers.

## Export API Contract

Document your API with OpenAPI schema.

Create `movie_service/scripts/export_openapi.py`:

````python
# filepath: movie_service/scripts/export_openapi.py
import json
from pathlib import Path

from movie_service.app.main import app

schema = app.openapi()

contracts_dir = Path("docs/contracts")
contracts_dir.mkdir(parents=True, exist_ok=True)

output_path = contracts_dir / "movie-service-openapi.json"
output_path.write_text(json.dumps(schema, indent=2))

print(f"Exported OpenAPI schema to {output_path}")
print(f"Title: {schema['info']['title']}")
print(f"Version: {schema['info']['version']}")
print(f"Endpoints: {len(schema['paths'])}")
````

Run it:
```bash
uv run python -m movie_service.scripts.export_openapi
```

**What this gives you:**
- Machine-readable API contract
- Can generate client code automatically
- Can validate API behavior with schema testing tools
- Living documentation that never gets outdated with your code

## Wrap-Up & Deliverables

### What You Built

- FastAPI application with CRUD operations  
- Pydantic validation with custom validators  
- Dependency injection for settings and repositories  
- Comprehensive test suite with 13 passing tests  
- Docker containerization  
- OpenAPI schema export  

### Complete Checklist

Before moving forward, ensure:

- [ ] All tests pass: `uv run pytest movie_service/tests -v`
- [ ] Server runs locally: `uv run uvicorn movie_service.app.main:app --reload`
- [ ] Docker build succeeds: `docker build -t movie-service -f movie_service/Dockerfile .`
- [ ] API docs load at `/docs`
- [ ] Can create, list, get, and delete movies
- [ ] Validation errors return 422 with details
- [ ] OpenAPI schema exports successfully

### Next Steps

**Enhancements to add:**
1. `PUT /movies/{id}` endpoint for updates
2. Pagination with `skip` and `limit` parameters
3. Search/filter endpoints
4. More comprehensive error handling
5. Update README with setup instructions

**Session 04 will upgrade this exact service with:**
- SQLModel + SQLite persistence (data survives restarts)
- Database-aware pytest fixtures (isolated test databases)
- Alembic migrations (version-controlled schema changes)
- Seed scripts (reproducible starter data)
- **Zero changes to HTTP routes** (only repository internals swap)

**Why the repository pattern matters:** Every `repo.create()` call you wrote today will work with SQLite tomorrow because we kept storage behind a clean interface. This is the architectural payoff for modular design.

## Troubleshooting

**Server won't start:**
```bash
# Verify dependencies
uv run python -c "import fastapi; print('OK')"

# Check for port conflicts
lsof -i :8000
```

**Tests failing:**
```bash
# Run single test with verbose output
uv run pytest movie_service/tests::test_create_movie_returns_201_and_payload -vv

# Print response in test
def test_something(client):
    response = client.post("/movies", json={...})
    print(response.json())  # Add this line
    assert ...
```

**Import errors:**
```bash
# Ensure you're in the right directory
pwd  # Should show .../hello-uv

# Run with proper module path
uv run python -m movie_service.app.main
```

**Docker build fails:**
```bash
# Build with verbose output
docker build --progress=plain -t movie-service -f movie_service/Dockerfile .

# Check if files exist
ls movie_service/app/main.py
```

## Key Takeaways

1. **FastAPI is productive**: Routes, validation, and docs are automatic
2. **Pydantic validates everything**: Catch errors before they cause problems
3. **Dependency injection is powerful**: Easy to test, easy to swap implementations
4. **Tests give confidence**: Run them often, commit when green
5. **Docker provides consistency**: Same behavior everywhere
6. **OpenAPI is free documentation**: Always up-to-date with your code

## Success Criteria

You're ready to move on when you can:

- [x] Explain how a request flows through FastAPI (middleware → route → dependencies → handler)
- [x] Create new endpoints with proper HTTP methods and status codes
- [x] Add Pydantic validation rules and custom validators
- [x] Write tests that cover happy paths and error cases
- [x] Use dependency injection to share resources
- [x] Run the same code locally and in Docker
- [x] Export and understand the OpenAPI schema

**Schedule a mentor session if any box remains unchecked.**

## AI Prompt Seeds

- "Given this spec for `/movies` CRUD plus `/health`, scaffold config, models, repository, dependencies, and FastAPI routes that use `pydantic-settings` + dependency injection."
- "Write pytest cases (using FastAPI's `TestClient`) that prove movie creation, lookup, deletion, and divide-by-zero-style errors work; include a fixture that clears the in-memory repository between tests."
- "Propose a Dockerfile and uv commands so the exact same FastAPI app runs locally and in a container; explain why each instruction exists."
- "Summarize a verification checklist for students building this example live: which commands should they run after each lab block to ensure parity with the instructor?"
