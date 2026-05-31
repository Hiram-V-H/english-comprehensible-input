import { el } from '../../utils/dom.js';

/**
 * Inline word editor — click a word to edit it in-place.
 * Usage:
 *   const editor = new WordInlineEditor(readerContainer);
 *   const result = await editor.open(wordSpan, wordData, contentText);
 */
export class WordInlineEditor {
    constructor(container) {
        this._container = container;
        this._input = null;
        this._originalSpan = null;
        this._originalWordData = null;
        this._resolve = null;
    }

    /**
     * Open inline editor on a word span.
     * @param {HTMLSpanElement} span — the [data-position] span clicked
     * @param {Object} wordData — { text, char_offset, position }
     * @param {string} contentText — full article content_text
     * @returns {Promise<{newWord: string, newContentText: string}|null>}
     */
    open(span, wordData, contentText) {
        this.close();

        this._originalSpan = span;
        this._originalWordData = wordData;

        return new Promise((resolve) => {
            this._resolve = resolve;

            const input = el('input', {
                type: 'text',
                className: 'word-inline-input',
                value: wordData.text,
                onKeydown: (e) => {
                    if (e.key === 'Enter') this._save(contentText, wordData);
                    if (e.key === 'Escape') this._cancel();
                },
                onBlur: () => {
                    setTimeout(() => {
                        if (this._input) this._save(contentText, wordData);
                    }, 150);
                },
            });

            input.style.minWidth = Math.max(60, span.offsetWidth + 10) + 'px';

            span.textContent = '';
            span.appendChild(input);
            this._input = input;

            input.focus();
            input.select();
        });
    }

    _replaceWord(contentText, charOffset, oldWord, newWord) {
        const slice = contentText.substring(charOffset, charOffset + oldWord.length);
        if (slice !== oldWord) {
            return null;
        }
        return contentText.substring(0, charOffset) + newWord + contentText.substring(charOffset + oldWord.length);
    }

    _save(contentText, wordData) {
        if (!this._input) return;
        const newWord = this._input.value.trim();
        this._cleanup();
        if (!newWord || newWord === wordData.text) {
            this._resolve(null);
            return;
        }
        const newContentText = this._replaceWord(contentText, wordData.char_offset, wordData.text, newWord);
        if (newContentText === null) {
            this._resolve(null);
            return;
        }
        this._resolve({ newWord, newContentText });
    }

    _cancel() {
        this._restoreSpan();
        this._cleanup();
        this._resolve(null);
    }

    _restoreSpan() {
        if (this._originalSpan && this._originalWordData) {
            this._originalSpan.textContent = this._originalWordData.text;
        }
    }

    _cleanup() {
        if (this._input) {
            this._input.remove();
            this._input = null;
        }
    }

    close() {
        this._cleanup();
        if (this._resolve) {
            this._resolve(null);
            this._resolve = null;
        }
    }
}
