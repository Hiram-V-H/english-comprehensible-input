import { el, clearElement } from '../utils/dom.js';
import { api } from '../api.js';
import { router } from '../router.js';
import { formatDate, formatPercent } from '../utils/formatters.js';

const STRIPE_GRADIENTS = [
    'linear-gradient(90deg, #8b6a4a, #c4a040, #6b4a2a)',
    'linear-gradient(90deg, #6b4a2a, #8b6a4a, #6b4a2a)',
    'linear-gradient(90deg, #5a8a4a, #7ab06a, #5a8a4a)',
    'linear-gradient(90deg, #8b6a9a, #a090b0, #8b6a9a)',
    'linear-gradient(90deg, #b8705a, #c4907a, #b8705a)',
];

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
            const chapterList = el('div');
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

                    let barColor, barBg;
                    if (unknownDensity == null) {
                        barColor = '#a08060';
                        barBg = '#a08060';
                    } else if (unknownDensity < 0.05) {
                        barColor = '#5a8a4a';
                        barBg = 'linear-gradient(90deg, #5a8a4a, #7ab06a)';
                    } else if (unknownDensity < 0.15) {
                        barColor = '#c4a040';
                        barBg = 'linear-gradient(90deg, #c4a040, #d4b860)';
                    } else {
                        barColor = '#b8543a';
                        barBg = 'linear-gradient(90deg, #b8543a, #c8705a)';
                    }

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
