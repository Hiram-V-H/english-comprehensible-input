const BASE = '/api';

async function request(method, path, body = null) {
    const opts = {
        method,
        headers: {},
    };
    if (body && !(body instanceof FormData)) {
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(body);
    } else if (body instanceof FormData) {
        opts.body = body;
    }
    const res = await fetch(BASE + path, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    return data.data;
}

export const api = {
    // Health
    health: () => request('GET', '/health'),

    // Vocabulary
    getWords: (params = {}) => {
        const q = new URLSearchParams();
        if (params.page) q.set('page', params.page);
        if (params.per_page) q.set('per_page', params.per_page);
        if (params.status) q.set('status', params.status);
        if (params.search) q.set('search', params.search);
        if (params.sort) q.set('sort', params.sort);
        return request('GET', '/vocabulary?' + q);
    },
    getVocabularyStats: () => request('GET', '/vocabulary/stats'),
    getWord: (id) => request('GET', '/vocabulary/' + id),
    updateWord: (id, data) => request('PATCH', '/vocabulary/' + id, data),
    bulkUpdateStatus: (data) => request('POST', '/vocabulary/bulk-status', data),
    searchWords: (q, limit = 10) => request('GET', `/vocabulary/search?q=${encodeURIComponent(q)}&limit=${limit}`),
    addWordNote: (wordId, data) => request('POST', `/vocabulary/${wordId}/notes`, data),
    updateWordNote: (wordId, noteId, data) => request('PATCH', `/vocabulary/${wordId}/notes/${noteId}`, data),
    deleteWordNote: (wordId, noteId) => request('DELETE', `/vocabulary/${wordId}/notes/${noteId}`),

    // Articles
    getArticles: (params = {}) => {
        const q = new URLSearchParams();
        if (params.page) q.set('page', params.page);
        if (params.per_page) q.set('per_page', params.per_page);
        if (params.sort) q.set('sort', params.sort);
        if (params.tag) q.set('tag', params.tag);
        return request('GET', '/articles?' + q);
    },
    getArticle: (id) => request('GET', '/articles/' + id),
    updateArticle: (id, data) => request('PATCH', '/articles/' + id, data),
    deleteArticle: (id) => request('DELETE', '/articles/' + id),

    // Import
    importText: (title, content) =>
        request('POST', '/import/text', { title, content }),
    importFile: (file) => {
        const fd = new FormData();
        fd.append('file', file);
        return request('POST', '/import/file', fd);
    },
    importFolder: (folderPath, recursive = false) =>
        request('POST', '/import/folder', { folder_path: folderPath, recursive }),
    getImportHistory: (params = {}) => {
        const q = new URLSearchParams();
        if (params.page) q.set('page', params.page);
        if (params.per_page) q.set('per_page', params.per_page);
        return request('GET', '/import/history?' + q);
    },
    checkImportPath: (path) => request('POST', '/import/check', { path }),

    // Analysis
    getAnalysis: (articleId) => request('GET', `/articles/${articleId}/analysis`),
    reanalyze: (articleId) => request('POST', `/articles/${articleId}/analysis/reanalyze`),

    // Reader
    getReaderData: (articleId) => request('GET', `/reader/${articleId}`),
    recordEncounter: (articleId, wordId) => request('POST', `/reader/${articleId}/word/${wordId}/encounter`),
    startSession: (articleId) => request('POST', `/reader/${articleId}/session/start`),
    endSession: (articleId, sessionId, data) =>
        request('POST', `/reader/${articleId}/session/${sessionId}/end`, data),

    // Highlights
    getHighlights: (articleId) => request('GET', `/articles/${articleId}/highlights`),
    createHighlight: (articleId, data) => request('POST', `/articles/${articleId}/highlights`, data),
    updateHighlight: (articleId, highlightId, data) =>
        request('PATCH', `/articles/${articleId}/highlights/${highlightId}`, data),
    deleteHighlight: (articleId, highlightId) =>
        request('DELETE', `/articles/${articleId}/highlights/${highlightId}`),

    // Annotations
    getAnnotations: (highlightId) => request('GET', `/highlights/${highlightId}/annotations`),
    createAnnotation: (highlightId, data) => request('POST', `/highlights/${highlightId}/annotations`, data),
    updateAnnotation: (annotationId, data) => request('PATCH', `/annotations/${annotationId}`, data),
    deleteAnnotation: (annotationId) => request('DELETE', `/annotations/${annotationId}`),

    // Tags
    getTags: () => request('GET', '/tags'),
    createTag: (data) => request('POST', '/tags', data),
    deleteTag: (tagId) => request('DELETE', '/tags/' + tagId),
    addAnnotationTag: (annotationId, tagId) =>
        request('POST', `/annotations/${annotationId}/tags`, { tag_id: tagId }),
    removeAnnotationTag: (annotationId, tagId) =>
        request('DELETE', `/annotations/${annotationId}/tags/${tagId}`),
};
