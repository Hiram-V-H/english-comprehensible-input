/**
 * Learning Overlay: applies word status classes to annotated HTML.
 * Walks [data-position] spans in the rendered DOM and adds
 * word--{status} classes based on the backend paragraphs data.
 */
export function applyWordAnnotations(container, paragraphs) {
    // Build position → status lookup from paragraphs data
    const statusMap = {};
    for (const para of paragraphs) {
        for (const w of para.words) {
            statusMap[w.position] = w.status || 'unknown';
        }
    }

    const spans = container.querySelectorAll('[data-position]');
    for (const span of spans) {
        const pos = parseInt(span.dataset.position);
        const status = statusMap[pos] || 'unknown';
        // Add the word status class
        span.classList.add('word', `word--${status}`);
        // Set status on dataset so WordPopup / updateWordStatus can read it
        span.dataset.status = status;
    }
}

/**
 * Update a word's status across ALL occurrences in the rendered DOM.
 * Finds all spans with the same word_id and updates them together.
 */
export function updateWordStatus(container, position, newStatus) {
    const span = container.querySelector(`[data-position="${position}"]`);
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

    const spans = container.querySelectorAll(selector);
    for (const s of spans) {
        s.className = s.className.replace(/word--\w+/g, `word--${newStatus}`);
        s.dataset.status = newStatus;
    }
}
