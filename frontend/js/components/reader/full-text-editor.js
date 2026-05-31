import { el } from '../../utils/dom.js';

/**
 * Open a full-text editor modal.
 * @param {string} contentText — current article content_text
 * @returns {Promise<string|null>} — new content_text or null if cancelled
 */
export async function showFullTextEditor(contentText) {
    return new Promise((resolve) => {
        const textarea = el('textarea', { className: 'full-text-editor', rows: 20 });
        textarea.value = contentText || '';

        // Build buttons inside the body so we read textarea.value BEFORE removing from DOM
        const cancelBtn = el('button', { className: 'btn', onClick: () => closeModal(null) }, ['取消']);
        const saveBtn = el('button', {
            className: 'btn btn-primary',
            onClick: () => {
                const val = (textarea.value || '').trim();
                if (!val) return;           // don't close if empty
                if (val === (contentText || '')) return; // don't close if unchanged
                closeModal(val);
            },
        }, ['保存修改']);

        const actionsEl = el('div', { className: 'modal-actions' }, [cancelBtn, saveBtn]);
        const bodyEl = el('div', { className: 'modal-body' }, [textarea, actionsEl]);

        // Modal overlay
        const overlay = el('div', {
            className: 'modal-overlay',
            onClick: (e) => { if (e.target === overlay) closeModal(null); },
        });
        const modal = el('div', { className: 'modal-box' }, [
            el('h2', {}, ['📝 编辑正文']),
            bodyEl,
        ]);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        function closeModal(value) {
            overlay.remove();
            resolve(value);
        }

        // Focus textarea
        setTimeout(() => textarea.focus(), 50);
    });
}
