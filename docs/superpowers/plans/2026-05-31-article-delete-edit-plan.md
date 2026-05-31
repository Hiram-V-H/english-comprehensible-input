# Article Delete & Metadata Edit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add article delete and metadata edit capabilities to the frontend, plus expand the backend ArticleUpdate schema to support exam metadata fields.

**Architecture:** Backend change is a one-line schema expansion (3 new optional fields on `ArticleUpdate`). Frontend adds delete/edit UI across 4 pages (library, reader, books, book-detail) using the existing `showModal()` and `showToast()` shared components. A new `article-editor.js` component handles the edit form. Batch management mode on the library page uses CSS class toggling (no re-render). Book deletion is included since the backend endpoint already exists.

**Tech Stack:** FastAPI + Pydantic (backend), vanilla JS SPA (frontend), SQLite

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/schemas/article.py` | Pydantic schema — add exam fields to ArticleUpdate |
| `backend/tests/test_article_crud.py` | **New** — tests for PATCH and DELETE article endpoints |
| `frontend/js/api.js` | API client — add `deleteBook(id)` |
| `frontend/js/components/article-editor.js` | **New** — edit metadata form builder |
| `frontend/js/pages/library.js` | Library page — hover buttons, batch mode, delete/edit wiring |
| `frontend/js/pages/reader.js` | Reader page — edit/delete toolbar callbacks |
| `frontend/js/components/reader/reader-toolbar.js` | Toolbar — add edit/delete buttons |
| `frontend/js/pages/books.js` | Books page — hover × delete on cards |
| `frontend/js/pages/book-detail.js` | Book detail page — delete button |
| `frontend/css/components.css` | Modal form fields, batch bar, card action buttons |
| `frontend/css/base.css` | Card relative positioning for hover buttons |

---

### Task 1: Expand `ArticleUpdate` schema

**Files:**
- Modify: `backend/app/schemas/article.py`

- [ ] **Step 1: Add exam fields to ArticleUpdate**

```python
# backend/app/schemas/article.py — replace the existing ArticleUpdate class

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None
    exam_type: Optional[str] = None
    exam_year: Optional[int] = None
    question_type: Optional[str] = None
```

No service code changes needed — `update_article` in `backend/app/services/article.py` already uses `setattr(article, key, value)` for every key in the update dict.

- [ ] **Step 2: Write backend tests**

Create `backend/tests/test_article_crud.py`:

```python
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
    article_id = resp.json()["data"]["id"]

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
    article_id = resp.json()["data"]["id"]

    # Update only title, leave exam fields unchanged
    resp = await client.patch(f"/api/articles/{article_id}", json={
        "title": "Updated Title",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["title"] == "Updated Title"
    # Exam fields should still be None
    assert data["exam_type"] is None
    assert data["exam_year"] is None


@pytest.mark.asyncio
async def test_delete_article_cascade(client: AsyncClient):
    """DELETE /api/articles/{id} should return 200 and article should be gone."""
    resp = await client.post("/api/import/text", json={
        "title": "To Be Deleted",
        "content": "This article will be deleted."
    })
    assert resp.status_code == 200
    article_id = resp.json()["data"]["id"]

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
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest tests/test_article_crud.py -v
```

Expected: 4 tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/article.py backend/tests/test_article_crud.py
git commit -m "feat: expand ArticleUpdate schema with exam metadata fields"
```

---

### Task 2: Add `deleteBook` to frontend API module

**Files:**
- Modify: `frontend/js/api.js`

- [ ] **Step 1: Add deleteBook function**

Add to the `api` export object in `frontend/js/api.js`, right after the existing article functions (around line 58):

```javascript
    // Book endpoints
    deleteBook: (id) => request('DELETE', '/books/' + id),
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/api.js
git commit -m "feat: add deleteBook API function"
```

---

### Task 3: Create article editor form component

**Files:**
- Create: `frontend/js/components/article-editor.js`

- [ ] **Step 1: Write the component**

Create `frontend/js/components/article-editor.js`:

```javascript
import { el } from '../utils/dom.js';
import { showModal } from './shared/modal.js';
import { showToast } from './shared/toast.js';
import { api } from '../api.js';

/**
 * Build the edit form DOM element for article metadata.
 * @param {Object} article — article summary object (id, title, exam_type, exam_year, question_type, is_archived)
 * @returns {HTMLDivElement}
 */
function buildEditForm(article) {
    const titleInput = el('input', {
        className: 'form-input',
        id: 'edit-title',
        value: article.title || '',
        placeholder: '文章标题',
    });
    const titleGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', textContent: '标题' }),
        titleInput,
    ]);

    const examTypeInput = el('input', {
        className: 'form-input',
        id: 'edit-exam-type',
        value: article.exam_type || '',
        placeholder: '如: 考研英语, CET-4, IELTS',
        list: 'exam-type-list',
    });
    const examTypeDatalist = el('datalist', { id: 'exam-type-list' }, [
        el('option', { value: '考研英语' }),
        el('option', { value: 'CET-4' }),
        el('option', { value: 'CET-6' }),
        el('option', { value: 'IELTS' }),
        el('option', { value: 'TOEFL' }),
        el('option', { value: '高考英语' }),
    ]);
    const examTypeGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', textContent: '考试类型' }),
        examTypeInput,
        examTypeDatalist,
    ]);

    const examYearInput = el('input', {
        className: 'form-input',
        id: 'edit-exam-year',
        type: 'number',
        value: article.exam_year || '',
        placeholder: '如: 2024',
        style: { maxWidth: '120px' },
    });
    const examYearGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', textContent: '年份' }),
        examYearInput,
    ]);

    const questionTypeInput = el('input', {
        className: 'form-input',
        id: 'edit-question-type',
        value: article.question_type || '',
        placeholder: '如: 阅读理解, 完形填空',
        list: 'question-type-list',
    });
    const questionTypeDatalist = el('datalist', { id: 'question-type-list' }, [
        el('option', { value: '阅读理解' }),
        el('option', { value: '完形填空' }),
        el('option', { value: '翻译' }),
        el('option', { value: '写作' }),
        el('option', { value: '新题型' }),
        el('option', { value: '听力' }),
    ]);
    const questionTypeGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', textContent: '题型' }),
        questionTypeInput,
        questionTypeDatalist,
    ]);

    const archiveCheckbox = el('input', {
        type: 'checkbox',
        id: 'edit-archived',
        checked: article.is_archived || false,
    });
    const archiveGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', style: { display: 'flex', alignItems: 'center', gap: '8px' } }, [
            archiveCheckbox,
            '归档（从库中隐藏）',
        ]),
    ]);

    return el('div', { className: 'edit-article-form' }, [
        titleGroup,
        el('div', { className: 'form-row' }, [examTypeGroup, examYearGroup]),
        questionTypeGroup,
        archiveGroup,
    ]);
}

/**
 * Open an edit modal for article metadata. Returns a Promise that resolves
 * with the updated article data on save, or null on cancel.
 * @param {Object} article
 * @returns {Promise<Object|null>}
 */
export async function showArticleEditor(article) {
    const formEl = buildEditForm(article);
    const bodyEl = el('div', { className: 'modal-body' }, [formEl]);

    const result = await showModal('✎ 编辑文章信息', bodyEl, [
        { label: '取消', value: false },
        { label: '保存修改', value: 'save', primary: true },
    ]);

    if (result !== 'save') return null;

    // Read form values
    const title = formEl.querySelector('#edit-title').value.trim();
    if (!title) {
        showToast('标题不能为空', 'error');
        return null;
    }

    const examTypeVal = formEl.querySelector('#edit-exam-type').value.trim() || null;
    const examYearRaw = formEl.querySelector('#edit-exam-year').value.trim();
    const examYearVal = examYearRaw ? parseInt(examYearRaw, 10) : null;
    const questionTypeVal = formEl.querySelector('#edit-question-type').value.trim() || null;
    const isArchived = formEl.querySelector('#edit-archived').checked;

    const updateData = {
        title,
        exam_type: examTypeVal,
        exam_year: examYearVal,
        question_type: questionTypeVal,
        is_archived: isArchived,
    };

    try {
        const updated = await api.updateArticle(article.id, updateData);
        showToast('已更新文章信息', 'success');
        return updated;
    } catch (err) {
        showToast('更新失败，请重试', 'error');
        return null;
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/components/article-editor.js
git commit -m "feat: add article editor modal component"
```

---

### Task 4: Update library page — hover buttons + batch mode + delete/edit

**Files:**
- Modify: `frontend/js/pages/library.js`
- Modify: `frontend/css/components.css`
- Modify: `frontend/css/base.css`

- [ ] **Step 1: Add CSS for card action buttons**

Add to `frontend/css/components.css` (before the `.card-import-placeholder` section):

```css
/* Card action buttons (hover reveal) */
.article-card {
    position: relative;
}

.card-actions {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 2;
}

.article-card:hover .card-actions {
    opacity: 1;
}

.card-action-btn {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    line-height: 1;
    transition: background 0.15s;
}

.card-delete-btn {
    background: var(--color-unknown);
    color: #fff;
}

.card-delete-btn:hover {
    background: #9a3a22;
}

.card-edit-btn {
    background: var(--color-sidebar);
    color: var(--color-sidebar-text);
}

.card-edit-btn:hover {
    background: var(--color-primary);
}

/* Batch management */
.batch-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    background: var(--color-sidebar);
    color: var(--color-sidebar-text);
    border-radius: 6px;
    margin-bottom: 16px;
}

.batch-bar-left {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.9em;
}

.batch-bar-left .select-all-btn {
    cursor: pointer;
    color: var(--color-sidebar-text);
    background: none;
    border: none;
    font-size: inherit;
}

.batch-bar-left .selected-count {
    font-size: 0.9em;
}

.batch-bar-left .selected-count strong {
    color: #fff;
}

.batch-bar-actions {
    display: flex;
    gap: 8px;
}

.batch-bar-actions .batch-delete-btn {
    background: var(--color-unknown);
    color: #fff;
    border: none;
    padding: 5px 14px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85em;
}

.batch-bar-actions .batch-delete-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

.batch-bar-actions .batch-cancel-btn {
    background: transparent;
    color: var(--color-sidebar-text);
    border: 1px solid var(--color-sidebar-text);
    padding: 5px 14px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85em;
}

/* Card checkbox (hidden by default, shown in batch mode) */
.card-checkbox {
    display: none;
    position: absolute;
    top: 10px;
    left: 10px;
    z-index: 2;
    width: 18px;
    height: 18px;
    accent-color: var(--color-primary);
}

.batch-mode .card-checkbox {
    display: block;
}

.batch-mode .card-actions {
    display: none;
}

.batch-mode .article-card.card-selected {
    border-color: var(--color-accent);
    border-width: 2px;
}
```

Add to `frontend/css/base.css` (at the end of the responsive section, or in the card section):

```css
/* Article card relative positioning for action buttons */
.article-card {
    position: relative;
}
```

- [ ] **Step 2: Modify library.js — import new dependencies**

At the top of `frontend/js/pages/library.js`, add the new imports:

```javascript
import { showArticleEditor } from '../components/article-editor.js';
import { showModal } from '../components/shared/modal.js';
import { showToast } from '../components/shared/toast.js';
```

These go alongside the existing imports. The existing imports are:
```javascript
import { el, clearElement } from '../utils/dom.js';
import { api } from '../api.js';
import { router } from '../router.js';
import { STRIPE_GRADIENTS, getDifficultyColors, getI1ScoreLabel } from '../utils/card-utils.js';
```

- [ ] **Step 3: Modify library.js — add batch mode state and header update**

After the existing module-level declarations (after `let currentExamType = null;` etc.), add:

```javascript
let batchMode = false;
let selectedIds = new Set();
let currentArticles = []; // keep a reference to current page articles for batch ops
```

Modify the page header section. Currently it creates a header div with title. Replace the header area to include the "管理" button. Find the section that creates `pageHeader` (around line 9-10 of the function body) and add the manage button:

```javascript
// Inside libraryPage(main), after creating the page header:
const headerRight = el('div', { style: { display: 'flex', gap: '8px' } }, [
    el('button', {
        className: 'btn',
        id: 'batch-toggle-btn',
        textContent: '☰ 管理',
        onClick: toggleBatchMode,
    }),
    el('button', {
        className: 'btn btn-primary',
        textContent: '+ 导入',
        onClick: () => router.navigate('#/import'),
    }),
]);
// Append headerRight to the page header div
// The existing header div should become a flex row with justify-content: space-between
```

Add the batch action bar (hidden by default):

```javascript
const batchBar = el('div', {
    className: 'batch-bar',
    id: 'batch-bar',
    style: { display: 'none' },
}, [
    el('div', { className: 'batch-bar-left' }, [
        el('button', {
            className: 'select-all-btn',
            textContent: '☑ 全选',
            onClick: toggleSelectAll,
        }),
        el('span', { className: 'selected-count', id: 'selected-count' }, ['已选择 ', el('strong', {}, ['0']), ' 篇']),
    ]),
    el('div', { className: 'batch-bar-actions' }, [
        el('button', {
            className: 'batch-delete-btn',
            id: 'batch-delete-btn',
            disabled: true,
            textContent: '🗑 删除所选',
            onClick: deleteSelected,
        }),
        el('button', {
            className: 'batch-cancel-btn',
            textContent: '✕ 取消',
            onClick: exitBatchMode,
        }),
    ]),
]);
// Insert batchBar before the content container
```

- [ ] **Step 4: Modify library.js — add batch mode functions**

Add these functions inside `libraryPage(main)`:

```javascript
function toggleBatchMode() {
    batchMode = !batchMode;
    selectedIds.clear();
    updateBatchUI();
}

function exitBatchMode() {
    batchMode = false;
    selectedIds.clear();
    updateBatchUI();
}

function updateBatchUI() {
    const grid = document.querySelector('.article-grid');
    const batchBar = document.getElementById('batch-bar');
    const toggleBtn = document.getElementById('batch-toggle-btn');
    const selectedCount = document.getElementById('selected-count');
    const deleteBtn = document.getElementById('batch-delete-btn');

    if (batchMode) {
        grid && grid.classList.add('batch-mode');
        batchBar && (batchBar.style.display = 'flex');
        toggleBtn && (toggleBtn.textContent = '✕ 取消');
        toggleBtn && (toggleBtn.className = 'btn');
    } else {
        grid && grid.classList.remove('batch-mode');
        batchBar && (batchBar.style.display = 'none');
        toggleBtn && (toggleBtn.textContent = '☰ 管理');
        toggleBtn && (toggleBtn.className = 'btn');
        // Uncheck all
        document.querySelectorAll('.card-checkbox').forEach(cb => cb.checked = false);
        document.querySelectorAll('.article-card').forEach(c => c.classList.remove('card-selected'));
    }

    if (selectedCount) {
        const strong = selectedCount.querySelector('strong');
        if (strong) strong.textContent = String(selectedIds.size);
    }
    if (deleteBtn) {
        deleteBtn.disabled = selectedIds.size === 0;
    }
}

function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.card-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);

    checkboxes.forEach(cb => {
        cb.checked = !allChecked;
        const card = cb.closest('.article-card');
        const articleId = parseInt(cb.dataset.articleId, 10);
        if (!allChecked) {
            selectedIds.add(articleId);
            card && card.classList.add('card-selected');
        } else {
            selectedIds.delete(articleId);
            card && card.classList.remove('card-selected');
        }
    });

    updateBatchUI();
}

function onCardCheckboxChange(e) {
    const cb = e.target;
    const articleId = parseInt(cb.dataset.articleId, 10);
    const card = cb.closest('.article-card');

    if (cb.checked) {
        selectedIds.add(articleId);
        card && card.classList.add('card-selected');
    } else {
        selectedIds.delete(articleId);
        card && card.classList.remove('card-selected');
    }
    updateBatchUI();
}

async function deleteSingle(article) {
    const bodyEl = el('div', { className: 'modal-body' }, [
        el('p', {}, ['确定要删除 ', el('strong', {}, [article.title]), ' 吗？']),
        el('p', { style: { color: 'var(--color-unknown)', fontSize: '0.85em', marginTop: '8px' } },
            ['此操作不可撤销，文章的所有高亮和笔记也会被删除。']),
    ]);

    const confirmed = await showModal('⚠️ 确认删除', bodyEl, [
        { label: '取消', value: false },
        { label: '确认删除', value: true, primary: true },
    ]);

    if (!confirmed) return;

    try {
        await api.deleteArticle(article.id);
        // Remove card from DOM
        const card = document.querySelector(`.article-card[data-article-id="${article.id}"]`);
        if (card) {
            card.style.opacity = '0';
            card.style.transition = 'opacity 0.15s';
            setTimeout(() => card.remove(), 150);
        }
        showToast(`已删除「${article.title}」`, 'success');
    } catch (err) {
        if (err.message && err.message.includes('404')) {
            // Already deleted — remove card anyway
            const card = document.querySelector(`.article-card[data-article-id="${article.id}"]`);
            card && card.remove();
            showToast('文章已不存在', 'info');
        } else {
            showToast('删除失败，请重试', 'error');
        }
    }
}

async function deleteSelected() {
    if (selectedIds.size === 0) return;

    const titles = [];
    currentArticles.forEach(a => {
        if (selectedIds.has(a.id)) titles.push(a.title);
    });

    const titleList = titles.length <= 3
        ? titles.map(t => `「${t}」`).join('、')
        : `「${titles[0]}」等 ${titles.length} 篇文章`;

    const bodyEl = el('div', { className: 'modal-body' }, [
        el('p', {}, [`确定要删除 ${titleList} 吗？`]),
        el('p', { style: { color: 'var(--color-unknown)', fontSize: '0.85em', marginTop: '8px' } },
            ['此操作不可撤销，这些文章的所有高亮和笔记也会被删除。']),
    ]);

    const confirmed = await showModal('⚠️ 确认批量删除', bodyEl, [
        { label: '取消', value: false },
        { label: '确认删除', value: true, primary: true },
    ]);

    if (!confirmed) return;

    let successCount = 0;
    let failCount = 0;
    const ids = Array.from(selectedIds);

    const results = await Promise.allSettled(
        ids.map(id => api.deleteArticle(id))
    );

    results.forEach((result, i) => {
        if (result.status === 'fulfilled') {
            const card = document.querySelector(`.article-card[data-article-id="${ids[i]}"]`);
            if (card) {
                card.style.opacity = '0';
                card.style.transition = 'opacity 0.15s';
                setTimeout(() => card.remove(), 150);
            }
            successCount++;
        } else {
            failCount++;
        }
    });

    if (failCount === 0) {
        showToast(`已删除 ${successCount} 篇文章`, 'success');
    } else {
        showToast(`成功删除 ${successCount} 篇，${failCount} 篇失败`, 'error');
    }

    exitBatchMode();
}
```

- [ ] **Step 5: Modify `renderArticleCard` — add action buttons and checkbox**

Modify the `renderArticleCard(article, index)` function. The card needs `data-article-id`, `className: 'article-card card'`, and action buttons. Replace the card creation:

```javascript
function renderArticleCard(article, index) {
    const unknownDensity = article.unknown_word_density || 0;
    const colors = getDifficultyColors(unknownDensity);
    const i1Label = getI1ScoreLabel(article.i_plus_one_score);
    const created = new Date(article.created_at);
    const dateStr = created.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });

    // Build metadata badges
    const badges = [];
    if (article.exam_type) {
        badges.push(el('span', { className: 'badge', textContent: article.exam_type }));
    }
    if (article.exam_year) {
        badges.push(el('span', { className: 'badge', textContent: String(article.exam_year) }));
    }
    if (article.question_type) {
        badges.push(el('span', { className: 'badge', textContent: article.question_type }));
    }

    return el('div', {
        className: 'article-card card',
        dataset: { articleId: String(article.id) },
    }, [
        // Checkbox for batch mode
        el('input', {
            type: 'checkbox',
            className: 'card-checkbox',
            dataset: { articleId: String(article.id) },
            onChange: onCardCheckboxChange,
        }),
        // Top color stripe
        el('div', {
            className: 'article-card-top-stripe',
            style: { background: STRIPE_GRADIENTS[index % 5] },
        }),
        // Hover action buttons
        el('div', { className: 'card-actions' }, [
            el('button', {
                className: 'card-action-btn card-edit-btn',
                title: '编辑',
                textContent: '✎',
                onClick: (e) => {
                    e.stopPropagation();
                    editArticle(article);
                },
            }),
            el('button', {
                className: 'card-action-btn card-delete-btn',
                title: '删除',
                textContent: '×',
                onClick: (e) => {
                    e.stopPropagation();
                    deleteSingle(article);
                },
            }),
        ]),
        // Title (click to navigate)
        el('div', {
            className: 'article-card-title',
            textContent: article.title,
            onClick: () => router.navigate('#/reader/' + article.id),
        }),
        // Badges
        badges.length ? el('div', { style: { display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '6px' } }, badges) : null,
        // Meta line
        el('div', { className: 'article-card-meta' }, [
            article.unknown_word_count != null
                ? el('span', { textContent: `${article.unknown_word_count} unknown` })
                : null,
            el('span', { className: 'meta-dot', textContent: '·' }),
            el('span', { textContent: `${article.word_count || 0} words` }),
            el('span', { className: 'meta-dot', textContent: '·' }),
            el('span', { textContent: dateStr }),
        ].filter(Boolean)),
        // Difficulty bar
        el('div', { className: 'difficulty-bar' }, [
            el('div', {
                className: 'difficulty-bar-inner',
                style: { width: `${Math.min(100, unknownDensity * 100)}%`, background: colors.bar },
            }),
        ]),
        // Difficulty labels
        el('div', { className: 'difficulty-label' }, [
            el('span', { style: { color: colors.text }, textContent: `${(unknownDensity * 100).toFixed(0)}% unknown` }),
            i1Label ? el('span', { textContent: `i+1: ${i1Label}` }) : null,
        ].filter(Boolean)),
    ]);
}
```

- [ ] **Step 6: Add `editArticle` function**

Add this function inside `libraryPage(main)`:

```javascript
async function editArticle(article) {
    const updated = await showArticleEditor(article);
    if (!updated) return;

    // Update the card in-place: refresh title and badges
    const card = document.querySelector(`.article-card[data-article-id="${article.id}"]`);
    if (!card) return;

    // Update title
    const titleEl = card.querySelector('.article-card-title');
    if (titleEl) titleEl.textContent = updated.title;

    // Update badges: remove old, rebuild
    const existingBadges = card.querySelectorAll('.badge');
    existingBadges.forEach(b => b.remove());

    const badgeContainer = card.querySelector('.article-card-title')?.nextElementSibling;
    const newBadges = [];
    if (updated.exam_type) newBadges.push(el('span', { className: 'badge', textContent: updated.exam_type }));
    if (updated.exam_year) newBadges.push(el('span', { className: 'badge', textContent: String(updated.exam_year) }));
    if (updated.question_type) newBadges.push(el('span', { className: 'badge', textContent: updated.question_type }));

    if (newBadges.length && badgeContainer) {
        // Replace badge container content
        badgeContainer.innerHTML = '';
        newBadges.forEach(b => badgeContainer.appendChild(b));
    }

    // Update article reference
    Object.assign(article, updated);
}
```

- [ ] **Step 7: Store current articles and update load()**

In the `load()` function, store the articles after fetching:

```javascript
// Inside load(), after getting data.items:
currentArticles = data.items;
```

Update `renderGroupedByYear` to also collect articles into `currentArticles`:

```javascript
// At the end of renderGroupedByYear, merge all rendered articles
```

Actually simpler: just set `currentArticles = data.items` in `load()`. That covers both the grouped and non-grouped paths.

- [ ] **Step 8: Commit**

```bash
git add frontend/js/pages/library.js frontend/css/components.css frontend/css/base.css
git commit -m "feat: add delete/edit/batch-mode to library page"
```

---

### Task 5: Update reader page — toolbar edit/delete buttons

**Files:**
- Modify: `frontend/js/components/reader/reader-toolbar.js`
- Modify: `frontend/js/pages/reader.js`

- [ ] **Step 1: Add setters and buttons to ReaderToolbar**

In `frontend/js/components/reader/reader-toolbar.js`, add two new setters:

```javascript
    setOnEdit(cb) { this._onEdit = cb; }
    setOnDelete(cb) { this._onDelete = cb; }
```

In the `render()` method, add the edit and delete buttons after the i+1 pill and before the spacer. Find the section:

```javascript
        // Inside render(), after the i+1 score pill
        if (this.articleData.i_plus_one_score != null) {
            const i1Label = getI1ScoreLabel(this.articleData.i_plus_one_score);
            if (i1Label) {
                toolbar.appendChild(el('div', { className: 'toolbar-pill', textContent: `i+1: ${i1Label}` }));
            }
        }
```

Add after that block (still before the spacer):

```javascript
        // Edit button
        const editBtn = el('button', {
            className: 'toolbar-btn',
            title: '编辑文章信息',
            textContent: '✎',
            onClick: () => { if (this._onEdit) this._onEdit(); },
        });
        toolbar.appendChild(editBtn);

        // Delete button
        const deleteBtn = el('button', {
            className: 'toolbar-btn',
            title: '删除文章',
            textContent: '🗑',
            onClick: () => { if (this._onDelete) this._onDelete(); },
        });
        toolbar.appendChild(deleteBtn);
```

Then the spacer `el('div', { style: { flex: 1 } })` and remaining buttons follow as before.

- [ ] **Step 2: Wire callbacks in reader.js**

In `frontend/js/pages/reader.js`, add imports at the top:

```javascript
import { showArticleEditor } from '../components/article-editor.js';
import { showModal } from '../components/shared/modal.js';
import { showToast } from '../components/shared/toast.js';
```

Find where the toolbar callbacks are set (after `new ReaderToolbar(toolbarEl, readerData.article)`), and add:

```javascript
    toolbar.setOnEdit(() => handleEditArticle(readerData.article));
    toolbar.setOnDelete(() => handleDeleteArticle(readerData.article));
```

Add the handler functions inside the async IIFE (before the reader body setup):

```javascript
    async function handleEditArticle(article) {
        const updated = await showArticleEditor({
            id: article.id,
            title: article.title,
            exam_type: article.exam_type,
            exam_year: article.exam_year,
            question_type: article.question_type,
            is_archived: article.is_archived,
        });
        if (!updated) return;
        // Update toolbar title
        const titleEl = document.querySelector('.toolbar-title');
        if (titleEl) titleEl.textContent = updated.title;
        // Update local data
        Object.assign(article, updated);
    }

    async function handleDeleteArticle(article) {
        const bodyEl = document.createElement('div');
        bodyEl.className = 'modal-body';
        bodyEl.innerHTML = `
            <p>确定要删除 <strong>${article.title}</strong> 吗？</p>
            <p style="color: var(--color-unknown); font-size: 0.85em; margin-top: 8px;">
                此操作不可撤销，文章的所有高亮和笔记也会被删除。
            </p>
        `;

        const confirmed = await showModal('⚠️ 确认删除', bodyEl, [
            { label: '取消', value: false },
            { label: '确认删除', value: true, primary: true },
        ]);

        if (!confirmed) return;

        try {
            await api.deleteArticle(article.id);
            showToast(`已删除「${article.title}」`, 'success');
            router.navigate('#/library');
        } catch (err) {
            showToast('删除失败，请重试', 'error');
        }
    }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/js/components/reader/reader-toolbar.js frontend/js/pages/reader.js
git commit -m "feat: add edit/delete buttons to reader toolbar"
```

---

### Task 6: Update books page — hover delete on cards

**Files:**
- Modify: `frontend/js/pages/books.js`

- [ ] **Step 1: Add delete button to book cards**

In `frontend/js/pages/books.js`, add imports:

```javascript
import { showModal } from '../components/shared/modal.js';
import { showToast } from '../components/shared/toast.js';
import { api } from '../api.js';
```

Modify the card creation in the render loop. Books currently uses direct `fetch()` and creates cards manually. Find the card creation code (around lines 30-40 in the async IIFE) and add the hover delete button. The card div becomes:

```javascript
            const card = el('div', {
                className: 'article-card card',
                dataset: { bookId: String(book.id) },
            }, [
                el('div', {
                    className: 'article-card-top-stripe',
                    style: { background: STRIPE_GRADIENTS[i % 5] },
                }),
                // Hover actions
                el('div', { className: 'card-actions' }, [
                    el('button', {
                        className: 'card-action-btn card-delete-btn',
                        title: '删除',
                        textContent: '×',
                        onClick: (e) => {
                            e.stopPropagation();
                            deleteBook(book);
                        },
                    }),
                ]),
                el('div', { className: 'article-card-title', textContent: book.title }),
                el('div', { className: 'article-card-meta' }, [
                    el('span', { textContent: `${book.chapter_count || 0} chapters` }),
                ]),
            ]);
            card.addEventListener('click', () => router.navigate('#/books/' + book.id));
```

Add the `deleteBook` function inside `booksPage(main)`:

```javascript
    async function deleteBook(book) {
        const bodyEl = document.createElement('div');
        bodyEl.className = 'modal-body';
        bodyEl.innerHTML = `
            <p>确定要删除 <strong>${book.title}</strong> 吗？</p>
            <p style="color: var(--color-unknown); font-size: 0.85em; margin-top: 8px;">
                此操作不可撤销，本书的所有章节也会被删除。
            </p>
        `;

        const confirmed = await showModal('⚠️ 确认删除', bodyEl, [
            { label: '取消', value: false },
            { label: '确认删除', value: true, primary: true },
        ]);

        if (!confirmed) return;

        try {
            await api.deleteBook(book.id);
            const card = document.querySelector(`.article-card[data-book-id="${book.id}"]`);
            if (card) {
                card.style.opacity = '0';
                card.style.transition = 'opacity 0.15s';
                setTimeout(() => card.remove(), 150);
            }
            showToast(`已删除「${book.title}」`, 'success');
        } catch (err) {
            showToast('删除失败，请重试', 'error');
        }
    }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/pages/books.js
git commit -m "feat: add delete button to book cards"
```

---

### Task 7: Update book detail page — delete button

**Files:**
- Modify: `frontend/js/pages/book-detail.js`

- [ ] **Step 1: Add delete button to book detail header**

In `frontend/js/pages/book-detail.js`, add imports at the top:

```javascript
import { showModal } from '../components/shared/modal.js';
import { showToast } from '../components/shared/toast.js';
import { router } from '../router.js';
```

In the async IIFE, after the page header is built (after the `h1` or header div creation), add a delete button:

```javascript
    // After the page header, add delete button
    const deleteBtn = el('button', {
        className: 'btn btn-danger',
        textContent: '🗑 删除本书',
        onClick: () => deleteCurrentBook(book),
    });
    // Append to header or a header-actions div
    pageHeader.appendChild(deleteBtn);
```

Add the delete function:

```javascript
    async function deleteCurrentBook(book) {
        const bodyEl = document.createElement('div');
        bodyEl.className = 'modal-body';
        bodyEl.innerHTML = `
            <p>确定要删除 <strong>${book.title}</strong> 吗？</p>
            <p style="color: var(--color-unknown); font-size: 0.85em; margin-top: 8px;">
                此操作不可撤销，本书的所有章节也会被删除。
            </p>
        `;

        const confirmed = await showModal('⚠️ 确认删除', bodyEl, [
            { label: '取消', value: false },
            { label: '确认删除', value: true, primary: true },
        ]);

        if (!confirmed) return;

        try {
            await fetch(`/api/books/${book.id}`, { method: 'DELETE' });
            showToast(`已删除「${book.title}」`, 'success');
            router.navigate('#/books');
        } catch (err) {
            showToast('删除失败，请重试', 'error');
        }
    }
```

Note: book-detail.js currently uses direct `fetch()` not the api module, so the delete also uses direct fetch. This is consistent with the existing pattern.

- [ ] **Step 2: Commit**

```bash
git add frontend/js/pages/book-detail.js
git commit -m "feat: add delete button to book detail page"
```

---

### Task 8: Mobile responsiveness and final polish

**Files:**
- Modify: `frontend/css/components.css`

- [ ] **Step 1: Add mobile styles for card actions**

Add inside the existing `@media (max-width: 768px)` block in `frontend/css/components.css`:

```css
    /* Always show card actions on touch devices */
    .card-actions {
        opacity: 1;
        position: static;
        justify-content: flex-end;
        margin-bottom: 4px;
    }

    .article-card {
        position: relative;
    }

    /* Full-width modals on mobile */
    .modal-box {
        margin: 16px;
        max-width: none;
        width: auto;
    }

    /* Batch bar stacks on mobile */
    .batch-bar {
        flex-direction: column;
        gap: 8px;
        align-items: flex-start;
    }

    .batch-bar-actions {
        width: 100%;
        justify-content: flex-end;
    }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/components.css
git commit -m "style: add mobile responsiveness for card actions and batch bar"
```

---

### Task 9: End-to-end verification

- [ ] **Step 1: Run backend tests**

```bash
cd backend && python -m pytest tests/test_article_crud.py -v
```

Expected: All 4 tests pass.

- [ ] **Step 2: Run all backend tests to check for regressions**

```bash
cd backend && python -m pytest -v
```

Expected: All existing tests still pass.

- [ ] **Step 3: Start dev server**

```bash
cd backend && python -m uvicorn app.main:app --reload
```

- [ ] **Step 4: Manual verification checklist**

Open the app in browser and verify:

**Library page:**
- [ ] Hover over article card → × and ✎ buttons appear
- [ ] Click × → confirmation modal → cancel → card stays
- [ ] Click × → confirmation modal → confirm → card fades out, toast "已删除"
- [ ] Click ✎ → edit modal with current values
- [ ] Change title → save → card updates
- [ ] Change exam metadata → save → badges update
- [ ] Click "管理" → batch mode activates (checkboxes, action bar)
- [ ] Select 2 cards → "删除所选" → confirmation → both removed
- [ ] "全选" toggles all checkboxes
- [ ] "取消" exits batch mode

**Reader page:**
- [ ] Toolbar shows ✎ and 🗑 buttons
- [ ] Click ✎ → edit modal → save → toolbar title updates
- [ ] Click 🗑 → confirmation → confirm → redirects to library

**Books page:**
- [ ] Hover over book card → × appears
- [ ] Click × → confirmation → confirm → card removed

**Book detail page:**
- [ ] "🗑 删除本书" button visible
- [ ] Click → confirmation → confirm → redirects to #/books

**Mobile / Dark theme:**
- [ ] Dark theme: modal and batch bar render correctly
- [ ] Mobile viewport: card buttons always visible, modals full-width

- [ ] **Step 5: Commit (if any fixes)**

---

## Task Execution Order

Tasks must run sequentially in order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9.

- Task 1 (backend schema) and Task 2 (api.js) are independent and could run in parallel, but sequential is safer for review.
- Task 3 (article-editor component) must complete before Tasks 4 and 5 (which import it).
- Tasks 4, 5, 6, 7 are independent of each other but all depend on Tasks 2 and 3.
- Task 8 (CSS polish) should run last among code changes.
- Task 9 (verification) always runs last.
