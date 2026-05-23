import { el } from '../../utils/dom.js';
import { api } from '../../api.js';
import { showToast } from '../shared/toast.js';

const HIGHLIGHT_COLORS = [
    { name: 'gold', css: 'hl-dot-gold' },
    { name: 'sage', css: 'hl-dot-sage' },
    { name: 'lavender', css: 'hl-dot-lavender' },
    { name: 'terracotta', css: 'hl-dot-terracotta' },
    { name: 'slate', css: 'hl-dot-slate' },
];

/**
 * Handles text selection → highlight creation via context menu.
 */
export class SelectionHandler {
    constructor(container, articleId, onHighlightCreated) {
        this.container = container;
        this.articleId = articleId;
        this.onHighlightCreated = onHighlightCreated;
        this._menu = null;
    }

    showMenu(selectionData) {
        this.hideMenu();
        if (!selectionData) return;

        const sel = window.getSelection();
        if (!sel || !sel.rangeCount) return;

        const range = sel.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        const menu = el('div', { className: 'highlight-menu' });

        for (const color of HIGHLIGHT_COLORS) {
            menu.appendChild(el('div', {
                className: 'hl-dot ' + color.css,
                onClick: async () => {
                    try {
                        await api.createHighlight(this.articleId, {
                            selected_text: selectionData.selected_text,
                            start_char_offset: selectionData.start_char_offset,
                            end_char_offset: selectionData.end_char_offset,
                            start_word_position: selectionData.start_word_position,
                            end_word_position: selectionData.end_word_position,
                            highlight_type: 'custom',
                            anchor_type: 'text_offset',
                            color: color.name,
                        });
                        showToast('Highlight created', 'success');
                        this.hideMenu();
                        if (this.onHighlightCreated) this.onHighlightCreated();
                    } catch (e) { showToast(e.message, 'error'); }
                },
            }));
        }

        // Position
        menu.style.position = 'fixed';
        menu.style.left = Math.min(rect.left + window.scrollX, window.innerWidth - 200) + 'px';
        menu.style.top = (rect.bottom + window.scrollY + 8) + 'px';

        document.body.appendChild(menu);
        this._menu = menu;

        // Click outside to dismiss
        setTimeout(() => {
            document.addEventListener('click', this._outsideClick = (e) => {
                if (!menu.contains(e.target)) this.hideMenu();
            });
        }, 0);
    }

    hideMenu() {
        if (this._menu) {
            this._menu.remove();
            this._menu = null;
        }
        if (this._outsideClick) {
            document.removeEventListener('click', this._outsideClick);
            this._outsideClick = null;
        }
    }
}
