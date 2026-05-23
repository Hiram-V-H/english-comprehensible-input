import { el } from '../../utils/dom.js';

export function showModal(title, bodyEl, actions = []) {
    return new Promise((resolve) => {
        const overlay = el('div', { className: 'modal-overlay', onClick: (e) => { if (e.target === overlay) close(null); } });
        const actionBtns = actions.map(a =>
            el('button', {
                className: 'btn ' + (a.primary ? 'btn-primary' : ''),
                onClick: () => close(a.value),
            }, [a.label])
        );
        const modal = el('div', { className: 'modal-box' }, [
            el('h2', {}, [title]),
            bodyEl,
            actionBtns.length ? el('div', { className: 'modal-actions' }, actionBtns) : null,
        ]);
        overlay.appendChild(modal);

        function close(value) {
            overlay.remove();
            resolve(value);
        }

        document.body.appendChild(overlay);
    });
}
