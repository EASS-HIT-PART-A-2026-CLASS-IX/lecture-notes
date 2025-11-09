# Optional MCP Workshop – Weather MCP Server

This add-on session slots in after **Session 12 – Tool-Friendly APIs** (or during the EX3 milestone sprint) to show how to publish Model Context Protocol tools end-to-end. It reuses the same 3×45-minute cadence as the core sessions and keeps the rest of the syllabus untouched.

- **Instructor GitHub handle:** `zozo123`
- **Docker Hub namespace:** `zozo001`

Learners finish with:
1. A FastMCP server exposing two tools backed by real weather data.
2. A FastAPI wrapper that mounts Streamable HTTP at `/mcp`.
3. Clients for stdio and HTTP transports.
4. A Docker image pushed to Docker Hub (`zozo001/weather-mcp`).
5. A validated `server.json` published to the official MCP Registry via OCI.

---

## Before Workshop – Preflight (JiTT)
- Install dependencies ahead of time:
  ```bash
  uv add mcp[cli] fastapi uvicorn httpx logfire
  ```
- Make sure Docker is logged in to `zozo001` and `uv run python -m mcp --help` succeeds.
- Review the Logfire FastMCP guide (link in LMS) and note how to toggle telemetry on/off (`LOGFIRE_SEND_OFFLINE=true|false`).
- Export NOAA API policy reminder: include `User-Agent` header with contact info.

---

## Agenda (3×45 Minutes)
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| MCP primer + scaffold | 45 min | Talk + live coding | Architecture, repo layout, FastMCP tools |
| Local/remote runs | 45 min | Guided coding | stdio + HTTP servers, Inspector + Python clients |
| Shipping & registry | 45 min | Guided coding | Docker build/push, server.json, MCP Registry publish |

## Learning Objectives
- Explain MCP transports (stdio vs Streamable HTTP) and when to use each.
- Scaffold a FastMCP server with deterministic tool schemas.
- Run and validate the server locally, then containerize and push it.
- Publish the server to the MCP Registry using OCI images from Docker Hub.

---

## Part A – Primer & Project Scaffold (45 min)

### 1. Architecture slide
Claude Desktop (stdio) / Claude Connector (HTTP) → MCP server → tools → upstream APIs. Emphasize deterministic schemas, no stdout noise, and reuse of `uv` workflows.

### 2. Create repo scaffold
```bash
git clone https://github.com/zozo123/weather-mcp.git
cd weather-mcp
uv init --python 3.12
uv add "mcp[cli]" httpx fastapi uvicorn
```

Repo layout:
```
weather-mcp/
├─ pyproject.toml
├─ weather_mcp.py
├─ app.py
├─ Dockerfile
├─ .dockerignore
├─ client_stdio.py
├─ client_http.py
└─ README.md (optional)
```

### 3. `pyproject.toml`
```toml
[project]
name = "weather-mcp"
version = "0.1.0"
description = "Weather MCP demo with alerts and forecast tools"
requires-python = ">=3.12"
dependencies = [
  "mcp[cli]",
  "httpx>=0.27.0",
  "fastapi>=0.115.0",
  "uvicorn>=0.30.0",
]

[tool.uv]
```

### 4. `weather_mcp.py`
```python
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("io.docker.zozo001.weather-mcp")

NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-mcp/0.1.0"

async def _get_json(url: str) -> dict[str, Any] | None:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

def _format_alert(feature: dict) -> str:
    props = feature.get("properties", {})
    return (
        f"Event: {props.get('event', 'Unknown')}\n"
        f"Area: {props.get('areaDesc', 'Unknown')}\n"
        f"Severity: {props.get('severity', 'Unknown')}\n"
        f"Description: {props.get('description', 'No description')}\n"
        f"Instructions: {props.get('instruction', 'None')}"
    )

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get active weather alerts for a US state (e.g., 'CA')."""
    data = await _get_json(f"{NWS_API_BASE}/alerts/active/area/{state}")
    if not data or "features" not in data:
        return "No alerts or fetch failed."
    items = data.get("features", [])
    if not items:
        return "No active alerts."
    return "\n---\n".join(_format_alert(f) for f in items)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get a short forecast for a US lat/long."""
    points_data = await _get_json(f"{NWS_API_BASE}/points/{latitude},{longitude}")
    if not points_data:
        return "Failed to resolve forecast grid."
    forecast_data = await _get_json(points_data["properties"]["forecast"])
    if not forecast_data:
        return "Detailed forecast unavailable."
    periods = forecast_data["properties"]["periods"][:5]
    sections = []
    for p in periods:
        sections.append(
            f"{p['name']}: {p['temperature']}°{p['temperatureUnit']}, "
            f"Wind {p['windSpeed']} {p['windDirection']}\n{p['detailedForecast']}"
        )
    return "\n---\n".join(sections)

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 4a. Optional telemetry toggle (Logfire)
Add `telemetry.py`:
```python
import os

import logfire


def configure() -> None:
    enabled = os.getenv("LOGFIRE_ENABLED", "false").lower() == "true"
    logfire.configure(
        service_name="weather-mcp",
        send_to_logfire=enabled,
    )
```
Call `telemetry.configure()` near the top of `weather_mcp.py`. This mirrors the observability discipline from Session 07 and allows instructors to switch telemetry on/off via environment variable.\n+
### 5. `app.py`
```python
import contextlib
from fastapi import FastAPI
from weather_mcp import mcp

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield

app = FastAPI(lifespan=lifespan)

@app.get("/healthz")
def health() -> dict[str, bool]:
    return {"ok": True}

app.mount("/mcp", mcp.streamable_http_app())
```

### 6. `.dockerignore`
```
__pycache__/
*.pyc
.venv/
.git/
```

---

## Part B – Local Runs & Clients (45 min)

1. **StdIO run**
   ```bash
   uv run python weather_mcp.py
   ```
2. **HTTP run**
   ```bash
   uv run uvicorn app:app --host 0.0.0.0 --port 8000
   # MCP endpoint: http://localhost:8000/mcp
   # Health:       http://localhost:8000/healthz
   ```
3. **Inspector**
   ```bash
   npx @modelcontextprotocol/inspector
   # stdio target: python weather_mcp.py
   # http target:  http://localhost:8000/mcp
   ```
4. **Clients**
   - `client_stdio.py`
     ```python
     import asyncio
     from mcp import ClientSession, StdioServerParameters, stdio_client

     async def main() -> None:
         params = StdioServerParameters(command="python", args=["weather_mcp.py"])
         async with stdio_client(params) as (read, write):
             async with ClientSession(read, write) as session:
                 await session.initialize()
                 tools = await session.list_tools()
                 print("TOOLS:", [tool.name for tool in tools.tools])

                 alerts = await session.call_tool("get_alerts", {"state": "CA"})
                 print("ALERT SAMPLE:", alerts.content[0].text[:400])

                 forecast = await session.call_tool(
                     "get_forecast", {"latitude": 38.58, "longitude": -121.49}
                 )
                 print("FORECAST SAMPLE:", forecast.content[0].text[:400])

     if __name__ == "__main__":
         asyncio.run(main())
     ```
   - `client_http.py`
     ```python
     import asyncio
     from mcp import ClientSession
     from mcp.client.streamable_http import streamablehttp_client

     async def main() -> None:
         url = "http://localhost:8000/mcp"
         async with streamablehttp_client(url) as (read, write, _):
             async with ClientSession(read, write) as session:
                 await session.initialize()
                 tools = await session.list_tools()
                 print("TOOLS:", [tool.name for tool in tools.tools])

                 alerts = await session.call_tool("get_alerts", {"state": "TX"})
                 print("ALERT SAMPLE:", alerts.content[0].text[:400])

                 forecast = await session.call_tool(
                     "get_forecast", {"latitude": 40.7128, "longitude": -74.0060}
                 )
                 print("FORECAST SAMPLE:", forecast.content[0].text[:400])

     if __name__ == "__main__":
         asyncio.run(main())
     ```
5. **Contract smoke tests**
   - Create `tests/test_weather_mcp.py` that mounts `app:app` with `httpx.ASGITransport` and asserts deterministic tool payloads.
   - Optional: `uv run schemathesis run http://localhost:8000/openapi.json --checks status_code_conformance --dry-run` to mirror Session 10 contract gates.

---

## Part C – Docker Hub + MCP Registry (45 min)

### Dockerfile
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"
COPY pyproject.toml ./
RUN uv venv && . .venv/bin/activate && uv pip install -e .

FROM python:3.12-slim
WORKDIR /app

ARG MCP_NAME=io.docker.zozo001.weather-mcp
LABEL io.modelcontextprotocol.server.name="${MCP_NAME}"

COPY weather_mcp.py ./weather_mcp.py
COPY app.py ./app.py
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd -m appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build, run, and push (Docker Hub `zozo001`)
```bash
docker login --username zozo001
TAG=zozo001/weather-mcp:latest
MCP=io.docker.zozo001.weather-mcp

docker build -t "$TAG" --build-arg MCP_NAME="$MCP" .
docker run --rm -p 8000:8000 "$TAG"
docker push "$TAG"
```

### MCP Registry – `server.json`
```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-07-09/server.schema.json",
  "name": "io.docker.zozo001.weather-mcp",
  "version": "0.1.0",
  "description": "Weather MCP demo (alerts + forecast tools)",
  "packages": [
    {
      "registry_type": "oci",
      "registry_base_url": "https://registry-1.docker.io",
      "identifier": "zozo001/weather-mcp",
      "version": "v0.1.0"
    }
  ]
}
```

Publish with the official CLI:
```bash
curl -L "https://github.com/modelcontextprotocol/registry/releases/download/v1.0.0/mcp-publisher_1.0.0_linux_amd64.tar.gz" | tar xz mcp-publisher
sudo mv mcp-publisher /usr/local/bin/mcp-publisher
mcp-publisher validate server.json
mcp-publisher login docker --username zozo001
mcp-publisher publish server.json
```

### Verify registry entry
```bash
curl "https://registry.modelcontextprotocol.io/v0/servers?search=io.docker.zozo001.weather-mcp"
```

---

## Remote Assistant Integration
- **Claude Desktop:** add a local MCP entry pointing to `python weather_mcp.py`.
- **Claude Custom Connector / LM Studio:** deploy the Docker image and expose `https://<host>/mcp`.
- **Inspector:** connect via stdio for debugging and HTTP for production parity.

## Troubleshooting
- Never print to stdout when running stdio (log to files instead).
- Ensure `USER_AGENT` is set or NWS rejects requests.
- If Docker push fails, re-run `docker login --username zozo001`.
- MCP Registry requires the Docker label `io.modelcontextprotocol.server.name` matching the `name` field.

## Student Success Criteria
- `python weather_mcp.py` responds to tool calls.
- `uvicorn app:app` serves MCP at `/mcp` and passes Inspector tests.
- `zozo001/weather-mcp:latest` runs locally and exposes `/mcp`.
- `server.json` validates and publishes to the MCP Registry.

---

## Remixing the Pattern for Movie Recommenders
Session 12 already has teams harden their REST endpoints (e.g., `/api/recommend-movie`). This workshop is the next logical mile: wrap that same logic in FastMCP so AI assistants can call it deterministically as `/tool/recommend-movie` while human clients still hit the HTTP API. The FastAPI app above shows the coexistence model—tool calls run through the MCP server, while `app.py` keeps your REST surface area alive. In practice:

1. Keep the recommendation core (vector search, collaborative filter, etc.) in a shared module.
2. Expose it twice—once via FastAPI/JSON just like EX3, and once via `@mcp.tool(name="recommend-movie")`.
3. Add it to the MCP streamable HTTP mount so connectors (Claude Desktop, Inspector, custom agents) discover it alongside `get_alerts`.

Encourage teams to remix this pattern so every movie recommender squad ships the same contract: an authenticated REST API for humans and `/tool/recommend-movie` for assistants, both powered by the exact same business logic.

### Example End-to-End Flow
1. A client POSTs to `/api/recommend-movie` with the viewer profile. FastAPI validates payloads and calls the shared recommender module.
2. Claude (or any MCP-aware assistant) invokes `/tool/recommend-movie` with the same schema. FastMCP calls the exact same shared module and streams the response back through MCP.
3. Both surfaces log to the same observability hooks, so product teams can compare assistant-initiated traffic vs human traffic without double maintenance.

### Shared Recommendation Core (`services/recommendation.py`)
```python
from typing import Sequence

def recommend_movie(user_id: str, liked_titles: Sequence[str], mood: str) -> dict:
    # Vector search or rules live here; return structured data instead of strings
    return {
        "title": "Starship Rescue",
        "reason": f"Matches {mood} mood and overlaps with {liked_titles[:2]}",
        "alternatives": ["Nebula Knights", "Mission to Europa"],
    }
```

### FastAPI Endpoint (`api.py`)
```python
from fastapi import APIRouter
from pydantic import BaseModel
from services.recommendation import recommend_movie

router = APIRouter(prefix="/api")

class RecommendRequest(BaseModel):
    user_id: str
    liked_titles: list[str]
    mood: str

@router.post("/recommend-movie")
def recommend(req: RecommendRequest):
    return recommend_movie(req.user_id, req.liked_titles, req.mood)
```

### MCP Tool (`movie_mcp.py`)
```python
from mcp.server.fastmcp import FastMCP
from services.recommendation import recommend_movie

mcp = FastMCP("io.docker.zozo001.movie-mcp")

@mcp.tool(name="recommend-movie")
async def recommend_tool(user_id: str, liked_titles: list[str], mood: str) -> str:
    rec = recommend_movie(user_id, liked_titles, mood)
    return (
        f"Top pick: {rec['title']} — {rec['reason']}\n"
        f"Alternatives: {', '.join(rec['alternatives'])}"
    )
```

### FastAPI + MCP Bridge (`app.py`)
```python
from fastapi import FastAPI
from api import router as api_router
from movie_mcp import mcp

app = FastAPI()
app.include_router(api_router)
app.mount("/mcp", mcp.streamable_http_app())
```

Now the exact same recommendation object feeds the REST route and the MCP tool:
- Humans call `POST /api/recommend-movie`.
- Assistants call `/tool/recommend-movie` (stdio or HTTP transport).
- Observatory parity stays aligned, and shipping MCP support becomes an additive change instead of a rewrite.
