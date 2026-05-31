import { el, clearElement } from '../../utils/dom.js';
import { getSelectionCharOffsets, charOffsetsToWordPositions } from '../../utils/text-offset.js';

/**
 * Renders article content as word-level spans with status classes.
 * Each span: <span class="word word--{status}" data-position="N" data-word-id="M" data-char-offset="X">
 */
export class ArticleDisplay {
    constructor(container, { onWordClick, onSelectionComplete }) {
        this.container = container;
        this.onWordClick = onWordClick;
        this.onSelectionComplete = onSelectionComplete;
        this._readerData = null;
        this._bindEvents();
    }

    _bindEvents() {
        this.container.addEventListener('click', (e) => {
            const wordEl = e.target.closest('.word');
            if (!wordEl) return;
            // Ignore clicks on punctuation tokens
            if (wordEl.dataset.status === 'punct') return;
            const wordId = wordEl.dataset.wordId;
            const wordText = wordEl.textContent;
            const wordLower = wordEl.dataset.wordLower;
            const status = wordEl.dataset.status;
            const position = parseInt(wordEl.dataset.position);
            this.onWordClick({
                wordId: wordId || null,
                wordText,
                wordLower,
                status,
                position,
                rect: wordEl.getBoundingClientRect(),
            });
        });

        this.container.addEventListener('mouseup', () => {
            setTimeout(() => {
                if (!this.onSelectionComplete) return;
                const offsets = getSelectionCharOffsets(this.container);
                if (offsets && this._readerData) {
                    const positions = charOffsetsToWordPositions(
                        this._readerData.paragraphs,
                        offsets.start_char_offset,
                        offsets.end_char_offset,
                    );
                    this.onSelectionComplete({ ...offsets, ...(positions || {}) });
                } else {
                    this.onSelectionComplete(null);
                }
            }, 10);
        });
    }

    render(data) {
        this._readerData = data;
        clearElement(this.container);

        // Build character offset map from paragraphs
        const charOffsetMap = {};
        for (const para of data.paragraphs) {
            for (const w of para.words) {
                // Calculate char offset by scanning content_text
                if (!charOffsetMap[w.position] || charOffsetMap[w.position] === undefined) {
                    // Use pre-computed offset from backend or compute here
                    charOffsetMap[w.position] = w.char_offset || 0;
                }
            }
        }

        for (const para of data.paragraphs) {
            const pEl = el('p', { className: 'reader-paragraph' });
            for (let i = 0; i < para.words.length; i++) {
                const w = para.words[i];
                const span = el('span', {
                    className: `word word--${w.status || 'unknown'}`,
                    dataset: {
                        position: String(w.position),
                        wordId: w.word_id ? String(w.word_id) : '',
                        wordLower: w.word_lower || '',
                        status: w.status || 'unknown',
                        charOffset: String(w.char_offset || 0),
                    },
                }, [w.text]);

                if (w.is_highlighted) {
                    span.style.backgroundColor = w.highlight_color + '66';
                    span.style.borderRadius = '2px';
                }

                pEl.appendChild(span);

                // Add space between words (but not before punctuation)
                const next = para.words[i + 1];
                const needsSpace = next && !/^[.,!?;:)'"]/.test(next.text);
                if (needsSpace) {
                    pEl.appendChild(document.createTextNode(' '));
                }
            }
            this.container.appendChild(pEl);
        }
    }

    updateWordStatus(position, newStatus) {
        const span = this.container.querySelector(`[data-position="${position}"]`);
        if (!span) return;

        // Find all spans with the same word_id, or fall back to same word_lower
        const wordId = span.dataset.wordId;
        const wordLower = span.dataset.wordLower;
        let selector;
        if (wordId) {
            selector = `[data-word-id="${wordId}"]`;
        } else if (wordLower) {
            selector = `[data-word-lower="${wordLower}"]`;
        } else {
            selector = `[data-position="${position}"]`;
        }

        const spans = this.container.querySelectorAll(selector);
        for (const s of spans) {
            s.className = s.className.replace(/word--\w+/g, `word--${newStatus}`);
            s.dataset.status = newStatus;
        }
    }
}
