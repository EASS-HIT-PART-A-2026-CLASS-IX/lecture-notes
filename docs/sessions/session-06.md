# Session 06 – Streamlit Dashboards + Typer UX

- **Date:** Monday, 13/04/2026
- **Theme:** Ship a Streamlit dashboard and Typer CLI on top of the Postgres-backed FastAPI API, plus a short JavaScript/TypeScript warm-up to prep for frontend work.

## Session Story
With Postgres live from Session 05, the backend is stable enough for real UIs. Today you’ll build a Streamlit dashboard that lists, filters, and creates movies through the existing API, and you’ll add Typer/Rich helpers for operators. We end with a short JavaScript/TypeScript warm-up so next week’s React sprint feels familiar.

## Learning Objectives
- Consume FastAPI with typed `httpx` helpers, shared env vars, and trace IDs.
- Build Streamlit dashboards that cache GETs, bust cache on writes, and render quick insights.
- Automate seed/reset/export flows with a Typer CLI layered on the repository.
- Keep tests green against Postgres while UI layers evolve.
- Refresh core JS/TS concepts (modules, async/await, fetch) to stay ready for frontend work.

## Deliverables (What You’ll Build)
- `frontend/client.py` – typed HTTP client with trace headers for `/movies`.
- `frontend/dashboard.py` – Streamlit page with list view, filters, metrics, and create/delete flows.
- `scripts/ui.py` – Typer CLI for seed/reset/export (uses the same repository).
- Updated docs/runbook notes for running FastAPI + Streamlit concurrently.

## Toolkit Snapshot
- **Streamlit** – Python-first dashboards + forms.
- **httpx** – shared client for Streamlit and Typer.
- **Typer + Rich** – operator UX with nice output.
- **PostgreSQL** – same DB from Session 05; UI never talks to it directly.
- **JavaScript/TypeScript primer** – light prep for Vite/React.

## Before Class (JiTT)
1. Ensure Postgres is running: `docker compose up -d db` and `curl http://localhost:8000/healthz`.
2. `.env` should include `MOVIE_API_BASE_URL=http://localhost:8000` plus the Postgres URL from Session 05.
3. Install UI deps:
   ```bash
   uv add streamlit rich typer httpx python-dotenv pandas
   ```
4. Seed some movies (reuse `scripts/db.py`): `uv run python scripts/db.py bootstrap --sample 5`.
5. JS preview sanity checks (for the short demo): `node --version`, `corepack enable`, `corepack prepare pnpm@latest --activate`, `pnpm --version`.

## Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Recap & intent | 10 min | Discussion | Why Postgres unlocks UI experiments. |
| Streamlit + API primer | 20 min | Talk + demo | Typed clients, caching, trace IDs, CORS. |
| **Part B – Lab 1** | **45 min** | **Guided build** | **Client helpers + dashboard list view.** |
| Break | 10 min | — | Cache/CORS Q&A. |
| **Part C – Lab 2** | **45 min** | **Guided build** | **Forms, Typer CLI, runbook updates.** |
| JS/TS preview | 15 min | Talk + mini-demo | Async/await, fetch, pnpm basics. |
| Wrap-up | 10 min | Q&A | Checklist and open questions. |

## Lab 1 – Typed client + dashboard (45 min)
Goal: render Postgres-backed movies in Streamlit with cached GETs and ready-to-wire write paths.

### Step 0 – Confirm API + data
Keep FastAPI running in one terminal:
```bash
uv run uvicorn movie_service.app.main:app --reload
curl http://localhost:8000/movies
```
Seed if empty: `uv run python scripts/db.py bootstrap --sample 5`.

### Step 1 – Typed client
`frontend/client.py`
````python
from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class UISettings(BaseSettings):
    api_base_url: str = "http://localhost:8000"
    trace_id: str = "ui-streamlit"

    model_config = SettingsConfigDict(env_prefix="MOVIE_", env_file=".env", extra="ignore")


settings = UISettings()


@lru_cache(maxsize=1)
def _client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.api_base_url,
        headers={"X-Trace-Id": settings.trace_id},
        timeout=5.0,
    )


def list_movies(*, genre: str | None = None) -> list[dict[str, Any]]:
    params = {"genre": genre} if genre else None
    response = _client().get("/movies", params=params)
    response.raise_for_status()
    return response.json()


def create_movie(*, title: str, year: int, genre: str) -> dict[str, Any]:
    response = _client().post("/movies", json={"title": title, "year": year, "genre": genre})
    response.raise_for_status()
    return response.json()


def delete_movie(movie_id: int) -> None:
    response = _client().delete(f"/movies/{movie_id}")
    response.raise_for_status()
````

### Step 2 – First Streamlit view
`frontend/dashboard.py`
````python
import pandas as pd
import streamlit as st

from frontend.client import list_movies

st.set_page_config(page_title="Movie Pulse", layout="wide")
st.title("Movie Service Dashboard")
st.caption("FastAPI + Postgres backing; trace IDs flow through headers.")


@st.cache_data(ttl=30)
def cached_movies(genre: str | None = None) -> list[dict]:
    return list_movies(genre=genre)


with st.spinner("Fetching movies..."):
    movies = cached_movies()

if not movies:
    st.info("No movies yet. Add some via the API or Typer CLI.")
else:
    st.metric("Total movies", len(movies))
    st.dataframe(pd.DataFrame(movies))
````
Run: `uv run streamlit run frontend/dashboard.py`.

### Step 3 – Filters + cache invalidation
```python
genres = sorted({m["genre"] for m in movies})
selected = st.multiselect("Filter by genre", genres)
displayed = cached_movies(selected[0] if selected else None)

if st.button("Refresh data"):
    cached_movies.clear()
    st.experimental_rerun()

st.dataframe(pd.DataFrame(displayed))
```

## Lab 2 – Forms, Typer, documentation (45 min)
Goal: mutate data from the UI, add an operator CLI, and capture how to run both servers.

### Step 1 – Write operations
In `frontend/dashboard.py`, add:
```python
from frontend.client import create_movie, delete_movie

with st.expander("Add movie"):
    with st.form("create_movie"):
        title = st.text_input("Title")
        year = st.number_input("Year", min_value=1900, max_value=2100, value=2024)
        genre = st.text_input("Genre", value="sci-fi")
        submitted = st.form_submit_button("Create")
    if submitted:
        try:
            movie = create_movie(title=title, year=year, genre=genre)
            cached_movies.clear()
            st.success(f"Created {movie['title']}")
        except Exception as exc:  # pragma: no cover
            st.error(f"Failed: {exc}")

if movies:
    to_delete = st.selectbox("Delete movie", options=[m["id"] for m in movies])
    if st.button("Delete selected"):
        delete_movie(int(to_delete))
        cached_movies.clear()
        st.success("Deleted movie")
```

### Step 2 – Typer CLI for operators
`scripts/ui.py` (describe; create during lab):
````python
import typer
from rich import print

from movie_service.app.models import MovieCreate
from movie_service.app.repository_db import MovieRepository
from movie_service.app.database import engine, init_db
from sqlmodel import Session

app = typer.Typer(help="UI/ops helpers")


@app.command()
def reset(sample: int = 5) -> None:
    """Drop + recreate tables; seed sample movies."""
    init_db()
    with Session(engine) as session:
        repo = MovieRepository(session)
        repo.delete_all()
        for idx in range(sample):
            repo.create(MovieCreate(title=f"Sample {idx+1}", year=2010 + idx, genre="sci-fi"))
    print(f"[green]Reset complete with {sample} movies[/green]")


@app.command()
def export() -> None:
    with Session(engine) as session:
        repo = MovieRepository(session)
        for movie in repo.list():
            print(movie)


if __name__ == "__main__":
    app()
````
Run: `uv run python scripts/ui.py reset --sample 5`.

### Step 3 – JS/TS preview (15 minutes)
- Verify Node/pnpm (`node --version`, `pnpm --version`).
- Mini fetch demo (run with `node`):
  ```js
  const res = await fetch("http://localhost:8000/movies");
  const movies = await res.json();
  console.log(movies.map((m) => m.title));
  ```
- Emphasize that any future frontend work will reuse the same API and trace headers.

## Wrap-Up & Success Criteria
- [ ] FastAPI + Postgres healthy; `/healthz` returns OK with trace header.
- [ ] Streamlit dashboard lists movies, filters, and creates/deletes entries (cache clears on writes).
- [ ] Typer CLI can reset/seed/export without touching production data.
- [ ] README/runbook notes mention how to run FastAPI and Streamlit side-by-side.
- [ ] JS/TS preview commands verified for the mini-demo.

## Next steps
- Keep Postgres + `/healthz` handy.
- Install Node 20 + pnpm if you plan to build a React/Vite variant.
- Note the existing API contract (`/movies` list/create/get/delete) for any frontend you add next.

## Troubleshooting
- **Streamlit cannot fetch** → verify FastAPI is running and CORS allows `http://localhost:8501`.
- **Cache not updating** → call `cached_movies.clear()` after POST/DELETE and rerun the script.
- **Typer commands fail on missing tables** → run `uv run alembic upgrade head` or `init_db()` first.
- **pnpm errors** → re-run `corepack enable` and ensure Node ≥ 20.
