import { el } from '../utils/dom.js';
import { router } from '../router.js';

export function booksPage(main) {
    main.appendChild(el('div', { className: 'page-header' }, [
        el('h1', { className: 'page-title' }, ['Books']),
    ]));

    const content = el('div');
    main.appendChild(content);

    (async () => {
        content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        try {
            const resp = await fetch('/api/books');
            const json = await resp.json();
            const items = json.data.items || [];

            if (items.length === 0) {
                content.innerHTML = '<div class="empty-state"><h3>No books yet</h3><p>Import an EPUB file to get started.</p></div>';
                return;
            }

            content.innerHTML = '';
            const grid = el('div', { className: 'article-grid' });
            for (const book of items) {
                grid.appendChild(el('div', {
                    className: 'card',
                    onClick: () => router.navigate('#/books/' + book.id),
                    style: 'cursor:pointer',
                }, [
                    el('div', { className: 'article-card-title' }, [book.title]),
                    el('div', { className: 'article-card-meta' }, [
                        book.author ? el('span', {}, ['by ' + book.author]) : null,
                        el('span', {}, [(book.total_chapters || 0) + ' chapters']),
                    ]),
                ]));
            }
            content.appendChild(grid);
        } catch (e) {
            content.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
        }
    })();
}
