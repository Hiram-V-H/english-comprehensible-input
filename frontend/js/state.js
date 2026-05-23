class AppState extends EventTarget {
    constructor() {
        super();
        this._store = {};
    }

    get(key) { return this._store[key]; }
    set(key, value) {
        this._store[key] = value;
        this.dispatchEvent(new CustomEvent('change:' + key, { detail: value }));
    }
}

export const appState = new AppState();
