# Session 08 – AI Sidecar for Dynamic Compute (Calculator + Codegen + SQL)

- **Date:** Monday, Dec 22, 2025
- **Theme:** Stand up a simple FastAPI calculator backend (add/subtract + tiny charts), pair it with a Streamlit UI, and bolt on an AI sidecar (Pydantic AI + local vLLM or remote AI Studio) that generates and validates Python snippets for advanced calculations on demand—under guardrails—and a free-language-to-SQL agent that runs against a DuckDB microservice loaded from uploaded CSVs.

## Session Story
We pivot to a contained “calculator + AI” slice: start with a FastAPI calculator backend (basic math endpoints plus a tiny plotting endpoint), add a Streamlit UI that uploads CSVs and calls the calculator, then attach an AI sidecar (FastAPI + Pydantic AI) that can generate/validate Python code for advanced calculations via vLLM or Google AI Studio. We also load the uploaded CSV into a tiny DuckDB microservice so an SQL agent can translate free language into SQL over that table. The same sidecar hosts both TEXT→PY and TEXT→SQL flows. The stack stays Postgres-free for this session—just FastAPI, Streamlit, the sidecar, and DuckDB in-memory—so all AI hops stay simple.

## Architecture Snapshot
- **Frontend:** Streamlit (CSV upload, charts, free-text prompts for Python and SQL paths). **Talks only to the calculator backend.**
- **Calculator backend (FastAPI):** basic math + chart endpoints; advanced endpoints call the AI sidecar and DuckDB service; adds execution/telemetry envelopes. Acts as the sole gateway for the UI.
- **AI sidecar (FastAPI + Pydantic AI):** Python codegen + validator + refine loop; SQL codegen + validator + refine loop; exposes `/ai/codegen`, `/ai/sql`, `/ai/execute` (sandboxed run). Same service covers TEXT→PY and TEXT→SQL.
- **DuckDB microservice:** holds the uploaded CSV as `uploaded` table; exposes `/upload_csv` and `/query` (SELECT-only).
- **LLM providers:** local vLLM/LM Studio (optional container in compose) or remote Google AI Studio behind the sidecar via the same typed client.

## Build Plan (stepwise)
1) **Baseline backend + UI (no AI)**: FastAPI `/healthz`, `/add`, `/subtract`, `/chart`; Streamlit calls only these; return `X-Trace-Id`.  
2) **DuckDB smoke test**: Stand up DuckDB microservice; backend adds `/data/ping` (hard-coded SELECT 1) and `/data/query/raw` (fixed SQL) to verify connectivity; UI shows the ping result.  
3) **AI sidecar (local LLM)**: Add sidecar with `/ai/codegen` + `/ai/validate/python`; backend adds `/calculate/advanced` that calls the sidecar and returns the code + validation (no execution yet); UI shows generated code.  
4) **CSV → DuckDB**: Backend exposes `/data/upload` to forward CSV to DuckDB microservice; UI uploads through backend; store returned columns.  
5) **Free-language → SQL**: Sidecar gets `/ai/sql` + validator; backend `/calculate/sql` calls sidecar then DuckDB; UI sends free text, receives SQL + rows.  
6) **Code execution + visualization**: Add `/ai/execute` sandbox; backend executes validated code; UI can run text-to-Python for analysis/plots; show suggested prompts.  
7) **Refinement + telemetry**: Enable refine loops, rate limits, observability; lock down safety (SQL + Python).

## Docker/Dev Layout (outline only)
- Use `docker-compose.yml` with four services:
  - `calculator`: FastAPI main backend (`uvicorn app.main:app`), depends on `duckdb` and `sidecar`.
  - `sidecar`: FastAPI AI sidecar (`uvicorn sidecar.main:app`), environment for LLM endpoint (`AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`).
  - `duckdb`: DuckDB microservice (`uvicorn duckdb_service.main:app`), mounts a writable volume for temp CSVs if needed.
  - `streamlit`: Frontend (`streamlit run ui/app.py`), depends on `calculator`.
- Optional: `llm-local`: LM Studio/vLLM-compatible API on `/v1` for local track; set `AI_BASE_URL=http://llm-local:8000/v1` when enabled.
- Shared network: `app-net`; expose ports 8000 (calculator), 8001 (duckdb), 8002 (sidecar), 8501 (streamlit).
- Volumes: optional `duckdb_data` for persisted duckdb files; otherwise in-memory.
- Env files: `.env` loaded into `calculator` and `sidecar` for AI keys/model/base URL; `DUCKDB_SERVICE_URL=http://duckdb:8001`; include `GOOGLE_API_KEY`, `GOOGLE_GEMINI_MODEL` for remote track.
- Healthchecks: `curl -f http://localhost:PORT/healthz` for calculator/sidecar/duckdb; Streamlit basic HTTP check.
- Dev loop: `docker compose up --build`; tests run inside `calculator` container with `pytest`.

## Learning Objectives
- Build a minimal FastAPI calculator service (add/subtract and a small chart endpoint) and keep routes stable.
- Stand up an AI sidecar (FastAPI + Pydantic AI) that generates Python snippets for advanced calculations and exposes them over HTTP to the calculator backend.
- Use validator + refinement agents to lint/approve and iteratively improve generated Python (reduce hallucinations, enforce safe imports/patterns) before execution.
- Translate free language to SQL against a DuckDB microservice loaded from CSV uploads; validate SQL and map results back to the UI.
- Wire Streamlit to upload CSVs, call calculator endpoints, and request sidecar codegen/SQL for custom analysis.
- Run both local (vLLM) and remote (Google AI Studio) LLMs through the same typed interface; cover with pytest/mocked transports and telemetry.

## Deliverables (What You’ll Build)
- Prompt templates/checklists for spec-first and tests-first requests.
- A FastAPI calculator service (basic math + tiny chart endpoint) with tests.
- An AI sidecar FastAPI service exposing Pydantic AI tools for code generation, validation, and SQL translation.
- DuckDB microservice that ingests CSV uploads and exposes a simple `/query` endpoint used by the SQL agent.
- Streamlit UI that uploads CSVs, hits calculator endpoints, and calls the sidecar for custom analysis (Python or SQL).
- pytest cases that mock LLM responses and verify validator gating for both Python and SQL; optional DSPy scratch file.

## Toolkit Snapshot
- **FastAPI** – calculator backend (core) + AI sidecar (codegen/validation gateway).
- **Pydantic AI** – typed tools/agents for code generation, SQL translation, and validation/refinement.
- **DuckDB + tiny HTTP microservice** – holds the uploaded CSV as an in-memory table for SQL agent execution.
- **vLLM / Google AI Studio** – interchangeable LLM endpoints behind the sidecar.
- **httpx** – shared HTTP client between services.
- **Streamlit** – CSV upload + calculator UI + AI-assisted analysis.
- **pytest** – mocks LLM transports and tests validator gating.
- **Logfire/structured logging** – telemetry with `X-Trace-Id` across backend + sidecar + DuckDB microservice.

## Before Class (JiTT)
1. FastAPI calculator + DuckDB microservice running; `/healthz` should echo `X-Trace-Id`. No Postgres needed in this session.
2. Install deps:
   ```bash
   uv add fastapi uvicorn pydantic-ai httpx duckdb pandas numpy streamlit plotly
   # Optional DSPy:
   uv add dspy-ai
   ```
3. **DuckDB microservice setup:**
   ```python
   # duckdb_service/main.py
   from fastapi import FastAPI, UploadFile, HTTPException
   from pydantic import BaseModel
   import duckdb
   import pandas as pd
   
   app = FastAPI()
   conn = duckdb.connect(":memory:")
   
   class QueryRequest(BaseModel):
       sql: str
       params: dict[str, str] = {}
   
   @app.post("/upload_csv")
   async def upload_csv(file: UploadFile):
       df = pd.read_csv(file.file)
       conn.register("uploaded", df)
       return {"columns": df.columns.tolist(), "rows": len(df)}
   
   @app.post("/query")
   async def query(req: QueryRequest):
       # Enforce SELECT-only
       if not req.sql.strip().upper().startswith("SELECT"):
           raise HTTPException(400, "Only SELECT queries allowed")
       result = conn.execute(req.sql, req.params).fetchdf()
       return {"rows": result.to_dict(orient="records"), "count": len(result)}
   ```
4. Pick one LLM track:
   - **Local vLLM**: run model, expose `/v1`, set `AI_BASE_URL=http://localhost:8000/v1`, `AI_API_KEY=dummy`.
   - **Google AI Studio (Gemini)**: set `GOOGLE_API_KEY`, `GOOGLE_GEMINI_MODEL`, install `uv add "pydantic-ai[google]" google-genai`.
5. Add AI env entries to `.env.example` / `.env` for the sidecar:
   ```ini
   AI_BASE_URL="http://localhost:8000/v1"
   AI_MODEL="local-model-or-gemini"
   AI_API_KEY="your-key-or-dummy"
   DUCKDB_SERVICE_URL="http://localhost:8001"
   CODE_EXECUTION_TIMEOUT=10
   CODE_EXECUTION_MAX_MEMORY_MB=256
   # For Google AI Studio track
   GOOGLE_API_KEY="your-google-api-key"
   GOOGLE_GEMINI_MODEL="gemini-1.5-flash"
   ```
6. Stand up skeleton services before class:
   - Calculator FastAPI service with `/add`, `/subtract`, `/chart` (matplotlib/plotly light) and tests.
   - AI sidecar FastAPI service with `/ai/codegen`, `/ai/validate`, and `/ai/sql` hitting Pydantic AI tools (mock transport OK).
   - DuckDB microservice reachable from calculator (or mounted in-process) with `/query`.
   - Streamlit page loads and can call calculator and AI endpoints locally.

## Agenda
| Segment | Duration | Format | Focus |
| --- | --- | --- | --- |
| Intent & safety | 10 min | Discussion | Why AI is sidecarred; guardrails, attribution. |
| Calculator core | 20 min | Live coding | FastAPI add/subtract + tiny chart endpoint + tests. |
| Streamlit upload | 20 min | Live demo | CSV upload, call calculator API, show chart, load CSV into DuckDB. |
| **Part B – Lab 1** | **45 min** | **Guided build** | **AI sidecar: Pydantic AI code + SQL tools, validator/refiner + `/ai/codegen` + `/ai/sql` routes.** |
| Break | 10 min | — | Timer + Q&A. |
| **Part C – Lab 2** | **45 min** | **Guided build** | **Wire Streamlit to sidecar + DuckDB; run local vLLM vs Google AI Studio; pytest with mocked LLM.** |
| Wrap-up | 10 min | Discussion | Telemetry, next steps, homework. |

## Guardrails & Prompt Patterns
1. **Policy reminder:** No secrets or private data; document AI assistance in changelog/PR. Every change must be understood and tested by a human.
2. **Spec-first prompt:** "Given this API contract and schema, draft the implementation." Paste types/acceptance criteria.
3. **Tests-first prompt:** Ask for pytest cases before code; run them locally; only then request implementation.
4. **Refactor prompt:** "Keep behavior, improve structure," paired with current code + tests.
5. **Telemetry toggle:** Keep `LOGFIRE_API_KEY` optional; default to local structured logs with `X-Trace-Id`.
6. **SQL safety:** Validator agent enforces SELECT-only SQL; blocks DDL/DML keywords; restricts to `uploaded` table; requires explicit column names from schema; adds `LIMIT 200` if missing.
7. **Python safety:** Validator agent blocks unsafe imports (os, subprocess, socket, requests); forbids eval/exec/compile; enforces numpy/pandas/math only; checks for file I/O patterns; uses `ast.parse()` for syntax validation.
8. **Execution safety:** Code runs in sandboxed environment with resource limits (see Security Hardening section).
9. **Refine loop:** If validator flags Python or SQL, ask the LLM to propose a patch diff; re-run validator; cap retries at 2; log all attempts with trace ID.

## Prompt Pack (copy/paste)
- **Spec-first (backend route):** “Given this contract for `POST /calculate/advanced` that returns `CodegenResponse` and `ValidationResult`, draft FastAPI code using dependency-injected httpx clients and Pydantic models. Include X-Trace-Id propagation and 422 on validation failure.”
- **Tests-first (sidecar agents):** “Write pytest with httpx.MockTransport to cover `/ai/codegen` success, invalid JSON, and unsafe import rejection. Use fixtures for mock LLM responses.”
- **SQL safety check:** “Review this SQL for safety. Enforce SELECT-only, table `uploaded`, allowed columns: {columns}, must include LIMIT <= 1000. Respond with JSON: is_valid (bool), issues (list).”
- **Python refine:** “Given validation issues {issues}, propose a minimal patch to this code to pass safety checks while keeping the behavior: ```{code}```. Return only the patched code in fenced ```python```.”

## Error Handling Matrix
Standardize HTTP status codes across services:
- **400**: Malformed request (invalid JSON, missing required fields)
- **422**: Validation failure (unsafe code, invalid SQL, schema violation)
- **500**: Execution error (code crash, DuckDB query failure)
- **503**: LLM timeout or unavailable
- **429**: Rate limit exceeded (if implemented)

All errors include `{"error": "message", "details": {...}, "trace_id": "..."}`.

## Lab 1 – Build the AI sidecar (45 min)
Goal: expose a safe codegen + validator sidecar (Python + SQL) that the calculator backend can call; cover it with pytest.

### Step 1 – Define settings + models (description)
- AI settings: `ai_base_url`, `ai_model`, `ai_api_key`, `ai_trace_id`, `duckdb_service_url`, `code_execution_timeout`, `code_execution_max_memory_mb`.
- Calculator models: `OperationRequest` (`op`, `a`, `b`), `ChartRequest` (list of numbers), `ChartResponse` (image/data URL).
- Sidecar models: `CodegenRequest` (operation description or CSV columns), `CodegenResponse` (python_code, summary, allowed_imports); `ValidationResult` (is_valid, issues, severity).
- SQL models: `SqlQueryRequest` (prompt, available_columns, table_name="uploaded"), `SqlQueryResponse` (sql, summary, parameters, estimated_rows).
- Execution models: `ExecuteCodeRequest` (python_code, input_data), `ExecuteCodeResponse` (result, logs, execution_time_ms, memory_used_mb).

### Step 2 – Tool implementation (sidecar `agents/` module)
```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel


class CodegenRequest(BaseModel):
    prompt: str
    context: dict = Field(default_factory=dict)


class CodegenResponse(BaseModel):
    python_code: str
    summary: str
    allowed_imports: list[str] = Field(default=["numpy", "pandas", "math"])


class SqlQueryRequest(BaseModel):
    prompt: str
    available_columns: list[str]
    table_name: str = "uploaded"


class SqlQueryResponse(BaseModel):
    sql: str
    summary: str
    parameters: dict[str, str] = Field(default_factory=dict)
    estimated_rows: int | None = None


class ValidationResult(BaseModel):
    is_valid: bool
    issues: list[str]
    severity: str = "error"  # error, warning, info


def build_codegen_agent(settings):
    """Agent that generates safe Python code for calculations."""
    model = OpenAIModel(
        model_name=settings.ai_model,
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
    )
    
    return Agent(
        model=model,
        system_prompt=(
            "You are a careful code generator for numerical calculations. "
            "ONLY use these imports: numpy, pandas, math. "
            "Never use: os, subprocess, socket, requests, urllib, eval, exec, compile, open, file operations. "
            "Return executable Python that defines a function named 'calculate' taking a dict as input. "
            "Include docstring explaining the calculation."
        ),
        result_type=CodegenResponse,
    )


def build_sql_agent(settings):
    """Agent that generates safe SELECT-only SQL for DuckDB."""
    model = OpenAIModel(
        model_name=settings.ai_model,
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
    )
    
    return Agent(
        model=model,
        system_prompt=(
            "You produce read-only SQL for DuckDB against the 'uploaded' table. "
            "ONLY generate SELECT statements. "
            "NEVER use: DROP, DELETE, UPDATE, INSERT, CREATE, ALTER, TRUNCATE. "
            "Always add LIMIT 200 unless user specifies a smaller limit. "
            "Use only columns provided in the request. "
            "Use parameterized queries with $param syntax for user inputs."
        ),
        result_type=SqlQueryResponse,
    )


def build_python_validator_agent(settings):
    """Agent that validates Python code for safety."""
    model = OpenAIModel(
        model_name=settings.ai_model,
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
    )
    
    return Agent(
        model=model,
        system_prompt=(
            "Review Python code for safety violations. Flag any of these as INVALID:\n"
            "- Imports other than numpy, pandas, math\n"
            "- Use of eval, exec, compile, __import__\n"
            "- File operations: open, read, write\n"
            "- Network access: socket, requests, urllib, http\n"
            "- System calls: os, subprocess, sys.exit\n"
            "- Missing 'calculate' function definition\n"
            "Return is_valid=false if ANY violation found. List all issues."
        ),
        result_type=ValidationResult,
    )


def build_sql_validator_agent(settings):
    """Agent that validates SQL for safety."""
    model = OpenAIModel(
        model_name=settings.ai_model,
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
    )
    
    return Agent(
        model=model,
        system_prompt=(
            "Review SQL for safety violations. Flag as INVALID if:\n"
            "- Contains DDL: CREATE, DROP, ALTER, TRUNCATE\n"
            "- Contains DML: INSERT, UPDATE, DELETE\n"
            "- Does not start with SELECT\n"
            "- References tables other than 'uploaded'\n"
            "- Uses columns not in the allowed list\n"
            "- Missing LIMIT clause (require LIMIT <= 1000)\n"
            "Return is_valid=false if ANY violation found."
        ),
        result_type=ValidationResult,
    )


async def refine_code(
    codegen_agent: Agent,
    validator_agent: Agent,
    request: CodegenRequest,
    max_attempts: int = 2
) -> CodegenResponse:
    """Generate code, validate, and request patches if invalid."""
    attempt_num = 0
    last_code = None
    
    while attempt_num <= max_attempts:
        # Generate code
        if attempt_num == 0:
            result = await codegen_agent.run(request.prompt, message_history=[])
        else:
            # Refine based on validation issues
            refine_prompt = (
                f"Fix this code to pass validation. Issues: {', '.join(validation.issues)}\n"
                f"Original request: {request.prompt}\n"
                f"Previous code:\n{last_code}"
            )
            result = await codegen_agent.run(refine_prompt, message_history=[])
        
        last_code = result.data.python_code
        
        # Validate
        validation = await validator_agent.run(
            f"Validate this code:\n{last_code}",
            message_history=[]
        )
        
        if validation.data.is_valid:
            return result.data
        
        attempt_num += 1
    
    # All attempts exhausted
    raise ValueError(f"Validation failed after {max_attempts+1} attempts: {validation.data.issues}")


async def refine_sql(
    sql_agent: Agent,
    validator_agent: Agent,
    request: SqlQueryRequest,
    max_attempts: int = 2
) -> SqlQueryResponse:
    """Generate SQL, validate, and request patches if invalid."""
    attempt_num = 0
    last_sql = None
    
    while attempt_num <= max_attempts:
        if attempt_num == 0:
            prompt = f"{request.prompt}\nAvailable columns: {', '.join(request.available_columns)}"
            result = await sql_agent.run(prompt, message_history=[])
        else:
            refine_prompt = (
                f"Fix this SQL to pass validation. Issues: {', '.join(validation.issues)}\n"
                f"Original request: {request.prompt}\n"
                f"Available columns: {', '.join(request.available_columns)}\n"
                f"Previous SQL:\n{last_sql}"
            )
            result = await sql_agent.run(refine_prompt, message_history=[])
        
        last_sql = result.data.sql
        
        # Validate
        validation = await validator_agent.run(
            f"Validate this SQL:\n{last_sql}\nAllowed columns: {', '.join(request.available_columns)}",
            message_history=[]
        )
        
        if validation.data.is_valid:
            return result.data
        
        attempt_num += 1
    
    raise ValueError(f"SQL validation failed after {max_attempts+1} attempts: {validation.data.issues}")
```

### Step 3 – Sidecar FastAPI routes (description)
- `POST /ai/codegen` → runs codegen agent with refine loop, returns `CodegenResponse`. Accepts `max_attempts` param (default 2).
- `POST /ai/validate/python` → runs Python validator agent on `python_code`, returns `ValidationResult`.
- `POST /ai/validate/sql` → runs SQL validator agent on `sql` + `available_columns`, returns `ValidationResult`.
- `POST /ai/sql` → runs SQL agent with refine loop, returns `SqlQueryResponse`.
- `POST /ai/execute` → executes validated Python in sandboxed subprocess (see Security Hardening), returns `ExecuteCodeResponse`.
- Propagate `X-Trace-Id`, log agent name + attempt count + validation outcome + execution time.
- Error handling per matrix: 400 (bad request), 422 (validation fail), 500 (execution crash), 503 (LLM timeout).

### Step 4 – Calculator backend integration (description)
Add advanced endpoints to the calculator service:
- `POST /calculate/advanced` → accepts `CodegenRequest`, calls sidecar `/ai/codegen` with refine loop, then `/ai/validate/python`; returns code + validation (no execution yet).
- `POST /calculate/advanced/execute` → accepts `ExecuteCodeRequest` (python_code + input_data), optionally revalidates, then calls `/ai/execute` with sandboxed limits.
- `POST /calculate/sql` → accepts `SqlQueryRequest`, calls sidecar `/ai/sql` with refine loop, then forwards SQL to DuckDB microservice `/query` with parameter binding.
- Return results with `X-Trace-Id`, execution metadata (time_ms, memory_mb, attempts), and validation summary.
- On validation failure after max attempts, return 422 with all `ValidationResult.issues` from final attempt.
- On execution timeout, return 500 with partial logs and timeout flag.

Example flow (Python):
```
Client → Calculator /calculate/advanced → Sidecar /ai/codegen (with refine loop) → LLM
                                       ↓
                          Sidecar /ai/validate/python → LLM

Client → Calculator /calculate/advanced/execute → Sidecar /ai/execute (sandboxed) → Response
```

Example flow (SQL over CSV via DuckDB microservice):
```
Client → Calculator /calculate/sql → Sidecar /ai/sql (with refine loop) → LLM
                              ↓
                    Sidecar /ai/validate/sql → LLM
                              ↓
                    DuckDB microservice /query → Response
```

## Security Hardening

### Code Execution Sandboxing
**Option 1 – RestrictedPython (in-process):**
```python
from RestrictedPython import compile_restricted, safe_globals
import resource

def execute_sandboxed(code: str, input_data: dict, timeout: int = 10) -> dict:
    # Compile with restrictions
    byte_code = compile_restricted(code, '<string>', 'exec')
    
    # Set resource limits
    resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    
    # Execute with safe globals
    exec_globals = safe_globals.copy()
    exec_globals['__builtins__'] = {
        '__import__': __import__,
        '__build_class__': __build_class__,
    }
    exec(byte_code, exec_globals)
    
    # Call the calculate function
    return exec_globals['calculate'](input_data)
```

**Option 2 – Docker container isolation:**
```python
import docker
import asyncio

async def execute_in_container(code: str, input_data: dict, timeout: int = 10) -> dict:
    client = docker.from_env()
    container = client.containers.run(
        "python:3.11-slim",
        command=["python", "-c", code],
        environment={"INPUT": json.dumps(input_data)},
        mem_limit="256m",
        cpu_period=100000,
        cpu_quota=50000,  # 50% of one CPU
        network_disabled=True,
        detach=True,
    )
    
    try:
        await asyncio.wait_for(container.wait(), timeout=timeout)
        logs = container.logs().decode()
        return json.loads(logs)
    finally:
        container.remove(force=True)
```

### Input Validation
- **CSV uploads:** Max file size 10MB; validate headers match expected schema; scan for zip bombs.
- **SQL parameters:** Type-check all parameters; reject overly long strings (>1000 chars).
- **Python code:** Max code length 5000 chars; syntax check with `ast.parse()` before LLM call.
- **Algorithmic complexity:** Reject code with nested loops >3 levels deep; limit list comprehension nesting.

### Rate Limiting
Implement per-endpoint rate limits:
- `/ai/codegen`: 10 requests/minute per IP
- `/ai/sql`: 20 requests/minute per IP
- `/ai/execute`: 5 requests/minute per IP (most resource-intensive)

## Tests (run locally)
- **Unit (sidecar):** httpx.MockTransport for deterministic Python and SQL responses; validator rejects unsafe imports/DDL and missing LIMIT; timeout/non-JSON tests.
- **Integration (calculator + sidecar + DuckDB):** AsyncClient against test app; `/calculate/advanced` returns code + validation; `/calculate/advanced/execute` runs sandboxed code; `/calculate/sql` returns rows; X-Trace-Id propagation; 422 on bad code/SQL.
- **Contract:** Assert schemas for CodegenResponse, ValidationResult, SqlQueryResponse stay in sync via `model_json_schema()`.
- **UI smoke:** Streamlit “Run Analysis” hits calculator-only endpoints; ensure no direct calls to sidecar/DuckDB from UI.

## Lab 2 – Connect real endpoints (45 min)
Goal: swap the mocked LLM for a real one (LM Studio/vLLM or Google AI Studio) and observe telemetry across Python and SQL flows.

### Local tracks (LM Studio or vLLM)
- Start the model server; confirm `GET /v1/models` works.
- Set `AI_BASE_URL` and `AI_API_KEY` (dummy for LM Studio) in `.env`.
- Hit `POST /calculate/advanced` with a prompt like "calculate mean and standard deviation of this list" and verify:
  - Generated code uses only numpy/pandas
  - Validation passes and refine loop returns best candidate
  - `X-Trace-Id` appears in logs from both services
- Then call `POST /calculate/advanced/execute` with the returned `python_code` and sample input; assert the sandboxed execution result and execution metadata.
- Hit `POST /calculate/sql` with "give me avg and max of sales by region" and verify:
  - SQL is SELECT-only, scoped to `uploaded` table, has `LIMIT`
  - DuckDB returns expected rows
- Test error scenarios:
  - Stop LLM server mid-request → verify 503 response
  - Send malformed prompt → verify graceful handling

### Google AI Studio track
- Export `GOOGLE_API_KEY` + `GOOGLE_GEMINI_MODEL`.
- Swap the agent model to `GoogleModel`:
  ```python
  from pydantic_ai.models.google import GoogleModel
  agent = Agent(
      model=GoogleModel(model=settings.ai_model, api_key=settings.ai_api_key),
      system_prompt="You are a code generator for safe numerical calculations. Only use numpy, pandas, and math.",
      tools=[codegen_tools(settings)],
      output_type=CodegenResponse,
  )
  ```
- Repeat the `/calculate/advanced`, `/calculate/advanced/execute`, and `/calculate/sql` calls with the same test cases; observe latency/quotas and logtrace.
- Compare response times: local vLLM vs Google AI Studio (document in README).

### Observability checkpoints
- Verify structured logs include:
  - LLM model name and provider
  - Token usage (if available from LLM response)
  - Request/response latency (P50, P95, P99)
  - Validation pass/fail rates by agent type
  - Refine loop: attempts distribution, convergence rate
  - Code execution time and memory usage
  - SQL path: rejected vs executed SQL count, table/column allowlist hits, DuckDB query time
  - Error rates by type (timeout, validation, execution)
- Set up alerts for:
  - Validation failure rate >20% (possible prompt drift)
  - LLM timeouts >5% of requests
  - Execution errors >10% (code generation quality issue)
  - SQL rejection spikes (>50% rejected) or DDL attempts detected
  - Memory usage >80% of limit
  - Request queue depth >50

### Streamlit Integration
Add these components to the Streamlit UI:

**CSV Upload & Analysis Tab (frontend talks only to calculator backend):**
```python
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
if uploaded_file:
    # Upload via calculator backend (which forwards to DuckDB microservice)
    response = httpx.post(f"{CALCULATOR_URL}/data/upload", files={"file": uploaded_file})
    payload = response.json()
    columns = payload["columns"]
    st.success(f"Uploaded {payload['rows']} rows")
    
    # Free-text SQL query
    query = st.text_area("What do you want to know?", 
                         "Show me average sales by region")
    if st.button("Run Analysis"):
        with st.spinner("Generating SQL..."):
            result = httpx.post(f"{CALCULATOR_URL}/calculate/sql", json={
                "prompt": query,
                "available_columns": columns
            })
        st.code(result.json()["sql"], language="sql")
        st.dataframe(result.json()["rows"])
```

**Custom Calculation Tab:**
```python
calc_prompt = st.text_area("Describe calculation", 
                           "Calculate compound annual growth rate")
if st.button("Generate Code"):
    with st.spinner("Generating and validating code..."):
        result = httpx.post(f"{CALCULATOR_URL}/calculate/advanced", json={
            "prompt": calc_prompt
        })
    
    st.subheader("Generated Code")
    st.code(result.json()["python_code"], language="python")
    
    st.subheader("Validation")
    if result.json()["validation"]["is_valid"]:
        st.success("✓ Code passed safety checks")
    else:
        st.error("✗ Validation issues: " + ", ".join(result.json()["validation"]["issues"]))
    
    if st.button("Execute"):
        exec_result = httpx.post(f"{CALCULATOR_URL}/calculate/advanced/execute", 
                                json={
                                    "python_code": result.json()["python_code"],
                                    "input_data": {}
                                })
        st.json(exec_result.json()["result"])
```

## Wrap-Up & Success Criteria
- [ ] Frontend calls only the calculator backend; calculator proxies sidecar and DuckDB.
- [ ] `/calculate/advanced` returns generated + validated code; `/calculate/advanced/execute` runs it in the sandbox with limits (refine loop capped).
- [ ] `/calculate/sql` returns SELECT-only SQL + rows from DuckDB; blocks DDL/DML.
- [ ] `/ai/codegen`, `/ai/validate/python`, `/ai/validate/sql`, `/ai/sql`, `/ai/execute` return typed payloads and log `X-Trace-Id`.
- [ ] Tests cover sidecar units, calculator-side integration, schema contracts, and UI smoke.
- [ ] README/changelog note AI usage, env vars, telemetry defaults, and safety rails.
- [ ] Local and remote LLM paths both exercised (document latency/quotas).

## Troubleshooting
- **LLM returns non-JSON** → enforce `response_format`; wrap parse in try/except and return 422 with details.
- **`403/401` from Google** → confirm `GOOGLE_API_KEY`, `GOOGLE_GEMINI_MODEL`; check quotas.
- **Local model unreachable** → `curl ${AI_BASE_URL}/v1/models`; restart LM Studio/vLLM; check firewall.
- **pytest hits real network** → use MockTransport; set `AI_API_KEY=mock`; override clients in tests.
- **Validation misses unsafe code/SQL** → tighten prompts; add regex/AST guards; reduce allowed imports/columns.
- **Code execution hangs** → lower timeout; enforce memory/CPU limits; prefer container sandbox for risky code.
- **UI bypasses backend** → audit Streamlit calls; ensure only calculator URLs are used.
- **SQL rejects valid queries** → ensure column list matches DuckDB schema; adjust default LIMIT; log rejected SQL for tuning.
