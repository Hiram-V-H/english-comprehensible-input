import { el } from '../utils/dom.js';
import { router } from '../router.js';

/**
 * Resolve a toc item href to an article ID via the chapter_path → id map.
 * Handles partial path matching (e.g. "OEBPS/ch1.xhtml" vs "ch1.xhtml").
 */
function resolveArticleId(href, chapterMap) {
    if (!href) return null;
    const basePath = href.split('#')[0];
    if (!basePath) return null;

    // Exact match
    if (chapterMap[basePath]) return chapterMap[basePath];

    // Try partial match (handle differing directory prefixes)
    for (const [path, id] of Object.entries(chapterMap)) {
        if (path.endsWith('/' + basePath) || basePath.endsWith('/' + path)
            || path === basePath.split('/').pop()
            || basePath === path.split('/').pop()) {
            return id;
        }
    }
    return null;
}

/**
 * Build a chapter_path → article_id lookup from a flat chapters array.
 * @param {Array} chapters — [{id, chapter_path, ...}]
 * @returns {Object} — { "OEBPS/ch1.xhtml": 42, ... }
 */
export function buildChapterMap(chapters) {
    const map = {};
    for (const ch of chapters) {
        if (ch.chapter_path) {
            map[ch.chapter_path] = ch.id;
        }
    }
    return map;
}

/**
 * Render a recursive TOC tree.
 * @param {Array} tree — TocItem[] with {title, href, children[]}
 * @param {Object} chapterMap — { chapter_path: articleId }
 * @param {number|null} currentArticleId — highlight this article
 * @param {Object} options
 * @param {number} options.defaultCollapseDepth — collapse items at depth >= this (default 2)
 * @returns {HTMLElement}
 */
export function renderTocTree(tree, chapterMap, currentArticleId, options = {}) {
    const { defaultCollapseDepth = 2 } = options;

    const rootEl = el('div', { className: 'toc-tree' });

    function _renderItems(items, depth) {
        const container = el('div', { className: 'toc-tree-level' });

        for (const item of items) {
            const hasChildren = item.children && item.children.length > 0;
            const articleId = resolveArticleId(item.href, chapterMap);
            const isCurrent = currentArticleId != null && articleId === currentArticleId;

            const row = el('div', {
                className: 'toc-tree-item' + (isCurrent ? ' current' : ''),
            });

            // Expand/collapse toggle arrow
            const toggle = el('span', {
                className: 'toc-tree-toggle' + (hasChildren ? '' : ' toc-tree-toggle-empty'),
            });
            if (hasChildren) {
                toggle.textContent = depth < defaultCollapseDepth ? '▾' : '▸';
            }
            row.appendChild(toggle);

            // Link
            const link = el('a', {
                className: 'toc-tree-link' + (isCurrent ? ' current' : ''),
                href: articleId ? '#/reader/' + articleId : '#',
                onClick: (e) => {
                    e.preventDefault();
                    if (articleId) router.navigate('#/reader/' + articleId);
                },
            }, [item.title || 'Untitled']);
            row.appendChild(link);

            container.appendChild(row);

            // Children
            if (hasChildren) {
                const childContainer = _renderItems(item.children, depth + 1);
                childContainer.classList.add('toc-tree-children');
                if (depth + 1 > defaultCollapseDepth) {
                    childContainer.classList.add('collapsed');
                }
                container.appendChild(childContainer);

                // Toggle click handler
                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const collapsed = childContainer.classList.toggle('collapsed');
                    toggle.textContent = collapsed ? '▸' : '▾';
                });
            }
        }

        return container;
    }

    rootEl.appendChild(_renderItems(tree, 1));
    return rootEl;
}

/**
 * Match a toc item href to the corresponding flat chapter entry.
 * Returns the chapter object or null.
 */
function matchChapter(href, hrefToChapter) {
    if (!href) return null;
    const basePath = href.split('#')[0].toLowerCase();
    if (!basePath) return null;

    // Exact match
    if (hrefToChapter[basePath]) return hrefToChapter[basePath];

    // Partial path match (handle differing directory prefixes)
    for (const [path, ch] of Object.entries(hrefToChapter)) {
        if (path.endsWith('/' + basePath) || basePath.endsWith('/' + path)
            || path === basePath.split('/').pop()
            || basePath === path.split('/').pop()) {
            return ch;
        }
    }
    return null;
}

/**
 * Render a TOC tree for the import preview page, with checkboxes for chapter selection.
 * @param {Array} tree — TocItem[] with {title, href, children[]}
 * @param {Array} chapters — flat chapters [{index, title, source_path, selected}]
 * @param {Array} chapterCheckboxes — output array, populated as [index] = checkboxElement
 * @returns {HTMLElement}
 */
export function renderImportTocTree(tree, chapters, chapterCheckboxes) {
    // Build href → chapter map from flat chapters
    const hrefToChapter = {};
    for (const ch of chapters) {
        const key = (ch.source_path || '').toLowerCase();
        if (key) {
            hrefToChapter[key] = ch;
        }
    }

    const rootEl = el('div', { className: 'toc-tree' });

    function _render(items, depth) {
        const container = el('div', { className: 'toc-tree-level' });

        for (const item of items) {
            const hasChildren = item.children && item.children.length > 0;
            const chapter = matchChapter(item.href, hrefToChapter);

            const row = el('label', {
                className: 'toc-tree-item toc-tree-import-item',
                style: 'display:flex;align-items:center;gap:5px;padding:3px 0;cursor:pointer',
            });

            // Expand/collapse arrow
            const toggle = el('span', {
                className: 'toc-tree-toggle' + (hasChildren ? '' : ' toc-tree-toggle-empty'),
            });
            if (hasChildren) {
                toggle.textContent = depth < 2 ? '▾' : '▸';
            }
            row.appendChild(toggle);

            // Checkbox (if this node maps to a chapter)
            if (chapter) {
                const cb = el('input', {
                    type: 'checkbox',
                    checked: chapter.selected !== false ? 'checked' : undefined,
                    style: 'width:14px;height:14px;flex-shrink:0;margin:0',
                });
                chapterCheckboxes[chapter.index] = cb;
                row.appendChild(cb);
            } else {
                // Placeholder for alignment (no chapter = no checkbox)
                row.appendChild(el('span', { style: 'width:14px;flex-shrink:0' }));
            }

            // Title
            row.appendChild(el('span', { style: 'font-size:13px;line-height:1.5' }, [item.title || 'Untitled']));

            container.appendChild(row);

            // Children
            if (hasChildren) {
                const childContainer = _render(item.children, depth + 1);
                childContainer.classList.add('toc-tree-children');
                if (depth + 1 > 2) {
                    childContainer.classList.add('collapsed');
                }
                container.appendChild(childContainer);

                toggle.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const collapsed = childContainer.classList.toggle('collapsed');
                    toggle.textContent = collapsed ? '▸' : '▾';
                });
            }
        }

        return container;
    }

    rootEl.appendChild(_render(tree, 1));
    return rootEl;
}
