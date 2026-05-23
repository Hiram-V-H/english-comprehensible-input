import { router } from './router.js';
import { libraryPage } from './pages/library.js';
import { booksPage } from './pages/books.js';
import { vocabularyPage } from './pages/vocabulary.js';
import { importPage } from './pages/import.js';

// Register routes
router.register('library', (main) => libraryPage(main));
router.register('books', (main) => booksPage(main));
router.register('vocabulary', (main) => vocabularyPage(main));
router.register('vocabulary/:id', (main, params) => {
    import('./pages/word-detail.js').then(m => m.wordDetailPage(main, params.id));
});
router.register('import', (main) => importPage(main));
router.register('reader/:id', (main, params) => {
    import('./pages/reader.js').then(m => m.readerPage(main, params.id));
});
router.register('books/:id', (main, params) => {
    import('./pages/book-detail.js').then(m => m.bookDetailPage(main, params.id));
});

// Initial route
router._handle();
