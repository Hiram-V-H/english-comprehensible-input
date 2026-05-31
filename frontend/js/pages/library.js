import { el } from '../utils/dom.js';
import { api } from '../api.js';
import { formatDate, formatPercent } from '../utils/formatters.js';
import { router } from '../router.js';
import { STRIPE_GRADIENTS, getDifficultyColors, getI1ScoreLabel } from '../utils/card-utils.js';
import { showArticleEditor } from '../components/article-editor.js';
import { showModal } from '../components/shared/modal.js';
import { showToast } from '../components/shared/toast.js';

export function libraryPage(main) {
    // ── Batch mode state ────────────────────────────────────
    let batchMode = false;
    let selectedIds = new Set();
    let currentArticles = [];

    // ── Page header ─────────────────────────────────────────
    const batchToggleBtn = el('button', { className: 'btn btn-sm' }, ['管理']);
    const importBtn = el('button', { className: 'btn btn-sm btn-primary' }, ['导入']);
    importBtn.addEventListener('click', () => router.navigate('#/import'));

    main.appendChild(el('div', {
        className: 'page-header',
        style: 'display:flex;justify-content:space-between;align-items:center',
    }, [
        el('h1', { className: 'page-title' }, ['Article Library']),
        el('div', { style: 'display:flex;gap:8px' }, [batchToggleBtn, importBtn]),
    ]));

    // ── Exam filter bar ────────────────────────────────────
    const filterBar = el('div', { style: 'display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;margin-bottom:16px' });

    const examTypeSelect = el('select', { className: 'form-input', style: 'min-width:110px' }, [
        el('option', { value: '' }, ['All Articles']),
        el('option', { value: 'cet6' }, ['CET-6']),
        el('option', { value: 'postgraduate' }, ['考研']),
    ]);

    const examYearInput = el('input', {
        className: 'form-input',
        type: 'number',
        placeholder: 'Year',
        style: 'min-width:80px',
        min: '2000',
        max: '2030',
    });

    const questionTypeSelect = el('select', { className: 'form-input', style: 'min-width:120px' }, [
        el('option', { value: '' }, ['All Types']),
        el('option', { value: '选词填空' }, ['选词填空']),
        el('option', { value: '长篇阅读' }, ['长篇阅读']),
        el('option', { value: '仔细阅读' }, ['仔细阅读']),
    ]);

    const clearBtn = el('button', { className: 'btn btn-sm', style: 'white-space:nowrap' }, ['Clear']);
    clearBtn.addEventListener('click', () => {
        examTypeSelect.value = '';
        examYearInput.value = '';
        questionTypeSelect.value = '';
        load();
    });

    [examTypeSelect, examYearInput, questionTypeSelect].forEach(el => {
        el.addEventListener('change', () => load());
        el.addEventListener('keydown', (e) => { if (e.key === 'Enter') load(); });
    });

    filterBar.appendChild(el('div', { style: 'display:flex;flex-direction:column' }, [
        el('label', { className: 'form-label', style: 'font-size:11px' }, ['Exam']),
        examTypeSelect,
    ]));
    filterBar.appendChild(el('div', { style: 'display:flex;flex-direction:column' }, [
        el('label', { className: 'form-label', style: 'font-size:11px' }, ['Year']),
        examYearInput,
    ]));
    filterBar.appendChild(el('div', { style: 'display:flex;flex-direction:column' }, [
        el('label', { className: 'form-label', style: 'font-size:11px' }, ['Type']),
        questionTypeSelect,
    ]));
    filterBar.appendChild(el('div', { style: 'display:flex;flex-direction:column;justify-content:flex-end' }, [
        clearBtn,
    ]));
    main.appendChild(filterBar);

    // ── Batch action bar ────────────────────────────────────
    const selectAllBtn = el('button', { className: 'select-all-btn' }, ['☑ 全选']);
    const selectedCountNum = el('strong', {}, ['0']);
    const batchDeleteBtn = el('button', { className: 'batch-delete-btn', disabled: true }, ['🗑 删除所选']);
    const batchCancelBtn = el('button', { className: 'batch-cancel-btn' }, ['✕ 取消']);

    const batchBar = el('div', { id: 'batch-bar', className: 'batch-bar', style: { display: 'none' } }, [
        el('div', { className: 'batch-bar-left' }, [
            selectAllBtn,
            el('span', { className: 'selected-count' }, ['已选择 ', selectedCountNum, ' 篇']),
        ]),
        el('div', { className: 'batch-bar-actions' }, [
            batchDeleteBtn,
            batchCancelBtn,
        ]),
    ]);
    main.appendChild(batchBar);

    const content = el('div');
    main.appendChild(content);

    // ── Batch mode functions ────────────────────────────────
    function updateBatchUI() {
        batchBar.style.display = batchMode ? 'flex' : 'none';
        batchToggleBtn.textContent = batchMode ? '完成' : '管理';
        selectedCountNum.textContent = String(selectedIds.size);
        batchDeleteBtn.disabled = selectedIds.size === 0;

        // Toggle batch-mode class on all article grids
        document.querySelectorAll('.article-grid').forEach(g => {
            g.classList.toggle('batch-mode', batchMode);
        });

        // Update all card checkboxes visibility and selected state
        document.querySelectorAll('.article-card').forEach(card => {
            const cb = card.querySelector('.card-checkbox');
            if (cb) {
                const aid = parseInt(card.dataset.articleId, 10);
                cb.checked = selectedIds.has(aid);
                card.classList.toggle('card-selected', selectedIds.has(aid));
            }
        });
    }

    function toggleBatchMode() {
        batchMode = !batchMode;
        selectedIds.clear();
        updateBatchUI();
    }

    function exitBatchMode() {
        batchMode = false;
        selectedIds.clear();
        updateBatchUI();
    }

    function toggleSelectAll() {
        const checkboxes = document.querySelectorAll('.card-checkbox');
        const allChecked = currentArticles.length > 0 && selectedIds.size === currentArticles.length;

        if (allChecked) {
            checkboxes.forEach(cb => { cb.checked = false; });
            selectedIds.clear();
        } else {
            checkboxes.forEach(cb => { cb.checked = true; });
            currentArticles.forEach(a => selectedIds.add(a.id));
        }

        document.querySelectorAll('.article-card').forEach(card => {
            const aid = parseInt(card.dataset.articleId, 10);
            card.classList.toggle('card-selected', selectedIds.has(aid));
        });

        updateBatchUI();
    }

    function onCardCheckboxChange(e) {
        const checkbox = e.target;
        const articleId = parseInt(checkbox.dataset.articleId, 10);

        if (checkbox.checked) {
            selectedIds.add(articleId);
        } else {
            selectedIds.delete(articleId);
        }

        const card = checkbox.closest('.article-card');
        if (card) card.classList.toggle('card-selected', checkbox.checked);

        updateBatchUI();
    }

    async function deleteSingle(article) {
        const result = await showModal('确认删除',
            el('div', { className: 'modal-body' }, [`确定要删除文章"${article.title}"吗？此操作不可撤销。`]),
            [
                { label: '取消', value: false },
                { label: '删除', value: true },
            ]
        );

        if (!result) return;

        try {
            await api.deleteArticle(article.id);
            const card = document.querySelector(`[data-article-id="${article.id}"]`);
            if (card) {
                // Also remove parent group header if this was the last card in a year group
                const parentGrid = card.parentElement;
                card.remove();
                if (parentGrid && parentGrid.classList.contains('article-grid') && parentGrid.children.length === 0) {
                    const groupHeader = parentGrid.previousElementSibling;
                    if (groupHeader && groupHeader.classList.contains('group-header')) {
                        groupHeader.remove();
                    }
                    parentGrid.remove();
                }
            }
            currentArticles = currentArticles.filter(a => a.id !== article.id);
            selectedIds.delete(article.id);
            showToast('已删除文章', 'success');
            updateBatchUI();
        } catch (err) {
            showToast('删除失败: ' + err.message, 'error');
        }
    }

    async function deleteSelected() {
        if (selectedIds.size === 0) return;

        const count = selectedIds.size;
        const result = await showModal('确认批量删除',
            el('div', { className: 'modal-body' }, [`确定要删除所选的 ${count} 篇文章吗？此操作不可撤销。`]),
            [
                { label: '取消', value: false },
                { label: '全部删除', value: true },
            ]
        );

        if (!result) return;

        const ids = [...selectedIds];
        const results = await Promise.allSettled(ids.map(id => api.deleteArticle(id)));

        let successCount = 0;
        let failCount = 0;

        results.forEach((r, i) => {
            if (r.status === 'fulfilled') {
                successCount++;
                const card = document.querySelector(`[data-article-id="${ids[i]}"]`);
                if (card) {
                    const parentGrid = card.parentElement;
                    card.remove();
                    if (parentGrid && parentGrid.classList.contains('article-grid') && parentGrid.children.length === 0) {
                        const groupHeader = parentGrid.previousElementSibling;
                        if (groupHeader && groupHeader.classList.contains('group-header')) {
                            groupHeader.remove();
                        }
                        parentGrid.remove();
                    }
                }
            } else {
                failCount++;
            }
        });

        currentArticles = currentArticles.filter(a => !selectedIds.has(a.id));
        exitBatchMode();

        if (failCount > 0) {
            showToast(`成功删除 ${successCount} 篇，${failCount} 篇失败`, 'error');
        } else {
            showToast(`已成功删除 ${successCount} 篇文章`, 'success');
        }
    }

    async function editArticle(article) {
        const updated = await showArticleEditor(article);
        if (!updated) return;

        // Update currentArticles
        const idx = currentArticles.findIndex(a => a.id === article.id);
        if (idx !== -1) currentArticles[idx] = updated;

        // Find and replace card in DOM
        const card = document.querySelector(`[data-article-id="${article.id}"]`);
        if (card) {
            const newCard = renderArticleCard(updated, idx >= 0 ? idx : 0);
            card.replaceWith(newCard);
        }
    }

    // ── Data functions ──────────────────────────────────────
    function getFilterParams() {
        const params = { sort: 'created_at', per_page: 50 };
        const examType = examTypeSelect.value;
        const examYear = examYearInput.value ? parseInt(examYearInput.value, 10) : null;
        const questionType = questionTypeSelect.value;

        if (examType) {
            params.exam_type = examType;
            params.sort = 'exam_year';
        }
        if (examYear) params.exam_year = examYear;
        if (questionType) params.question_type = questionType;

        return params;
    }

    // ── Card rendering ──────────────────────────────────────
    function renderArticleCard(article, index) {
        const stripeColor = STRIPE_GRADIENTS[index % STRIPE_GRADIENTS.length];
        const unknownDensity = article.unknown_word_count != null && article.word_count
            ? article.unknown_word_count / article.word_count
            : null;

        const diffColors = getDifficultyColors(unknownDensity);
        const barColor = diffColors.barColor;
        const barBg = diffColors.barBg;

        const i1score = getI1ScoreLabel(article.i_plus_one_score);
        const isSelected = selectedIds.has(article.id);

        // Batch mode checkbox
        const checkbox = el('input', {
            type: 'checkbox',
            className: 'card-checkbox',
            dataset: { articleId: String(article.id) },
            checked: isSelected,
        });
        checkbox.addEventListener('change', onCardCheckboxChange);

        // Hover action buttons
        const editBtn = el('button', {
            className: 'card-action-btn card-edit-btn',
            title: '编辑',
        }, ['✎']);
        editBtn.addEventListener('click', (e) => { e.stopPropagation(); editArticle(article); });

        const deleteBtn = el('button', {
            className: 'card-action-btn card-delete-btn',
            title: '删除',
        }, ['×']);
        deleteBtn.addEventListener('click', (e) => { e.stopPropagation(); deleteSingle(article); });

        const actions = el('div', { className: 'card-actions' }, [editBtn, deleteBtn]);

        // Exam metadata badges
        const badges = [];
        if (article.exam_type) badges.push(el('span', { className: 'badge badge-learning', style: 'font-size:10px;margin-right:4px' }, [article.exam_type]));
        if (article.exam_year) badges.push(el('span', { className: 'badge badge-familiar', style: 'font-size:10px;margin-right:4px' }, [String(article.exam_year)]));
        if (article.question_type) badges.push(el('span', { className: 'badge badge-unknown', style: 'font-size:10px' }, [article.question_type]));

        // Title with navigation click
        const titleEl = el('div', {
            className: 'article-card-title',
            style: { cursor: 'pointer' },
        }, [article.title]);
        titleEl.addEventListener('click', (e) => { e.stopPropagation(); router.navigate('#/reader/' + article.id); });

        return el('div', {
            className: 'article-card card' + (isSelected ? ' card-selected' : ''),
            dataset: { articleId: String(article.id) },
        }, [
            el('div', { className: 'article-card-top-stripe', style: { background: stripeColor } }),
            checkbox,
            actions,
            titleEl,
            badges.length ? el('div', { style: 'margin-bottom:4px' }, badges) : null,
            article.author ? el('div', { className: 'article-card-author' }, [article.author]) : null,
            el('div', { className: 'article-card-meta' }, [
                article.unknown_word_count != null ? el('span', {}, [
                    el('span', { className: 'meta-dot', style: { background: barColor } }),
                    article.unknown_word_count + ' new',
                ]) : null,
                el('span', {}, [article.word_count + ' words']),
                el('span', { style: 'margin-left:auto' }, [formatDate(article.created_at)]),
            ]),
            unknownDensity != null ? el('div', { className: 'difficulty-bar' }, [
                el('div', { className: 'difficulty-bar-inner', style: { width: (100 - unknownDensity * 100) + '%', background: barBg } }),
            ]) : null,
            unknownDensity != null ? el('div', { className: 'difficulty-label' }, [
                el('span', {}, [formatPercent(1 - unknownDensity) + ' known']),
                i1score ? el('span', {}, ['i+1: ' + i1score]) : null,
            ]) : null,
        ]);
    }

    function renderGroupedByYear(items, container) {
        // Group items by exam_year
        const groups = {};
        for (const item of items) {
            const year = item.exam_year || 'Unknown';
            if (!groups[year]) groups[year] = [];
            groups[year].push(item);
        }

        // Sort years descending
        const years = Object.keys(groups).sort((a, b) => {
            if (a === 'Unknown') return 1;
            if (b === 'Unknown') return -1;
            return b - a;
        });

        for (const year of years) {
            const groupItems = groups[year];
            container.appendChild(el('h2', {
                className: 'group-header',
                style: 'font-size:18px;font-weight:600;margin:20px 0 12px;color:var(--color-text);border-bottom:1px solid var(--color-accent-light,#d4c0a0);padding-bottom:6px',
            }, [year + ' (' + groupItems.length + ')']));

            const grid = el('div', { className: 'article-grid' + (batchMode ? ' batch-mode' : '') });
            for (let i = 0; i < groupItems.length; i++) {
                grid.appendChild(renderArticleCard(groupItems[i], i));
            }
            container.appendChild(grid);
        }
    }

    async function load() {
        content.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        try {
            const params = getFilterParams();
            const data = await api.getArticles(params);
            currentArticles = data.items || [];
            if (batchMode) {
                const currentIds = new Set(currentArticles.map(a => a.id));
                selectedIds = new Set([...selectedIds].filter(id => currentIds.has(id)));
                updateBatchUI();
            }
            if (!data.items || data.items.length === 0) {
                content.innerHTML = '<div class="empty-state"><h3>No articles found</h3><p>Try adjusting the filters or import some articles.</p></div>';
                return;
            }
            content.innerHTML = '';

            // Year-grouped display when exam_type is selected
            if (params.exam_type) {
                renderGroupedByYear(data.items, content);
            } else {
                const grid = el('div', { className: 'article-grid' + (batchMode ? ' batch-mode' : '') });
                for (let i = 0; i < data.items.length; i++) {
                    grid.appendChild(renderArticleCard(data.items[i], i));
                }
                grid.appendChild(createImportPlaceholder());
                content.appendChild(grid);
            }
        } catch (e) {
            content.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${e.message}</p></div>`;
        }
    }

    // ── Event listeners ─────────────────────────────────────
    batchToggleBtn.addEventListener('click', toggleBatchMode);
    selectAllBtn.addEventListener('click', toggleSelectAll);
    batchDeleteBtn.addEventListener('click', deleteSelected);
    batchCancelBtn.addEventListener('click', exitBatchMode);

    load();
}

function createImportPlaceholder() {
    return el('div', {
        className: 'card-import-placeholder',
        onClick: () => router.navigate('#/import'),
    }, [
        el('div', {}, [
            el('div', { style: 'font-size:24px;margin-bottom:4px' }, ['+']),
            el('div', {}, ['Import new article']),
        ]),
    ]);
}
