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
import { showArticleEditor } from '../components/article-editor.js';
import { WordInlineEditor } from '../components/reader/word-inline-editor.js';
import { showFullTextEditor } from '../components/reader/full-text-editor.js';
import { showModal } from '../components/shared/modal.js';
import { renderTocTree, buildChapterMap } from '../components/toc-tree.js';
import { getSelectionCharOffsets, charOffsetsToWordPositions } from '../utils/text-offset.js';

export function readerPage(main, articleId) {

    main.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    let readerData = null;
    let sessionId = null;
    let highlightsVisible = true;
    let isNativeRenderer = false;  // true when using ContentRenderer (annotated_html)
    let readerCleanup = null;  // Stored by async setup, called by router on navigate away

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
            toolbar.setOnToggleSidebar(() => {
                const isHidden = sidebarEl.classList.toggle('hidden');
                // When hidden, completely remove sidebar and grip from layout
                sidebarEl.style.display = isHidden ? 'none' : '';
                resizeGrip.style.display = isHidden ? 'none' : '';
            });
            toolbar.setOnEdit(() => handleEditArticle(readerData.article));
            toolbar.setOnDelete(() => handleDeleteArticle(readerData.article));

            toolbar.setOnEditContent(() => handleEditContent());
            toolbar.render();

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

                // Clear and re-render
                if (readerData.article.annotated_html) {
                    // This shouldn't happen after edit (annotated_html is cleared)
                    // but handle it anyway for robustness
                    renderer.render(readerData.article.annotated_html);
                    applyWordAnnotations(textEl, readerData.paragraphs);
                } else {
                    // Fallback to ArticleDisplay
                    if (!articleDisplay) {
                        articleDisplay = new ArticleDisplay(textEl, {
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
                        isNativeRenderer = false;
                    }
                    articleDisplay.render(readerData);
                }

                // Re-apply highlights
                overlay.removeAll();
                if (readerData.highlights) {
                    overlay.apply(readerData.highlights, readerData.paragraphs);
                }

                // Refresh annotation panel
                panel.render(articleId, readerData.highlights, readerData.annotations);

                // Restore scroll position
                window.scrollTo(0, Math.min(scrollTop, document.body.scrollHeight));
            }

            // ── Body: content + sidebar ──
            const bodyEl = el('div', { className: 'reader-body' });
            const contentEl = el('div', { className: 'reader-content' });
            const textEl = el('div', { className: 'reader-text' });

            // Init inline word editor (must be after textEl declaration)
            const inlineEditor = new WordInlineEditor(textEl);

            // Determine rendering path: native HTML or legacy ArticleDisplay
            const hasAnnotatedHtml = readerData.article.annotated_html;
            let display;  // unified interface: { render(), updateWordStatus() }
            let renderer = null;
            let articleDisplay = null;

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
                articleDisplay = new ArticleDisplay(textEl, {
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

            // Resize grip — standalone element between content and sidebar
            const resizeGrip = el('div', { className: 'reader-resize-grip' });

            // Restore saved sidebar width
            const savedWidth = localStorage.getItem('reader-sidebar-width');
            if (savedWidth) {
                sidebarEl.style.width = savedWidth + 'px';
            }

            // Drag-to-resize logic
            let resizeDragging = false;
            let resizeStartX = 0;
            let resizeStartWidth = 0;

            resizeGrip.addEventListener('mousedown', (e) => {
                e.preventDefault();
                resizeDragging = true;
                resizeStartX = e.clientX;
                resizeStartWidth = sidebarEl.offsetWidth;
                resizeGrip.classList.add('dragging');
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
            });

            document.addEventListener('mousemove', (e) => {
                if (!resizeDragging) return;
                const delta = resizeStartX - e.clientX;  // drag left = narrower sidebar
                const newWidth = Math.max(100, Math.min(500, resizeStartWidth + delta));
                sidebarEl.style.width = newWidth + 'px';
            });

            document.addEventListener('mouseup', () => {
                if (!resizeDragging) return;
                resizeDragging = false;
                resizeGrip.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                localStorage.setItem('reader-sidebar-width', sidebarEl.offsetWidth);
            });

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
            bodyEl.appendChild(resizeGrip);
            bodyEl.appendChild(sidebarEl);
            readerContainer.appendChild(bodyEl);
            main.appendChild(readerContainer);

            // Render content
            display.render(readerData);

            // For native renderer, bind word click and text selection after DOM is populated
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

                // Text selection → highlight creation
                textEl.addEventListener('mouseup', () => {
                    setTimeout(() => {
                        const offsets = getSelectionCharOffsets(textEl);
                        if (offsets && readerData) {
                            const positions = charOffsetsToWordPositions(
                                readerData.paragraphs,
                                offsets.start_char_offset,
                                offsets.end_char_offset,
                            );
                            selectionHandler.showMenu({ ...offsets, ...(positions || {}) });
                        } else {
                            selectionHandler.showMenu(null);
                        }
                    }, 10);
                });
            }

            // Double-click to edit: detect dblclicks on word spans
            textEl.addEventListener('dblclick', (e) => {
                const span = e.target.closest('[data-position]');
                if (!span) return;

                const position = parseInt(span.dataset.position, 10);
                if (isNaN(position)) return;

                // Find word data in paragraphs
                let wordData = null;
                for (const para of readerData.paragraphs) {
                    const found = para.words.find(w => w.position === position);
                    if (found) { wordData = found; break; }
                }
                if (!wordData || wordData.status === 'punct') return;

                // Get char_offset from dataset or wordData
                const charOffset = parseInt(span.dataset.charOffset, 10);

                inlineEditor.open(span, {
                    text: wordData.text,
                    char_offset: isNaN(charOffset) ? wordData.char_offset : charOffset,
                    position: wordData.position,
                }, readerData.article.content_text).then(async (result) => {
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

            overlay.apply(readerData.highlights, readerData.paragraphs);
            panel.render(articleId, readerData.highlights, readerData.annotations);

            // Global click to dismiss popup
            const dismissHandler = (e) => {
                if (popup.visible && !e.target.closest('.word') && !e.target.closest('.word-popup')) {
                    popup.hide();
                }
            };
            document.addEventListener('click', dismissHandler);

            readerCleanup = () => {
                // Reset inline styles set on #app-main for reader layout
                main.style.padding = '';
                main.style.maxWidth = '';
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

    // Return cleanup wrapper for the router to call on navigation
    return () => {
        if (readerCleanup) readerCleanup();
    };
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
