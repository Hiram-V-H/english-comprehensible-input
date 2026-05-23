import { appState } from '../state.js';

const NAV_ITEMS = [
    { pattern: 'library',    href: '#/library',    icon: '📚', label: 'Library' },
    { pattern: 'books',      href: '#/books',      icon: '📕', label: 'Books' },
    { pattern: 'vocabulary', href: '#/vocabulary', icon: '📝', label: 'Vocabulary' },
    { pattern: 'import',     href: '#/import',     icon: '⤵',       label: 'Import' },
];

export function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    renderNav(sidebar);
    updateActive();

    const toggle = sidebar.querySelector('.sidebar-toggle');
    toggle.addEventListener('click', () => {
        const collapsed = sidebar.classList.toggle('collapsed');
        appState.set('sidebarCollapsed', collapsed);
    });

    const saved = appState.get('sidebarCollapsed');
    if (saved) {
        sidebar.classList.add('collapsed');
    }

    appState.addEventListener('change:sidebarCollapsed', (e) => {
        if (e.detail) {
            sidebar.classList.add('collapsed');
        } else {
            sidebar.classList.remove('collapsed');
        }
    });
}

function renderNav(sidebar) {
    const nav = sidebar.querySelector('.sidebar-nav');
    nav.innerHTML = '';
    for (const item of NAV_ITEMS) {
        const a = document.createElement('a');
        a.className = 'sidebar-nav-item';
        a.href = item.href;
        a.setAttribute('data-pattern', item.pattern);
        a.innerHTML = `<span class="nav-icon">${item.icon}</span><span class="nav-label">${item.label}</span>`;
        nav.appendChild(a);
    }
}

export function updateActive() {
    let hash = window.location.hash.slice(1) || 'library';
    if (hash.startsWith('/')) hash = hash.slice(1);

    document.querySelectorAll('.sidebar-nav-item').forEach(item => {
        const pattern = item.getAttribute('data-pattern');
        const isActive = hash.startsWith(pattern) || (pattern === 'library' && !hash);
        item.classList.toggle('active', isActive);
    });
}
