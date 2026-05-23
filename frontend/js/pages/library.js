import { el } from '../utils/dom.js';
import { api } from '../api.js';
import { formatDate, formatPercent } from '../utils/formatters.js';
import { router } from '../router.js';

const STRIPE_GRADIENTS = [
    'linear-gradient(90deg, #8b6a4a, #c4a040, #6b4a2a)',
    'linear-gradient(90deg, #6b4a2a, #8b6a4a, #6b4a2a)',
    'linear-gradient(90deg, #5a8a4a, #7ab06a, #5a8a4a)',
    'linear-gradient(90deg, #8b6a9a, #a090b0, #8b6a9a)',
    'linear-gradient(90deg, #b8705a, #c4907a, #b8705a)',
];

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

    const i1score = article.i_plus_one_score != null
        ? (article.i_plus_one_score >= 0.8 ? 'Ideal' : article.i_plus_one_score >= 0.5 ? 'Challenging' : 'Difficult')
        : null;

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
