# AI Local SDK README – PydanticAI Gemini & Local Models

This README replaces the PDF crash course with a Python-only walkthrough. It slots in after **Session 12 – Tool-Friendly APIs** (or during the EX3 sprint) to showcase a PydanticAI stack without touching OpenAI. We wire Google Gemini through the Generative Language API and provide a drop-in swap for local Ollama models.

- **Instructor GitHub handle:** `zozo123`
- **Model tracks:** Google GLA (Gemini 2.x) and Ollama-compatible local LLMs

Learners finish with:
1. A `uv`-managed Python project that wraps PydanticAI agents behind FastAPI + Typer.
2. Structured outputs enforced with `pydantic` models and retry logic handled by the agent.
3. Tool calls that blend first-party data (JSON/YAML) with lightweight HTTP lookups.
4. A toggleable provider layer (`GOOGLE_API_KEY` vs `OLLAMA_BASE_URL`) so the same code serves hosted or local models.

---

## Project Files (Python)
- `ai_local_sdk/settings.py`
- `ai_local_sdk/schemas.py`
- `ai_local_sdk/catalog.py`
- `ai_local_sdk/agent.py`
- `ai_local_sdk/service.py`
- `ai_local_sdk/api.py`
- `cli.py`

Every code block below is copy/paste ready and written in Python; shell snippets remain limited to environment setup.

---

## Before Workshop – Preflight (JiTT)
- Install `uv` ≥ 0.5 and Python 3.12+ (PydanticAI pins to `>=3.9`, we standardize on 3.12).
- Enable one model track:
  - **Google AI Studio:** create an API key at <https://aistudio.google.com/app/api-keys>, note the quota, and copy the key.
  - **Local:** install [Ollama](https://ollama.com), pull a model (`ollama pull llama3.2`) and confirm `ollama list`.
- `uv add` will grab extras; no `pip install --break-system-packages`.
- Clone or prep a repo with write access; the session assumes `git` is ready.

Environment secrets to export ahead of time:
```bash
export GOOGLE_API_KEY="..."        # only if using Google GLA
export OLLAMA_BASE_URL="http://127.0.0.1:11434"  # default daemon URL
```

---

## Agenda (3×45 Minutes)
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Bootstrap & providers | 45 min | Talk + live coding | `uv` init, secrets, provider toggles |
| Typed agents & tools | 45 min | Guided coding | Pydantic schemas, tool wiring, retries |
| Interfaces & ops | 45 min | Pairing / solo | FastAPI surface, Typer CLI, local vs cloud runs |

## Learning Objectives
- Explain how PydanticAI selects models (`google-gla:` vs custom provider instances).
- Model structured responses with Pydantic types and force LLM retries until they validate.
- Register async tools that combine local datasets and live HTTP calls.
- Ship the agent behind FastAPI/CLI surfaces and switch between Google Gemini and Ollama without code rewrites.

---

## Part A – Foundation & Project Bootstrap (45 min)

### 1. Create the workspace
```bash
uv init ai-local-sdk --python 3.12
cd ai-local-sdk
uv add "pydantic-ai[google]" "google-generativeai" "pydantic-settings" "python-dotenv" \
       "httpx" "fastapi" "uvicorn[standard]" "typer[all]"
```
The `pydantic-ai[google]` extra supplies the Google Generative Language bindings. `google-generativeai` is optional but gives helper clients if you want raw fallback calls.

### 2. Scaffold project layout
```
ai-local-sdk/
├─ pyproject.toml
├─ .env.example
├─ ai_local_sdk/
│  ├─ __init__.py
│  ├─ settings.py
│  ├─ schemas.py
│  ├─ catalog.py
│  ├─ agent.py
│  ├─ service.py
│  └─ api.py
├─ cli.py
└─ README.md
```

### 3. Manage secrets
`ai_local_sdk/settings.py`
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    google_api_key: str | None = None
    gemini_model_id: str = "gemini-2.0-flash"

    use_local_model: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434"
    local_model_id: str = "llama3.2"

    timeout_seconds: float = 45.0


settings = Settings()
```

`.env.example`
```
GOOGLE_API_KEY=replace-me
USE_LOCAL_MODEL=false
OLLAMA_BASE_URL=http://127.0.0.1:11434
LOCAL_MODEL_ID=llama3.2
GEMINI_MODEL_ID=gemini-2.0-flash
TIMEOUT_SECONDS=45.0
```

Keep `.env` out of source control; document the key exchange policy if learners need to rotate.

---

## Part B – Typed Agent & Tooling (45 min)

### 4. Model structured input/output
`ai_local_sdk/schemas.py`
```python
from datetime import date
from pydantic import BaseModel, Field, PositiveInt, model_validator


class TripRequest(BaseModel):
    city: str = Field(min_length=2, description="City name to explore")
    days: PositiveInt = Field(le=7, description="Number of days to plan")
    budget_eur: int = Field(ge=100, le=5000)
    work_sessions: int = Field(ge=0, le=7, description="Focused work blocks needed")
    travel_date: date

    @model_validator(mode="after")
    def check_work_sessions(self) -> "TripRequest":
        if self.work_sessions > self.days:
            raise ValueError("work_sessions cannot exceed requested days")
        return self


class TripStop(BaseModel):
    title: str
    focus: str = Field(description="Key experience or takeaway")
    morning: str
    afternoon: str
    evening: str


class TripPlan(BaseModel):
    city: str
    summary: str
    remote_ready_score: int = Field(ge=1, le=10)
    highlights: list[str]
    days: list[TripStop]
```

The validator enforces `work_sessions <= days`, showing how Pydantic keeps LLM output usable.

### 5. Simple knowledge base
`ai_local_sdk/catalog.py`
```python
from dataclasses import dataclass


@dataclass(slots=True)
class CityGuide:
    tagline: str
    coworking: list[str]
    meals: list[str]
    wifi_tip: str


CATALOG = {
    "lisbon": CityGuide(
        tagline="Atlantic light, historic hills, remote-friendly coffee",
        coworking=["Second Home Lisboa", "Resvés", "Avila Spaces"],
        meals=["Cervejaria Ramiro", "Time Out Market", "Prado"],
        wifi_tip="Ask for 'rede' passwords; most cafes post QR codes near the bar.",
    ),
    "barcelona": CityGuide(
        tagline="Beach mornings, Gothic afternoons, tapas evenings",
        coworking=["Cloudworks Passeig de Gràcia", "La Vaca", "OneCoWork Marina"],
        meals=["El Xampanyet", "Cal Pep", "Blai 9"],
        wifi_tip="Metro stations broadcast free Wi-Fi; grab an 8-day Hola BCN pass.",
    ),
}
```

Learners can extend this with their own data set or connect to Postgres later.

### 6. Build the agent
`ai_local_sdk/agent.py`
```python
from dataclasses import dataclass

import httpx
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from .catalog import CATALOG
from .schemas import TripPlan, TripRequest
from .settings import settings


@dataclass(slots=True)
class PlannerDeps:
    http: httpx.AsyncClient


def _choose_model():
    if settings.use_local_model:
        provider = OllamaProvider(base_url=settings.ollama_base_url)
        return OpenAIChatModel(settings.local_model_id, provider=provider)
    google_provider = "google-gla"  # Google Generative Language API (API key auth)
    return GoogleModel(settings.gemini_model_id, provider=google_provider)


planner_agent = Agent(
    model=_choose_model(),
    deps_type=PlannerDeps,
    output_type=TripPlan,
    instructions=(
        "You are a concise travel concierge for remote workers. "
        "Use registered tools, respect the requested number of days, "
        "and never hallucinate restaurants that are not in the catalog."
    ),
)


@planner_agent.tool
async def catalog_lookup(ctx: RunContext[PlannerDeps], city: str) -> dict:
    """Return coworking suggestions and food picks from the curated catalog."""
    guide = CATALOG.get(city.lower())
    if not guide:
        return {}
    return {
        "tagline": guide.tagline,
        "coworking": guide.coworking,
        "meals": guide.meals,
        "wifi_tip": guide.wifi_tip,
    }


@planner_agent.tool
async def nominatim_points(ctx: RunContext[PlannerDeps], city: str, query: str = "coworking") -> list[str]:
    """Search OpenStreetMap for venues (default: coworking spaces)."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{query} {city}", "format": "json", "limit": 3}
    headers = {"User-Agent": "ai-local-sdk/0.1"}
    resp = await ctx.deps.http.get(url, params=params, headers=headers, timeout=settings.timeout_seconds)
    if resp.status_code != 200:
        return []
    return [
        f"{item['display_name']} · importance {float(item.get('importance', 0)):.2f}"
        for item in resp.json()
    ]
```

Swap Nominatim for any API learners can reach without extra keys; even a local JSON file works if outbound HTTP is blocked.

### 7. Service layer
`ai_local_sdk/service.py`
```python
from contextlib import asynccontextmanager

import httpx

from .agent import PlannerDeps, planner_agent
from .schemas import TripPlan, TripRequest


@asynccontextmanager
async def deps_lifespan():
    async with httpx.AsyncClient() as client:
        yield PlannerDeps(http=client)


async def generate_plan(payload: TripRequest) -> TripPlan:
    async with deps_lifespan() as deps:
        result = await planner_agent.run(payload, deps=deps)
    return result.output
```

PydanticAI will retry automatically if the model returns invalid JSON, so learners can experiment with `TripPlan` fields and observe validation feedback in logs.

---

## Part C – Interfaces & Runs (45 min)

### 8. FastAPI surface
`ai_local_sdk/api.py`
```python
from fastapi import FastAPI, HTTPException

from .schemas import TripPlan, TripRequest
from .service import generate_plan

app = FastAPI(title="AI Local SDK", version="0.1.0")


@app.post("/plan", response_model=TripPlan)
async def plan_trip(request: TripRequest) -> TripPlan:
    try:
        return await generate_plan(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
```

Run it:
```bash
uv run uvicorn ai_local_sdk.api:app --reload --port 8031
```

Test the endpoint:
```bash
curl -s http://localhost:8031/plan \
  -H "Content-Type: application/json" \
  -d '{"city":"Lisbon","days":3,"budget_eur":1200,"work_sessions":2,"travel_date":"2025-06-10"}' \
  | jq
```

### 9. Typer CLI for scripted use
`cli.py`
```python
import asyncio
from datetime import date

import typer

from ai_local_sdk.schemas import TripPlan, TripRequest
from ai_local_sdk.service import generate_plan

cli = typer.Typer(help="Run the AI Local SDK agent from the terminal.")


@cli.command()
def plan(city: str, days: int = 3, budget: int = 1200, work: int = 1, when: date = date.today()):
    payload = TripRequest(city=city, days=days, budget_eur=budget, work_sessions=work, travel_date=when)
    plan_result: TripPlan = asyncio.run(generate_plan(payload))
    typer.echo(plan_result.model_dump_json(indent=2))


if __name__ == "__main__":
    cli()
```

Run:
```bash
uv run python cli.py plan --city "Barcelona" --days 4 --budget 1500 --work 2
```

### 10. Switching providers mid-session
- Google track:
  ```bash
  cp .env.example .env
  uv run uvicorn ai_local_sdk.api:app --reload
  ```
  Open `.env`, keep `USE_LOCAL_MODEL=false`, and set `GOOGLE_API_KEY=***`. The agent will pick `google-gla:{GEMINI_MODEL_ID}` and authenticate with the key.
- Local track:
  ```bash
  ollama pull llama3.2
  export USE_LOCAL_MODEL=true
  export LOCAL_MODEL_ID=llama3.2
  export OLLAMA_BASE_URL=http://127.0.0.1:11434
  uv run uvicorn ai_local_sdk.api:app --reload
  ```
  `OllamaProvider` wraps an OpenAI-compatible client pointed at Ollama; no cloud calls involved.

---

## Extensions & Assessment
- Add a test that freezes the agent output by injecting a fake provider returning canned JSON; grade learners on schema validation.
- Use `planner_agent.with_history()` to persist chat state across multiple CLI calls.
- Introduce streaming via `planner_agent.stream(...)` and surface tokens over Server-Sent Events.
- Replace Eventbrite with a local SQLite `events` table to practice deterministic tool outputs.

**Check for understanding:** learners should demo both provider modes, explain how PydanticAI enforces structured output, and outline how to extend the agent with another tool (e.g., weather) without rewriting FastAPI.
