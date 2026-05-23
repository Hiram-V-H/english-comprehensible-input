import { el, clearElement } from '../../utils/dom.js';

const HIGHLIGHT_CLASSES = {
    'yellow': 'hl-gold',
    'green': 'hl-sage',
    'blue': 'hl-lavender',
    'pink': 'hl-terracotta',
    'orange': 'hl-slate',
    'gold': 'hl-gold',
    'sage': 'hl-sage',
    'lavender': 'hl-lavender',
    'terracotta': 'hl-terracotta',
    'slate': 'hl-slate',
};

const ALL_HL_CLASSES = ['hl-gold', 'hl-sage', 'hl-lavender', 'hl-terracotta', 'hl-slate'];

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
        const cssClass = HIGHLIGHT_CLASSES[hl.color] || 'hl-gold';
        const wordSpans = this.container.querySelectorAll('.word');
        for (const span of wordSpans) {
            const charOffset = parseInt(span.dataset.charOffset);
            if (!isNaN(charOffset) && charOffset >= hl.start_char_offset && charOffset < hl.end_char_offset) {
                span.classList.add(cssClass);
            }
        }
    }

    _applyPositionHighlight(hl) {
        const cssClass = HIGHLIGHT_CLASSES[hl.color] || 'hl-gold';
        const spans = this.container.querySelectorAll('.word');
        for (const span of spans) {
            const pos = parseInt(span.dataset.position);
            if (!isNaN(pos) && pos >= hl.start_word_position && pos <= hl.end_word_position) {
                span.classList.add(cssClass);
            }
        }
    }

    removeAll() {
        const spans = this.container.querySelectorAll('.word');
        for (const span of spans) {
            span.classList.remove(...ALL_HL_CLASSES);
        }
    }
}
