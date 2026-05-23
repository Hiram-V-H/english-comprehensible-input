export function el(tag, attrs = {}, children = []) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
        if (k === 'className') e.className = v;
        else if (k === 'innerHTML') e.innerHTML = v;
        else if (k === 'textContent') e.textContent = v;
        else if (k.startsWith('on')) e.addEventListener(k.slice(2).toLowerCase(), v);
        else if (k === 'style') {
            if (typeof v === 'string') e.style.cssText = v;
            else Object.assign(e.style, v);
        }
        else if (k === 'dataset') Object.assign(e.dataset, v);
        else if (v != null) e.setAttribute(k, v);
    }
    const kids = Array.isArray(children) ? children : [children];
    for (const child of kids) {
        if (child == null) continue;
        e.append(typeof child === 'string' ? document.createTextNode(child) : child);
    }
    return e;
}

export function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

export function debounce(fn, ms = 300) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

export function clearElement(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
}
