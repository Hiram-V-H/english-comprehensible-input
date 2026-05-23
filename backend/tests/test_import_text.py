import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_import_text_creates_article(client: AsyncClient):
    resp = await client.post("/api/import/text", json={
        "title": "Test Article",
        "content": "This is a simple test.\n\nIt has multiple sentences. And some words.",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["title"] == "Test Article"
    assert data["data"]["status"] == "imported"
    assert data["data"]["word_count"] > 0


@pytest.mark.anyio
async def test_import_text_duplicate_detected(client: AsyncClient):
    content = "Unique content for dedup test."
    resp1 = await client.post("/api/import/text", json={
        "title": "First",
        "content": content,
    })
    assert resp1.json()["data"]["status"] == "imported"

    resp2 = await client.post("/api/import/text", json={
        "title": "Second",
        "content": content,
    })
    assert resp2.json()["data"]["status"] == "duplicate"
