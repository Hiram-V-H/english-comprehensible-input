from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_import_txt(client: AsyncClient):
    content = b"The quick brown fox jumps over the lazy dog."
    resp = await client.post(
        "/api/import/file",
        files={"file": ("test.txt", content, "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["data"]["status"] == "imported"
    assert data["data"]["word_count"] == 9


@pytest.mark.asyncio
async def test_import_duplicate(client: AsyncClient):
    content = b"The quick brown fox jumps over the lazy dog."
    # First import
    await client.post(
        "/api/import/file",
        files={"file": ("test2.txt", content, "text/plain")},
    )
    # Duplicate import
    resp = await client.post(
        "/api/import/file",
        files={"file": ("test2_dup.txt", content, "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["status"] == "duplicate"


@pytest.mark.asyncio
async def test_articles_list(client: AsyncClient):
    # Import an article first
    await client.post(
        "/api/import/file",
        files={"file": ("article.txt", b"Hello world.", "text/plain")},
    )
    resp = await client.get("/api/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["total"] >= 1


@pytest.mark.asyncio
async def test_import_markdown(client: AsyncClient):
    md = b"---\ntitle: Test MD\n---\n\n# Hello\n\nThis is a **test** article.\n\nIt has two paragraphs."
    resp = await client.post(
        "/api/import/file",
        files={"file": ("test.md", md, "text/markdown")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["status"] == "imported"
