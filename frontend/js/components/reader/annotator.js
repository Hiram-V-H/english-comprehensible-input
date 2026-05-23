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
 * Update a single word's status class in the rendered DOM.
 */
export function updateWordStatus(container, position, newStatus) {
    const span = container.querySelector(`[data-position="${position}"]`);
    if (span) {
        span.className = span.className.replace(/word--\w+/g, `word--${newStatus}`);
        span.dataset.status = newStatus;
    }
}
