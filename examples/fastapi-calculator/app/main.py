from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class CalculationRequest(BaseModel):
    a: float
    b: float


class CalculationResponse(BaseModel):
    operation: str
    a: float
    b: float
    result: float


app = FastAPI(title="Calculator API", version="0.1.0")


def _make_response(operation: str, payload: CalculationRequest, result: float) -> CalculationResponse:
    return CalculationResponse(operation=operation, a=payload.a, b=payload.b, result=result)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/calc/add", response_model=CalculationResponse)
def add(payload: CalculationRequest) -> CalculationResponse:
    return _make_response("add", payload, payload.a + payload.b)


@app.post("/calc/subtract", response_model=CalculationResponse)
def subtract(payload: CalculationRequest) -> CalculationResponse:
    return _make_response("subtract", payload, payload.a - payload.b)


@app.post("/calc/multiply", response_model=CalculationResponse)
def multiply(payload: CalculationRequest) -> CalculationResponse:
    return _make_response("multiply", payload, payload.a * payload.b)


@app.post(
    "/calc/divide",
    response_model=CalculationResponse,
    responses={400: {"description": "Cannot divide by zero"}},
)
def divide(payload: CalculationRequest) -> CalculationResponse:
    if payload.b == 0:
        raise HTTPException(status_code=400, detail="Cannot divide by zero")
    return _make_response("divide", payload, payload.a / payload.b)
