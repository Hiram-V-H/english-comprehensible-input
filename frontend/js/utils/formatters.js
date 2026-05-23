export function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
}

export function formatPercent(val) {
    if (val == null) return '--';
    return (val * 100).toFixed(1) + '%';
}

export function pluralize(n, singular, plural) {
    return n === 1 ? singular : (plural || singular + 's');
}
