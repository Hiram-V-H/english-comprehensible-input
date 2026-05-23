import { el } from '../../utils/dom.js';

export function renderPagination(page, totalPages, onPageChange) {
    if (totalPages <= 1) return el('div');

    const items = [];
    for (let i = 1; i <= totalPages; i++) {
        items.push(el('button', {
            className: 'btn btn-sm' + (i === page ? ' btn-primary' : ''),
            onClick: () => onPageChange(i),
        }, [String(i)]));
    }
    return el('div', { className: 'pagination' }, items);
}
