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
        value: contentText,
        rows: 20,
    });

    const bodyEl = el('div', { className: 'modal-body' }, [textarea]);

    const result = await showModal('📝 编辑正文', bodyEl, [
        { label: '取消', value: false },
        { label: '保存修改', value: 'save', primary: true },
    ]);

    if (result !== 'save') return null;

    const newText = textarea.value.trim();
    if (!newText) return null;
    if (newText === contentText) return null;

    return newText;
}
