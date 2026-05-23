import { el } from '../utils/dom.js';
import { api } from '../api.js';
import { router } from '../router.js';
import { showToast } from '../components/shared/toast.js';
import { renderPagination } from '../components/shared/pagination.js';

export function vocabularyPage(main) {
    main.appendChild(el('div', { className: 'page-header' }, [
        el('h1', { className: 'page-title' }, ['Vocabulary']),
    ]));

    // Stats bar
    const statsEl = el('div', { className: 'vocab-stats' });
    main.appendChild(statsEl);

    // Search + filter
    const controls = el('div', { style: 'display:flex;gap:12px;align-items:center;margin-bottom:16px;' });
    const searchInput = el('input', {
        className: 'search-input',
        placeholder: 'Search words...',
        onInput: (e) => { currentSearch = e.target.value; loadPage(1); },
    });
    controls.appendChild(searchInput);

    const filterTabs = el('div', { className: 'filter-tabs' });
    const statuses = [
        { value: '', label: 'All' },
        { value: 'unknown', label: 'Unknown' },
        { value: 'learning', label: 'Learning' },
        { value: 'known', label: 'Known' },
    ];
    let currentStatus = '';
    for (const s of statuses) {
        filterTabs.appendChild(el('button', {
            className: 'filter-tab' + (s.value === currentStatus ? ' active' : ''),
            onClick: (e) => {
                currentStatus = s.value;
                filterTabs.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                loadPage(1);
            },
        }, [s.label]));
    }
    controls.appendChild(filterTabs);
    main.appendChild(controls);

    // Table container
    const tableContainer = el('div');
    main.appendChild(tableContainer);

    // Pagination
    const pagEl = el('div');
    main.appendChild(pagEl);

    let currentSearch = '';
    let currentPage = 1;

    async function loadStats() {
        try {
            const stats = await api.getVocabularyStats();
            statsEl.innerHTML = '';
            const items = [
                { label: 'Unknown', type: 'unknown' },
                { label: 'Learning', type: 'learning' },
                { label: 'Known', type: 'known' },
            ];
            for (const item of items) {
                statsEl.appendChild(el('div', { className: 'vocab-stat vocab-stat-' + item.type }, [
                    el('div', { className: 'vocab-stat-value' }, [String(stats[item.type] || 0)]),
                    el('div', { className: 'vocab-stat-label' }, [item.label]),
                ]));
            }
        } catch (e) { /* ignore */ }
    }

    async function loadPage(page) {
        currentPage = page;
        tableContainer.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        try {
            const data = await api.getWords({
                page, per_page: 30,
                status: currentStatus || undefined,
                search: currentSearch || undefined,
            });
            renderTable(data.items);
            pagEl.innerHTML = '';
            if (data.total_pages > 1) {
                pagEl.appendChild(renderPagination(page, data.total_pages, loadPage));
            }
        } catch (e) {
            tableContainer.innerHTML = `<div class="empty-state">Error: ${e.message}</div>`;
        }
    }

    function renderTable(words) {
        const table = el('table', { className: 'word-table' });
        table.appendChild(el('thead', {}, [el('tr', {}, [
            el('th', {}, ['Word']),
            el('th', {}, ['Status']),
            el('th', {}, ['Encounters']),
            el('th', {}, ['Notes']),
        ])]));

        const tbody = el('tbody');
        for (const w of words) {
            tbody.appendChild(el('tr', {}, [
                el('td', {}, [el('span', { className: 'word-link', onClick: () => { router.navigate('#/vocabulary/' + w.id); } }, [w.word])]),
                el('td', {}, [renderStatusBadge(w.status)]),
                el('td', {}, [String(w.encounter_count)]),
                el('td', { className: 'word-notes' }, [w.notes || '']),
            ]));
        }
        table.appendChild(tbody);
        tableContainer.innerHTML = '';
        tableContainer.appendChild(table);
    }

    loadStats();
    loadPage(1);
}

function renderStatusBadge(status) {
    const map = { unknown: 'badge-unknown', learning: 'badge-learning', known: 'badge-known', familiar: 'badge-familiar' };
    return el('span', { className: 'badge ' + (map[status] || '') }, [status]);
}
