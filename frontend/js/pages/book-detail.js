import { el, clearElement } from '../utils/dom.js';
import { api } from '../api.js';
import { router } from '../router.js';
import { formatDate, formatPercent } from '../utils/formatters.js';
import { STRIPE_GRADIENTS, getDifficultyColors } from '../utils/card-utils.js';

export function bookDetailPage(main, bookId) {
    main.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    (async () => {
        try {
            const resp = await fetch('/api/books/' + bookId);
            const json = await resp.json();
            const book = json.data;

            main.innerHTML = '';

            // Header
            main.appendChild(el('div', { className: 'page-header' }, [
                el('div', {}, [
                    el('h1', { className: 'page-title' }, [book.title]),
                    book.author ? el('div', { style: 'color:var(--color-text-secondary);font-size:14px;margin-top:4px' }, ['by ' + book.author]) : null,
                ]),
            ]));

            // Chapters list
            const chapterList = el('div', { style: 'max-width:640px' });
            chapterList.appendChild(el('h3', { style: 'margin-bottom:12px' }, [
                `Chapters (${(book.chapters || []).length})`,
            ]));

            if (book.chapters && book.chapters.length > 0) {
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
                    chapterList.appendChild(card);
                }
            } else {
                chapterList.appendChild(el('p', { style: 'color:var(--color-text-secondary)' }, ['No chapters imported.']));
            }

            main.appendChild(chapterList);

        } catch (e) {
            main.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
        }
    })();
}
