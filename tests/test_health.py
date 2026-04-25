"""Health check endpoint tests."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_health_db(client: AsyncClient):
    resp = await client.get("/health/db")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "docs" in resp.json()
