import { clearElement } from './utils/dom.js';

class Router {
    constructor() {
        this._routes = {};
        this._currentCleanup = null;
        window.addEventListener('hashchange', () => this._handle());
    }

    register(pattern, handler) {
        this._routes[pattern] = handler;
    }

    navigate(hash) {
        window.location.hash = hash;
    }

    _handle() {
        let hash = window.location.hash.slice(1) || 'library';
        // Strip leading slash from hash (nav links use #/library format)
        if (hash.startsWith('/')) hash = hash.slice(1);
        // Update active sidebar nav
        import('./components/sidebar.js').then(m => m.updateActive());

        // Call cleanup
        if (this._currentCleanup) {
            try { this._currentCleanup(); } catch (e) { /* ignore */ }
            this._currentCleanup = null;
        }

        const main = document.getElementById('app-main');
        clearElement(main);

        // Match route
        for (const [pattern, handler] of Object.entries(this._routes)) {
            const params = this._match(pattern, hash);
            if (params !== null) {
                this._currentCleanup = handler(main, params) || null;
                return;
            }
        }

        // 404
        main.innerHTML = '<div class="empty-state"><h3>Page not found</h3></div>';
    }

    _match(pattern, hash) {
        const patternParts = pattern.split('/');
        const hashParts = hash.split('/');

        if (patternParts.length !== hashParts.length) return null;

        const params = {};
        for (let i = 0; i < patternParts.length; i++) {
            if (patternParts[i].startsWith(':')) {
                params[patternParts[i].slice(1)] = hashParts[i];
            } else if (patternParts[i] !== hashParts[i]) {
                return null;
            }
        }
        return params;
    }
}

export const router = new Router();
