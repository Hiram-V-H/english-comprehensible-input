import { el } from '../utils/dom.js';
import { router } from '../router.js';
import { STRIPE_GRADIENTS } from '../utils/card-utils.js';
import { showModal } from '../components/shared/modal.js';
import { showToast } from '../components/shared/toast.js';
import { api } from '../api.js';

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
                    className: 'article-card card',
                    dataset: { bookId: String(book.id) },
                    onClick: () => router.navigate('#/books/' + book.id),
                    style: { cursor: 'pointer' },
                }, [
                    el('div', { className: 'article-card-top-stripe', style: { background: stripeColor } }),
                    el('div', { className: 'article-card-title' }, [book.title]),
                    book.author ? el('div', { className: 'article-card-author' }, [book.author]) : null,
                    el('div', { className: 'article-card-meta' }, [
                        el('span', {}, [(book.total_chapters || 0) + ' chapters']),
                    ]),
                    el('div', { className: 'card-actions' }, [
                        el('button', {
                            className: 'card-action-btn card-delete-btn',
                            title: '删除',
                            textContent: '×',
                            onClick: (e) => {
                                e.stopPropagation();
                                deleteBook(book);
                            },
                        }),
                    ]),
                ]));
            }
            content.appendChild(grid);
        } catch (e) {
            content.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
        }
    })();

    async function deleteBook(book) {
        const bodyEl = document.createElement('div');
        bodyEl.className = 'modal-body';
        bodyEl.innerHTML = `
            <p>确定要删除 <strong>${book.title}</strong> 吗？</p>
            <p style="color: var(--color-unknown); font-size: 0.85em; margin-top: 8px;">
                此操作不可撤销，本书的所有章节也会被删除。
            </p>
        `;

        const confirmed = await showModal('⚠️ 确认删除', bodyEl, [
            { label: '取消', value: false },
            { label: '确认删除', value: true, primary: true },
        ]);

        if (!confirmed) return;

        try {
            await api.deleteBook(book.id);
            const card = document.querySelector(`.article-card[data-book-id="${book.id}"]`);
            if (card) {
                card.style.opacity = '0';
                card.style.transition = 'opacity 0.15s';
                setTimeout(() => card.remove(), 150);
            }
            showToast('已删除「${book.title}」', 'success');
        } catch (err) {
            showToast('删除失败，请重试', 'error');
        }
    }
}
