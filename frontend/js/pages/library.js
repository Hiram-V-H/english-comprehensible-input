import { el } from '../utils/dom.js';
import { api } from '../api.js';
import { formatDate, formatPercent } from '../utils/formatters.js';
import { router } from '../router.js';

export function libraryPage(main) {
    main.appendChild(el('div', { className: 'page-header' }, [
        el('h1', { className: 'page-title' }, ['Article Library']),
    ]));

    const content = el('div');
    main.appendChild(content);

    async function load() {
        content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        try {
            const data = await api.getArticles({ sort: 'created_at', per_page: 50 });
            if (!data.items || data.items.length === 0) {
                content.innerHTML = '<div class="empty-state"><h3>No articles yet</h3><p>Import an article to get started.</p></div>';
                return;
            }
            const grid = el('div', { className: 'article-grid' });
            for (const a of data.items) {
                grid.appendChild(renderArticleCard(a));
            }
            content.innerHTML = '';
            content.appendChild(grid);
        } catch (e) {
            content.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
        }
    }

    load();
}

function renderArticleCard(article) {
    const unknownDensity = article.unknown_word_count != null && article.word_count
        ? article.unknown_word_count / article.word_count
        : null;

    return el('div', {
        className: 'card',
        onClick: () => router.navigate('#/reader/' + article.id),
        style: { cursor: 'pointer' },
    }, [
        el('div', { className: 'article-card-title' }, [article.title]),
        el('div', { className: 'article-card-meta' }, [
            el('span', {}, [article.word_count + ' words']),
            article.unknown_word_count != null ? el('span', {}, [article.unknown_word_count + ' new']) : null,
            el('span', {}, [formatDate(article.created_at)]),
        ]),
        unknownDensity != null ? el('div', { className: 'difficulty-bar' }, [
            el('div', { className: 'difficulty-bar-inner', style: { width: (unknownDensity * 100) + '%' } }),
        ]) : null,
    ]);
}
