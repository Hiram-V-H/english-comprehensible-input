import { el, clearElement } from '../utils/dom.js';
import { api } from '../api.js';
import { router } from '../router.js';
import { ArticleDisplay } from '../components/reader/article-display.js';
import { ContentRenderer } from '../components/reader/content-renderer.js';
import { applyWordAnnotations, updateWordStatus } from '../components/reader/annotator.js';
import { WordPopup } from '../components/reader/word-popup.js';
import { SelectionHandler } from '../components/reader/selection-handler.js';
import { HighlightOverlay } from '../components/reader/highlight-overlay.js';
import { AnnotationPanel } from '../components/reader/annotation-panel.js';
import { ReaderToolbar } from '../components/reader/reader-toolbar.js';
import { showToast } from '../components/shared/toast.js';
import { renderTocTree, buildChapterMap } from '../components/toc-tree.js';

export function readerPage(main, articleId) {
    main.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    let readerData = null;
    let sessionId = null;
    let highlightsVisible = true;
    let isNativeRenderer = false;  // true when using ContentRenderer (annotated_html)

    (async () => {
        try {
            readerData = await api.getReaderData(articleId);

            try { const s = await api.startSession(articleId); sessionId = s.session_id; } catch (e) { /* ignore */ }

            main.innerHTML = '';
            main.style.padding = '0';
            main.style.maxWidth = 'none';

            // ── Outer container ──
            const readerContainer = el('div', { className: 'reader-container' });

            // ── Book chapter navigation ──
            if (readerData.book) {
                const navEl = renderChapterNav(readerData.book, articleId);
                readerContainer.appendChild(navEl);
            }

            // Toolbar
            const toolbarEl = el('div');
            readerContainer.appendChild(toolbarEl);
            const toolbar = new ReaderToolbar(toolbarEl, readerData.article);
            toolbar.setOnBack(() => {
                if (sessionId) { api.endSession(articleId, sessionId, {}).catch(() => {}); }
                if (readerData.book) {
                    router.navigate('#/books/' + readerData.book.book_id);
                } else {
                    router.navigate('#/library');
                }
            });
            toolbar.setOnToggleHighlights(() => {
                highlightsVisible = !highlightsVisible;
                if (highlightsVisible) {
                    overlay.apply(readerData.highlights, readerData.paragraphs);
                } else {
                    overlay.removeAll();
                }
            });
            toolbar.render();

            // ── Body: content + sidebar ──
            const bodyEl = el('div', { className: 'reader-body' });
            const contentEl = el('div', { className: 'reader-content' });
            const textEl = el('div', { className: 'reader-text' });

            // Determine rendering path: native HTML or legacy ArticleDisplay
            const hasAnnotatedHtml = readerData.article.annotated_html;
            let display;  // unified interface: { render(), updateWordStatus() }
            let renderer = null;

            if (hasAnnotatedHtml) {
                isNativeRenderer = true;
                renderer = new ContentRenderer(textEl);
                display = {
                    render(data) {
                        renderer.render(data.article.annotated_html);
                        applyWordAnnotations(textEl, data.paragraphs);
                    },
                    updateWordStatus(pos, status) {
                        updateWordStatus(textEl, pos, status);
                    },
                };

                // Wire toolbar font-size and theme controls
                toolbar.setOnFontSizeChange((delta) => {
                    renderer.setFontSize(renderer.fontSize + delta);
                });
                toolbar.setOnThemeToggle(() => {
                    const next = renderer.theme === 'dark' ? 'light' : 'dark';
                    renderer.setTheme(next);
                });
            } else {
                const articleDisplay = new ArticleDisplay(textEl, {
                    onWordClick: (wordData) => {
                        popup.show(wordData);
                        if (wordData.wordId) {
                            api.recordEncounter(articleId, wordData.wordId).catch(() => {});
                        }
                    },
                    onSelectionComplete: (selData) => {
                        selectionHandler.showMenu(selData);
                    },
                });
                display = articleDisplay;
            }

            const popup = new WordPopup();
            popup.setOnStatusChange((position, newStatus) => {
                display.updateWordStatus(position, newStatus);
            });

            const selectionHandler = new SelectionHandler(contentEl, articleId, async () => {
                readerData = await api.getReaderData(articleId);
                panel.refresh(readerData);
                overlay.removeAll();
                overlay.apply(readerData.highlights, readerData.paragraphs);
            });

            const overlay = new HighlightOverlay(contentEl);

            contentEl.appendChild(textEl);

            // Sidebar — annotations or book TOC
            const sidebarEl = el('div', { className: 'reader-sidebar' });
            const panel = new AnnotationPanel(sidebarEl);
            panel.refresh = async (data) => {
                panel.render(articleId, data.highlights, data.annotations);
                overlay.removeAll();
                overlay.apply(data.highlights, data.paragraphs);
            };
            panel.setOnRefresh(async () => {
                readerData = await api.getReaderData(articleId);
                panel.refresh(readerData);
            });

            if (readerData.book) {
                const tocEl = renderBookTOC(readerData.book, articleId);
                sidebarEl.appendChild(tocEl);
            }

            bodyEl.appendChild(contentEl);
            bodyEl.appendChild(sidebarEl);
            readerContainer.appendChild(bodyEl);
            main.appendChild(readerContainer);

            // Render content
            display.render(readerData);

            // For native renderer, bind word click after DOM is populated
            if (isNativeRenderer) {
                textEl.addEventListener('click', (e) => {
                    const wordEl = e.target.closest('[data-position]');
                    if (!wordEl) return;
                    if (wordEl.dataset.status === 'punct') return;
                    const rect = wordEl.getBoundingClientRect();
                    popup.show({
                        wordId: wordEl.dataset.wordId || null,
                        wordText: wordEl.textContent,
                        wordLower: wordEl.dataset.wordLower || wordEl.textContent.toLowerCase(),
                        status: wordEl.dataset.status || 'unknown',
                        position: parseInt(wordEl.dataset.position),
                        rect,
                    });
                });
            }

            overlay.apply(readerData.highlights, readerData.paragraphs);
            panel.render(articleId, readerData.highlights, readerData.annotations);

            // Global click to dismiss popup
            const dismissHandler = (e) => {
                if (popup.visible && !e.target.closest('.word') && !e.target.closest('.word-popup')) {
                    popup.hide();
                }
            };
            document.addEventListener('click', dismissHandler);

            return () => {
                document.removeEventListener('click', dismissHandler);
                popup.hide();
                selectionHandler.hideMenu();
                if (sessionId) {
                    api.endSession(articleId, sessionId, {}).catch(() => {});
                }
            };

        } catch (e) {
            main.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
            main.style.padding = '24px';
            main.style.maxWidth = '1100px';
        }
    })();
}

// ── Chapter navigation bar ──────────────────────────────────

function renderChapterNav(book, currentArticleId) {
    const bar = el('div', { className: 'chapter-nav' });

    const prevBtn = el('button', {
        className: 'chapter-nav-btn',
        disabled: !book.prev_chapter ? '' : undefined,
        onClick: () => { if (book.prev_chapter) router.navigate('#/reader/' + book.prev_chapter.id); },
    }, [book.prev_chapter ? '◀ ' + book.prev_chapter.title : '◀']);
    bar.appendChild(prevBtn);

    bar.appendChild(el('span', { className: 'chapter-nav-info' }, [
        el('a', {
            href: '#/books/' + book.book_id,
            onClick: (e) => { e.preventDefault(); router.navigate('#/books/' + book.book_id); },
        }, [book.book_title]),
        el('span', { style: 'color:var(--color-text-secondary)' }, [
            ' — Chapter ' + ((book.current_chapter_index || 0) + 1) + ' / ' + book.total_chapters,
        ]),
    ]));

    const nextBtn = el('button', {
        className: 'chapter-nav-btn',
        disabled: !book.next_chapter ? '' : undefined,
        onClick: () => { if (book.next_chapter) router.navigate('#/reader/' + book.next_chapter.id); },
    }, [book.next_chapter ? book.next_chapter.title + ' ▶' : '▶']);
    bar.appendChild(nextBtn);

    return bar;
}

// ── Book TOC sidebar section ────────────────────────────────

function renderBookTOC(book, currentArticleId) {
    const toc = el('div', { className: 'book-toc' });
    toc.appendChild(el('h3', { style: 'font-size:14px;margin-bottom:8px;color:var(--color-text-secondary)' }, ['Contents']));

    const chapterMap = buildChapterMap(book.all_chapters || []);

    if (book.toc_tree && book.toc_tree.length > 0) {
        toc.appendChild(renderTocTree(book.toc_tree, chapterMap, parseInt(currentArticleId)));
    } else {
        for (const ch of (book.all_chapters || [])) {
            const isCurrent = ch.id === parseInt(currentArticleId);
            const link = el('a', {
                className: 'book-toc-item' + (isCurrent ? ' current' : ''),
                href: '#/reader/' + ch.id,
                onClick: (e) => { e.preventDefault(); router.navigate('#/reader/' + ch.id); },
                style: `display:block;padding:4px 8px;border-radius:4px;font-size:13px;text-decoration:none;color:${isCurrent ? 'var(--color-primary)' : 'var(--color-text)'};background:${isCurrent ? 'var(--color-primary-light)' : 'transparent'}`,
            }, [
                (isCurrent ? '▶ ' : '') + ch.title,
            ]);
            toc.appendChild(link);
        }
    }
    return toc;
}
