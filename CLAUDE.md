# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

```bash
# Start dev server (run from backend/)
python -m uvicorn app.main:app --reload

# Run all tests
cd backend && pytest

# Generate a new Alembic migration
cd backend && alembic revision --autogenerate -m "description"

# Apply migrations
cd backend && alembic upgrade head
```

## Architecture

This is a full-stack **Comprehensible Input English Learning System**: FastAPI (async) backend + vanilla JS SPA frontend, SQLite database with Alembic migrations.

### Key architectural patterns

**Unified Import Framework** (`backend/app/providers/importer.py`):
- `ContentImporter` ABC for single-article formats (txt, md) — returns `ImportedArticle`
- `BookImporter` ABC for multi-chapter formats (EPUB) — two-phase: `preview()` → chapter selection → `import_chapters()`
- `ImporterRegistry` (`backend/app/importers/registry.py`) separates content vs. book importers; register new formats there
- Books contain chapters (Articles with `book_id`, `chapter_index`, `chapter_path`)
- **`TocItem` dataclass** — recursive tree node: `{title, href, children[]}`; `BookImportResult.toc_tree` carries the full hierarchical TOC alongside the flat chapter list

**EPUB TOC recursive parsing** (`backend/app/importers/epub_importer.py`):
- Parses EPUB ZIP directly (does not rely on ebooklib's flat TOC):
  1. Read `META-INF/container.xml` → find OPF `full-path`
  2. Parse OPF manifest → **EPUB 3 first**: find `properties="nav"` item → `nav.xhtml`; **EPUB 2 fallback**: find `media-type="application/x-dtbncx+xml"` → `toc.ncx`
  3. Recursive parse: NCX `<navPoint>` nesting or NAV `<ol>/<li>` nesting
- `_resolve_path()` normalizes all `src`/`href` relative to the OPF directory — no assumption about `Text/` or `OEBPS/` folders
- `_get_ns()` extracts XML namespace dynamically from root element tag; both namespaced and non-namespaced XML work
- Produces both `List[ChapterInfo]` (flat depth-first, for import selection) and `List[TocItem]` (tree, stored as JSON)
- **Fallback chain**: NAV → NCX → manifest spine → ebooklib spine
- `toc_tree` is stored as JSON in `Book.toc_json` (column added by migration `006_add_book_toc_json.py`)

**Reader endpoint design** (`GET /api/reader/{id}`):
- Backend pre-computes the full reader payload: paragraphs of word tokens, each with `position`, `word_id`, `status` (known/unknown/punct), `char_offset` — the frontend never does its own tokenization or vocabulary lookup
- `_compute_char_offsets()` omits spaces before punctuation tokens to match real text rendering

**Character-offset highlight anchoring** (`frontend/js/utils/text-offset.js`):
- Highlights are stored as `(start_char_offset, end_char_offset)` into `article.content_text`, not as DOM nodes
- Word spans render with `data-char-offset` attributes; when the user selects text, offsets are computed from the DOM, and when highlights are rendered, offsets are mapped back to word spans
- This means the renderer can be rewritten (React, canvas, etc.) without losing highlight data

**Composite analyzer** (`backend/app/analysis/composite.py`):
- Pluggable algorithms (word count, unknown word detection, coverage, i+1 scoring) all implement `AnalysisAlgorithm` ABC
- Each algorithm receives `(article_id, article_words, db_session)` and returns an `AnalysisResult`
- Results are persisted to `articles` columns (e.g., `unknown_word_count`, `i_plus_one_score`)

**Tokenizer contract** (`backend/app/services/tokenizer.py`):
- Tokenizes both words AND punctuation into separate `Token` objects with `is_punctuation: bool`
- `ArticleWord` rows always include punctuation tokens — filtering is done by caller via `is_punctuation == False`
- All analysis algorithms, word counters, and stats must filter out `is_punctuation` tokens

### Frontend: vanilla SPA with no build step

- **Hash-based router** (`frontend/js/router.js`): routes like `#/library`, `#/reader/3`, `#/books/1`; supports async handlers and `_currentCleanup` pattern (handler returns cleanup fn called before next route)
- Hash always starts with `/` in nav links (`#/library`), but the router strips the leading slash before matching
- **Page transitions**: 120ms fade-out/in via `#app-main` opacity — `_handle()` is async to support rendering delay
- `el()` helper (`frontend/js/utils/dom.js`) creates DOM elements — set `style` as string or object, boolean HTML attrs must skip `null`/`undefined` values
- `NoCacheStaticMiddleware` in `main.py` sets `Cache-Control: no-cache` on JS/CSS/HTML — must be registered before `StaticFiles` mount
- Each page module exports a function `pageName(mainElement, params)` that builds the page; routes are registered in `app.js`
- **Collapsible sidebar** (`frontend/js/components/sidebar.js`): `#app-shell` flex container holds `<aside id="sidebar">` + `<main id="app-main">`; sidebar expands to 200px / collapses to 48px via `collapsed` class; state persisted in `appState`; `updateActive()` exported for route highlighting
- **Shared card utilities** (`frontend/js/utils/card-utils.js`): `STRIPE_GRADIENTS`, `getDifficultyColors(unknownDensity)`, `getI1ScoreLabel(score)` — imported by library, books, and book-detail pages
- **TOC tree component** (`frontend/js/components/toc-tree.js`):
  - `renderTocTree(tree, chapterMap, currentArticleId, options)` — recursive renderer for book-detail and reader pages; resolves `href → chapter_path → article_id` for navigation links; highlights current chapter
  - `renderImportTocTree(tree, chapters, chapterCheckboxes)` — import-page variant with checkboxes; populates `chapterCheckboxes[chapter.index] = checkbox` for the confirm flow; nodes without a matching chapter render as labels only
  - `buildChapterMap(chapters)` — builds `{chapter_path → article_id}` lookup from flat chapter arrays
  - Expand/collapse: arrow toggle (`▸`/`▾`), `defaultCollapseDepth = 2`, depth ≥ 2 collapsed by default
  - TOC tree gracefully falls back to flat list when `toc_tree` is null/empty

### Design system (Rich Mahogany editorial)

- **Color palette** (`frontend/css/base.css` — `:root` variables):
  - Page: `--color-bg: #faf6f0` (warm cream), `--color-text: #3d2010` (deep brown), `--color-text-secondary: #6b4a2a`
  - Primary: `--color-primary: #6b4a2a` (dark wood), `--color-accent: #c4a040` (gold)
  - Sidebar: `--color-sidebar: #3d2010` (dark mahogany), `--color-sidebar-text: #d4c0a0`
  - Word states: `--color-unknown: #b8543a` (terracotta), `--color-learning: #c4956a` (amber), `--color-known: #5a8a4a` (sage), `--color-familiar: #a08060` (tan)
  - Highlights: gold (#c4a040), sage (#6b8a5a), lavender (#8b6a9a), terracotta (#b8705a), slate (#6a8a9a)
- **Typography**: `--font-display: "Spectral", Georgia, serif` (headings), `--font-body: "Crimson Text", Georgia, serif` (content/reading), loaded from Google Fonts in `index.html`
- **Backward-compatible aliases** (`--color-primary-light` → `--color-accent-light`, `--shadow` → `--shadow-card`, `--font-serif` → `--font-body`) preserve references in code not yet migrated
- **Responsive breakpoint**: 768px — sidebar auto-collapses to icon-only, grid becomes single-column, reader font shrinks to 16px
- **CSS file roles**: `base.css` (tokens, reset, sidebar, buttons, badges, forms), `components.css` (toast, modal, cards, pagination, drop zone, tables, TOC tree), `reader.css` (reader layout, word states, popup, highlights, annotation panel), `vocabulary.css` (stats bar, word table, word detail, note cards)

### Import page: three-way input

- **Text paste** (left column): large `<textarea>`, first line → title, posts to `POST /api/import/text` with `{title, content}`
- **File drop** (right column): compact drop zone for .txt/.md/.epub, delegates to `POST /api/import/file`
- **Folder path** (right column): text input + Scan button, delegates to `POST /api/import/folder`
- **EPUB flow**: upload → `POST /api/import/epub/preview` → hierarchical TOC tree with checkboxes + Expand All/Collapse All → `POST /api/import/epub/confirm` with selected chapter indices
- Import history table below the two columns

### Database conventions

- All tables use `INTEGER PRIMARY KEY AUTOINCREMENT` (SQLite requirement — `batch_alter_table` in Alembic strips this, so migrations that touch `articles` must use raw SQL recreation, see migration `005_fix_articles_pk.py`)
- Deduplication: `articles.sha256_hash UNIQUE`, `words.word_lower UNIQUE`
- `user_id` column defaults to `"default"` everywhere — multi-user is reserved but not implemented
- `Book.toc_json` (Text) stores the full hierarchical TOC tree as JSON; read by book-detail and reader endpoints; `Article.chapter_path` is the matching key for `TocItem.href → chapter_path → article.id` lookup in the frontend

### Test setup (`backend/tests/conftest.py`)

- In-memory SQLite with tables created per-test via `Base.metadata.create_all`
- DB dependency overridden to inject the test session
- `httpx.AsyncClient` with `ASGITransport` — no server process needed
