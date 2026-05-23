from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analysis_after_import(client: AsyncClient):
    # Import article
    content = b"The cat sat on the mat. It was a sunny day."
    resp = await client.post(
        "/api/import/file",
        files={"file": ("analysis_test.txt", content, "text/plain")},
    )
    article_id = resp.json()["data"]["article_id"]

    # Get analysis
    resp = await client.get(f"/api/articles/{article_id}/analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    analysis = data["data"]
    assert analysis["article_id"] == article_id
    assert analysis["word_count"] is not None
    assert analysis["unknown_word_count"] is not None


@pytest.mark.asyncio
async def test_reanalyze(client: AsyncClient):
    content = b"A simple test article for reanalysis."
    resp = await client.post(
        "/api/import/file",
        files={"file": ("reanalyze_test.txt", content, "text/plain")},
    )
    article_id = resp.json()["data"]["article_id"]

    resp = await client.post(f"/api/articles/{article_id}/analysis/reanalyze")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data["data"]
    assert len(data["data"]["results"]) > 0


@pytest.mark.asyncio
async def test_reader_data(client: AsyncClient):
    content = b"A reader test article. It has some words."
    resp = await client.post(
        "/api/import/file",
        files={"file": ("reader_test.txt", content, "text/plain")},
    )
    article_id = resp.json()["data"]["article_id"]

    resp = await client.get(f"/api/reader/{article_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "article" in data["data"]
    assert "paragraphs" in data["data"]
    assert "stats" in data["data"]
    assert data["data"]["paragraphs"][0]["words"][0]["char_offset"] is not None
