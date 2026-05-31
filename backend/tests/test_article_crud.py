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


@pytest.mark.asyncio
async def test_update_article_content_single_word(client: AsyncClient):
    """PUT /api/articles/{id}/content -- change one word, verify full regeneration."""
    resp = await client.post("/api/import/text", json={
        "title": "Content Edit Test",
        "content": "The quick brown fox jumps over the lazy dog."
    })
    assert resp.status_code == 200
    article_id = resp.json()["data"]["article_id"]

    # Edit one word: "fox" -> "cat"
    resp = await client.put(f"/api/articles/{article_id}/content", json={
        "content_text": "The quick brown cat jumps over the lazy dog."
    })
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Verify word changed in paragraphs
    words = [w["text"] for p in data["paragraphs"] for w in p["words"] if w.get("status") != "punct"]
    assert "cat" in words
    assert "fox" not in words

    # Verify annotated_html is cleared
    assert data["article"]["annotated_html"] is None

    # Verify content_text updated
    assert data["article"]["content_text"] == "The quick brown cat jumps over the lazy dog."


@pytest.mark.asyncio
async def test_update_article_content_empty_rejected(client: AsyncClient):
    """PUT with empty content_text should return 422."""
    resp = await client.post("/api/import/text", json={
        "title": "Will Edit",
        "content": "Some content."
    })
    assert resp.status_code == 200
    article_id = resp.json()["data"]["article_id"]

    resp = await client.put(f"/api/articles/{article_id}/content", json={
        "content_text": "",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_article_content_highlight_remap(client: AsyncClient):
    """Highlights should survive content edits when selected_text unchanged."""
    resp = await client.post("/api/import/text", json={
        "title": "Highlight Test",
        "content": "The quick brown fox jumps over the lazy dog."
    })
    assert resp.status_code == 200
    article_id = resp.json()["data"]["article_id"]

    # Build word positions from reader data
    reader_resp = await client.get(f"/api/reader/{article_id}")
    paragraphs = reader_resp.json()["data"]["paragraphs"]
    all_words = [w for p in paragraphs for w in p["words"]]
    # Find positions for "brown" (pos 2) and "fox" (pos 3)
    brown_word = next(w for w in all_words if w["text"] == "brown")
    fox_word = next(w for w in all_words if w["text"] == "fox")

    # Add a highlight on "brown fox"
    resp = await client.post(f"/api/articles/{article_id}/highlights", json={
        "selected_text": "brown fox",
        "start_char_offset": brown_word["char_offset"],
        "end_char_offset": fox_word["char_offset"] + len("fox"),
        "start_word_position": brown_word["position"],
        "end_word_position": fox_word["position"],
    })
    assert resp.status_code == 200

    # Edit content -- add a word before "brown"
    resp = await client.put(f"/api/articles/{article_id}/content", json={
        "content_text": "The quick big brown fox jumps over the lazy dog."
    })
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Highlight should still exist with updated offsets
    highlights = data["highlights"]
    assert len(highlights) == 1
    assert highlights[0]["selected_text"] == "brown fox"
    # Char offsets should have shifted by 4 (length of "big ")
    assert highlights[0]["start_char_offset"] == 14
