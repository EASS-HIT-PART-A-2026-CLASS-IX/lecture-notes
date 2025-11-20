# Session 08 – Working with AI Coding Assistants (Local or Cloud)

- **Date:** Monday, Dec 22, 2025
- **Theme:** Pair program with AI safely—prompt with intent, validate outputs, and wire a typed agent (Pydantic AI) to the FastAPI backend. Optional DSPy mini-lab shows declarative prompting.

## Session Story
You now have FastAPI + Postgres with both Streamlit and React clients. Session 08 layers AI assistance on top: students practice spec/tests-first prompting, wrap the existing API behind a typed Pydantic AI tool, and call either a local model (LM Studio/vLLM) or Google AI Studio. The emphasis is on safety, telemetry, and keeping humans in charge.

## Learning Objectives
- Apply spec-first and tests-first prompting patterns; review AI outputs critically.
- Expose FastAPI functionality as a typed Pydantic AI tool with trace/log hooks.
- Call local or hosted LLM endpoints (LM Studio/vLLM/Google AI Studio) via the same interface.
- Evaluate agent responses with pytest; keep secrets and telemetry under control.
- (Optional) Explore DSPy `Signature` + `Predict` to see declarative prompting.

## Deliverables (What You’ll Build)
- Prompt templates/checklists for spec-first and tests-first requests.
- A Pydantic AI tool that calls the `/movies` API with validated inputs/outputs.
- A small FastAPI route (e.g., `/ai/pitch`) that invokes the agent and returns a typed response.
- pytest cases that call the agent with a mocked LLM client.
- Optional DSPy scratch file showing `Signature` + `Predict` wired to the same tool.

## Toolkit Snapshot
- **Pydantic AI** – typed agent + tool-calling framework.
- **httpx** – used by tools to call FastAPI.
- **LM Studio / vLLM / Google AI Studio** – interchangeable LLM endpoints (OpenAI-compatible or Gemini).
- **Logfire (or structured logging)** – telemetry with `X-Trace-Id`.
- **pytest** – evaluates agent outputs safely.
- **DSPy (optional)** – declarative prompting layer.

## Before Class (JiTT)
1. FastAPI + Postgres running; `/healthz` should echo `X-Trace-Id`.
2. Install deps:
   ```bash
   uv add pydantic-ai httpx
   # Optional DSPy:
   uv add dspy-ai
   ```
3. Pick one LLM track:
   - **LM Studio**: start a local model, note base URL (e.g., `http://localhost:1234/v1`), set `AI_API_KEY=dummy`.
   - **vLLM**: run the provided Docker image and expose `:8000/v1`.
   - **Google AI Studio (Gemini)**: create an API key, export:
     ```bash
     export GOOGLE_API_KEY="..."; export GOOGLE_GEMINI_MODEL="gemini-2.0-flash"
     uv add "pydantic-ai[google]" google-genai
     ```
4. Add AI env entries to `.env.example` / `.env`:
   ```ini
   AI_BASE_URL="http://localhost:1234/v1"  # or Google endpoint via pydantic-ai models
   AI_MODEL="local-model-or-gemini"
   AI_API_KEY="your-key-or-dummy"
   ```
5. Review Session 04–07 tests; be ready to add agent tests next to them.

## Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| EX2 gallery walk | 15 min | Student demos | Trace IDs visible in UIs/logs. |
| Policy + prompting | 15 min | Talk | Spec/tests-first, safety, attribution. |
| Micro demo: prompt → test | 5 min | Live demo | Write tests first, then code with AI. |
| Pydantic AI tool-calling | 20 min | Live coding | Typed tool + FastAPI route + telemetry. |
| **Part B – Lab 1** | **45 min** | **Guided pairing** | **Build the agent tool + pytest around it.** |
| Break | 10 min | — | Launch a 10-minute timer. |
| **Part C – Lab 2** | **45 min** | **Guided pairing** | **Plug into LM Studio/vLLM or Google AI Studio; optional DSPy.** |
| Wrap-up | 10 min | Discussion | What worked, what to harden next. |

## Guardrails & Prompt Patterns
1. **Policy reminder:** No secrets or private data; document AI assistance in changelog/PR. Every change must be understood and tested by a human.
2. **Spec-first prompt:** “Given this API contract and schema, draft the implementation.” Paste types/acceptance criteria.
3. **Tests-first prompt:** Ask for pytest cases before code; run them locally; only then request implementation.
4. **Refactor prompt:** “Keep behavior, improve structure,” paired with current code + tests.
5. **Telemetry toggle:** Keep `LOGFIRE_API_KEY` optional; default to local structured logs with `X-Trace-Id`.

## Lab 1 – Build a Pydantic AI tool (45 min)
Goal: expose a safe tool that reuses the `/movies` API and returns validated data; cover it with pytest.

### Step 1 – Define settings + models (description only)
- Add AI fields to your existing settings module: `ai_base_url`, `ai_model`, `ai_api_key`.
- Create a Pydantic response model for the AI output (e.g., `MoviePitch` with `title`, `hook`).

### Step 2 – Tool implementation (place in an `agents/` module)
```python
from typing import Annotated

import httpx
from pydantic import BaseModel
from pydantic_ai import Agent, Tool

from movie_service.app.config import Settings


class PitchRequest(BaseModel):
    title: str
    mood: str = "optimistic"


class PitchResponse(BaseModel):
    title: str
    hook: str


def build_client(settings: Settings) -> httpx.Client:
    return httpx.Client(
        base_url=settings.ai_base_url,
        headers={"Authorization": f"Bearer {settings.ai_api_key}"},
        timeout=10.0,
    )


def movie_tools(settings: Settings) -> Tool:
    client = build_client(settings)

    @Tool
    def write_pitch(payload: PitchRequest) -> PitchResponse:
        """Ask the LLM for a one-sentence pitch about a movie title."""
        response = client.post(
            "/chat/completions",
            json={
                "model": settings.ai_model,
                "messages": [
                    {"role": "system", "content": "Return JSON with title + hook."},
                    {"role": "user", "content": f"Title: {payload.title}. Mood: {payload.mood}."},
                ],
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()["choices"][0]["message"]["content"]
        return PitchResponse.model_validate_json(data)

    return write_pitch


def build_agent(settings: Settings) -> Agent[PitchRequest, PitchResponse]:
    agent = Agent(
        model="openai:gpt-4o-mini",  # or GoogleModel / local alias
        system_prompt="You are a concise movie pitch assistant.",
        tools=[movie_tools(settings)],
        output_type=PitchResponse,
    )
    return agent
```

### Step 3 – FastAPI route (description)
- Add a route like `POST /ai/pitch` that accepts `PitchRequest`, calls `build_agent(settings).run_sync(...)`, and returns `PitchResponse`.
- Include `X-Trace-Id` propagation and log the tool name + outcome.

### Step 4 – Tests (run locally)
Use pytest to mock the LLM call:
```python
from movie_service.app.agents.movies import build_agent, PitchRequest
from pydantic_ai.models.openai import OpenAIModel


def test_pitch_agent_uses_mocked_llm(monkeypatch):
    from movie_service.app.config import Settings

    settings = Settings(ai_base_url="https://example.test", ai_model="fake", ai_api_key="key")
    agent = build_agent(settings)
    agent.model = OpenAIModel(  # type: ignore[assignment]
        model="fake",
        api_key="key",
        client_kwargs={"base_url": "https://example.test"},
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json={
            "choices": [{"message": {"content": '{"title": "Mock", "hook": "Hook"}'}}]
        })),
    )

    result = agent.run_sync(PitchRequest(title="Test"))
    assert result.data.hook == "Hook"
```

## Lab 2 – Connect real endpoints (45 min)
Goal: swap the mocked LLM for a real one (LM Studio/vLLM or Google AI Studio) and observe telemetry.

### Local tracks (LM Studio or vLLM)
- Start the model server; confirm `GET /v1/models` works.
- Set `AI_BASE_URL` and `AI_API_KEY` (dummy for LM Studio) in `.env`.
- Hit `POST /ai/pitch` and verify JSON output; ensure `X-Trace-Id` appears in logs.

### Google AI Studio track
- Export `GOOGLE_API_KEY` + `GOOGLE_GEMINI_MODEL`.
- Swap the agent model to `GoogleModel`:
  ```python
  from pydantic_ai.models.google import GoogleModel
  agent = Agent(
      model=GoogleModel(model=settings.ai_model, api_key=settings.ai_api_key),
      system_prompt="You are a concise movie pitch assistant.",
      tools=[movie_tools(settings)],
      output_type=PitchResponse,
  )
  ```
- Repeat the `/ai/pitch` call; observe latency/quotas and logtrace.

### Optional DSPy mini-lab
- Install `dspy-ai` if not already.
- Create a scratch file with:
  ```python
  import dspy

  class Pitch(dspy.Signature):
      """Return a short hook for a movie title."""
      title: str = dspy.InputField()
      hook: str = dspy.OutputField()

  dspy.configure(lm=dspy.OpenAI(model="gpt-4o-mini"))
  predict = dspy.Predict(Pitch)
  print(predict(title="Orbit Shift").hook)
  ```
- Discuss how DSPy `Signature` maps to the Pydantic schemas above.

## Wrap-Up & Success Criteria
- [ ] `/ai/pitch` returns a typed response and logs `X-Trace-Id`.
- [ ] Agent/tool code is covered by pytest with mocked transports.
- [ ] LLM endpoint (local or Google) responds successfully with JSON payloads.
- [ ] README/changelog notes AI usage, env vars, and telemetry defaults.

## Session 09 Preview – Async Jobs + Queues
| Component | Session 08 | Session 09 | Change? |
| --- | --- | --- | --- |
| Backend | FastAPI + Postgres + AI tool | Add async jobs/Redis/worker | Extend |
| UIs | Streamlit + React | Reused | None |
| AI | Pydantic AI (optional DSPy) | Reused, called from jobs | Extend |
| Tests | Agent mocks + pytest | Add worker/queue fixtures | Extend |

Action items before Session 09:
1. Keep AI env vars handy; decide on LM Studio/vLLM/Google path.
2. Clean up mocked LLM fixtures so CI stays deterministic.
3. Note any latency/quotas to budget for async job runs.

## Troubleshooting
- **LLM returns non-JSON** → enforce `response_format` or wrap parsing with try/except and return 422.
- **`403/401` from Google** → confirm `GOOGLE_API_KEY` and `GOOGLE_GEMINI_MODEL`; regenerate the key if needed.
- **Local model not reachable** → `curl ${AI_BASE_URL}/v1/models`; restart LM Studio/vLLM container.
- **pytest hits real network** → use `httpx.MockTransport` or dependency overrides to avoid live calls in tests.
