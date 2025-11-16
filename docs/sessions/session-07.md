# Session 07 – React/Vite Foundations + Reliability Upgrades

- **Date:** Monday, Dec 15, 2025
- **Theme:** Finish the UI runway with a Vite/React (TypeScript) client, then harden the platform with deeper testing, observability, and profiling.

## Session Story
Session 06 delivered Streamlit + Typer and previewed modern JavaScript. Session 07 takes that preview to completion: you’ll scaffold a Vite + React project, consume the same FastAPI/Postgres API, and practice TypeScript patterns (hooks, service modules, React Query). Once the UI is talking to the backend, we pivot back to reliability—expanding pytest coverage, wiring Logfire, and capturing profiling data so EX2 demos stay solid.

## Learning Objectives
- Refresh essential JavaScript/TypeScript syntax (modules, async/await, generics, JSX) for Python-first teams.
- Scaffold a Vite React app with pnpm, configure API clients, and ship list/create flows matching the FastAPI contract.
- Layer automated checks for the frontend (lint, Vitest) and integrate them into the existing uv/dev workflow.
- Deepen backend reliability via parametrized pytest suites, Hypothesis property tests, Logfire tracing, and lightweight profiling.

## What You’ll Build
- `frontend-react/` Vite project (`pnpm create vite ... --template react-ts`) colocated with the FastAPI codebase.
- `src/lib/api.ts`, `src/services/movies.ts`, and `src/hooks/useMovies.ts` centralizing TypeScript clients.
- `src/App.tsx` (or feature modules) featuring filters, totals, and create forms with React Query invalidation.
- Frontend tooling scripts: ESLint, Prettier (optional), Vitest + Testing Library, Playwright smoke test (stretch).
- Backend reliability upgrades: improved fixtures, Hypothesis tests, snapshot stores, Logfire instrumentation, and profiling notes.

## Prerequisites
1. **Session 05 Postgres + Session 06 Streamlit/Typer are complete**; FastAPI is running on `http://localhost:8000`.
2. **Node.js ≥ 20 with corepack and pnpm installed.** Verify:
   ```bash
   node --version   # Should be v20.x or higher
   corepack enable
   corepack prepare pnpm@latest --activate
   pnpm --version   # Should be v8.x or higher
   ```
3. **Install backend reliability dependencies** (if not already from earlier sessions):
   ```bash
   uv add pytest-cov hypothesis logfire
   ```
4. **Optional but helpful:** Clone the JS primer repo linked in the LMS and run `pnpm install && pnpm test` to warm up on TypeScript syntax.

## Toolchain Primer – Node + pnpm + TypeScript
> **Why?** Sessions 06–07 rely on FastAPI for the backend *and* a modern JavaScript toolchain for UI work. Many students are Python-first, so this section captures the minimum commands you’ll use repeatedly.

### Node runtime
- Install Node 20+ (use fnm, Volta, or the Node installer—whatever your team standard is).
- Verify the version and package manager bridge (Corepack) whenever you sit down at a new machine:
  ```bash
  node --version          # Expect v20.x
  corepack enable         # Enables pnpm/yarn wrappers that ship with Node
  corepack prepare pnpm@latest --activate
  pnpm --version          # Expect v8.x
  ```
- Keep Node tooling separate from `uv` (Python). Run Node commands from `frontend-react/`; use `uv` for FastAPI or database scripts.

### pnpm quick reference
| Command | Purpose |
| --- | --- |
| `pnpm create vite@latest frontend-react -- --template react-ts` | Scaffold a new React + TypeScript + Vite project in `frontend-react/`. |
| `pnpm install` | Install dependencies listed in `package.json`. |
| `pnpm dev` | Start the Vite dev server (defaults to `http://localhost:5173`). |
| `pnpm test` | Run Vitest/Testing Library suites (configured later in this session). |
| `pnpm lint` | Run ESLint across `src/`. |
| `pnpm build` | Produce optimized assets in `dist/` (used for deployment demos). |
| `pnpm tsc --noEmit` | Optional: run the TypeScript compiler type-check without writing files. |

> ✅ **Tip:** pnpm stores a global content-addressable cache. The first install is the slowest; subsequent installs on student laptops are much faster than `npm` or `yarn`.

### JavaScript/TypeScript cheat card
- `import`/`export` behave like Python modules—use named exports for functions/types, default exports for main components.
- `async/await` maps to Python’s `asyncio`, but `fetch/axios` return `Promise`s instead of `coroutines`.
- TypeScript syntax you’ll see today:
  - `type Movie = { id: number; title: string }`
  - `Omit<Movie, "id">` (drop the `id` when creating)
  - `Promise<Movie[]>` return types on async functions
- Vite exposes env vars as `import.meta.env.VITE_*`, not `process.env`. Keep that consistent so frontend builds work across dev/prod.

Revisit this primer anytime a console error complains about the toolchain; most fixes boil down to running the right pnpm command in the correct directory.

## Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Recap & JS/TS warm-up | 15 min | Talk + mini-demo | Module syntax, async/await, typing cheat sheet. |
| Vite architecture primer | 15 min | Slides + code walkthrough | Project layout, env vars, React Query, trace IDs. |
| **Part B – Lab 1** | **45 min** | **Guided coding** | **Scaffold Vite + build movie services/hooks/UI.** |
| Break | 10 min | — | Encourage pnpm install fixes + React Q&A. |
| **Part C – Lab 2** | **45 min** | **Guided reliability** | **Fixtures, Hypothesis, Logfire, coverage, profiling.** |
| Wrap-up & EX2 planning | 10 min | Discussion | Deployment, combined UI options, quality gates before demos. |

## Part A – JavaScript/TypeScript Warm-up
1. **Modules & imports:**
   ```ts
   import { listMovies } from "./services/movies";
   export type Movie = { id: number; title: string; year: number; genre: string };
   ```
2. **Async/await:**
   ```ts
   export async function listMovies(): Promise<Movie[]> {
     const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/movies`, {
       headers: { "X-Trace-Id": "ui-react" },
     });
     if (!response.ok) throw new Error("Failed to load movies");
     return response.json();
   }
   ```
3. **Typing essentials:** unions (`string | undefined`), utility helpers (`Omit<Movie, "id">`), React component props with generics.
4. **Tooling expectations:** Node 20 + pnpm, Vite dev server (port 5173), TypeScript compiler inside Vite, ESLint/Prettier, Vitest for unit tests.

> 🔁 Encourage students to map Streamlit constructs to React equivalents (e.g., `st.cache_data` ↔ React Query, forms ↔ controlled components). The API contract stays identical, so Postgres-backed data flows seamlessly between UIs.

## Part B – Lab 1: Scaffold Vite + service layer (45 minutes)
Goal: run `pnpm dev`, fetch movies, and create new entries from React.

### Step 0 – Align repo structure
```bash
cd hello-uv
pnpm create vite@latest frontend-react -- --template react-ts
cd frontend-react
pnpm install
```
Add `.env.local`:
```ini
VITE_API_BASE_URL=http://localhost:8000
VITE_TRACE_ID=ui-react
```
Commit `node_modules` to `.gitignore` if not already.

### Step 1 – Install runtime deps
```bash
pnpm add axios @tanstack/react-query
pnpm add -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin vitest @testing-library/react @testing-library/jest-dom
```

### Step 2 – Service utilities
`src/lib/api.ts`:
```ts
import axios from "axios";

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "X-Trace-Id": import.meta.env.VITE_TRACE_ID ?? "ui-react",
  },
  timeout: 5000,
});

export async function get<T>(url: string, params?: Record<string, unknown>) {
  const response = await client.get<T>(url, { params });
  return response.data;
}

export async function post<T>(url: string, body: unknown) {
  const response = await client.post<T>(url, body);
  return response.data;
}
```

### Step 3 – Domain services & hooks
`src/services/movies.ts`:
```ts
import { get, post } from "../lib/api";

export type Movie = {
  id: number;
  title: string;
  year: number;
  genre: string;
};

export function listMovies(genre?: string) {
  return get<Movie[]>("/movies", genre ? { genre } : undefined);
}

export function createMovie(payload: Omit<Movie, "id">) {
  return post<Movie>("/movies", payload);
}
```

`src/hooks/useMovies.ts`:
```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createMovie, listMovies, Movie } from "../services/movies";

export function useMovies(genre?: string) {
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["movies", genre],
    queryFn: () => listMovies(genre),
  });

  const create = useMutation({
    mutationFn: (payload: Omit<Movie, "id">) => createMovie(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["movies"] });
    },
  });

  return { ...listQuery, create };
}
```
Wrap the app in `QueryClientProvider` (update `main.tsx`).

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
```

### Step 4 – Replace `src/App.tsx`
```tsx
import { FormEvent, useState } from "react";
import "./App.css";
import { useMovies } from "./hooks/useMovies";

export default function App() {
  const [genre, setGenre] = useState<string | undefined>(undefined);
  const { data, isLoading, isError, create } = useMovies(genre);

  if (isLoading) return <p>Loading movies…</p>;
  if (isError) return <p role="alert">Failed to load movies.</p>;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    create.mutate({
      title: String(formData.get("title")),
      year: Number(formData.get("year")),
      genre: String(formData.get("genre")),
    });
    event.currentTarget.reset();
  };

  return (
    <main>
      <header>
        <h1>Movie Pulse</h1>
        <p>Total movies: {data?.length ?? 0}</p>
        <label>
          Genre filter
          <input
            value={genre ?? ""}
            onChange={(event) => setGenre(event.target.value || undefined)}
          />
        </label>
      </header>

      <section>
        <form onSubmit={handleSubmit}>
          <input name="title" placeholder="Title" required />
          <input name="year" type="number" min={1900} max={2100} required />
          <input name="genre" placeholder="Genre" defaultValue="sci-fi" />
          <button type="submit" disabled={create.isLoading}>
            {create.isLoading ? "Saving…" : "Add movie"}
          </button>
        </form>
      </section>

      <ul>
        {data?.map((movie) => (
          <li key={movie.id}>
            {movie.title} ({movie.year}) – {movie.genre}
          </li>
        ))}
      </ul>
    </main>
  );
}
```
Run `pnpm dev` → hit `http://localhost:5173` → confirm Postgres-backed data flows end-to-end with the same trace identifiers Streamlit used.

### Step 5 – Frontend tests/lint (stretch)
- Add `"lint": "eslint src --ext .ts,.tsx"` and `"test": "vitest"` to `package.json`.
- Create `src/components/MovieList.test.tsx` with Testing Library assertions.
- Optional: `pnpm create playwright@latest` for smoke tests hitting the dev server (requires FastAPI running).

> 🎉 **Quick win:** When both Streamlit and Vite show the same movies (seeded via Typer or Postgres), EX2 teams can choose their preferred UI stack with confidence.

## Part C – Lab 2: Reliability & Observability (45 minutes)
Goal: keep quality high now that multiple clients exist.

### Lab timeline
- **Minutes 0–10** – Wire autouse fixtures + dependency overrides for Postgres.
- **Minutes 10–25** – Add parametrized + Hypothesis tests.
- **Minutes 25–35** – Capture snapshots, run coverage, wire Logfire.
- **Minutes 35–45** – Profile hot paths and correlate traces with Vite/Streamlit actions.

### 1. Enhance pytest fixtures (`tests/conftest.py`)

**Note:** Session 05 already created Postgres test fixtures. We'll enhance them here with additional features.

**Review what Session 05 gave us:**
- `_create_db()` and `_drop_db()` helpers for temporary databases
- `session_url` fixture that creates/destroys test databases
- `repo` fixture that overrides FastAPI dependencies

**Enhancements for Session 07:**

Add to your existing `tests/conftest.py`:
```python
# ...existing Session 05 fixture code above...

import pytest
from fastapi.testclient import TestClient

from movie_service.app.main import app


@pytest.fixture
def client(repo) -> TestClient:
    """TestClient with Postgres-backed repository.
    
    The repo fixture already overrides dependencies,
    so this client uses the test database.
    """
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_db_state(repo):
    """Clear all data between tests for isolation."""
    yield
    # Clean up after each test
    deleted = repo.delete_all()
    print(f"\nCleaned up {deleted} test records")
```

Explain how the fixture parallels the runtime Postgres config so tests match production.

### 2. Parametrized + property-based tests (`tests/test_movies.py`)
```python
import pytest
from hypothesis import given, strategies as st

@pytest.mark.parametrize(
    "payload",
    [
        {"title": "Arrival", "year": 2016, "genre": "sci-fi"},
        {"title": "Dune", "year": 2021, "genre": "Sci-Fi"},
    ],
)
def test_create_movie_variants(client, payload):
    response = client.post("/movies", json=payload, headers={"X-Trace-Id": "pytest"})
    assert response.status_code == 201
    assert response.json()["genre"].istitle()
                                                 

@pytest.mark.parametrize("bad_year", [1800, 2150])
def test_create_movie_rejects_out_of_range_year(client, bad_year):
    response = client.post(
        "/movies",
        json={"title": "Bad Year", "year": bad_year, "genre": "Sci-Fi"},
    )
    assert response.status_code == 422


ascii_titles = st.text(
    alphabet=st.characters(min_codepoint=32, max_codepoint=126),
    min_size=1,
    max_size=40,
)


@given(title=ascii_titles)
def test_title_round_trip(client, title):
    response = client.post(
        "/movies",
        json={"title": title, "year": 2000, "genre": "Drama"},
    )
    response.raise_for_status()
    movie_id = response.json()["id"]
    fetched = client.get(f"/movies/{movie_id}").json()
    assert fetched["title"] == title
```
The `ascii_titles` strategy limits Hypothesis to printable ASCII so Postgres validators don’t choke on control characters. Call out Hypothesis shrink reports and how to fix flaky inputs.

### 3. Snapshot + coverage + Logfire
```python
from pathlib import Path

SNAPSHOT_DIR = Path("tests/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

def test_movies_list_snapshot(client):
    client.post("/movies", json={"title": "Interstellar", "year": 2014, "genre": "Sci-Fi"})
    client.post("/movies", json={"title": "Blade Runner", "year": 1982, "genre": "Sci-Fi"})

    response = client.get("/movies")
    snapshot = SNAPSHOT_DIR / "movies_list.json"
    if not snapshot.exists():
        snapshot.write_text(response.text)
    assert response.text == snapshot.read_text()
```
- Run `uv run pytest --cov=movie_service --cov-report=term-missing`.
- Wire Logfire (or structured logging) in `app/main.py` to capture request/response traces with `X-Trace-Id` so frontends can share IDs.
- Use `logfire.instrument_fastapi(app)` (see service docs) and demo one trace triggered from Streamlit + Vite.

**Mini Logfire demo**

1. Add instrumentation in `movie_service/app/main.py` right after creating the FastAPI app:
   ```python
   import os
   import logfire

   logfire.configure(
       send_to_logfire=bool(os.getenv("LOGFIRE_API_KEY")),
       service_name="movie-service",
   )
   logfire.instrument_fastapi(app)
   ```
   Set `LOGFIRE_API_KEY` in `.env` if you want to stream to Logfire’s SaaS; otherwise the logs stay local but still show trace IDs.

2. Run a tiny script to emit a counter and hit the health endpoint:
   ```python
   # filepath: movie_service/scripts/demo_logfire.py
   import httpx
   import logfire

   logfire.configure(send_to_logfire=False, service_name="movie-service-demo")
   logfire.counter("demo.run", tags={"env": "local"})

   response = httpx.get("http://localhost:8000/healthz", headers={"X-Trace-Id": "logfire-demo"})
   logfire.info("health.response", status=response.status_code, body=response.json())
   print(response.json())
   ```
   Execute with `uv run python -m movie_service.scripts.demo_logfire` while FastAPI is running. In the Logfire dashboard (or terminal output), you’ll see the `X-Trace-Id` plus the counter/s structured logs—proof that observability is wired up before EX2.

### 4. Profiling quick wins
- Use `uv run python -m cProfile -o profile.out movie_service/scripts/load.py` or simple `time.perf_counter()` wrappers around repository methods to ensure Postgres queries stay performant.
- Encourage teams to measure `pnpm test` + `uv run pytest` runtime to set CI budgets.

> 🎉 **Quick win:** When React + Streamlit share the same backend and the reliability suite stays green, EX2 deliverables feel production-ready.

## Wrap-up & Next Steps
- Choose the UI (Streamlit, React, or both) that best fits your EX2 backlog and document how to run it.
- Maintain the Postgres + pytest fixtures so regressions are caught before demos.
- Plan deployment targets (Railway, Fly, Render) that can host FastAPI + Postgres + frontend assets.
- Preview Session 08 (AI tools / advanced integrations) knowing your stack already spans backend, database, and multiple UIs.

## Troubleshooting
- **`pnpm dev` cannot reach API** → verify FastAPI runs on port 8000 and CORS allows `http://localhost:5173`.
- **TypeScript errors referencing `process.env`** → switch to `import.meta.env` (Vite convention).
- **pytest fixture fails to drop DB** → ensure connections are terminated before `DROP DATABASE`; check for `psycopg.errors.ObjectInUse`.
- **Logfire missing traces** → confirm `X-Trace-Id` headers are forwarded from Streamlit/React clients and Logfire API key is in `.env`.

## Student Success Criteria
- [ ] Vite dev server loads movies from FastAPI/Postgres and can create new entries (trace IDs intact).
- [ ] Frontend lint/tests run locally (`pnpm lint`, `pnpm test` or Playwright).
- [ ] Backend pytest suite includes parametrized cases, Hypothesis, snapshots, and coverage reporting.
- [ ] Logfire (or equivalent) captures traces correlated with Streamlit + React requests; profiling notes are documented.

Book a pairing session if any checkbox is missing before heading into Session 08.

## AI Prompt Seeds
- “Generate a TypeScript axios client + React Query hook for `/movies`, complete with create/list functions and cache invalidation.”
- “Write pytest fixtures that create/drop temporary Postgres databases per test and override FastAPI dependencies.”
- “Show how to instrument a FastAPI app with Logfire so React/Streamlit `X-Trace-Id` headers appear in traces.”
