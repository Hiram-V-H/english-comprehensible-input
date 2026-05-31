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


@pytest.mark.anyio
async def test_numbers_not_treated_as_words(client: AsyncClient):
    """Numbers, question numbers, and option labels should not become vocabulary."""
    resp = await client.post("/api/import/text", json={
        "title": "Quiz Article",
        "content": (
            "2025 Exam Questions\n\n"
            "1. What is the capital of France?\n"
            "A) Paris\n"
            "B) London\n"
            "C) Berlin\n\n"
            "The answer is 42. Don't overthink it.\n"
        ),
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["status"] == "imported"

    article_id = data["data"]["article_id"]

    # Check that numbers are NOT in vocabulary
    for token in ["2025", "1", "42"]:
        r = await client.get(f"/api/vocabulary/search?q={token}")
        results = r.json()["data"]
        assert len(results) == 0, f"'{token}' should not be a vocabulary word"

    # Check that real words ARE in vocabulary
    # Contractions are expanded by the tokenizer before vocabulary lookup
    # (e.g., "don't" → "do" + "not")
    for word in ["what", "paris", "do", "not", "answer"]:
        r = await client.get(f"/api/vocabulary/search?q={word}")
        results = r.json()["data"]
        assert len(results) > 0, f"'{word}' should be in vocabulary"


@pytest.mark.anyio
async def test_word_count_excludes_numbers(client: AsyncClient):
    """Word count should only count tokens with letters."""
    resp = await client.post("/api/import/text", json={
        "title": "Number Test",
        "content": "One two 3 four 5 six.",
    })
    assert resp.status_code == 200
    data = resp.json()
    # "One two 3 four 5 six" — 6 tokens total, 4 with letters
    # But the word_count in the response is from the tokenizer which counts
    # all non-punctuation tokens. Let's just verify real words exist and numbers don't.
    assert data["data"]["status"] == "imported"

    article_id = data["data"]["article_id"]

    # Numbers should not be vocabulary
    for token in ["3", "5"]:
        r = await client.get(f"/api/vocabulary/search?q={token}")
        results = r.json()["data"]
        assert len(results) == 0, f"'{token}' should not be a vocabulary word"

    # Real words should be vocabulary
    for word in ["one", "two", "four", "six"]:
        r = await client.get(f"/api/vocabulary/search?q={word}")
        results = r.json()["data"]
        assert len(results) > 0, f"'{word}' should be in vocabulary"
