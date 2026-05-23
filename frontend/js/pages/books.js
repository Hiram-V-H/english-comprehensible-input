import { el } from '../utils/dom.js';
import { router } from '../router.js';
import { formatDate } from '../utils/formatters.js';

const STRIPE_GRADIENTS = [
    'linear-gradient(90deg, #8b6a4a, #c4a040, #6b4a2a)',
    'linear-gradient(90deg, #6b4a2a, #8b6a4a, #6b4a2a)',
    'linear-gradient(90deg, #5a8a4a, #7ab06a, #5a8a4a)',
    'linear-gradient(90deg, #8b6a9a, #a090b0, #8b6a9a)',
    'linear-gradient(90deg, #b8705a, #c4907a, #b8705a)',
];

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
            for (let i = 0; i < items.length; i++) {
                const book = items[i];
                const stripeColor = STRIPE_GRADIENTS[i % STRIPE_GRADIENTS.length];
                grid.appendChild(el('div', {
                    className: 'card',
                    onClick: () => router.navigate('#/books/' + book.id),
                    style: { cursor: 'pointer' },
                }, [
                    el('div', { className: 'article-card-top-stripe', style: { background: stripeColor } }),
                    el('div', { className: 'article-card-title' }, [book.title]),
                    book.author ? el('div', { className: 'article-card-author' }, [book.author]) : null,
                    el('div', { className: 'article-card-meta' }, [
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
