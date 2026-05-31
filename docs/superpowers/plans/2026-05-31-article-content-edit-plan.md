# Article Content Editing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to edit article content (fix typos) via inline word click or full-text editor, with automatic re-tokenization, highlight remapping, and analysis re-run.

**Architecture:** A single `PUT /articles/{id}/content` backend endpoint accepts the full updated `content_text`. The backend re-tokenizes, rebuilds ArticleWord rows, clears `annotated_html` (falling back to ArticleDisplay rendering), remaps highlights by searching `selected_text` in a window, and re-runs CompositeAnalyzer. Frontend sends the complete new content_text regardless of edit scope (single word or bulk).

**Tech Stack:** FastAPI + Pydantic (backend), vanilla JS SPA (frontend), SQLite + SQLAlchemy async

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/schemas/article.py` | Add `ArticleContentUpdate` schema |
| `backend/app/services/article.py` | Add `update_content()` + `_remap_highlights()` |
| `backend/app/services/reader_service.py` | Add `content_text` to reader payload |
| `backend/app/api/article.py` | Add `PUT /{id}/content` route |
| `backend/tests/test_article_crud.py` | Add 3 content edit tests |
| `frontend/js/api.js` | Add `updateArticleContent(id, text)` |
| `frontend/js/components/reader/word-inline-editor.js` | **New** — inline word editing |
| `frontend/js/components/reader/full-text-editor.js` | **New** — full-text modal editor |
| `frontend/js/components/reader/reader-toolbar.js` | Add 📝 edit content button |
| `frontend/js/pages/reader.js` | Wire editors, refresh logic, click handling |
| `frontend/css/reader.css` | Inline input + textarea styles |

---

### Task 1: Add `content_text` to reader payload

**Files:**
- Modify: `backend/app/services/reader_service.py`

- [ ] **Step 1: Add content_text to the article dict**

In `reader_service.py`, find the return statement in `assemble_reader_payload()` where the `"article"` dict is built (currently has: `id, title, word_count, difficulty_score, unknown_word_count, i_plus_one_score, annotated_html`). Add `content_text`:

Find this block:
```python
        "article": {
            "id": article.id,
            "title": article.title,
            "word_count": article.word_count,
            "difficulty_score": article.difficulty_score,
            "unknown_word_count": article.unknown_word_count,
            "i_plus_one_score": article.i_plus_one_score,
            "annotated_html": article.annotated_html,
        },
```

Add `"content_text": article.content_text,` after `"annotated_html"`:
```python
        "article": {
            "id": article.id,
            "title": article.title,
            "word_count": article.word_count,
            "difficulty_score": article.difficulty_score,
            "unknown_word_count": article.unknown_word_count,
            "i_plus_one_score": article.i_plus_one_score,
            "annotated_html": article.annotated_html,
            "content_text": article.content_text,
        },
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/reader_service.py
git commit -m "feat: include content_text in reader payload"
```

---

### Task 2: Add `ArticleContentUpdate` schema

**Files:**
- Modify: `backend/app/schemas/article.py`

- [ ] **Step 1: Add the schema class**

At the end of `backend/app/schemas/article.py`, after the `ArticleUpdate` class, add:

```python
class ArticleContentUpdate(BaseModel):
    content_text: str
```

The field is required (no `Optional`, no default) — Pydantic will automatically reject empty strings with a validation error if we add `min_length=1`:

```python
from pydantic import Field

class ArticleContentUpdate(BaseModel):
    content_text: str = Field(..., min_length=1)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/article.py
git commit -m "feat: add ArticleContentUpdate schema"
```

---

### Task 3: Implement `update_content` service with highlight remapping

**Files:**
- Modify: `backend/app/services/article.py`

- [ ] **Step 1: Add imports at top of article.py**

Add these imports (some may already exist):
```python
import hashlib
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.annotation import Highlight
from ..models.article import Article, ArticleWord
from ..models.word import Word
from ..services.tokenizer import tokenize
from ..analysis.composite import CompositeAnalyzer
```

- [ ] **Step 2: Add `update_content()` function**

Add before the `delete_article` function:

```python
async def update_content(db: AsyncSession, article_id: int, new_text: str) -> dict:
    """Replace article content_text, re-tokenize, remap highlights, re-analyze."""
    from ..services.reader_service import assemble_reader_payload

    article = await get_article(db, article_id)

    # Validate
    if not new_text or not new_text.strip():
        raise ValueError("Content text cannot be empty")

    # Dedup check
    new_hash = hashlib.sha256(new_text.encode()).hexdigest()
    existing = await db.execute(
        select(Article).where(Article.sha256_hash == new_hash, Article.id != article_id)
    )
    if existing.scalar_one_or_none():
        raise ValueError("Another article with identical content already exists")

    # Save old highlights before deleting ArticleWords
    old_highlights = (await db.execute(
        select(Highlight).where(Highlight.article_id == article_id)
    )).scalars().all()

    # Update article
    article.content_text = new_text
    article.sha256_hash = new_hash
    article.annotated_html = None  # fall back to ArticleDisplay rendering

    # Delete old ArticleWords
    await db.execute(
        select(ArticleWord).where(ArticleWord.article_id == article_id)
    )
    old_words = (await db.execute(
        select(ArticleWord).where(ArticleWord.article_id == article_id)
    )).scalars().all()
    for aw in old_words:
        await db.delete(aw)
    await db.flush()

    # Re-tokenize and insert new ArticleWords
    tokens = tokenize(new_text)
    word_count = 0
    for tok in tokens:
        # Look up word in vocabulary
        word_result = await db.execute(
            select(Word).where(Word.word_lower == tok.text.lower())
        )
        word = word_result.scalar_one_or_none()

        aw = ArticleWord(
            article_id=article_id,
            word_id=word.id if word else None,
            word_text=tok.text,
            word_lower=tok.text.lower(),
            position=tok.position,
            sentence_index=tok.sentence_index,
            is_punctuation=tok.is_punctuation,
            is_unknown_at_import=None,
        )
        db.add(aw)
        if not tok.is_punctuation:
            word_count += 1

    article.word_count = word_count
    await db.flush()

    # Remap highlights
    new_article_words = (await db.execute(
        select(ArticleWord).where(ArticleWord.article_id == article_id).order_by(ArticleWord.position)
    )).scalars().all()
    await _remap_highlights(db, old_highlights, new_text, new_article_words)

    await db.flush()

    # Re-run analysis
    analyzer = CompositeAnalyzer()
    await analyzer.analyze_and_persist(article_id, db)

    await db.commit()

    # Return fresh reader payload
    return await assemble_reader_payload(db, article_id)
```

- [ ] **Step 3: Add `_remap_highlights()` helper function**

Add before `update_content`:

```python
async def _remap_highlights(
    db: AsyncSession,
    old_highlights: List[Highlight],
    new_text: str,
    new_article_words: List[ArticleWord],
) -> None:
    """Remap highlight character offsets and word positions after content edit."""
    for hl in old_highlights:
        old_start = hl.start_char_offset or 0
        old_end = hl.end_char_offset or 0
        selected = hl.selected_text

        # Search window: 50 chars around old position
        window_start = max(0, old_start - 50)
        window_end = min(len(new_text), old_end + 50)
        search_region = new_text[window_start:window_end]

        found_at = search_region.find(selected)

        if found_at == -1:
            # Selected text is gone — delete the highlight
            await db.delete(hl)
            continue

        new_start = window_start + found_at
        new_end = new_start + len(selected)

        # Find word positions that overlap [new_start, new_end)
        start_pos = None
        end_pos = None
        for aw in new_article_words:
            # Reconstruct char offset for this word
            aw_start = _word_char_offset(new_article_words, aw.position)
            aw_end = aw_start + len(aw.word_text)
            if aw_start <= new_start < aw_end and start_pos is None:
                start_pos = aw.position
            if aw_start < new_end <= aw_end:
                end_pos = aw.position
            elif new_end <= aw_start and end_pos is None:
                end_pos = aw.position - 1 if aw.position > 0 else 0

        hl.start_char_offset = new_start
        hl.end_char_offset = new_end
        hl.start_word_position = start_pos if start_pos is not None else hl.start_word_position
        hl.end_word_position = end_pos if end_pos is not None else hl.end_word_position


def _word_char_offset(article_words: List[ArticleWord], position: int) -> int:
    """Compute char_offset for a single word position."""
    offset = 0
    for i, aw in enumerate(article_words):
        if aw.position == position:
            return offset
        offset += len(aw.word_text)
        if i < len(article_words) - 1:
            next_aw = article_words[i + 1]
            if not next_aw.is_punctuation:
                offset += 1
    return 0
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/article.py
git commit -m "feat: add update_content service with highlight remapping"
```

---

### Task 4: Add `PUT /{id}/content` endpoint

**Files:**
- Modify: `backend/app/api/article.py`

- [ ] **Step 1: Add import and route**

Add the import at top:
```python
from ..schemas.article import ArticleContentUpdate, ArticleDetail, ArticleSummary, ArticleUpdate
```

Add the route after the existing `PATCH /{article_id}` route:

```python
@router.put("/{article_id}/content")
async def update_article_content(article_id: int, data: ArticleContentUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await article_service.update_content(db, article_id, data.content_text)
        return {"status": "ok", "data": result}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/article.py
git commit -m "feat: add PUT /articles/{id}/content endpoint"
```

---

### Task 5: Write backend tests

**Files:**
- Modify: `backend/tests/test_article_crud.py`

- [ ] **Step 1: Add the three test functions**

Append to `backend/tests/test_article_crud.py`:

```python
@pytest.mark.asyncio
async def test_update_article_content_single_word(client: AsyncClient):
    """PUT /api/articles/{id}/content — change one word, verify full regeneration."""
    resp = await client.post("/api/import/text", json={
        "title": "Content Edit Test",
        "content": "The quick brown fox jumps over the lazy dog."
    })
    assert resp.status_code == 200
    article_id = resp.json()["data"]["id"]

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
    article_id = resp.json()["data"]["id"]

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
    article_id = resp.json()["data"]["id"]

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

    # Edit content — add a word before "brown"
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
```

- [ ] **Step 2: Run tests**

```bash
cd backend && python -m pytest tests/test_article_crud.py -v
```

Expected: All 7 tests pass (4 existing + 3 new).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_article_crud.py
git commit -m "test: add content edit and highlight remap tests"
```

---

### Task 6: Add `updateArticleContent` to frontend API

**Files:**
- Modify: `frontend/js/api.js`

- [ ] **Step 1: Add the function**

Add to the `api` export object, after `updateArticle`:

```javascript
    updateArticleContent: (id, contentText) => request('PUT', `/articles/${id}/content`, { content_text: contentText }),
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/api.js
git commit -m "feat: add updateArticleContent API function"
```

---

### Task 7: Create `WordInlineEditor` component

**Files:**
- Create: `frontend/js/components/reader/word-inline-editor.js`

- [ ] **Step 1: Write the component**

Create `frontend/js/components/reader/word-inline-editor.js`:

```javascript
import { el } from '../../utils/dom.js';

/**
 * Inline word editor — click a word to edit it in-place.
 * Usage:
 *   const editor = new WordInlineEditor(readerContainer);
 *   editor.open(wordSpan, wordData, contentText, async (newContentText) => {
 *       // save and refresh
 *   });
 */
export class WordInlineEditor {
    constructor(container) {
        this._container = container;
        this._input = null;
        this._originalSpan = null;
        this._originalWordData = null;
        this._resolve = null;
    }

    /**
     * Open inline editor on a word span.
     * @param {HTMLSpanElement} span — the [data-position] span clicked
     * @param {Object} wordData — { text, char_offset, position }
     * @param {string} contentText — full article content_text
     * @returns {Promise<{newText: string, newContentText: string}|null>}
     */
    open(span, wordData, contentText) {
        this.close(); // close any existing

        this._originalSpan = span;
        this._originalWordData = wordData;

        return new Promise((resolve) => {
            this._resolve = resolve;

            // Replace span text with input
            const input = el('input', {
                type: 'text',
                className: 'word-inline-input',
                value: wordData.text,
                onKeydown: (e) => {
                    if (e.key === 'Enter') this._save(contentText, wordData);
                    if (e.key === 'Escape') this._cancel();
                },
                onBlur: () => {
                    // Small delay so Enter/Escape handlers fire first
                    setTimeout(() => {
                        if (this._input) this._save(contentText, wordData);
                    }, 150);
                },
            });

            // Size the input to fit the word
            input.style.minWidth = Math.max(60, span.offsetWidth + 10) + 'px';

            // Replace span content with input
            span.textContent = '';
            span.appendChild(input);
            this._input = input;

            // Focus and select
            input.focus();
            input.select();
        });
    }

    _replaceWord(contentText, charOffset, oldWord, newWord) {
        const slice = contentText.substring(charOffset, charOffset + oldWord.length);
        if (slice !== oldWord) {
            return null; // text changed concurrently
        }
        return contentText.substring(0, charOffset) + newWord + contentText.substring(charOffset + oldWord.length);
    }

    _save(contentText, wordData) {
        if (!this._input) return;
        const newWord = this._input.value.trim();
        this._cleanup();
        if (!newWord || newWord === wordData.text) {
            this._resolve(null);
            return;
        }
        const newContentText = this._replaceWord(contentText, wordData.char_offset, wordData.text, newWord);
        if (newContentText === null) {
            this._resolve(null);
            return;
        }
        this._resolve({ newWord, newContentText });
    }

    _cancel() {
        this._restoreSpan();
        this._cleanup();
        this._resolve(null);
    }

    _restoreSpan() {
        if (this._originalSpan && this._originalWordData) {
            this._originalSpan.textContent = this._originalWordData.text;
        }
    }

    _cleanup() {
        if (this._input) {
            this._input.remove();
            this._input = null;
        }
    }

    close() {
        this._cleanup();
        if (this._resolve) {
            this._resolve(null);
            this._resolve = null;
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/components/reader/word-inline-editor.js
git commit -m "feat: add inline word editor component"
```

---

### Task 8: Create `FullTextEditor` component

**Files:**
- Create: `frontend/js/components/reader/full-text-editor.js`

- [ ] **Step 1: Write the component**

Create `frontend/js/components/reader/full-text-editor.js`:

```javascript
import { el } from '../../utils/dom.js';
import { showModal } from '../shared/modal.js';

/**
 * Open a full-text editor modal.
 * @param {string} contentText — current article content_text
 * @returns {Promise<string|null>} — new content_text or null if cancelled
 */
export async function showFullTextEditor(contentText) {
    const textarea = el('textarea', {
        className: 'full-text-editor',
        value: contentText,
        rows: 20,
    });

    const bodyEl = el('div', { className: 'modal-body' }, [textarea]);

    const result = await showModal('📝 编辑正文', bodyEl, [
        { label: '取消', value: false },
        { label: '保存修改', value: 'save', primary: true },
    ]);

    if (result !== 'save') return null;

    const newText = textarea.value.trim();
    if (!newText) return null;
    if (newText === contentText) return null;

    return newText;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/components/reader/full-text-editor.js
git commit -m "feat: add full-text editor modal component"
```

---

### Task 9: Update reader toolbar — add edit content button

**Files:**
- Modify: `frontend/js/components/reader/reader-toolbar.js`

- [ ] **Step 1: Add setter and button**

In the constructor (find `this._onEdit` and `this._onDelete`), add:
```javascript
        this._onEditContent = null;
```

Add setter alongside the existing ones:
```javascript
    setOnEditContent(cb) { this._onEditContent = cb; }
```

In `render()`, find the edit (✎) and delete (🗑) buttons. After the delete button, add:

```javascript
        // Edit content button
        const editContentBtn = el('button', {
            className: 'toolbar-btn',
            title: '编辑正文',
            textContent: '📝',
            onClick: () => { if (this._onEditContent) this._onEditContent(); },
        });
        toolbar.appendChild(editContentBtn);
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/components/reader/reader-toolbar.js
git commit -m "feat: add edit content button to reader toolbar"
```

---

### Task 10: Update reader.js — wire editors, refresh, click handling

**Files:**
- Modify: `frontend/js/pages/reader.js`

- [ ] **Step 1: Add imports**

Add at the top (near existing component imports):
```javascript
import { WordInlineEditor } from '../components/reader/word-inline-editor.js';
import { showFullTextEditor } from '../components/reader/full-text-editor.js';
```

- [ ] **Step 2: Initialize WordInlineEditor and wire toolbar**

Find where `new ReaderToolbar` is created and callbacks are set. Add after `setOnDelete`:

```javascript
    // Init inline editor
    const inlineEditor = new WordInlineEditor(readerContent);

    // Wire toolbar
    toolbar.setOnEdit(() => handleEditArticle(readerData.article));
    toolbar.setOnDelete(() => handleDeleteArticle(readerData.article));
    toolbar.setOnEditContent(() => handleEditContent());
```

- [ ] **Step 3: Add click handler for inline word editing**

Find where click handlers are attached to `readerContent`. If no existing click delegation, add:

```javascript
    // Click-to-edit: detect clicks on word spans
    readerContent.addEventListener('click', (e) => {
        const span = e.target.closest('[data-position]');
        if (!span) return;

        const position = parseInt(span.dataset.position, 10);
        if (isNaN(position)) return;

        // Find word data
        let wordData = null;
        for (const para of readerData.paragraphs) {
            const found = para.words.find(w => w.position === position);
            if (found) { wordData = found; break; }
        }
        if (!wordData || wordData.status === 'punct') return;

        // Prevent if already editing
        // The WordInlineEditor handles this internally

        // Open inline editor
        inlineEditor.open(span, wordData, readerData.article.content_text).then(async (result) => {
            if (!result) return;
            try {
                const newPayload = await api.updateArticleContent(readerData.article.id, result.newContentText);
                refreshReader(newPayload);
                showToast('已更新正文', 'success');
            } catch (err) {
                showToast('更新失败，请重试', 'error');
            }
        });
    });
```

- [ ] **Step 4: Add handleEditContent and refreshReader functions**

Add inside the async IIFE, near the other handler functions:

```javascript
    async function handleEditContent() {
        const newText = await showFullTextEditor(readerData.article.content_text);
        if (!newText) return;
        try {
            const newPayload = await api.updateArticleContent(readerData.article.id, newText);
            refreshReader(newPayload);
            showToast('已更新正文', 'success');
        } catch (err) {
            showToast('更新失败，请重试', 'error');
        }
    }

    function refreshReader(newPayload) {
        const scrollTop = window.scrollY;

        readerData = newPayload;

        // Re-render content
        if (readerData.article.annotated_html) {
            contentRenderer.render(readerData.article.annotated_html);
            applyWordAnnotations(readerContent, readerData.paragraphs);
        } else {
            // Fallback to ArticleDisplay
            articleDisplay.render(readerData.paragraphs, readerContent);
        }

        // Re-apply highlights
        highlightOverlay.clear();
        if (readerData.highlights) {
            readerData.highlights.forEach(h => highlightOverlay.addHighlight(h));
        }

        // Re-initialize popup and selection
        wordPopup.detach();
        selectionHandler.detach();
        wordPopup = new WordPopup(readerContent, async (wordId, status) => {
            await api.updateWord(wordId, { status });
        });
        selectionHandler = new SelectionHandler(readerContent, readerData.article.id, readerData.paragraphs);
        selectionHandler.setOnHighlightCreated((hl) => highlightOverlay.addHighlight(hl));

        // Restore scroll
        window.scrollTo(0, Math.min(scrollTop, document.body.scrollHeight));
    }
```

- [ ] **Step 5: Commit**

```bash
git add frontend/js/pages/reader.js
git commit -m "feat: wire inline word editor and full-text editor to reader"
```

---

### Task 11: Add CSS styles

**Files:**
- Modify: `frontend/css/reader.css`

- [ ] **Step 1: Add styles**

Add at the end of `frontend/css/reader.css`:

```css
/* Inline word editor */
.word-inline-input {
    font: inherit;
    font-size: inherit;
    font-family: inherit;
    border: 1px solid var(--color-accent);
    border-radius: 3px;
    padding: 1px 4px;
    background: var(--color-surface);
    color: var(--color-text);
    outline: none;
}
.word-inline-input:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px var(--color-accent-light);
}

/* Full-text editor */
.full-text-editor {
    width: 100%;
    min-height: 400px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 14px;
    line-height: 1.6;
    padding: 12px;
    border: 1px solid var(--color-border);
    border-radius: 6px;
    resize: vertical;
    background: var(--color-bg);
    color: var(--color-text);
    box-sizing: border-box;
}
.full-text-editor:focus {
    outline: none;
    border-color: var(--color-primary);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/reader.css
git commit -m "style: add inline word editor and full-text editor styles"
```

---

### Task 12: End-to-end verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: All tests pass (~76 tests: 73 existing + 3 new).

- [ ] **Step 2: Start dev server and manually verify**

```bash
cd backend && python -m uvicorn app.main:app --reload
```

Checklist:
- [ ] Open an article in reader → click a word → inline input appears
- [ ] Type corrected word → press Enter → page refreshes with new word
- [ ] Click 📝 in toolbar → full-text editor modal opens
- [ ] Edit text → save → page refreshes with new content
- [ ] Verify word stats update (unknown word count may change)
- [ ] Verify existing highlights survive (if highlighted text wasn't edited)
- [ ] Verify dark theme: inline input and textarea look correct
- [ ] Mobile: inline editor works on touch

- [ ] **Step 3: Commit any fixes if needed**

---

## Task Execution Order

Tasks 1-5 (backend) must run sequentially: 1 → 2 → 3 → 4 → 5.
Tasks 6-11 (frontend) depend on Task 5 completing first, but are independent of each other: 6, 7, 8, 9 can run in parallel; 10 depends on 7, 8, 9; 11 is independent.
Task 12 always runs last.

Recommended: 1 → 2 → 3 → 4 → 5 → (6, 7, 8, 9 in parallel) → 10 → 11 → 12
