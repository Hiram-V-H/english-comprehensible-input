import { el } from '../../utils/dom.js';
import { showModal } from '../shared/modal.js';

/**
 * Open a full-text editor modal.
 * @param {string} contentText — current article content_text
 * @returns {Promise<string|null>} — new content_text or null if cancelled
 */
export async function showFullTextEditor(contentText) {
    const textarea = el('textarea', {
        className: 'full-text-editor',
        rows: 20,
    });
    // Set value directly — el()'s setAttribute('value',...) doesn't work for textarea
    textarea.value = contentText;

    const bodyEl = el('div', { className: 'modal-body' }, [textarea]);

    // Capture the value before the modal removes the textarea from DOM
    // showModal's close() calls overlay.remove() BEFORE resolving the promise,
    // which can cause textarea.value to return empty in some browsers.
    let savedText = null;
    const actions = [
        { label: '取消', value: false },
        {
            label: '保存修改',
            value: 'save',
            primary: true,
            onClick: () => { savedText = textarea.value.trim(); },
        },
    ];

    // Build custom modal using the same pattern as showModal
    const result = await new Promise((resolve) => {
        const overlay = el('div', {
            className: 'modal-overlay',
            onClick: (e) => { if (e.target === overlay) { resolve(false); overlay.remove(); } },
        });

        const actionBtns = actions.map(a =>
            el('button', {
                className: 'btn ' + (a.primary ? 'btn-primary' : ''),
                onClick: () => {
                    if (a.onClick) a.onClick();
                    resolve(a.value);
                    overlay.remove();
                },
            }, [a.label])
        );

        const modal = el('div', { className: 'modal-box' }, [
            el('h2', {}, ['📝 编辑正文']),
            bodyEl,
            el('div', { className: 'modal-actions' }, actionBtns),
        ]);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
    });

    if (result !== 'save') return null;
    if (!savedText) return null;
    if (savedText === contentText) return null;

    return savedText;
}
