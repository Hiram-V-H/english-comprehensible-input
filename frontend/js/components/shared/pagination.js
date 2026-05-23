import { el } from '../../utils/dom.js';

export function renderPagination(page, totalPages, onPageChange) {
    if (totalPages <= 1) return el('div');

    const items = [];
    const pages = getVisiblePages(page, totalPages);

    // Prev button
    items.push(el('button', {
        disabled: page === 1 ? '' : undefined,
        onClick: () => { if (page > 1) onPageChange(page - 1); },
    }, ['←']));

    for (const p of pages) {
        if (p === '...') {
            items.push(el('span', { style: 'padding:4px 4px;color:var(--color-text-subtle);font-size:12px' }, ['…']));
        } else {
            items.push(el('button', {
                className: p === page ? 'active' : '',
                onClick: () => onPageChange(p),
            }, [String(p)]));
        }
    }

    // Next button
    items.push(el('button', {
        disabled: page === totalPages ? '' : undefined,
        onClick: () => { if (page < totalPages) onPageChange(page + 1); },
    }, ['→']));

    return el('div', { className: 'pagination' }, items);
}

function getVisiblePages(current, total) {
    if (total <= 7) {
        const result = [];
        for (let i = 1; i <= total; i++) result.push(i);
        return result;
    }

    const pages = [];

    // Always show first page
    pages.push(1);

    if (current > 3) {
        pages.push('...');
    }

    // Pages around current
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) {
        pages.push(i);
    }

    if (current < total - 2) {
        pages.push('...');
    }

    // Always show last page
    if (total > 1) {
        pages.push(total);
    }

    return pages;
}
