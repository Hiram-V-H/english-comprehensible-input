import { el, clearElement } from '../../utils/dom.js';

/**
 * Renders colored background overlays for highlights on the reader.
 * Uses character offsets to find and mark word spans.
 */
export class HighlightOverlay {
    constructor(container) {
        this.container = container;
    }

    apply(highlights, paragraphs) {
        // Build lookup: word position -> char offset
        const posToCharOffset = {};
        for (const para of paragraphs) {
            for (const w of para.words) {
                if (w.char_offset !== undefined) {
                    posToCharOffset[w.position] = w.char_offset;
                }
            }
        }

        // Apply each highlight
        for (const hl of highlights) {
            if (hl.start_char_offset != null && hl.end_char_offset != null) {
                this._applyCharOffsetHighlight(hl, paragraphs);
            } else if (hl.start_word_position != null && hl.end_word_position != null) {
                this._applyPositionHighlight(hl);
            }
        }
    }

    _applyCharOffsetHighlight(hl, paragraphs) {
        // Find all word spans whose char_offset falls within the highlight range
        const wordSpans = this.container.querySelectorAll('.word');
        for (const span of wordSpans) {
            const charOffset = parseInt(span.dataset.charOffset);
            const wordLen = span.textContent.length;
            if (!isNaN(charOffset) && charOffset >= hl.start_char_offset && charOffset < hl.end_char_offset) {
                span.style.backgroundColor = (hl.color || '#FFEB3B') + '44';
                span.style.borderRadius = '2px';
            }
        }
    }

    _applyPositionHighlight(hl) {
        const spans = this.container.querySelectorAll('.word');
        for (const span of spans) {
            const pos = parseInt(span.dataset.position);
            if (!isNaN(pos) && pos >= hl.start_word_position && pos <= hl.end_word_position) {
                span.style.backgroundColor = (hl.color || '#FFEB3B') + '44';
                span.style.borderRadius = '2px';
            }
        }
    }

    removeAll() {
        const spans = this.container.querySelectorAll('.word');
        for (const span of spans) {
            span.style.backgroundColor = '';
            span.style.borderRadius = '';
        }
    }
}
