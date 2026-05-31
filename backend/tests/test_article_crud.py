import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_article_exam_metadata(client: AsyncClient):
    """PATCH /api/articles/{id} with exam fields should persist them."""
    # Create an article first via text import
    resp = await client.post("/api/import/text", json={
        "title": "Test Article",
        "content": "This is a test article for exam metadata editing."
    })
    assert resp.status_code == 200
    article_id = resp.json()["data"]["article_id"]

    # Update exam metadata
    resp = await client.patch(f"/api/articles/{article_id}", json={
        "exam_type": "考研英语",
        "exam_year": 2024,
        "question_type": "阅读理解",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["exam_type"] == "考研英语"
    assert data["exam_year"] == 2024
    assert data["question_type"] == "阅读理解"


@pytest.mark.asyncio
async def test_update_article_partial_fields(client: AsyncClient):
    """PATCH with partial fields should only update specified fields."""
    resp = await client.post("/api/import/text", json={
        "title": "Original Title",
        "content": "Some content here for partial update test."
    })
    assert resp.status_code == 200
    article_id = resp.json()["data"]["article_id"]

    # Update only title, leave exam fields unchanged
    resp = await client.patch(f"/api/articles/{article_id}", json={
        "title": "Updated Title",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "Updated Title"
    # Exam fields should still be None (or not present)
    assert data.get("exam_type") is None
    assert data.get("exam_year") is None


@pytest.mark.asyncio
async def test_delete_article_cascade(client: AsyncClient):
    """DELETE /api/articles/{id} should return 200 and article should be gone."""
    resp = await client.post("/api/import/text", json={
        "title": "To Be Deleted",
        "content": "This article will be deleted."
    })
    assert resp.status_code == 200
    article_id = resp.json()["data"]["article_id"]

    # Delete
    resp = await client.delete(f"/api/articles/{article_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Verify gone
    resp = await client.get(f"/api/articles/{article_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_article(client: AsyncClient):
    """DELETE /api/articles/{id} for nonexistent id should return 404."""
    resp = await client.delete("/api/articles/99999")
    assert resp.status_code == 404
