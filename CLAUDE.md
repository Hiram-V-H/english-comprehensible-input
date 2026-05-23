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
- **`annotated_html` field**: when an article has `annotated_html` (generated during EPUB import), the frontend renders it directly as semantic HTML via `ContentRenderer`; articles without it (txt, md, legacy imports) fall back to `ArticleDisplay` which builds DOM from token arrays

**Character-offset highlight anchoring** (`frontend/js/utils/text-offset.js`):
- Highlights are stored as `(start_char_offset, end_char_offset)` into `article.content_text`, not as DOM nodes
- Word spans render with `data-char-offset` attributes; when the user selects text, offsets are computed from the DOM, and when highlights are rendered, offsets are mapped back to word spans
- This means the renderer can be rewritten (React, canvas, etc.) without losing highlight data
- **Selector contract**: uses `[data-position]` attribute selectors, compatible with both `ContentRenderer` (annotated HTML) and `ArticleDisplay` (JS-built DOM) paths

**Reader Core / Learning Overlay separation**:
- **Reader Core** (`ContentRenderer` in `frontend/js/components/reader/content-renderer.js`): renders `annotated_html` via innerHTML; manages font size, line height, light/dark theme; settings persisted to localStorage; knows NOTHING about word status, highlights, or vocabulary
- **Learning Overlay** (`annotator.js` in `frontend/js/components/reader/annotator.js`): post-render step that walks `[data-position]` spans and adds `word--{status}` CSS classes based on `paragraphs[].words[].status` data; `updateWordStatus()` updates a single span's class when the user changes a word's learning status
- **Fallback**: when `annotated_html` is null (txt, md, legacy EPUB imports), the reader uses the legacy `ArticleDisplay` class which builds the DOM from paragraph token arrays — fully backward compatible
- Highlight overlay, word popup, selection handler, and annotation panel all work through `[data-position]` attribute selectors, agnostic to which rendering path is active

**EPUB import: clean HTML + span injection pipeline**:
- `_html_to_clean_html()` (`backend/app/importers/epub_importer.py`): HTMLParser-based; strips `<script>`, `<style>`, `<img>`, `<svg>`, inline CSS; removes `class`/`id`/`style` attributes; preserves semantic tags (`<h1>`-`<h6>`, `<p>`, `<em>`, `<strong>`, `<blockquote>`, `<ul>`/`<ol>`/`<li>`, `<a href="...">`); decodes HTML entities
- `inject_word_spans()` (`backend/app/importers/epub_importer.py`): walks clean HTML text nodes, matches tokens by text in order, injects `<span data-position="N" data-char-offset="M" data-word-lower="w" data-word-id="M">` around each token; whitespace passes through unchanged; token mismatches emit as-is with a console warning
- **Import flow**: `_save_book_chapter` / `_save_article` tokenize `content_text` → build `span_tokens` list during `ArticleWord` creation → call `inject_word_spans(data.content_html, span_tokens)` → store in `Article.annotated_html`
- **Commit pattern**: `_save_book_chapter` only flushes (no commit); `import_book_chapters` calls `db.commit()` once after all chapters saved, then runs `CompositeAnalyzer` in batch — avoids per-article commit session-state conflicts
- **Deduplication**: `_parse_ncx` and `_parse_nav` use a `seen_paths` set to skip duplicate `source_path` values; TOC tree retains full hierarchy, flat chapter list contains only unique files
- `Article.annotated_html` column added by migration `007_add_annotated_html.py`

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
- **Reader components** (`frontend/js/components/reader/`):
  - `content-renderer.js` — Reader Core: `render(annotatedHtml)` via innerHTML; `setFontSize/LineHeight/Theme` persisted to localStorage
  - `annotator.js` — Learning Overlay: `applyWordAnnotations(container, paragraphs)` walks `[data-position]` spans and adds `word--{status}` classes; `updateWordStatus(container, position, newStatus)` for single-word status changes
  - `article-display.js` — Legacy fallback: builds DOM from `paragraphs[].words[]` token arrays; used when `annotated_html` is null
  - `highlight-overlay.js` — Uses `[data-position]` selector; compatible with both rendering paths
  - `reader-toolbar.js` — Back, title, word count, i+1 score, font size A−/A+, theme toggle ◐, highlights toggle

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
- **CSS file roles**: `base.css` (tokens, reset, sidebar, buttons, badges, forms), `components.css` (toast, modal, cards, pagination, drop zone, tables, TOC tree), `reader.css` (reader layout, word states, popup, highlights, annotation panel, native HTML reader typography, dark theme), `vocabulary.css` (stats bar, word table, word detail, note cards)

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
- `Article.annotated_html` (Text) stores the clean semantic HTML with injected `<span data-position="N">` tags; generated at import time by `inject_word_spans()`; null for non-EPUB or legacy imports
- `Article.sha256_hash` deduplication: `_parse_ncx`/`_parse_nav` use `seen_paths` set to avoid creating duplicate `ChapterInfo` entries for the same `source_path`; TOC tree retains full hierarchy regardless
- Import commit pattern: `_save_book_chapter` uses `db.flush()` only; `import_book_chapters` calls `db.commit()` once after all chapters are saved, then runs batch analysis — avoids per-article commit session-state conflicts

### Test setup (`backend/tests/conftest.py`)

- In-memory SQLite with tables created per-test via `Base.metadata.create_all`
- DB dependency overridden to inject the test session
- `httpx.AsyncClient` with `ASGITransport` — no server process needed
