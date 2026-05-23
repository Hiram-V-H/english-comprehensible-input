from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.fixture
async def article_with_highlight(client: AsyncClient) -> int:
    content = b"An article for annotation testing purposes here."
    resp = await client.post(
        "/api/import/file",
        files={"file": ("anno_test.txt", content, "text/plain")},
    )
    return resp.json()["data"]["article_id"]


@pytest.mark.asyncio
async def test_create_highlight(client: AsyncClient, article_with_highlight: int):
    aid = article_with_highlight
    resp = await client.post(
        f"/api/articles/{aid}/highlights",
        json={
            "selected_text": "annotation testing",
            "start_char_offset": 12,
            "end_char_offset": 29,
            "highlight_type": "phrase",
            "color": "#FFEB3B",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_get_highlights(client: AsyncClient, article_with_highlight: int):
    aid = article_with_highlight
    # Create a highlight first
    await client.post(
        f"/api/articles/{aid}/highlights",
        json={
            "selected_text": "test",
            "start_char_offset": 12,
            "end_char_offset": 16,
            "highlight_type": "word",
            "color": "#A5D6A7",
        },
    )
    resp = await client.get(f"/api/articles/{aid}/highlights")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_create_annotation(client: AsyncClient, article_with_highlight: int):
    aid = article_with_highlight
    # Create highlight
    h_resp = await client.post(
        f"/api/articles/{aid}/highlights",
        json={
            "selected_text": "annotation",
            "start_char_offset": 0,
            "end_char_offset": 10,
            "highlight_type": "word",
            "color": "#FFEB3B",
        },
    )
    hid = h_resp.json()["data"]["id"]

    # Create annotation
    resp = await client.post(
        f"/api/highlights/{hid}/annotations",
        json={"content": "This is a test note", "annotation_type": "note"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data["data"]

    # Get annotations
    resp = await client.get(f"/api/highlights/{hid}/annotations")
    assert len(resp.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_tags(client: AsyncClient):
    # Create tag
    resp = await client.post("/api/tags", json={"name": "vocabulary", "color": "#FFEB3B"})
    assert resp.status_code == 200
    tag_id = resp.json()["data"]["id"]

    # Get tags
    resp = await client.get("/api/tags")
    assert len(resp.json()["data"]) >= 1

    # Delete tag
    resp = await client.delete(f"/api/tags/{tag_id}")
    assert resp.status_code == 200
