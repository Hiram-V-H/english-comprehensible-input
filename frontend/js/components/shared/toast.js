import { el } from '../../utils/dom.js';

export function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    const toast = el('div', { className: `toast toast-${type}` }, [message]);
    container.appendChild(toast);
    setTimeout(() => { toast.remove(); }, duration);
}
