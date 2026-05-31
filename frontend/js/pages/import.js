import { el, clearElement } from '../utils/dom.js';
import { api } from '../api.js';
import { showToast } from '../components/shared/toast.js';
import { formatDate } from '../utils/formatters.js';
import { renderImportTocTree } from '../components/toc-tree.js';

export function importPage(main) {
    main.appendChild(el('div', { className: 'page-header' }, [
        el('h1', { className: 'page-title' }, ['Import']),
        el('p', { className: 'page-subtitle' }, ['Add articles from text, files, or folders']),
    ]));

    // ── Exam metadata row ──────────────────────────────────
    function getExamMeta() {
        const meta = {};
        if (examTypeSelect.value) meta.exam_type = examTypeSelect.value;
        if (examYearInput.value) meta.exam_year = parseInt(examYearInput.value, 10);
        if (questionTypeSelect.value) meta.question_type = questionTypeSelect.value;
        return meta;
    }

    const examTypeSelect = el('select', { className: 'form-input', style: 'min-width:110px' }, [
        el('option', { value: '' }, ['(none)']),
        el('option', { value: 'cet6' }, ['CET-6']),
        el('option', { value: 'postgraduate' }, ['考研']),
    ]);

    const examYearInput = el('input', {
        className: 'form-input',
        type: 'number',
        placeholder: 'e.g. 2024',
        style: 'min-width:90px',
        min: '2000',
        max: '2030',
    });

    const questionTypeSelect = el('select', { className: 'form-input', style: 'min-width:130px' }, [
        el('option', { value: '' }, ['(none)']),
        el('option', { value: '选词填空' }, ['选词填空']),
        el('option', { value: '长篇阅读' }, ['长篇阅读']),
        el('option', { value: '仔细阅读' }, ['仔细阅读']),
    ]);

    const examMetaCard = el('div', { className: 'card', style: 'margin-bottom:20px;padding:14px 18px' }, [
        el('div', { style: 'font-size:11px;font-weight:600;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:10px' }, ['Exam categorization (optional)']),
        el('div', { style: 'display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap' }, [
            el('div', { style: 'display:flex;flex-direction:column' }, [
                el('label', { className: 'form-label', style: 'font-size:12px' }, ['Exam Type']),
                examTypeSelect,
            ]),
            el('div', { style: 'display:flex;flex-direction:column' }, [
                el('label', { className: 'form-label', style: 'font-size:12px' }, ['Year']),
                examYearInput,
            ]),
            el('div', { style: 'display:flex;flex-direction:column' }, [
                el('label', { className: 'form-label', style: 'font-size:12px' }, ['Question Type']),
                questionTypeSelect,
            ]),
        ]),
    ]);
    main.appendChild(examMetaCard);

    // ── Two-column layout ──────────────────────────────────
    const columns = el('div', { style: 'display:flex;gap:20px;flex-wrap:wrap' });
    main.appendChild(columns);

    // ── LEFT COLUMN: Paste text ────────────────────────────
    const leftCol = el('div', { className: 'card', style: 'flex:1 1 55%;min-width:340px;padding:20px' }, [
        el('div', { style: 'font-size:13px;font-weight:600;color:var(--color-text);margin-bottom:10px' }, ['Paste article text']),
        el('textarea', {
            className: 'form-textarea',
            placeholder: 'Paste your article content here...\n\nThe first line will be used as the title. You can paste plain text or markdown.',
            style: 'min-height:220px;resize:vertical',
        }),
        el('div', { style: 'display:flex;align-items:center;justify-content:space-between;margin-top:12px' }, [
            el('span', { style: 'font-size:11px;color:var(--color-text-muted)' }, ['First line becomes the title']),
            el('button', {
                className: 'btn btn-primary',
                onClick: async () => {
                    const ta = leftCol.querySelector('textarea');
                    const raw = ta.value.trim();
                    if (!raw) {
                        showToast('Please paste some text first', 'error');
                        return;
                    }
                    const lines = raw.split('\n');
                    const title = lines[0].trim() || 'Untitled';
                    const content = lines.slice(1).join('\n').trim();
                    try {
                        await api.importText(title, content, getExamMeta());
                        showToast('Text imported successfully', 'success');
                        ta.value = '';
                        loadHistory();
                    } catch (e) {
                        showToast(e.message, 'error');
                    }
                },
            }, ['Import Text']),
        ]),
    ]);
    columns.appendChild(leftCol);

    // ── RIGHT COLUMN: File + Folder ────────────────────────
    const rightCol = el('div', { style: 'flex:1 1 35%;min-width:300px;display:flex;flex-direction:column;gap:16px' });

    // Drop zone card
    const dropZoneCard = el('div', { className: 'card', style: 'padding:20px' }, [
        el('div', { style: 'font-size:13px;font-weight:600;color:var(--color-text);margin-bottom:10px' }, ['Upload file']),
        el('div', { className: 'drop-zone', style: 'padding:28px 20px' }, [
            el('div', { className: 'drop-zone-icon', style: 'font-size:28px;margin-bottom:8px' }, ['\u{1F4C4}']),
            el('p', { style: 'font-size:13px' }, ['Drop file here or click to browse']),
            el('p', { style: 'font-size:11px;color:var(--color-text-muted);margin-top:4px' }, ['.txt, .md, .epub']),
            el('input', {
                type: 'file', accept: '.txt,.md,.markdown,.epub',
                style: 'display:none',
                onChange: (e) => handleFiles(e.target.files),
            }),
        ]),
    ]);
    dropZoneCard.querySelector('.drop-zone').addEventListener('click', () => dropZoneCard.querySelector('input').click());
    dropZoneCard.querySelector('.drop-zone').addEventListener('dragover', (e) => { e.preventDefault(); dropZoneCard.querySelector('.drop-zone').classList.add('drag-over'); });
    dropZoneCard.querySelector('.drop-zone').addEventListener('dragleave', () => dropZoneCard.querySelector('.drop-zone').classList.remove('drag-over'));
    dropZoneCard.querySelector('.drop-zone').addEventListener('drop', (e) => { e.preventDefault(); dropZoneCard.querySelector('.drop-zone').classList.remove('drag-over'); handleFiles(e.dataTransfer.files); });
    rightCol.appendChild(dropZoneCard);

    // Folder import card
    const scanBtn = el('button', { className: 'btn btn-primary' }, ['Scan']);
    scanBtn.addEventListener('click', async () => {
        const input = folderCard.querySelector('input');
        const path = input.value.trim();
        if (!path) return;
        try {
            const result = await api.importFolder(path, false);
            showToast(`Imported ${result.imported} article(s)`, 'success');
            loadHistory();
        } catch (e) { showToast(e.message, 'error'); }
    });

    const folderCard = el('div', { className: 'card', style: 'padding:20px' }, [
        el('div', { style: 'font-size:13px;font-weight:600;color:var(--color-text);margin-bottom:10px' }, ['Import from folder']),
        el('div', { style: 'display:flex;gap:8px' }, [
            el('input', {
                className: 'form-input',
                placeholder: 'Folder path...',
                style: 'flex:1',
                onKeyDown: (e) => { if (e.key === 'Enter') scanBtn.click(); },
            }),
            scanBtn,
        ]),
    ]);
    rightCol.appendChild(folderCard);

    columns.appendChild(rightCol);

    // ── EPUB preview area (shown on EPUB upload) ────────────
    const epubPreviewSection = el('div', { className: 'card', style: 'display:none;margin-top:20px;padding:20px' });
    main.appendChild(epubPreviewSection);

    // ── Import History ──────────────────────────────────────
    const histSection = el('div', { style: 'margin-top:24px' }, [
        el('div', { className: 'import-section-title', style: 'margin-bottom:10px' }, ['Import History']),
    ]);
    const histContainer = el('div');
    histSection.appendChild(histContainer);
    main.appendChild(histSection);

    // ── Handlers ────────────────────────────────────────────

    async function handleFiles(files) {
        for (const file of files) {
            const ext = file.name.split('.').pop().toLowerCase();
            if (ext === 'epub') {
                await handleEpubFile(file);
            } else {
                try {
                    await api.importFile(file, getExamMeta());
                    showToast(`Imported: ${file.name}`, 'success');
                } catch (e) {
                    showToast(`${file.name}: ${e.message}`, 'error');
                }
            }
        }
        loadHistory();
    }

    async function handleEpubFile(file) {
        epubPreviewSection.style.display = 'block';
        epubPreviewSection.innerHTML = '';
        epubPreviewSection.appendChild(el('div', { className: 'loading' }, [el('div', { className: 'spinner' }), ' Parsing EPUB...']));

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
            epubPreviewSection.appendChild(el('p', { style: 'color:var(--color-unknown);font-size:14px' }, ['Error: ' + e.message]));
            return;
        }

        epubPreviewSection.innerHTML = '';
        epubPreviewSection.appendChild(el('div', { style: 'font-size:15px;font-weight:700;color:var(--color-text);margin-bottom:4px' }, [previewData.title]));
        if (previewData.author) {
            epubPreviewSection.appendChild(el('p', { style: 'color:var(--color-text-muted);font-size:12px;margin-bottom:16px' }, ['by ' + previewData.author]));
        }

        const chapterList = el('div', { style: 'margin-bottom:16px' });
        const chapterCheckboxes = [];

        const toolbarRow = el('div', { style: 'display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap' });
        toolbarRow.appendChild(el('button', { className: 'btn btn-sm', onClick: () => { chapterCheckboxes.forEach(cb => { cb.checked = true; }); } }, ['Select All']));
        toolbarRow.appendChild(el('button', { className: 'btn btn-sm', onClick: () => { chapterCheckboxes.forEach(cb => { cb.checked = false; }); } }, ['Deselect All']));
        toolbarRow.appendChild(el('span', { style: 'flex:1' }));
        toolbarRow.appendChild(el('button', { className: 'btn btn-sm', onClick: () => {
            chapterList.querySelectorAll('.toc-tree-children').forEach(el => el.classList.remove('collapsed'));
            chapterList.querySelectorAll('.toc-tree-toggle').forEach(t => { if (!t.classList.contains('toc-tree-toggle-empty')) t.textContent = '▾'; });
        } }, ['Expand All']));
        toolbarRow.appendChild(el('button', { className: 'btn btn-sm', onClick: () => {
            chapterList.querySelectorAll('.toc-tree-children').forEach(el => el.classList.add('collapsed'));
            chapterList.querySelectorAll('.toc-tree-toggle').forEach(t => { if (!t.classList.contains('toc-tree-toggle-empty')) t.textContent = '▸'; });
        } }, ['Collapse All']));
        chapterList.appendChild(toolbarRow);

        if (previewData.toc_tree && previewData.toc_tree.length > 0) {
            chapterList.appendChild(renderImportTocTree(previewData.toc_tree, previewData.chapters, chapterCheckboxes));
        } else {
            for (const ch of previewData.chapters) {
                const row = el('label', { className: 'card', style: 'display:flex;align-items:center;gap:12px;margin-bottom:4px;cursor:pointer;padding:10px 16px' });
                const cb = el('input', { type: 'checkbox', checked: ch.selected ? 'checked' : undefined, style: 'width:16px;height:16px' });
                chapterCheckboxes.push(cb);
                row.appendChild(cb);
                row.appendChild(el('span', { style: 'font-size:14px' }, [(ch.index + 1) + '. ' + ch.title]));
                chapterList.appendChild(row);
            }
        }
        epubPreviewSection.appendChild(chapterList);

        epubPreviewSection.appendChild(el('button', {
            className: 'btn btn-primary',
            onClick: async () => {
                const selectedIndices = [];
                chapterCheckboxes.forEach((cb, i) => { if (cb.checked) selectedIndices.push(i); });
                if (selectedIndices.length === 0) {
                    showToast('Please select at least one chapter', 'error');
                    return;
                }
                try {
                    const confirmResp = await fetch('/api/import/epub/confirm', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ temp_file_path: previewData.temp_file_path, selected_chapter_indices: selectedIndices }),
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
