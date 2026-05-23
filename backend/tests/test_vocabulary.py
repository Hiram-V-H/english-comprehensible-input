from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["database"] == "connected"


@pytest.mark.asyncio
async def test_vocabulary_empty(client: AsyncClient):
    resp = await client.get("/api/vocabulary?per_page=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_search_vocabulary(client: AsyncClient):
    resp = await client.get("/api/vocabulary/search?q=test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_stats_empty(client: AsyncClient):
    resp = await client.get("/api/vocabulary/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_word_not_found(client: AsyncClient):
    resp = await client.get("/api/vocabulary/99999")
    assert resp.status_code == 404
