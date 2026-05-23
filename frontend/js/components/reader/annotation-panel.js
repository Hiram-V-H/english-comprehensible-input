import { el, clearElement } from '../../utils/dom.js';
import { api } from '../../api.js';
import { showToast } from '../shared/toast.js';

const HIGHLIGHT_COLOR_MAP = {
    'gold': 'var(--hl-gold, #e6b422)',
    'sage': 'var(--hl-sage, #7d9b76)',
    'lavender': 'var(--hl-lavender, #9b8ec4)',
    'terracotta': 'var(--hl-terracotta, #c97d60)',
    'slate': 'var(--hl-slate, #7c8b9c)',
    'yellow': 'var(--hl-gold, #e6b422)',
    'green': 'var(--hl-sage, #7d9b76)',
    'blue': 'var(--hl-lavender, #9b8ec4)',
    'pink': 'var(--hl-terracotta, #c97d60)',
    'orange': 'var(--hl-slate, #7c8b9c)',
};

function getHighlightColor(colorValue) {
    return HIGHLIGHT_COLOR_MAP[colorValue] || 'var(--hl-gold, #e6b422)';
}

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

        this.container.appendChild(el('div', { className: 'sidebar-title' }, ['Annotations']));

        if (highlights.length === 0 && annotations.length === 0) {
            this.container.appendChild(el('p', { style: 'color:var(--color-text-secondary);font-size:13px' }, [
                'Select text to create highlights and add notes.',
            ]));
            return;
        }

        for (const hl of highlights) {
            const hlAnns = annotations.filter(a => a.highlight_id === hl.id);
            const highlightColor = getHighlightColor(hl.color);
            const item = el('div', {
                className: 'annotation-item',
                style: { borderLeft: '3px solid ' + highlightColor },
            });
            item.appendChild(el('div', { style: 'display:flex;align-items:center;gap:8px;margin-bottom:4px' }, [
                el('span', { className: 'ann-word' }, ['"' + hl.selected_text.substring(0, 50) + '"']),
                el('button', {
                    className: 'ann-delete',
                    onClick: async () => {
                        try {
                            await api.deleteHighlight(this.articleId, hl.id);
                            showToast('Highlight deleted', 'success');
                            if (this._onRefresh) this._onRefresh();
                        } catch (e) { showToast(e.message, 'error'); }
                    },
                }, ['×']),
            ]));

            // Annotations for this highlight
            for (const ann of hlAnns) {
                item.appendChild(el('div', { style: 'margin-left:0;font-size:13px;padding:4px 0' }, [
                    el('div', { style: 'color:var(--color-text-secondary);font-size:11px' }, [ann.annotation_type]),
                    el('div', { className: 'ann-text' }, [ann.content]),
                ]));
            }

            // Add annotation button
            item.appendChild(el('button', {
                className: 'ann-add-note',
                onClick: async () => {
                    const textarea = el('textarea', { className: 'form-textarea', placeholder: 'Add note...', style: 'min-height:50px;font-size:13px' });
                    const saveBtn = el('button', { className: 'btn btn-sm btn-primary', style: 'margin-top:4px' }, ['Save']);
                    textarea.addEventListener('keydown', (e) => { e.stopPropagation(); });
                    const formDiv = el('div', { style: 'margin-top:4px' }, [textarea, saveBtn]);
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
