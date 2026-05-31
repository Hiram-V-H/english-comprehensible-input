# Article Content Editing — Design Spec

**Date:** 2026-05-31  
**Scope:** Phase 2 — Word-level and full-text content editing for articles

---

## Goals

Users want to fix typos and word errors in article content directly from the reader page, without re-importing. Two editing modes: click-to-edit a single word inline, or open a full-text editor for batch fixes.

---

## Approach: Full content_text replacement + ArticleDisplay fallback

The frontend always sends the complete updated `content_text` to the backend (whether a single word or multiple words were changed). The backend re-tokenizes, rebuilds ArticleWord records, clears `annotated_html` (falling back to ArticleDisplay rendering), remaps highlights, and re-runs analysis.

**Why clear annotated_html:** Regenerating `annotated_html` requires matching tokens against `content_html` via `inject_word_spans()`. When `content_text` changes but `content_html` is stale, the matching fails. Clearing `annotated_html` causes the reader to use `ArticleDisplay`, which builds word spans dynamically from the new paragraphs data. The visual difference is minimal — both paths render words with `[data-position]` spans. Most imported articles (txt, md) already lack `annotated_html` and use this path.

**Post-edit rendering:** Articles edited this way lose rich HTML structure (headings, bold, italic, lists from EPUB). For the primary use case (fixing typos in English learning materials), this trade-off is acceptable. A future enhancement could make HTML-aware word replacement.

---

## Backend Changes

### 0. Reader payload addition: `content_text`

**File:** `backend/app/services/reader_service.py`

The reader payload currently does NOT include `content_text` in the `article` object. Add it so the frontend can perform word replacement locally:

```python
# In assemble_reader_payload(), add to the article dict:
"content_text": article.content_text,
```

This also enables the frontend to detect if the article was modified since loading (compare stored `content_text` with the current value before applying an inline edit).

**File:** `backend/app/api/article.py`

```python
@router.put("/{article_id}/content")
async def update_article_content(article_id: int, data: ArticleContentUpdate, db: AsyncSession = Depends(get_db)):
    result = await article_service.update_content(db, article_id, data.content_text)
    return {"status": "ok", "data": result}
```

### 2. New schema: `ArticleContentUpdate`

**File:** `backend/app/schemas/article.py`

```python
class ArticleContentUpdate(BaseModel):
    content_text: str  # required, non-empty
```

### 3. New service: `update_content()`

**File:** `backend/app/services/article.py`

Processing pipeline:

1. **Validate** — `content_text` must be non-empty (400 if empty)
2. **Dedup check** — compute `sha256(content_text)`. If another article already has this hash (excluding current article), return 409 Conflict.
3. **Update article** — set `article.content_text = new_text`, `article.sha256_hash = new_hash`, `article.annotated_html = None`, `article.updated_at = now`
4. **Rebuild ArticleWords** — delete all existing `ArticleWord` rows for this article. Re-tokenize `content_text` via `tokenizer.tokenize()`. Bulk-insert new `ArticleWord` rows with updated `position`, `word_text`, `word_lower`, `sentence_index`, `is_punctuation`, `char_offset` (computed by tokenizer).
5. **Update word_count** — `article.word_count = count of tokens where is_punctuation == False`
6. **Remap highlights** — see highlight remapping section below
7. **Re-run analysis** — instantiate `CompositeAnalyzer` and run `analyze_and_persist(db, article_id)`. This updates `unknown_word_count`, `unknown_word_density`, `i_plus_one_score`, `difficulty_score`, and `ArticleWord.is_unknown_at_import`.
8. **Commit** — single `db.commit()` at the end
9. **Return** — call `reader_service.assemble_reader_payload(db, article_id)` and return the complete reader payload (same format as `GET /reader/{id}`)

### 4. Highlight remapping algorithm

**File:** `backend/app/services/article.py` (private function `_remap_highlights()`)

For each `Highlight` belonging to the article:

1. Retrieve `highlight.selected_text`, `highlight.start_char_offset` (old), `highlight.end_char_offset` (old)
2. Define search window: `[max(0, old_start - 50), min(len(new_text), old_end + 50)]`
3. Search for `selected_text` within the window in the new `content_text`
4. **If found (single match):**
   - Update `highlight.start_char_offset = found_index`
   - Update `highlight.end_char_offset = found_index + len(selected_text)`
   - Query new ArticleWords to find which positions overlap `[found_index, found_index + len(selected_text))` — set `start_word_position` and `end_word_position`
5. **If found (multiple matches):** pick the match closest to the old `start_char_offset`
6. **If not found:** the highlighted text was edited. Delete the highlight (and its cascade annotations).

Edge case: opening punctuation or trailing whitespace in `selected_text` — the search uses exact string matching, so `selected_text` must appear verbatim in the new content.

### 5. Tokenizer adjustment

The existing tokenizer computes `char_offset` as `m.start()` from regex matching. No changes needed — it works on any plain text. The key is that `_compute_char_offsets()` in `reader_service.py` will reconstruct offsets correctly from the new ArticleWords since it walks them in position order.

### 6. Tests

**File:** `backend/tests/test_article_crud.py` (add to existing)

```python
@pytest.mark.asyncio
async def test_update_article_content_single_word(client: AsyncClient):
    """PUT /api/articles/{id}/content — change one word, verify full regeneration."""
    # Create article
    resp = await client.post("/api/import/text", json={
        "title": "Content Edit Test",
        "content": "The quick brown fox jumps over the lazy dog."
    })
    article_id = resp.json()["data"]["id"]

    # Edit one word
    resp = await client.put(f"/api/articles/{article_id}/content", json={
        "content_text": "The quick brown cat jumps over the lazy dog."
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Verify word changed in paragraphs
    words = [w["text"] for p in data["paragraphs"] for w in p["words"] if not w.get("is_punctuation")]
    assert "cat" in words
    assert "fox" not in words


@pytest.mark.asyncio
async def test_update_article_content_empty_rejected(client: AsyncClient):
    """PUT with empty content_text should return 422 or 400."""
    resp = await client.post("/api/import/text", json={
        "title": "Will Edit",
        "content": "Some content."
    })
    article_id = resp.json()["data"]["id"]
    resp = await client.put(f"/api/articles/{article_id}/content", json={
        "content_text": "",
    })
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_update_article_content_highlight_remap(client: AsyncClient):
    """Highlights should survive content edits when selected_text unchanged."""
    # Create article and add a highlight
    resp = await client.post("/api/import/text", json={
        "title": "Highlight Test",
        "content": "The quick brown fox jumps over the lazy dog."
    })
    article_id = resp.json()["data"]["id"]

    # Add a highlight on "brown fox"
    resp = await client.post(f"/api/articles/{article_id}/highlights", json={
        "selected_text": "brown fox",
        "start_char_offset": 10,
        "end_char_offset": 19,
        "start_word_position": 2,
        "end_word_position": 4,
    })
    assert resp.status_code == 200
    highlight_id = resp.json()["data"]["id"]

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
    assert highlights[0]["end_char_offset"] == 23
```

---

## Frontend Changes

### File change summary

| File | Change |
|------|--------|
| `frontend/js/api.js` | Add `updateArticleContent(id, contentText)` function |
| `frontend/js/pages/reader.js` | Add inline word editor, full-text editor button, toolbar button, refresh logic |
| `frontend/js/components/reader/reader-toolbar.js` | Add "编辑正文" button |
| `frontend/js/components/reader/word-inline-editor.js` | **New** — inline word editing component |
| `frontend/js/components/reader/full-text-editor.js` | **New** — full-text editing modal |
| `frontend/css/reader.css` | Inline editor input style, full-text editor textarea style |

### 1. API module (`api.js`)

```javascript
updateArticleContent: (id, contentText) => request('PUT', `/articles/${id}/content`, { content_text: contentText }),
```

### 2. Inline word editor (`components/reader/word-inline-editor.js`)

A `WordInlineEditor` class:

```javascript
export class WordInlineEditor {
    constructor(container, onSave)
    // container: the reader content DOM element
    // onSave(newContentText): called with full updated content_text

    open(spanElement, wordData, fullContentText)
    // spanElement: the [data-position] span that was clicked
    // wordData: { position, text, char_offset, word_lower }
    // fullContentText: the current article.content_text
    
    close()
    // Remove the inline input, restore the span
}
```

Behavior:
- Click a word span → hide the span text, show an `<input>` at the same position
- Input inherits the span's font size/family via CSS
- Width auto-sizes to fit the current word (min-width matches original word width)
- Enter or blur → replace word in fullContentText at char_offset, call onSave
- Escape → close without saving
- Only operates on non-punctuation words (`[data-position]` spans that are not punctuation)

**Word replacement logic (in reader.js, not the component):**

```javascript
function replaceWordInContent(contentText, charOffset, oldWord, newWord) {
    // Verify the word at charOffset matches oldWord
    const slice = contentText.substring(charOffset, charOffset + oldWord.length);
    if (slice !== oldWord) {
        showToast('文本已变更，请刷新后重试', 'error');
        return null;
    }
    return contentText.substring(0, charOffset) + newWord + contentText.substring(charOffset + oldWord.length);
}
```

### 3. Full-text editor (`components/reader/full-text-editor.js`)

A `showFullTextEditor(contentText)` function:

- Opens a modal with a large `<textarea>` (monospace font, ~20 rows)
- Pre-filled with the current `content_text`
- Save button → calls `onSave(newContentText)`
- Cancel button → closes modal
- Uses existing `showModal()` pattern but with a custom body containing the textarea

### 4. Reader page changes (`pages/reader.js`)

**Toolbar button:** Add "编辑正文" button to `ReaderToolbar` (alongside existing ✎ and 🗑).

**Inline editing:**
- Add click handler on the reader content area
- If click target is a `[data-position]` span and the word is not punctuation:
  - Open `WordInlineEditor` at that span
  - On save: call `replaceWordInContent()` → `api.updateArticleContent()` → refresh reader

**Refresh after edit:**
```javascript
async function refreshReader(newPayload) {
    readerData = newPayload;
    // Re-render content
    if (newPayload.article.annotated_html) {
        contentRenderer.render(newPayload.article.annotated_html);
        applyWordAnnotations(readerContent, newPayload.paragraphs);
    } else {
        articleDisplay.render(newPayload.paragraphs, readerContent);
    }
    // Re-apply highlights
    highlightOverlay.clear();
    newPayload.highlights.forEach(h => highlightOverlay.addHighlight(h));
    // Re-initialize word popup and selection handler
    // ...
}
```

**Scroll position preservation:**
- Before refresh, record `window.scrollY` (or the reader content scroll position)
- After refresh, restore scroll position
- If the edit changed text length significantly, scroll may be slightly off — acceptable

### 5. Toolbar changes (`reader-toolbar.js`)

Add setter and button:
```javascript
setOnEditContent(cb) { this._onEditContent = cb; }

// In render(), add after the metadata edit/delete buttons:
const editContentBtn = el('button', {
    className: 'toolbar-btn',
    title: '编辑正文',
    textContent: '📝',
    onClick: () => { if (this._onEditContent) this._onEditContent(); },
});
```

### 6. CSS additions (`reader.css`)

```css
/* Inline word editor */
.word-inline-input {
    font: inherit;
    border: 1px solid var(--color-accent);
    border-radius: 3px;
    padding: 1px 4px;
    background: var(--color-surface);
    color: var(--color-text);
    outline: none;
    min-width: 60px;
}
.word-inline-input:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px var(--color-accent-light);
}

/* Full-text editor */
.full-text-editor {
    width: 100%;
    min-height: 400px;
    font-family: 'Courier New', monospace;
    font-size: 14px;
    line-height: 1.6;
    padding: 12px;
    border: 1px solid var(--color-border);
    border-radius: 4px;
    resize: vertical;
    background: var(--color-bg);
    color: var(--color-text);
}
```

---

## Interaction Flow

### Inline word edit

1. User clicks word "broun" (typo) in the reader
2. The word span disappears, replaced by an `<input>` pre-filled with "broun"
3. User types "brown" and presses Enter
4. Frontend: `replaceWordInContent(contentText, charOffset, "broun", "brown")` → new full content_text
5. Frontend: `api.updateArticleContent(id, newContentText)`
6. Backend: re-tokenize, rebuild, remap highlights, re-analyze, return new payload
7. Frontend: refresh reader with new payload, scroll position restored
8. Toast: "已更新正文"

### Full-text edit

1. User clicks 📝 in toolbar
2. Modal opens with textarea showing full article text
3. User fixes multiple typos
4. User clicks "保存修改"
5. Same flow as steps 5-8 above

### Error cases

- **Empty text on save:** disable save button if textarea is empty
- **Network error:** show error toast, keep editor open so user can retry
- **Concurrent edit:** if the word at the expected char_offset no longer matches the old word text (article was edited in another tab/session), show "文本已变更，请刷新后重试"
- **Duplicate hash:** if the edited text matches another article's content, return 409, show "此内容与已有文章重复"

---

## Out of Scope

- HTML-aware editing (preserving EPUB semantic structure)
- Undo/redo within the editor
- Collaborative/real-time editing
- Editing articles not in the reader (e.g., from library page)
