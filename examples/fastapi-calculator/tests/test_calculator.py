from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_add_returns_result():
    response = client.post("/calc/add", json={"a": 2, "b": 3})
    assert response.status_code == 200
    assert response.json()["result"] == 5


def test_divide_by_zero_returns_400():
    response = client.post("/calc/divide", json={"a": 2, "b": 0})
    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot divide by zero"
