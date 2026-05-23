import { el, clearElement } from '../utils/dom.js';
import { api } from '../api.js';
import { router } from '../router.js';
import { formatDate } from '../utils/formatters.js';

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
                for (const ch of book.chapters) {
                    const card = el('div', {
                        className: 'card',
                        style: 'cursor:pointer;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center',
                        onClick: () => router.navigate('#/reader/' + ch.id),
                    }, [
                        el('div', {}, [
                            el('div', { style: 'font-weight:600;font-size:14px' }, [ch.title]),
                            el('div', { style: 'color:var(--color-text-secondary);font-size:12px;margin-top:4px' }, [
                                (ch.word_count || 0) + ' words' +
                                (ch.unknown_word_count != null ? ' · ' + ch.unknown_word_count + ' new' : '') +
                                (ch.difficulty_score != null ? ' · difficulty: ' + (ch.difficulty_score * 100).toFixed(0) + '%' : ''),
                            ]),
                        ]),
                        el('span', { style: 'color:var(--color-text-secondary);font-size:18px' }, ['→']),
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
