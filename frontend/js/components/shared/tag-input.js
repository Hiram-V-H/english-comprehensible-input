import { el } from '../../utils/dom.js';
import { api } from '../../api.js';

export function renderTagInput(selectedTags = [], onChange) {
    const container = el('div', { className: 'tag-input-container' });
    const tagList = el('div', { className: 'tag-list' });
    let currentTags = [...selectedTags];

    function refresh() {
        tagList.innerHTML = '';
        for (const tag of currentTags) {
            tagList.appendChild(el('span', { className: 'tag tag-removable', style: { background: tag.color + '33' || '#e0e0e0' } }, [
                tag.name,
                el('span', { className: 'tag-remove', onClick: () => { currentTags = currentTags.filter(t => t.id !== tag.id); refresh(); onChange(currentTags); } }, ['x']),
            ]));
        }
        // add button
        const select = el('select', { className: 'status-select', onChange: (e) => {
            const tid = parseInt(e.target.value);
            if (!tid) return;
            const t = allTags.find(t => t.id === tid);
            if (t && !currentTags.find(ct => ct.id === t.id)) {
                currentTags.push(t);
                refresh();
                onChange(currentTags);
            }
            e.target.value = '';
        } }, [
            el('option', { value: '' }, ['+ tag']),
        ]);
        // Load all tags
        api.getTags().then(all => {
            allTags = all;
            for (const t of all) {
                if (!currentTags.find(ct => ct.id === t.id)) {
                    select.appendChild(el('option', { value: t.id }, [t.name]));
                }
            }
        }).catch(() => {});
        tagList.appendChild(select);
    }

    let allTags = [];
    refresh();
    container.appendChild(tagList);
    return container;
}
