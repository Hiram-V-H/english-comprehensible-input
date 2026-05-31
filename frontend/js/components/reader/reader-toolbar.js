import { el, clearElement } from '../../utils/dom.js';

export class ReaderToolbar {
    constructor(container, articleData) {
        this.container = container;
        this.articleData = articleData;
        this._onBack = null;
        this._onToggleHighlights = null;
        this._onFontSizeChange = null;
        this._onThemeToggle = null;
        this._onToggleSidebar = null;
        this._onEdit = null;
        this._onDelete = null;
        this._onEditContent = null;
    }

    setOnBack(cb) { this._onBack = cb; }
    setOnToggleHighlights(cb) { this._onToggleHighlights = cb; }
    setOnFontSizeChange(cb) { this._onFontSizeChange = cb; }
    setOnThemeToggle(cb) { this._onThemeToggle = cb; }
    setOnToggleSidebar(cb) { this._onToggleSidebar = cb; }
    setOnEdit(cb) { this._onEdit = cb; }
    setOnDelete(cb) { this._onDelete = cb; }
    setOnEditContent(cb) { this._onEditContent = cb; }

    render() {
        clearElement(this.container);
        const a = this.articleData;

        this.container.appendChild(el('div', { className: 'reader-toolbar' }, [
            el('button', {
                className: 'toolbar-back',
                onClick: () => { if (this._onBack) this._onBack(); },
            }, ['← Back']),
            el('span', { className: 'toolbar-title' }, [a.title]),
            el('span', { className: 'toolbar-stat' }, [
                `${a.word_count || '?'} words`,
            ]),
            a.unknown_word_count != null ? el('span', { className: 'toolbar-stat' }, [
                `${a.unknown_word_count} new`,
            ]) : null,
            a.i_plus_one_score != null ? el('div', { className: 'toolbar-pill' }, [
                el('span', { className: 'pill-dot' }),
                a.i_plus_one_score >= 0.7 ? ' i+1 Ideal' : a.i_plus_one_score >= 0.4 ? ' Challenging' : ' Hard',
            ]) : null,
            // Edit button
            el('button', {
                className: 'toolbar-btn',
                title: '编辑文章信息',
                textContent: '✎',
                onClick: () => { if (this._onEdit) this._onEdit(); },
            }),
            // Delete button
            el('button', {
                className: 'toolbar-btn',
                title: '删除文章',
                textContent: '🗑',
                onClick: () => { if (this._onDelete) this._onDelete(); },
            }),
            // Edit content button
            el('button', {
                className: 'toolbar-btn',
                title: '编辑正文',
                textContent: '📝',
                onClick: () => { if (this._onEditContent) this._onEditContent(); },
            }),
            el('span', { style: 'flex:1' }),
            el('button', {
                className: 'toolbar-btn',
                title: 'Decrease font size',
                onClick: () => { if (this._onFontSizeChange) this._onFontSizeChange(-1); },
            }, ['A−']),
            el('button', {
                className: 'toolbar-btn',
                title: 'Increase font size',
                onClick: () => { if (this._onFontSizeChange) this._onFontSizeChange(1); },
            }, ['A+']),
            el('button', {
                className: 'toolbar-btn',
                title: 'Toggle dark/light theme',
                onClick: () => { if (this._onThemeToggle) this._onThemeToggle(); },
            }, ['◐']),
            el('button', {
                className: 'toolbar-btn',
                onClick: () => { if (this._onToggleHighlights) this._onToggleHighlights(); },
            }, ['Toggle Highlights']),
            el('button', {
                className: 'toolbar-btn',
                title: 'Toggle annotations sidebar',
                onClick: () => { if (this._onToggleSidebar) this._onToggleSidebar(); },
            }, ['☰']),
        ]));
    }
}
