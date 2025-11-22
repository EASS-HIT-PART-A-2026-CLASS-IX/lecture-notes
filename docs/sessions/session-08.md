# Session 08 – AI Sidecar for Dynamic Compute (Calculator + Codegen)

- **Date:** Monday, Dec 22, 2025
- **Theme:** Stand up a simple FastAPI calculator backend (add/subtract + tiny charts), pair it with a Streamlit UI, and bolt on an AI sidecar (Pydantic AI + local vLLM or remote AI Studio) that generates and validates Python snippets for advanced calculations on demand—under guardrails.

## Session Story
We pivot to a contained “calculator + AI” slice: start with a FastAPI calculator backend (basic math endpoints plus a tiny plotting endpoint), add a Streamlit UI that uploads CSVs and calls the calculator, then attach an AI sidecar (FastAPI + Pydantic AI) that can generate/validate Python code for advanced calculations via vLLM or Google AI Studio. The main backend stays simple and defers complex ops to the sidecar via HTTP, with a validator agent to reduce hallucinations and enforce best practices.

## Learning Objectives
- Build a minimal FastAPI calculator service (add/subtract and a small chart endpoint) and keep routes stable.
- Stand up an AI sidecar (FastAPI + Pydantic AI) that generates Python snippets for advanced calculations and exposes them over HTTP to the calculator backend.
- Use a validator agent to lint/approve generated Python (reduce hallucinations, enforce safe imports/patterns) before execution.
- Wire Streamlit to upload CSVs, call calculator endpoints, and request sidecar codegen for custom analysis.
- Run both local (vLLM) and remote (Google AI Studio) LLMs through the same typed interface; cover with pytest/mocked transports and telemetry.

## Deliverables (What You’ll Build)
- Prompt templates/checklists for spec-first and tests-first requests.
- A FastAPI calculator service (basic math + tiny chart endpoint) with tests.
- An AI sidecar FastAPI service exposing Pydantic AI tools for code generation + validation.
- Streamlit UI that uploads CSVs, hits calculator endpoints, and calls the sidecar for custom analysis.
- pytest cases that mock LLM responses and verify validator gating; optional DSPy scratch file.

## Toolkit Snapshot
- **FastAPI** – calculator backend (core) + AI sidecar (codegen/validation gateway).
- **Pydantic AI** – typed tools/agents for code generation and validation.
- **vLLM / Google AI Studio** – interchangeable LLM endpoints behind the sidecar.
- **httpx** – shared HTTP client between services.
- **Streamlit** – CSV upload + calculator UI + AI-assisted analysis.
- **pytest** – mocks LLM transports and tests validator gating.
- **Logfire/structured logging** – telemetry with `X-Trace-Id` across backend + sidecar.

## Before Class (JiTT)
1. FastAPI + Postgres running; `/healthz` should echo `X-Trace-Id`.
2. Install deps:
   ```bash
   uv add pydantic-ai httpx
   # Optional DSPy:
   uv add dspy-ai
   ```
3. Pick one LLM track:
   - **Local vLLM**: run model, expose `/v1`, set `AI_BASE_URL=http://localhost:8000/v1`, `AI_API_KEY=dummy`.
   - **Google AI Studio (Gemini)**: set `GOOGLE_API_KEY`, `GOOGLE_GEMINI_MODEL`, install `uv add "pydantic-ai[google]" google-genai`.
4. Add AI env entries to `.env.example` / `.env` for the sidecar:
   ```ini
   AI_BASE_URL="http://localhost:8000/v1"
   AI_MODEL="local-model-or-gemini"
   AI_API_KEY="your-key-or-dummy"
   ```
5. Stand up skeleton services before class:
   - Calculator FastAPI service with `/add`, `/subtract`, `/chart` (matplotlib/plotly light) and tests.
   - AI sidecar FastAPI service with `/ai/codegen` and `/ai/validate` hitting Pydantic AI tools (mock transport OK).
   - Streamlit page loads and can call calculator endpoints locally.

## Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Intent & safety | 10 min | Discussion | Why AI is sidecarred; guardrails, attribution. |
| Calculator core | 20 min | Live coding | FastAPI add/subtract + tiny chart endpoint + tests. |
| Streamlit upload | 20 min | Live demo | CSV upload, call calculator API, show chart. |
| **Part B – Lab 1** | **45 min** | **Guided build** | **AI sidecar: Pydantic AI tool + code validator + `/ai/codegen` route.** |
| Break | 10 min | — | Timer + Q&A. |
| **Part C – Lab 2** | **45 min** | **Guided build** | **Wire Streamlit to sidecar; run local vLLM vs Google AI Studio; pytest with mocked LLM.** |
| Wrap-up | 10 min | Discussion | Telemetry, next steps, homework. |

## Guardrails & Prompt Patterns
1. **Policy reminder:** No secrets or private data; document AI assistance in changelog/PR. Every change must be understood and tested by a human.
2. **Spec-first prompt:** “Given this API contract and schema, draft the implementation.” Paste types/acceptance criteria.
3. **Tests-first prompt:** Ask for pytest cases before code; run them locally; only then request implementation.
4. **Refactor prompt:** “Keep behavior, improve structure,” paired with current code + tests.
5. **Telemetry toggle:** Keep `LOGFIRE_API_KEY` optional; default to local structured logs with `X-Trace-Id`.

## Lab 1 – Build the AI sidecar (45 min)
Goal: expose a safe codegen + validator sidecar that the calculator backend can call; cover it with pytest.

### Step 1 – Define settings + models (description)
- AI settings: `ai_base_url`, `ai_model`, `ai_api_key`, `ai_trace_id`.
- Calculator models: `OperationRequest` (`op`, `a`, `b`), `ChartRequest` (list of numbers), `ChartResponse` (image/data URL).
- Sidecar models: `CodegenRequest` (operation description or CSV columns), `CodegenResponse` (python_code, summary); `ValidationResult` (is_valid, issues).

### Step 2 – Tool implementation (sidecar `agents/` module)
```python
from pydantic import BaseModel
from pydantic_ai import Agent, Tool


class CodegenRequest(BaseModel):
    prompt: str


class CodegenResponse(BaseModel):
    python_code: str
    summary: str


def codegen_tools(settings):
    client = build_client(settings)

    @Tool
    def generate_code(payload: CodegenRequest) -> CodegenResponse:
        """Return safe Python to run inside the calculator (numpy/pandas only)."""
        response = client.post(
            "/chat/completions",
            json={
                "model": settings.ai_model,
                "messages": [
                    {"role": "system", "content": "Return JSON with python_code and summary. Use numpy/pandas only."},
                    {"role": "user", "content": payload.prompt},
                ],
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        return CodegenResponse.model_validate_json(response.json()["choices"][0]["message"]["content"])

    return generate_code


def build_codegen_agent(settings):
    return Agent(
        model="openai:gpt-4o-mini",  # or GoogleModel / local vLLM alias
        system_prompt="You are a careful code generator. Never use unsafe imports.",
        tools=[codegen_tools(settings)],
        output_type=CodegenResponse,
    )

# Validator agent (lint unsafe patterns)
class ValidationResult(BaseModel):
    is_valid: bool
    issues: list[str]

def build_validator_agent(settings):
    return Agent(
        model="openai:gpt-4o-mini",
        system_prompt="Review the provided python_code. Flag unsafe imports, file/network access.",
        output_type=ValidationResult,
    )
```

### Step 3 – Sidecar FastAPI routes (description)
- `POST /ai/codegen` → runs codegen agent, returns `CodegenResponse`.
- `POST /ai/validate` → runs validator agent on `python_code`, returns `ValidationResult`; calculator backend calls this before executing.
- Propagate `X-Trace-Id`, log tool name + outcome.

### Step 4 – Tests (run locally)
- Mock LLM via `httpx.MockTransport` to return deterministic `python_code`.
- Assert validator rejects unsafe imports (`os`, `subprocess`) and passes numpy/pandas.
- Anyio test for calculator backend calling sidecar `/ai/validate` before execution.

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
