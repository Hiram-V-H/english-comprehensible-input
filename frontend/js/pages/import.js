import { el, clearElement } from '../utils/dom.js';
import { api } from '../api.js';
import { showToast } from '../components/shared/toast.js';
import { formatDate } from '../utils/formatters.js';

export function importPage(main) {
    main.appendChild(el('div', { className: 'page-header' }, [
        el('h1', { className: 'page-title' }, ['Import']),
    ]));

    // ── Two-column layout ────────────────────────────────
    const columns = el('div', { style: 'display:flex;gap:24px;flex-wrap:wrap' });
    main.appendChild(columns);

    // ── LEFT COLUMN: Paste text (~60%) ───────────────────
    const leftCol = el('div', { style: 'flex:1 1 55%;min-width:320px' });

    leftCol.appendChild(el('label', { className: 'form-label' }, ['Paste article text']));

    const textarea = el('textarea', {
        className: 'form-textarea',
        placeholder: 'Paste your article content here...\n\nYou can paste plain text or markdown. The first line will be used as the title.',
        style: 'min-height:200px;resize:vertical',
    });
    leftCol.appendChild(textarea);

    const footer = el('div', { style: 'display:flex;align-items:center;justify-content:space-between;margin-top:8px' });
    footer.appendChild(el('span', { style: 'font-size:12px;color:var(--color-text-secondary)' }, ['First line becomes the title']));
    const importTextBtn = el('button', { className: 'btn btn-primary' }, ['Import Text']);
    importTextBtn.addEventListener('click', async () => {
        const raw = textarea.value.trim();
        if (!raw) {
            showToast('Please paste some text first', 'error');
            return;
        }
        const lines = raw.split('\n');
        const title = lines[0].trim() || 'Untitled';
        const content = raw;
        try {
            await api.importText(title, content);
            showToast('Text imported successfully', 'success');
            textarea.value = '';
            loadHistory();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });
    footer.appendChild(importTextBtn);
    leftCol.appendChild(footer);

    columns.appendChild(leftCol);

    // ── RIGHT COLUMN: File + Folder (~40%) ───────────────
    const rightCol = el('div', { style: 'flex:1 1 35%;min-width:280px' });

    // Drop zone
    rightCol.appendChild(el('label', { className: 'form-label' }, ['Or drop files']));

    const dropZone = el('div', { className: 'drop-zone' }, [
        el('div', { className: 'drop-zone-icon', style: 'font-size:28px;margin-bottom:8px' }, ['\u{1F4C4}']),
        el('p', {}, ['Drop files or click']),
        el('p', { style: 'font-size:12px;color:var(--color-text-secondary);margin-top:4px' }, ['.txt, .md, .epub']),
        el('input', {
            type: 'file', accept: '.txt,.md,.markdown,.epub',
            style: 'display:none',
            onChange: (e) => handleFiles(e.target.files),
        }),
    ]);
    dropZone.addEventListener('click', () => dropZone.querySelector('input').click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
    dropZone.addEventListener('drop', (e) => { e.preventDefault(); dropZone.classList.remove('drag-over'); handleFiles(e.dataTransfer.files); });
    rightCol.appendChild(dropZone);

    // Folder import
    rightCol.appendChild(el('label', { className: 'form-label', style: 'margin-top:16px' }, ['Folder import']));

    const folderRow = el('div', { style: 'display:flex;gap:8px;' });
    const folderInput = el('input', {
        className: 'form-input',
        placeholder: 'Folder path...',
        style: 'flex:1',
    });
    folderRow.appendChild(folderInput);
    const scanBtn = el('button', {
        className: 'btn btn-primary',
        onClick: async () => {
            const path = folderInput.value.trim();
            if (!path) return;
            try {
                const result = await api.importFolder(path, false);
                showToast(`Imported ${result.imported} article(s)`, 'success');
                loadHistory();
            } catch (e) { showToast(e.message, 'error'); }
        },
    }, ['Scan']);
    folderRow.appendChild(scanBtn);
    rightCol.appendChild(folderRow);

    columns.appendChild(rightCol);

    // ── EPUB preview area (shown on EPUB upload) ──────────
    const epubPreviewSection = el('div', { className: 'import-section', style: 'display:none' });
    main.appendChild(epubPreviewSection);

    // ── Import History ────────────────────────────────────
    const histSection = el('div', { className: 'import-section' }, [
        el('div', { className: 'import-section-title' }, ['Import History']),
    ]);
    const histContainer = el('div');
    histSection.appendChild(histContainer);
    main.appendChild(histSection);

    // ── Handlers ──────────────────────────────────────────

    async function handleFiles(files) {
        for (const file of files) {
            const ext = file.name.split('.').pop().toLowerCase();
            if (ext === 'epub') {
                await handleEpubFile(file);
            } else {
                try {
                    await api.importFile(file);
                    showToast(`Imported: ${file.name}`, 'success');
                } catch (e) {
                    showToast(`${file.name}: ${e.message}`, 'error');
                }
            }
        }
        loadHistory();
    }

    async function handleEpubFile(file) {
        // Show preview section with loading
        epubPreviewSection.style.display = 'block';
        epubPreviewSection.innerHTML = '';
        epubPreviewSection.appendChild(el('div', { className: 'import-section-title' }, ['EPUB Preview']));
        epubPreviewSection.appendChild(el('div', { className: 'loading' }, [el('div', { className: 'spinner' }), ' Parsing EPUB...']));

        // Upload for preview
        const formData = new FormData();
        formData.append('file', file);
        let previewData;
        try {
            const resp = await fetch('/api/import/epub/preview', { method: 'POST', body: formData });
            const json = await resp.json();
            if (json.status !== 'ok') throw new Error(json.detail || 'Preview failed');
            previewData = json.data;
        } catch (e) {
            epubPreviewSection.innerHTML = '';
            epubPreviewSection.appendChild(el('div', { className: 'import-section-title' }, ['EPUB Preview']));
            epubPreviewSection.appendChild(el('p', { style: 'color:var(--color-unknown)' }, ['Error: ' + e.message]));
            return;
        }

        // Build chapter selection UI
        epubPreviewSection.innerHTML = '';
        epubPreviewSection.appendChild(el('div', { className: 'import-section-title' }, ['EPUB: ' + previewData.title]));
        if (previewData.author) {
            epubPreviewSection.appendChild(el('p', { style: 'color:var(--color-text-secondary);font-size:13px;margin-bottom:12px' }, ['by ' + previewData.author]));
        }

        const chapterList = el('div', { style: 'margin-bottom:12px' });
        const chapterCheckboxes = [];

        // Select all / deselect all
        const selectAllRow = el('div', { style: 'display:flex;gap:8px;margin-bottom:8px' });
        selectAllRow.appendChild(el('button', {
            className: 'btn btn-sm',
            onClick: () => {
                chapterCheckboxes.forEach(cb => { cb.checked = true; });
            },
        }, ['Select All']));
        selectAllRow.appendChild(el('button', {
            className: 'btn btn-sm',
            onClick: () => {
                chapterCheckboxes.forEach(cb => { cb.checked = false; });
            },
        }, ['Deselect All']));
        chapterList.appendChild(selectAllRow);

        for (const ch of previewData.chapters) {
            const row = el('label', { className: 'card', style: 'display:flex;align-items:center;gap:12px;margin-bottom:4px;cursor:pointer;padding:10px 16px' });
            const cb = el('input', {
                type: 'checkbox',
                checked: ch.selected ? '' : undefined,
                style: 'width:16px;height:16px',
            });
            chapterCheckboxes.push(cb);
            row.appendChild(cb);
            row.appendChild(el('span', { style: 'font-size:14px' }, [(ch.index + 1) + '. ' + ch.title]));
            chapterList.appendChild(row);
        }
        epubPreviewSection.appendChild(chapterList);

        // Confirm button
        epubPreviewSection.appendChild(el('button', {
            className: 'btn btn-primary',
            onClick: async () => {
                const selectedIndices = [];
                chapterCheckboxes.forEach((cb, i) => {
                    if (cb.checked) selectedIndices.push(i);
                });
                if (selectedIndices.length === 0) {
                    showToast('Please select at least one chapter', 'error');
                    return;
                }

                try {
                    const confirmResp = await fetch('/api/import/epub/confirm', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            temp_file_path: previewData.temp_file_path,
                            selected_chapter_indices: selectedIndices,
                        }),
                    });
                    const confirmJson = await confirmResp.json();
                    if (confirmJson.status === 'ok') {
                        showToast(`Imported ${confirmJson.data.articles_imported} chapters as a book`, 'success');
                        epubPreviewSection.style.display = 'none';
                        loadHistory();
                    } else {
                        showToast(confirmJson.detail || 'Import failed', 'error');
                    }
                } catch (e) {
                    showToast(e.message, 'error');
                }
            },
        }, ['Import Selected Chapters']));

        // Scroll to preview
        epubPreviewSection.scrollIntoView({ behavior: 'smooth' });
    }

    async function loadHistory() {
        try {
            const data = await api.getImportHistory({ per_page: 20 });
            const table = el('table', { className: 'import-history-table' });
            table.appendChild(el('thead', {}, [el('tr', {}, [
                el('th', {}, ['Source']), el('th', {}, ['Type']), el('th', {}, ['Status']), el('th', {}, ['Date']),
            ])]));
            const tbody = el('tbody');
            for (const r of data.items || []) {
                tbody.appendChild(el('tr', {}, [
                    el('td', {}, [r.source_path]),
                    el('td', {}, [r.source_type]),
                    el('td', {}, [el('span', { className: 'badge ' + (r.import_status === 'success' ? 'badge-known' : 'badge-unknown') }, [r.import_status])]),
                    el('td', {}, [formatDate(r.imported_at)]),
                ]));
            }
            table.appendChild(tbody);
            histContainer.innerHTML = '';
            histContainer.appendChild(table);
        } catch (e) { /* ignore */ }
    }

    loadHistory();
}
