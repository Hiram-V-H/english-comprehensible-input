import { el, clearElement } from '../utils/dom.js';
import { api } from '../api.js';
import { router } from '../router.js';
import { formatDate, formatPercent } from '../utils/formatters.js';
import { STRIPE_GRADIENTS, getDifficultyColors } from '../utils/card-utils.js';
import { renderTocTree, buildChapterMap } from '../components/toc-tree.js';
import { showModal } from '../components/shared/modal.js';
import { showToast } from '../components/shared/toast.js';

export function bookDetailPage(main, bookId) {
    main.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    (async () => {
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
                showToast('已删除「${book.title}」', 'success');
                router.navigate('#/books');
            } catch (err) {
                showToast('删除失败，请重试', 'error');
            }
        }

        try {
            const resp = await fetch('/api/books/' + bookId);
            const json = await resp.json();
            const book = json.data;

            main.innerHTML = '';

            // Header
            main.appendChild(el('div', { className: 'page-header' }, [
                el('div', { style: 'flex:1' }, [
                    el('h1', { className: 'page-title' }, [book.title]),
                    book.author ? el('div', { style: 'color:var(--color-text-secondary);font-size:14px;margin-top:4px' }, ['by ' + book.author]) : null,
                ]),
                el('div', { className: 'header-actions' }, [
                    el('button', {
                        className: 'btn btn-danger',
                        textContent: '🗑 删除本书',
                        onClick: () => deleteCurrentBook(book),
                    }),
                ]),
            ]));

            // Chapters section — centered with constrained width
            const chapterWrapper = el('div', { style: 'max-width:640px;margin:0 auto' });

            if (book.chapters && book.chapters.length > 0) {
                const chapterMap = buildChapterMap(book.chapters);
                const chapterById = {};
                for (const ch of book.chapters) {
                    chapterById[ch.id] = ch;
                }

                // Use TOC tree if available, otherwise fall back to flat list
                if (book.toc_tree && book.toc_tree.length > 0) {
                    chapterWrapper.appendChild(el('h3', { style: 'margin-bottom:12px;font-family:var(--font-display);font-size:16px;color:var(--color-text-secondary)' }, [
                        `Contents (${book.chapters.length} chapters)`,
                    ]));
                    chapterWrapper.appendChild(renderTocTree(book.toc_tree, chapterMap, null));
                } else {
                    chapterWrapper.appendChild(el('h3', { style: 'margin-bottom:12px;font-family:var(--font-display);font-size:16px;color:var(--color-text-secondary)' }, [
                        `Chapters (${book.chapters.length})`,
                    ]));

                    for (let i = 0; i < book.chapters.length; i++) {
                        const ch = book.chapters[i];
                        const stripeColor = STRIPE_GRADIENTS[i % STRIPE_GRADIENTS.length];

                        const unknownDensity = ch.unknown_word_count != null && ch.word_count
                            ? ch.unknown_word_count / ch.word_count
                            : null;

                        const diffColors = getDifficultyColors(unknownDensity);
                        const barColor = diffColors.barColor;
                        const barBg = diffColors.barBg;

                        const card = el('div', {
                            className: 'card',
                            onClick: () => router.navigate('#/reader/' + ch.id),
                            style: { cursor: 'pointer' },
                        }, [
                            el('div', { className: 'article-card-top-stripe', style: { background: stripeColor } }),
                            el('div', { className: 'article-card-title' }, ['Ch. ' + (ch.chapter_index ?? i + 1) + ': ' + ch.title]),
                            el('div', { className: 'article-card-meta' }, [
                                ch.unknown_word_count != null ? el('span', {}, [
                                    el('span', { className: 'meta-dot', style: { background: barColor } }),
                                    ch.unknown_word_count + ' new',
                                ]) : null,
                                el('span', {}, [(ch.word_count || 0) + ' words']),
                            ]),
                            unknownDensity != null ? el('div', { className: 'difficulty-bar' }, [
                                el('div', { className: 'difficulty-bar-inner', style: { width: (100 - unknownDensity * 100) + '%', background: barBg } }),
                            ]) : null,
                            unknownDensity != null ? el('div', { className: 'difficulty-label' }, [
                                el('span', {}, [formatPercent(1 - unknownDensity) + ' known']),
                            ]) : null,
                        ]);
                        chapterWrapper.appendChild(card);
                    }
                }
            } else {
                chapterWrapper.appendChild(el('p', { style: 'color:var(--color-text-secondary)' }, ['No chapters imported.']));
            }

            main.appendChild(chapterWrapper);

        } catch (e) {
            main.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
        }
    })();
}
