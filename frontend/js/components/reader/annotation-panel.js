import { el, clearElement } from '../../utils/dom.js';
import { api } from '../../api.js';
import { showToast } from '../shared/toast.js';

/**
 * Sidebar panel displaying annotations for highlights.
 */
export class AnnotationPanel {
    constructor(container) {
        this.container = container;
        this.articleId = null;
        this.highlights = [];
        this.annotations = [];
        this._onRefresh = null;
    }

    setOnRefresh(cb) { this._onRefresh = cb; }

    render(articleId, highlights, annotations) {
        this.articleId = articleId;
        this.highlights = highlights;
        this.annotations = annotations;
        clearElement(this.container);

        this.container.appendChild(el('h3', { style: 'font-size:16px;margin-bottom:12px' }, ['Annotations']));

        if (highlights.length === 0 && annotations.length === 0) {
            this.container.appendChild(el('p', { style: 'color:var(--color-text-secondary);font-size:13px' }, [
                'Select text to create highlights and add notes.',
            ]));
            return;
        }

        for (const hl of highlights) {
            const hlAnns = annotations.filter(a => a.highlight_id === hl.id);
            const item = el('div', { className: 'annotation-item' });
            item.appendChild(el('div', { style: 'display:flex;align-items:center;gap:8px;margin-bottom:4px' }, [
                el('span', { style: `display:inline-block;width:12px;height:12px;border-radius:2px;background:${hl.color};flex-shrink:0` }),
                el('span', { style: 'font-size:13px;font-style:italic;color:var(--color-text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap' }, ['"' + hl.selected_text.substring(0, 50) + '"']),
                el('button', {
                    className: 'btn btn-sm btn-danger',
                    style: 'margin-left:auto;flex-shrink:0',
                    onClick: async () => {
                        try {
                            await api.deleteHighlight(this.articleId, hl.id);
                            showToast('Highlight deleted', 'success');
                            if (this._onRefresh) this._onRefresh();
                        } catch (e) { showToast(e.message, 'error'); }
                    },
                }, ['Del']),
            ]));

            // Annotations for this highlight
            for (const ann of hlAnns) {
                item.appendChild(el('div', { style: 'margin-left:20px;font-size:13px;padding:4px 0' }, [
                    el('div', { style: 'color:var(--color-text-secondary);font-size:11px' }, [ann.annotation_type]),
                    el('div', {}, [ann.content]),
                ]));
            }

            // Add annotation button
            item.appendChild(el('button', {
                className: 'btn btn-sm',
                style: 'margin-left:20px;margin-top:4px',
                onClick: async () => {
                    const textarea = el('textarea', { className: 'form-textarea', placeholder: 'Add note...', style: 'min-height:50px;font-size:13px' });
                    const saveBtn = el('button', { className: 'btn btn-sm btn-primary', style: 'margin-top:4px' }, ['Save']);
                    textarea.addEventListener('keydown', (e) => { e.stopPropagation(); });
                    const formDiv = el('div', { style: 'margin-left:20px' }, [textarea, saveBtn]);
                    item.appendChild(formDiv);

                    saveBtn.addEventListener('click', async () => {
                        const content = textarea.value.trim();
                        if (!content) return;
                        try {
                            await api.createAnnotation(hl.id, { content, annotation_type: 'note' });
                            showToast('Note saved', 'success');
                            if (this._onRefresh) this._onRefresh();
                        } catch (e) { showToast(e.message, 'error'); }
                    });
                },
            }, ['+ Note']));

            this.container.appendChild(item);
        }
    }
}
