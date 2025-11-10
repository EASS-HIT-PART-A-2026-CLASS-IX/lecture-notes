# FastAPI Calculator Example

This folder holds a deliberately tiny FastAPI project that exposes a JSON calculator API. Use it as a reference when Session 03 feels abstract—you can run it locally in seconds (with Python 3.12) and the same code will build into a Docker image.

## Prerequisites
- [`uv`](https://github.com/astral-sh/uv) 0.8+ installed globally.
- Python 3.12 runtime available to `uv`. Install once if needed:
  ```bash
  uv python install 3.12.9
  ```

## Run locally with uv
1. `cd examples/fastapi-calculator`
2. `uv venv --python 3.12 && source .venv/bin/activate` (any Python 3.12+ virtualenv works)
3. `uv pip install -r requirements.txt` (or `pip install -r requirements.txt`)
4. `uv run uvicorn app.main:app --reload`

### Swagger / OpenAPI
FastAPI auto-generates an OpenAPI schema and serves “Swagger UI” at `/docs`. It is a browser-based client you can use to:
- Inspect every route, its parameters, and example payloads.
- Send live requests without leaving the browser (perfect for demos).
- View the exact request/response schemas that tools like Schemathesis can reuse.

Visit <http://127.0.0.1:8000/docs>, expand `/calc/add`, fill in the JSON body, and hit “Execute” to see the round trip.

Example `curl` request:

```bash
curl -X POST http://127.0.0.1:8000/calc/add \
  -H 'Content-Type: application/json' \
  -d '{"a": 20, "b": 5}'
```

## Run the tests (pytest + FastAPI TestClient)
```bash
uv run pytest tests -q
```
`tests/test_calculator.py` uses FastAPI’s `TestClient` to exercise `/calc/add` and the divide-by-zero guard.

## Bonus: httpx smoke test
`tests/test_httpx_client.py` shows how to call the app with `httpx.AsyncClient` plus `ASGITransport`, so you can fire requests without starting a server:

```python
import httpx

transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
    response = await client.post("/calc/add", json={"a": 1, "b": 4})
```

## Build and run with Docker
```bash
docker build -t calculator-api .
docker run --rm -p 8000:8000 calculator-api
```

The container uses `python:3.12-slim` and launches `uvicorn app.main:app`, so the exact same routes are reachable at <http://127.0.0.1:8000> after the container starts.
