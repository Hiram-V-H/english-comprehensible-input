import { el, clearElement } from '../../utils/dom.js';

export class ReaderToolbar {
    constructor(container, articleData) {
        this.container = container;
        this.articleData = articleData;
        this._onBack = null;
        this._onToggleHighlights = null;
    }

    setOnBack(cb) { this._onBack = cb; }
    setOnToggleHighlights(cb) { this._onToggleHighlights = cb; }

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
            el('button', {
                className: 'toolbar-btn',
                onClick: () => { if (this._onToggleHighlights) this._onToggleHighlights(); },
            }, ['Toggle Highlights']),
        ]));
    }
}
