import { el } from '../utils/dom.js';
import { api } from '../api.js';
import { formatDate, formatPercent } from '../utils/formatters.js';
import { router } from '../router.js';
import { STRIPE_GRADIENTS, getDifficultyColors, getI1ScoreLabel } from '../utils/card-utils.js';

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
            for (let i = 0; i < data.items.length; i++) {
                grid.appendChild(renderArticleCard(data.items[i], i));
            }
            grid.appendChild(createImportPlaceholder());
            content.innerHTML = '';
            content.appendChild(grid);
        } catch (e) {
            content.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
        }
    }

    load();
}

function renderArticleCard(article, index) {
    const stripeColor = STRIPE_GRADIENTS[index % STRIPE_GRADIENTS.length];
    const unknownDensity = article.unknown_word_count != null && article.word_count
        ? article.unknown_word_count / article.word_count
        : null;

    const diffColors = getDifficultyColors(unknownDensity);
    const barColor = diffColors.barColor;
    const barBg = diffColors.barBg;

    const i1score = getI1ScoreLabel(article.i_plus_one_score);

    return el('div', {
        className: 'card',
        onClick: () => router.navigate('#/reader/' + article.id),
        style: { cursor: 'pointer' },
    }, [
        el('div', { className: 'article-card-top-stripe', style: { background: stripeColor } }),
        el('div', { className: 'article-card-title' }, [article.title]),
        article.author ? el('div', { className: 'article-card-author' }, [article.author]) : null,
        el('div', { className: 'article-card-meta' }, [
            article.unknown_word_count != null ? el('span', {}, [
                el('span', { className: 'meta-dot', style: { background: barColor } }),
                article.unknown_word_count + ' new',
            ]) : null,
            el('span', {}, [article.word_count + ' words']),
            el('span', { style: 'margin-left:auto' }, [formatDate(article.created_at)]),
        ]),
        unknownDensity != null ? el('div', { className: 'difficulty-bar' }, [
            el('div', { className: 'difficulty-bar-inner', style: { width: (100 - unknownDensity * 100) + '%', background: barBg } }),
        ]) : null,
        unknownDensity != null ? el('div', { className: 'difficulty-label' }, [
            el('span', {}, [formatPercent(1 - unknownDensity) + ' known']),
            i1score ? el('span', {}, ['i+1: ' + i1score]) : null,
        ]) : null,
    ]);
}

function createImportPlaceholder() {
    return el('div', {
        className: 'card-import-placeholder',
        onClick: () => router.navigate('#/import'),
    }, [
        el('div', {}, [
            el('div', { style: 'font-size:24px;margin-bottom:4px' }, ['+']),
            el('div', {}, ['Import new article']),
        ]),
    ]);
}
