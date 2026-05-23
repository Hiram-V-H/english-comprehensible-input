import { el, clearElement } from '../../utils/dom.js';

/**
 * Reader Core: renders clean semantic HTML with typography/theme controls.
 * Does NOT know about word status, highlights, or learning data —
 * those are applied as post-processing by the annotator.
 */
export class ContentRenderer {
    constructor(container) {
        this.container = container;
        this._settings = {
            fontSize: 18,
            lineHeight: 1.8,
            theme: 'light',
        };
        this._loadSettings();
    }

    _loadSettings() {
        try {
            const saved = localStorage.getItem('reader-settings');
            if (saved) Object.assign(this._settings, JSON.parse(saved));
        } catch (e) { /* ignore */ }
    }

    _saveSettings() {
        try {
            localStorage.setItem('reader-settings', JSON.stringify(this._settings));
        } catch (e) { /* ignore */ }
    }

    /** Render annotated HTML via innerHTML. */
    render(annotatedHtml) {
        clearElement(this.container);
        this.container.className = 'reader-html-content';
        this._applyTheme();
        this._applyTypography();
        this.container.innerHTML = annotatedHtml;
    }

    get fontSize() { return this._settings.fontSize; }
    get lineHeight() { return this._settings.lineHeight; }
    get theme() { return this._settings.theme; }

    setFontSize(size) {
        this._settings.fontSize = Math.max(12, Math.min(28, size));
        this._applyTypography();
        this._saveSettings();
    }

    setLineHeight(height) {
        this._settings.lineHeight = Math.max(1.2, Math.min(3.0, height));
        this._applyTypography();
        this._saveSettings();
    }

    setTheme(theme) {
        this._settings.theme = theme;
        this._applyTheme();
        this._saveSettings();
    }

    _applyTypography() {
        this.container.style.fontSize = this._settings.fontSize + 'px';
        this.container.style.lineHeight = String(this._settings.lineHeight);
    }

    _applyTheme() {
        if (this._settings.theme === 'dark') {
            this.container.classList.add('theme-dark');
        } else {
            this.container.classList.remove('theme-dark');
        }
    }
}
