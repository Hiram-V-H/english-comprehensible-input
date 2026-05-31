# Article Delete & Metadata Edit — Design Spec

**Date:** 2026-05-31  
**Scope:** Phase 1 — Article deletion + metadata editing (frontend UI + backend schema expansion)  

---

## Goals

Users want to delete imported articles and edit article metadata directly from the web UI, without using the terminal. Currently the backend has `DELETE /articles/{id}` and `PATCH /articles/{id}`, but the frontend has no UI for either operation.

**Out of scope (Phase 2):** Editing article body text (`content_text`). That requires re-tokenization, span regeneration, analysis re-run, and highlight remapping — significant backend rework deferred to a separate spec.

---

## Backend Changes

### 1. Expand `ArticleUpdate` schema

**File:** `backend/app/schemas/article.py`

Add `exam_type`, `exam_year`, `question_type` to the existing `ArticleUpdate` model:

```python
class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None
    exam_type: Optional[str] = None      # NEW
    exam_year: Optional[int] = None      # NEW
    question_type: Optional[str] = None  # NEW
```

### 2. Expand `update_article` service

**File:** `backend/app/services/article.py`

The existing `update_article` already applies any non-None field from the update dict. Adding the three exam fields to the schema is sufficient — no service code changes needed, since it already uses `setattr(article, key, value)` for each key in the update dict.

### 3. No new endpoints needed

`DELETE /articles/{id}` and `PATCH /articles/{id}` are already implemented and functional. The cascade behavior (article delete → cascades to highlights, annotations, article_words, tags, reading_sessions) is already correct.

### 4. Tests

Add test cases in `backend/tests/`:
- PATCH article with exam metadata fields → 200, verify fields updated
- PATCH article with partial fields → only specified fields change
- DELETE article → 200, verify article and cascade gone

---

## Frontend Changes

### File change summary

| File | Change |
|------|--------|
| `frontend/js/api.js` | Add `deleteBook(id)` function |
| `frontend/js/pages/library.js` | Add hover buttons, batch management mode, delete confirmation, edit modal integration |
| `frontend/js/pages/reader.js` | Add edit/delete buttons to toolbar, wire to modal and confirmation |
| `frontend/js/pages/books.js` | Add hover × delete on book cards |
| `frontend/js/pages/book-detail.js` | Add delete book button in page header |
| `frontend/js/components/modal.js` | **New** — reusable modal component (edit form, delete confirmation) |
| `frontend/js/components/article-editor.js` | **New** — edit metadata form inside modal |
| `frontend/css/components.css` | Add modal backdrop, form field, confirmation dialog styles |
| `frontend/css/base.css` | Add batch management bar, card hover state styles |

### 1. API module additions (`api.js`)

```javascript
// Already exists: updateArticle(id, data), deleteArticle(id)
// Add:
export function deleteBook(id) {
  return request('DELETE', `/books/${id}`);
}
```

The `updateArticle` function already exists and uses `PATCH /articles/{id}` — with the expanded schema it will automatically support the new fields.

### 2. Reusable modal component (`components/modal.js`)

A single `showModal(options)` function that creates a modal overlay with:
- Title bar with close button
- Body content (passed as DOM element or HTML string)
- Footer with action buttons (cancel + confirm, configurable)
- Backdrop click dismisses (same as cancel — Promise rejects)
- Escape key dismisses (same as cancel — Promise rejects)
- Returns a Promise that resolves with `true` on confirm, resolves with `false` on cancel/dismiss

```javascript
// Usage:
const confirmed = await showModal({
  title: '确认删除',
  body: deleteConfirmationBody,
  confirmLabel: '确认删除',
  confirmClass: 'btn-danger',
});
```

### 3. Article editor component (`components/article-editor.js`)

An `ArticleEditForm(article, onSave)` function that renders a form with:
- Title input (text, required)
- Exam type dropdown (考研英语, CET-4, CET-6, IELTS, TOEFL, 其他, or blank)
- Exam year input (number, 4-digit)
- Question type dropdown (阅读理解, 完形填空, 翻译, 写作, 新题型, or blank)
- Is archived checkbox
- Save button → calls `api.updateArticle(id, data)` → invokes `onSave(updatedArticle)`

The exam type and question type dropdowns should be free-text inputs with datalist suggestions, allowing custom values beyond the predefined options.

### 4. Library page changes (`pages/library.js`)

**Card hover state (CSS):**
- Each card gets class `.article-card`
- On hover: show `.card-delete-btn` (×) and `.card-edit-btn` (✎) via CSS `:hover` pseudo-class
- Both buttons are `position: absolute` within the card

**Batch management mode:**
- "管理" button in the page header toggles `batchMode` state
- In batch mode: replace the header area with a dark action bar showing:
  - "全选" toggle
  - "已选择 N 篇" counter
  - "🗑 删除所选" button (disabled when 0 selected)
  - "✕ 取消" button (exits batch mode)
- Cards gain a checkbox overlay; checked cards get a gold border
- "删除所选" opens a single confirmation modal listing the selected titles, then calls `api.deleteArticle(id)` for each in parallel (Promise.allSettled), removes successfully deleted cards, and reports any failures

**Card edit button:**
- Opens `ArticleEditForm` inside a modal
- On save: update the card's displayed metadata (title, badges) without full page reload

**Delete flow (single article):**
1. Click × on hover → `showModal(delete confirmation)` → confirm → `api.deleteArticle(id)` → remove card from DOM → show toast "已删除"
2. If delete fails: show error toast, card stays

**Card removal animation:**
- Add a short fade-out transition (150–200ms) before removing the card element
- Match the existing page transition pattern (120ms opacity)

### 5. Reader page changes (`pages/reader.js`)

Add two buttons to the reader toolbar (alongside existing font size, theme, etc.):
- ✎ Edit → opens `ArticleEditForm` modal with current article data → on save, updates the displayed title in toolbar
- 🗑 Delete → opens delete confirmation modal → on confirm, deletes article and navigates back to `#/library`

Toolbar button order (left to right):
`← Back | Title | Word count | i+1 score | ✎ Edit | 🗑 Delete | A− A+ | ◐ Theme | ☆ Highlights`

### 6. Books page (`pages/books.js`)

Add hover × delete button to book cards (same pattern as library article cards). The backend `DELETE /books/{id}` endpoint exists; just needs `deleteBook` in `api.js`. On confirm: `api.deleteBook(id)` → remove card → toast.

### 7. Book detail page (`pages/book-detail.js`)

Add a "🗑 删除本书" button in the page header area that opens a delete confirmation modal. On confirm: delete book → navigate to `#/books`. The confirmation warning text should mention "本书的所有章节也会被删除".

---

## Interaction Patterns

### Delete confirmation modal

- Icon: ⚠️
- Title: "确认删除"
- Body: "确定要删除 [article/book title] 吗？"
- Warning (red): "此操作不可撤销。[文章的高亮和笔记也会被删除 / 本书的所有章节也会被删除]。"
- Buttons: [取消] [确认删除 (red)]

### Edit metadata modal

- Title: "✎ 编辑文章信息"
- Fields: title, exam_type, exam_year, question_type, is_archived
- Buttons: [取消] [保存修改]
- On save: PATCH → update local card/toolbar → close modal → toast "已更新"

### Toast notifications

Reuse existing toast system (`frontend/js/components/toast.js`):
- Delete success: "已删除「文章标题」"
- Edit success: "已更新文章信息"
- Error: "操作失败，请重试"

---

## Error Handling

- **Network errors:** Catch in API calls, show error toast, do not remove card/close modal
- **404 on delete:** Article already deleted — still remove card from UI, show toast "文章已不存在"
- **Validation:** Title is required in edit form; disable save button if empty
- **Batch delete:** If some deletes fail, continue deleting the rest, report count of failures at end

---

## CSS Considerations

- Card hover effects should use `transition: opacity 0.15s` for smooth button reveal
- Batch management bar uses existing `--color-sidebar` (#3d2010) background with `--color-sidebar-text` (#d4c0a0)
- Modal backdrop: `rgba(0,0,0,0.3)` with centered white card, matching existing modal pattern
- Delete confirm button uses `--color-unknown` (#b8543a, terracotta) for danger association
- Edit save button uses `--color-primary` (#6b4a2a, dark wood)
- Mobile (≤768px, or touch devices): × and ✎ buttons are always visible (not hover-dependent); modal goes full-width, full-height for easier touch interaction

---

## Testing

### Backend tests
- PATCH article with exam_type, exam_year, question_type → verify 200 and fields persisted
- PATCH with partial update → unchanged fields preserved
- DELETE article → 200, cascade verified

### Frontend manual verification
- Hover × on library card → opens confirmation → confirm → card disappears
- Batch mode → select 2 cards → delete selected → both removed
- Edit modal from library → change title → save → card reflects new title
- Edit modal from reader → change exam metadata → save → reader title updates
- Delete from reader → confirmation → redirects to library
- Dark theme: modal and action bar render correctly
- Mobile: buttons visible without hover, modals full-width
