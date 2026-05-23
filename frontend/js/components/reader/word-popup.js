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
                popup.appendChild(el('div', { className: 'popup-word' }, [wd.wordText]));
                popup.appendChild(el('div', { className: 'popup-status status-unknown' }, ['new word']));
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

        // Header area: word text + phonetic + status badge
        popup.appendChild(el('div', { className: 'popup-word' }, [
            word.word,
            word.pronunciation ? el('span', { className: 'popup-phonetic' }, ['/' + word.pronunciation + '/']) : null,
        ]));

        // Status badge
        popup.appendChild(el('div', { className: 'popup-status status-' + (word.status || 'unknown') }, [
            word.status || 'unknown',
        ]));

        // Definition (notes content as closest equivalent)
        const notes = word.word_notes || [];
        const hasNotes = word.notes || notes.length > 0;
        if (hasNotes) {
            const defDiv = el('div', { className: 'popup-definition' });
            if (word.notes) {
                defDiv.appendChild(el('div', {}, [word.notes]));
            }
            for (const note of notes) {
                defDiv.appendChild(el('div', {}, [
                    el('div', { style: 'font-size:11px;color:var(--color-text-secondary);margin-bottom:2px' }, [note.note_type]),
                    el('div', {}, [note.content]),
                ]));
            }
            popup.appendChild(defDiv);
        }

        // Status selector buttons
        const statusSelector = el('div', { className: 'popup-status-selector' });
        for (const s of ['unknown', 'learning', 'familiar', 'known']) {
            statusSelector.appendChild(el('button', {
                className: 'status-btn' + (s === word.status ? ' active' : ''),
                onClick: async (ev) => {
                    try {
                        await api.updateWord(word.id, { status: s });
                        word.status = s;
                        // Update status badge
                        const badge = popup.querySelector('.popup-status');
                        if (badge) {
                            badge.className = 'popup-status status-' + s;
                            badge.textContent = s;
                        }
                        // Update active button
                        popup.querySelectorAll('.status-btn').forEach(b => b.classList.remove('active'));
                        ev.target.classList.add('active');
                        showToast('Status updated', 'success');
                        if (this._onStatusChange) this._onStatusChange(wd.position, s);
                    } catch (err) { showToast(err.message, 'error'); }
                },
            }, [s]));
        }
        popup.appendChild(statusSelector);

        // Meta info
        popup.appendChild(el('div', { className: 'popup-meta' }, [
            `Encountered: ${word.encounter_count} times`,
        ]));

        // Note form
        const addNoteBtn = el('button', {
            className: 'btn btn-sm',
            onClick: async () => {
                const textarea = el('textarea', { className: 'form-textarea', placeholder: 'Add a note...', style: 'min-height:50px;font-size:13px' });
                const submitBtn = el('button', { className: 'btn btn-sm btn-primary', style: 'margin-top:4px' }, ['Save']);
                const formDiv = el('div', { className: 'popup-note-form' }, [textarea, submitBtn]);

                submitBtn.addEventListener('click', async () => {
                    const content = textarea.value.trim();
                    if (!content) return;
                    try {
                        await api.addWordNote(word.id, { content, note_type: 'general' });
                        showToast('Note added', 'success');
                        // Refresh popup
                        this.show(wd);
                    } catch (err) { showToast(err.message, 'error'); }
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
