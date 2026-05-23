/**
 * Maps DOM selections to character offsets relative to the article's plain text.
 * Each word span has data-char-offset="N" indicating its character position in content_text.
 */

export function getSelectionCharOffsets(container) {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;

    const range = sel.getRangeAt(0);
    if (!container.contains(range.commonAncestorContainer)) return null;

    const startOffset = getCharOffset(container, range.startContainer, range.startOffset, 'start');
    const endOffset = getCharOffset(container, range.endContainer, range.endOffset, 'end');
    const selectedText = sel.toString();

    if (!selectedText.trim() || startOffset === null || endOffset === null) return null;

    return {
        start_char_offset: Math.min(startOffset, endOffset),
        end_char_offset: Math.max(startOffset, endOffset),
        selected_text: selectedText,
    };
}

function getCharOffset(container, node, offset, which) {
    // Walk up to find a word span or the container itself
    let el = node.nodeType === 3 ? node.parentElement : node;
    while (el && el !== container && !el.classList.contains('word')) {
        el = el.parentElement;
    }

    if (el && el.classList.contains('word')) {
        const charOffset = parseInt(el.dataset.charOffset);
        if (!isNaN(charOffset)) {
            // If at start of the word, use the word's char_offset
            if (offset === 0 || which === 'start') {
                return charOffset;
            }
            // If at end, add the word's text length
            const wordText = el.textContent;
            if (offset >= wordText.length || which === 'end') {
                return charOffset + wordText.length;
            }
            return charOffset + offset;
        }
    }

    // Fallback: find the nearest word span
    const allWords = container.querySelectorAll('.word');
    if (which === 'start') {
        for (const w of allWords) {
            if (container.compareDocumentPosition(w) & Node.DOCUMENT_POSITION_FOLLOWING) {
                return parseInt(w.dataset.charOffset) || 0;
            }
        }
        return 0;
    } else {
        for (let i = allWords.length - 1; i >= 0; i--) {
            const w = allWords[i];
            const co = parseInt(w.dataset.charOffset) || 0;
            return co + (w.textContent?.length || 0);
        }
        return 0;
    }
}

/**
 * Given an article's plain text and char offsets, compute which word positions are inside the highlight.
 * Returns { start_word_position, end_word_position } or null.
 */
export function charOffsetsToWordPositions(paragraphs, startCharOffset, endCharOffset) {
    let startPos = null, endPos = null;
    for (const para of paragraphs) {
        for (const w of para.words) {
            const wStart = w.char_offset;
            const wEnd = wStart + w.text.length;
            if (wStart < endCharOffset && wEnd > startCharOffset) {
                if (startPos === null) startPos = w.position;
                endPos = w.position;
            }
        }
    }
    if (startPos === null) return null;
    return { start_word_position: startPos, end_word_position: endPos };
}
