import asyncio

import httpx

from app.main import app


async def _call_add() -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        return await client.post("/calc/add", json={"a": 1, "b": 4})


def test_httpx_can_call_add_endpoint():
    response = asyncio.run(_call_add())
    assert response.status_code == 200
    assert response.json()["result"] == 5
