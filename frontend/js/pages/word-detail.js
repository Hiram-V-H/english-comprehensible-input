import { el } from '../utils/dom.js';
import { api } from '../api.js';
import { showToast } from '../components/shared/toast.js';
import { formatDate } from '../utils/formatters.js';

export function wordDetailPage(main, wordId) {
    main.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    (async () => {
        try {
            const word = await api.getWord(wordId);
            main.innerHTML = '';

            main.appendChild(el('div', { className: 'word-detail-header' }, [
                el('h1', { className: 'word-detail-word' }, [word.word]),
                el('div', { className: 'word-detail-meta' }, [
                    el('span', { className: 'badge badge-' + word.status }, [word.status]),
                    word.pronunciation ? el('span', { className: 'word-detail-pronunciation' }, ['/' + word.pronunciation + '/']) : null,
                    el('span', {}, [`Encountered ${word.encounter_count} times`]),
                    el('span', {}, ['Since ' + formatDate(word.first_seen)]),
                ]),
            ]));

            if (word.notes) {
                main.appendChild(el('div', {}, [
                    el('h3', { style: 'margin-bottom:8px' }, ['Notes']),
                    el('p', { style: 'color:var(--color-text-secondary)' }, [word.notes]),
                ]));
            }

            // Word notes section
            main.appendChild(el('h3', { style: 'margin:20px 0 8px' }, ['Study Notes']));

            const notesContainer = el('div');
            if (word.word_notes && word.word_notes.length > 0) {
                for (const note of word.word_notes) {
                    notesContainer.appendChild(el('div', { className: 'note-card' }, [
                        el('div', { className: 'note-card-header' }, [
                            el('span', { className: 'note-card-type' }, [note.note_type]),
                            el('span', { className: 'note-card-date' }, [formatDate(note.created_at)]),
                        ]),
                        el('div', { className: 'note-card-content' }, [note.content]),
                    ]));
                }
            } else {
                notesContainer.appendChild(el('p', { style: 'color:var(--color-text-secondary)' }, ['No notes yet.']));
            }
            main.appendChild(notesContainer);

            // Add note form
            const form = el('div', { style: 'margin-top:16px' });
            const textarea = el('textarea', { className: 'form-textarea', placeholder: 'Add a note...' });
            form.appendChild(textarea);
            form.appendChild(el('button', {
                className: 'btn btn-primary',
                style: 'margin-top:8px',
                onClick: async () => {
                    const content = textarea.value.trim();
                    if (!content) return;
                    try {
                        await api.addWordNote(wordId, { content, note_type: 'general' });
                        showToast('Note added', 'success');
                        textarea.value = '';
                        wordDetailPage(main, wordId); // refresh
                    } catch (e) { showToast(e.message, 'error'); }
                },
            }, ['Add Note']));
            main.appendChild(form);

        } catch (e) {
            main.innerHTML = `<div class="empty-state">Error: ${e.message}</div>`;
        }
    })();
}
