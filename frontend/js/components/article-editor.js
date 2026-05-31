import { el } from '../utils/dom.js';
import { showModal } from './shared/modal.js';
import { showToast } from './shared/toast.js';
import { api } from '../api.js';

/**
 * Build the edit form DOM element for article metadata.
 * @param {Object} article — article summary object (id, title, exam_type, exam_year, question_type, is_archived)
 * @returns {HTMLDivElement}
 */
function buildEditForm(article) {
    const titleInput = el('input', {
        className: 'form-input',
        id: 'edit-title',
        value: article.title || '',
        placeholder: '文章标题',
    });
    const titleGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', textContent: '标题' }),
        titleInput,
    ]);

    const examTypeInput = el('input', {
        className: 'form-input',
        id: 'edit-exam-type',
        value: article.exam_type || '',
        placeholder: '如: 考研英语, CET-4, IELTS',
        list: 'exam-type-list',
    });
    const examTypeDatalist = el('datalist', { id: 'exam-type-list' }, [
        el('option', { value: '考研英语' }),
        el('option', { value: 'CET-4' }),
        el('option', { value: 'CET-6' }),
        el('option', { value: 'IELTS' }),
        el('option', { value: 'TOEFL' }),
        el('option', { value: '高考英语' }),
    ]);
    const examTypeGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', textContent: '考试类型' }),
        examTypeInput,
        examTypeDatalist,
    ]);

    const examYearInput = el('input', {
        className: 'form-input',
        id: 'edit-exam-year',
        type: 'number',
        value: article.exam_year || '',
        placeholder: '如: 2024',
        style: { maxWidth: '120px' },
    });
    const examYearGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', textContent: '年份' }),
        examYearInput,
    ]);

    const questionTypeInput = el('input', {
        className: 'form-input',
        id: 'edit-question-type',
        value: article.question_type || '',
        placeholder: '如: 阅读理解, 完形填空',
        list: 'question-type-list',
    });
    const questionTypeDatalist = el('datalist', { id: 'question-type-list' }, [
        el('option', { value: '阅读理解' }),
        el('option', { value: '完形填空' }),
        el('option', { value: '翻译' }),
        el('option', { value: '写作' }),
        el('option', { value: '新题型' }),
        el('option', { value: '听力' }),
    ]);
    const questionTypeGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', textContent: '题型' }),
        questionTypeInput,
        questionTypeDatalist,
    ]);

    const archiveCheckbox = el('input', {
        type: 'checkbox',
        id: 'edit-archived',
        checked: article.is_archived || false,
    });
    const archiveGroup = el('div', { className: 'form-group' }, [
        el('label', { className: 'form-label', style: { display: 'flex', alignItems: 'center', gap: '8px' } }, [
            archiveCheckbox,
            '归档（从库中隐藏）',
        ]),
    ]);

    return el('div', { className: 'edit-article-form' }, [
        titleGroup,
        el('div', { className: 'form-row' }, [examTypeGroup, examYearGroup]),
        questionTypeGroup,
        archiveGroup,
    ]);
}

/**
 * Open an edit modal for article metadata. Returns a Promise that resolves
 * with the updated article data on save, or null on cancel.
 * @param {Object} article
 * @returns {Promise<Object|null>}
 */
export async function showArticleEditor(article) {
    const formEl = buildEditForm(article);
    const bodyEl = el('div', { className: 'modal-body' }, [formEl]);

    const result = await showModal('✎ 编辑文章信息', bodyEl, [
        { label: '取消', value: false },
        { label: '保存修改', value: 'save', primary: true },
    ]);

    if (result !== 'save') return null;

    // Read form values
    const title = formEl.querySelector('#edit-title').value.trim();
    if (!title) {
        showToast('标题不能为空', 'error');
        return null;
    }

    const examTypeVal = formEl.querySelector('#edit-exam-type').value.trim() || null;
    const examYearRaw = formEl.querySelector('#edit-exam-year').value.trim();
    const examYearVal = examYearRaw ? parseInt(examYearRaw, 10) : null;
    const questionTypeVal = formEl.querySelector('#edit-question-type').value.trim() || null;
    const isArchived = formEl.querySelector('#edit-archived').checked;

    const updateData = {
        title,
        exam_type: examTypeVal,
        exam_year: examYearVal,
        question_type: questionTypeVal,
        is_archived: isArchived,
    };

    try {
        const updated = await api.updateArticle(article.id, updateData);
        showToast('已更新文章信息', 'success');
        return updated;
    } catch (err) {
        showToast('更新失败，请重试', 'error');
        return null;
    }
}
