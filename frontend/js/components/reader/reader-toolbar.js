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
                className: 'btn btn-sm',
                onClick: () => { if (this._onBack) this._onBack(); },
            }, ['Back to Library']),
            el('span', { style: 'font-weight:600;margin-left:8px' }, [a.title]),
            el('span', { style: 'color:var(--color-text-secondary);font-size:13px;margin-left:8px' }, [
                `${a.word_count || '?'} words`,
            ]),
            a.unknown_word_count != null ? el('span', { className: 'badge badge-unknown', style: 'margin-left:8px' }, [
                `${a.unknown_word_count} new`,
            ]) : null,
            a.i_plus_one_score != null ? el('span', {
                className: 'badge ' + (a.i_plus_one_score >= 0.7 ? 'badge-known' : a.i_plus_one_score >= 0.4 ? 'badge-learning' : 'badge-unknown'),
                style: 'margin-left:4px',
            }, [
                a.i_plus_one_score >= 0.7 ? 'i+1 Ideal' : a.i_plus_one_score >= 0.4 ? 'Challenging' : 'Hard',
            ]) : null,
            el('button', {
                className: 'btn btn-sm',
                style: 'margin-left:auto',
                onClick: () => { if (this._onToggleHighlights) this._onToggleHighlights(); },
            }, ['Toggle Highlights']),
        ]));
    }
}
