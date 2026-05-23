import { el, clearElement } from '../../utils/dom.js';
import { api } from '../../api.js';
import { showToast } from '../shared/toast.js';

/**
 * Manages the click-word popup card.
 */
export class WordPopup {
    constructor() {
        this._popup = null;
        this._visible = false;
        this._onStatusChange = null;
    }

    setOnStatusChange(cb) { this._onStatusChange = cb; }

    show(wordData) {
        this.hide();

        const popup = el('div', { className: 'word-popup' });
        this._popup = popup;
        this._visible = true;

        // Position near the clicked word
        const rect = wordData.rect;
        const x = rect.left + window.scrollX;
        const y = rect.bottom + window.scrollY + 6;
        popup.style.position = 'fixed';
        popup.style.left = Math.min(x, window.innerWidth - 340) + 'px';
        popup.style.top = y + 'px';

        // Loading state
        popup.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        document.body.appendChild(popup);

        // Load word data
        this._loadWord(wordData);
    }

    async _loadWord(wd) {
        const popup = this._popup;
        try {
            let word = null;
            // Try to load by word_id first, then by text search
            if (wd.wordId) {
                try { word = await api.getWord(wd.wordId); } catch (e) { /* ignore */ }
            }
            if (!word && wd.wordLower) {
                try {
                    const results = await api.searchWords(wd.wordLower, 1);
                    if (results.length > 0) word = await api.getWord(results[0].id);
                } catch (e) { /* ignore */ }
            }

            if (!word) {
                popup.innerHTML = '';
                popup.appendChild(el('div', { className: 'word-popup-word' }, [wd.wordText]));
                popup.appendChild(el('div', { className: 'word-popup-status' }, [
                    el('span', { className: 'badge badge-unknown' }, ['new word']),
                ]));
                return;
            }

            this._renderPopup(popup, word, wd);

        } catch (e) {
            popup.innerHTML = '';
            popup.appendChild(el('div', {}, ['Error loading word']));
        }
    }

    _renderPopup(popup, word, wd) {
        clearElement(popup);

        // Word text
        popup.appendChild(el('div', { className: 'word-popup-word' }, [
            word.word,
            word.pronunciation ? el('span', { style: 'font-size:14px;color:var(--color-text-secondary);font-weight:400;margin-left:8px' }, ['/' + word.pronunciation + '/']) : null,
        ]));

        // Status toggle
        const statusSelect = el('select', {
            className: 'status-select',
            style: 'margin-bottom:8px',
        });
        for (const s of ['unknown', 'learning', 'familiar', 'known', 'mastered']) {
            statusSelect.appendChild(el('option', { value: s, selected: s === word.status ? '' : undefined }, [s]));
        }
        statusSelect.addEventListener('change', async () => {
            try {
                await api.updateWord(word.id, { status: statusSelect.value });
                word.status = statusSelect.value;
                showToast('Status updated', 'success');
                if (this._onStatusChange) this._onStatusChange(wd.position, statusSelect.value);
            } catch (e) { showToast(e.message, 'error'); }
        });
        popup.appendChild(el('div', { className: 'word-popup-status' }, [statusSelect]));

        // Encounter counter
        popup.appendChild(el('div', { style: 'font-size:12px;color:var(--color-text-secondary);margin-bottom:8px' }, [
            `Encountered: ${word.encounter_count} times`,
        ]));

        // Personal notes
        const notesDiv = el('div', { className: 'word-popup-notes' });
        const notes = word.word_notes || [];
        if (notes.length > 0) {
            for (const note of notes) {
                notesDiv.appendChild(el('div', { className: 'word-popup-note' }, [
                    el('div', { style: 'font-size:11px;color:var(--color-text-secondary);margin-bottom:2px' }, [note.note_type]),
                    el('div', {}, [note.content]),
                ]));
            }
        }
        if (word.notes) {
            notesDiv.appendChild(el('div', { className: 'word-popup-note' }, [word.notes]));
        }
        popup.appendChild(notesDiv);

        // Add note form
        const addNoteBtn = el('button', {
            className: 'btn btn-sm',
            onClick: async () => {
                const textarea = el('textarea', { className: 'form-textarea', placeholder: 'Add a note...', style: 'min-height:50px;font-size:13px' });
                const submitBtn = el('button', { className: 'btn btn-sm btn-primary', style: 'margin-top:4px' }, ['Save']);
                const formDiv = el('div', { style: 'margin-top:8px' }, [textarea, submitBtn]);

                submitBtn.addEventListener('click', async () => {
                    const content = textarea.value.trim();
                    if (!content) return;
                    try {
                        await api.addWordNote(word.id, { content, note_type: 'general' });
                        showToast('Note added', 'success');
                        // Refresh popup
                        this.show(wd);
                    } catch (e) { showToast(e.message, 'error'); }
                });

                // Replace add button with form
                addNoteBtn.replaceWith(formDiv);
            },
        }, ['+ Add Note']);
        popup.appendChild(addNoteBtn);
    }

    hide() {
        if (this._popup) {
            this._popup.remove();
            this._popup = null;
        }
        this._visible = false;
    }

    get visible() { return this._visible; }
}
