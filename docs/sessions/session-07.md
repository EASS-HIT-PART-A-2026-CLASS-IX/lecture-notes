# Session 07 – React/Vite Foundations + Reliability Upgrades

- **Date:** Monday, Dec 15, 2025
- **Theme:** Build a Vite/React (TypeScript) client that reuses the FastAPI/Postgres API, then tighten reliability with frontend checks and stronger backend tests/observability.

## Session Story
Session 06 delivered Streamlit + Typer. Session 07 finishes the UI runway with React + Vite while keeping the same `/movies` contract. Once the React client works, we add lightweight lint/tests for the frontend and expand backend reliability (pytest improvements, trace logging) so multiple clients stay stable.

## Learning Objectives
- Scaffold a Vite + React TypeScript app with pnpm and consume the existing API.
- Centralize API calls in a service layer with trace headers.
- Manage data fetching/mutation with React Query and simple forms.
- Add frontend lint/tests (ESLint, Vitest/Testing Library) to catch regressions.
- Strengthen backend reliability with parametrized tests and trace-aware logging.

## Deliverables (What You’ll Build)
- `frontend-react/` Vite project (React + TS) using the `/movies` API.
- `src/lib/api.ts`, `src/services/movies.ts`, `src/hooks/useMovies.ts` service layer + hook.
- `src/App.tsx` list/create UI with React Query invalidation.
- Frontend scripts for `dev`, `lint`, and `test`.
- Backend reliability add-ons: parametrized tests + trace-aware logging (reuse Postgres fixtures).

## Toolkit Snapshot
- **Node 20 + pnpm** – runtime/package manager for React.
- **Vite + React + TS** – frontend build + framework.
- **Axios or fetch + React Query** – API client + caching.
- **ESLint + Vitest + Testing Library** – frontend quality checks.
- **pytest + existing Postgres fixtures** – backend regression safety.

## Before Class (JiTT)
1. Postgres + FastAPI running (`docker compose up -d db`, `curl http://localhost:8000/healthz`).
2. Node ≥ 20 with pnpm ready:
   ```bash
   node --version
   corepack enable
   corepack prepare pnpm@latest --activate
   pnpm --version
   ```
3. Install backend reliability extras (if missing):
   ```bash
   uv add pytest-cov hypothesis logfire
   ```
4. Keep `.env` with `MOVIE_API_BASE_URL` for parity across Streamlit/React.

## Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| JS/TS warm-up | 15 min | Talk + mini-demo | Modules, async/await, fetch vs axios. |
| Vite setup | 15 min | Walkthrough | Scaffold project, env vars, scripts. |
| **Part B – Lab 1** | **45 min** | **Guided build** | **Service layer + React Query UI.** |
| Break | 10 min | — | Fix pnpm/env issues. |
| **Part C – Lab 2** | **45 min** | **Guided reliability** | **Frontend lint/tests + backend test boosts.** |
| Wrap-up | 10 min | Discussion | Checklist and discussion. |

## Lab 1 – Scaffold Vite + movie client (45 min)
Goal: run `pnpm dev`, see Postgres-backed movies, and create new entries using the same trace headers Streamlit used.

### Step 0 – Create project
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

### Step 1 – Install UI deps
```bash
pnpm add axios @tanstack/react-query
pnpm add -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

### Step 2 – API client + services
`src/lib/api.ts`
```ts
import axios from "axios";

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { "X-Trace-Id": import.meta.env.VITE_TRACE_ID ?? "ui-react" },
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

`src/services/movies.ts`
```ts
import { get, post } from "../lib/api";

export type Movie = { id: number; title: string; year: number; genre: string };

export function listMovies(genre?: string) {
  return get<Movie[]>("/movies", genre ? { genre } : undefined);
}

export function createMovie(payload: Omit<Movie, "id">) {
  return post<Movie>("/movies", payload);
}
```

`src/hooks/useMovies.ts`
```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createMovie, listMovies, Movie } from "../services/movies";

export function useMovies(genre?: string) {
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["movies", genre],
    queryFn: () => listMovies(genre),
  });

  const create = useMutation({
    mutationFn: (payload: Omit<Movie, "id">) => createMovie(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["movies"] }),
  });

  return { ...listQuery, create };
}
```

Wrap React Query in `src/main.tsx`:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";

const qc = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
```

### Step 3 – Replace `src/App.tsx`
```tsx
import { FormEvent, useState } from "react";
import { useMovies } from "./hooks/useMovies";
import "./App.css";

export default function App() {
  const [genre, setGenre] = useState<string | undefined>();
  const { data, isLoading, isError, create } = useMovies(genre);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({
      title: String(form.get("title")),
      year: Number(form.get("year")),
      genre: String(form.get("genre")),
    });
    event.currentTarget.reset();
  };

  if (isLoading) return <p>Loading movies…</p>;
  if (isError) return <p role="alert">Failed to load movies.</p>;

  return (
    <main>
      <header>
        <h1>Movie Pulse</h1>
        <p>Total movies: {data?.length ?? 0}</p>
        <label>
          Genre filter
          <input value={genre ?? ""} onChange={(e) => setGenre(e.target.value || undefined)} />
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
Run `pnpm dev`, visit `http://localhost:5173`, and verify movies list/create work against FastAPI/Postgres.

## Lab 2 – Reliability + tests (45 min)
Goal: keep quality high now that two UIs exist.

### Frontend lint/tests
- Add scripts to `package.json`:
  ```json
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint src --ext .ts,.tsx",
    "test": "vitest"
  }
  ```
- Sample test `src/App.test.tsx`:
  ```tsx
  import { afterEach, expect, it, vi } from "vitest";
  import { render, screen, waitFor } from "@testing-library/react";
  import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
  import App from "./App";
  import * as svc from "./services/movies";

  const qc = new QueryClient();
  afterEach(() => qc.clear());

  it("renders movies", async () => {
    vi.spyOn(svc, "listMovies").mockResolvedValue([
      { id: 1, title: "Arrival", year: 2016, genre: "Sci-Fi" },
    ]);
    render(
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(screen.getByText(/Arrival/)).toBeInTheDocument());
  });
  ```

### Backend reliability boosts
- Reuse Postgres fixtures from Session 05; add parametrized tests (year bounds, genre casing) in `movie_service/tests/test_movies.py`.
- Optional property tests with Hypothesis (ASCII titles) to catch edge cases.
- Ensure `X-Trace-Id` flows through logs; add basic structured logging if missing.

### Regression commands
```bash
pnpm lint && pnpm test
uv run pytest movie_service/tests -v
```

## Wrap-Up & Success Criteria
- [ ] React app lists and creates movies against FastAPI/Postgres with trace IDs.
- [ ] `pnpm lint` and `pnpm test` pass.
- [ ] Backend pytest suite still green after UI changes.
- [ ] Docs note how to run Streamlit *or* React with the same API.

## Next steps
- Keep `/healthz` green and Postgres running.
- Ensure React + Streamlit can both hit the API (CORS/trace).
- Install `uv add pydantic-ai httpx` (plus `dspy-ai` if you plan to explore agentic tools).

## Troubleshooting
- **`pnpm dev` cannot reach API** → verify FastAPI on port 8000 and CORS allows `http://localhost:5173`.
- **TypeScript references `process.env`** → use `import.meta.env.VITE_*` (Vite convention).
- **pytest fixtures drop DB slowly** → terminate active connections before `DROP DATABASE` (Session 05 helpers handle this).
- **Trace IDs missing** → ensure React client sends `X-Trace-Id` header (defaulted in `api.ts`).
