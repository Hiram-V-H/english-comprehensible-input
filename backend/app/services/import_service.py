from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..importers.folder_scanner import scan_folder
from ..importers.registry import ImporterRegistry
from ..models.article import Article, ArticleWord
from ..models.book import Book
from ..models.import_record import ImportRecord
from ..providers.importer import BookImportResult, ImportedArticle
from .tokenizer import tokenize
from .vocabulary import get_or_create_word


def _has_letter(text: str) -> bool:
    """Return True if text contains at least one ASCII letter (a-z, A-Z)."""
    return any(c.isalpha() for c in text)


async def import_file(
    db: AsyncSession,
    file_path: str,
    registry: ImporterRegistry,
) -> Tuple[int, bool]:
    """Import a single file. Returns (article_id, is_new)."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = p.suffix.lower()
    importer_cls = registry.find(extension)
    if not importer_cls:
        raise ValueError(f"No importer found for extension: {extension}")

    importer = importer_cls()
    article_data = await importer.import_file(str(p))

    return await _save_article(db, article_data)


async def import_content(
    db: AsyncSession,
    raw_bytes: bytes,
    filename: str,
    registry: ImporterRegistry,
    title: str | None = None,
) -> Tuple[int, bool]:
    """Import from uploaded content. Returns (article_id, is_new)."""
    extension = Path(filename).suffix.lower()
    importer_cls = registry.find(extension)
    if not importer_cls:
        raise ValueError(f"No importer found for extension: {extension}")

    importer = importer_cls()
    article_data = await importer.import_content(raw_bytes, filename)

    if title is not None:
        article_data.title = title

    return await _save_article(db, article_data)


async def import_folder(
    db: AsyncSession,
    folder_path: str,
    recursive: bool,
    registry: ImporterRegistry,
) -> dict:
    """Scan and import all supported files from a folder."""
    files = scan_folder(folder_path, recursive)
    results = {"imported": 0, "skipped": 0, "errors": []}

    for f in files:
        try:
            _, is_new = await import_file(db, f, registry)
            if is_new:
                results["imported"] += 1
                # Move file to processed
                _move_file(f, settings.materials_processed_dir)
            else:
                results["skipped"] += 1
        except Exception as e:
            results["errors"].append({"file": f, "error": str(e)})
            _move_file(f, settings.materials_failed_dir)

    return results


async def _save_article(db: AsyncSession, data: ImportedArticle) -> Tuple[int, bool]:
    """Save an imported article and its word mappings. Returns (article_id, is_new)."""
    # Check for duplicate by SHA256
    existing = await db.execute(
        select(Article).where(Article.sha256_hash == data.sha256_hash)
    )
    existing_article = existing.scalar_one_or_none()
    if existing_article:
        # Record the duplicate import
        record = ImportRecord(
            source_path=data.source_path or "",
            source_type=data.source_type,
            sha256_hash=data.sha256_hash,
            article_id=existing_article.id,
            import_status="duplicate",
            imported_at=datetime.now(),
        )
        db.add(record)
        await db.commit()
        return existing_article.id, False

    # Tokenize
    tokens = tokenize(data.content_text)

    # Count only real words (exclude punctuation and non-letter tokens)
    real_word_count = sum(1 for t in tokens if not t.is_punctuation and _has_letter(t.text))

    # Create article
    article = Article(
        title=data.title,
        source_path=data.source_path,
        source_type=data.source_type,
        content_text=data.content_text,
        content_html=data.content_html,
        word_count=real_word_count,
        language="en",
        sha256_hash=data.sha256_hash,
        frontmatter=str(data.frontmatter) if data.frontmatter else None,
    )
    db.add(article)
    await db.flush()

    # Create article_word entries
    for token in tokens:
        if token.is_punctuation or not _has_letter(token.text):
            aw = ArticleWord(
                article_id=article.id,
                word_id=None,
                word_text=token.text,
                word_lower=token.text.lower(),
                position=token.position,
                sentence_index=token.sentence_index,
                is_punctuation=True,
            )
        else:
            word_record = await get_or_create_word(db, token.text)
            aw = ArticleWord(
                article_id=article.id,
                word_id=word_record.id,
                word_text=token.text,
                word_lower=token.text.lower(),
                position=token.position,
                sentence_index=token.sentence_index,
                is_unknown_at_import=(word_record.status == "unknown"),
                is_punctuation=False,
            )
        db.add(aw)

    # Record import
    record = ImportRecord(
        source_path=data.source_path or "",
        source_type=data.source_type,
        sha256_hash=data.sha256_hash,
        article_id=article.id,
        import_status="success",
        imported_at=datetime.now(),
    )
    db.add(record)

    await db.commit()

    # Run analysis
    from ..analysis.composite import CompositeAnalyzer
    analyzer = CompositeAnalyzer()
    await analyzer.analyze_and_persist(article.id, db)

    return article.id, True


def _move_file(file_path: str, dest_dir: str) -> None:
    """Move a file to the destination directory."""
    try:
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        dest = Path(dest_dir) / Path(file_path).name
        shutil.move(file_path, str(dest))
    except Exception:
        pass  # Non-critical


# ── Book import (EPUB etc.) ──────────────────────────────────

async def preview_book(
    file_path: str,
    registry: ImporterRegistry,
) -> BookImportResult:
    """Parse book file and return TOC for user preview."""
    extension = Path(file_path).suffix.lower()
    importer_cls = registry.find_book(extension)
    if not importer_cls:
        raise ValueError(f"No book importer found for extension: {extension}")

    importer = importer_cls()
    return await importer.preview(file_path)


async def import_book_chapters(
    db: AsyncSession,
    file_path: str,
    selected_chapter_indices: List[int],
    registry: ImporterRegistry,
) -> dict:
    """Import selected chapters from a book. Creates Book + Articles."""
    extension = Path(file_path).suffix.lower()
    importer_cls = registry.find_book(extension)
    if not importer_cls:
        raise ValueError(f"No book importer found for extension: {extension}")

    importer = importer_cls()
    result = await importer.import_chapters(file_path, selected_chapter_indices)

    # Check if book already exists
    existing = await db.execute(
        select(Book).where(Book.sha256_hash == result.sha256_hash)
    )
    existing_book = existing.scalar_one_or_none()
    if existing_book:
        return {"book_id": existing_book.id, "status": "duplicate", "articles_imported": 0}

    # Create Book
    book = Book(
        title=result.title,
        author=result.author or "",
        source_path=result.source_path,
        source_type=result.source_type,
        language=result.language,
        sha256_hash=result.sha256_hash,
        total_chapters=len([c for c in result.chapters if c.selected]),
        metadata_json=json.dumps(result.metadata) if result.metadata else None,
    )
    db.add(book)
    await db.flush()

    imported_count = 0
    for ch in result.chapters:
        if not ch.selected or not ch.text_content:
            continue

        article_data = ImportedArticle(
            title=ch.title,
            content_text=ch.text_content,
            source_path=ch.source_path,
            source_type="epub_chapter",
            sha256_hash=hashlib.sha256(ch.text_content.encode("utf-8")).hexdigest(),
        )

        article_id, _ = await _save_book_chapter(
            db, article_data, book.id, ch.index
        )
        imported_count += 1

    book.total_chapters = imported_count
    await db.commit()

    return {"book_id": book.id, "status": "imported", "articles_imported": imported_count}


async def _save_book_chapter(
    db: AsyncSession,
    data: ImportedArticle,
    book_id: int,
    chapter_index: int,
) -> Tuple[int, bool]:
    """Save a single book chapter as an Article linked to a Book."""
    existing = await db.execute(
        select(Article).where(Article.sha256_hash == data.sha256_hash)
    )
    if existing.scalar_one_or_none():
        return existing.scalar_one_or_none().id, False

    tokens = tokenize(data.content_text)
    real_word_count = sum(1 for t in tokens if not t.is_punctuation and _has_letter(t.text))

    article = Article(
        title=data.title,
        source_path=data.source_path,
        source_type=data.source_type,
        content_text=data.content_text,
        content_html=data.content_html,
        word_count=real_word_count,
        language="en",
        sha256_hash=data.sha256_hash,
        book_id=book_id,
        chapter_index=chapter_index,
        chapter_path=data.source_path,
    )
    db.add(article)
    await db.flush()

    for token in tokens:
        if token.is_punctuation or not _has_letter(token.text):
            aw = ArticleWord(
                article_id=article.id, word_id=None,
                word_text=token.text, word_lower=token.text.lower(),
                position=token.position, sentence_index=token.sentence_index,
                is_punctuation=True,
            )
        else:
            word_record = await get_or_create_word(db, token.text)
            aw = ArticleWord(
                article_id=article.id, word_id=word_record.id,
                word_text=token.text, word_lower=token.text.lower(),
                position=token.position, sentence_index=token.sentence_index,
                is_unknown_at_import=(word_record.status == "unknown"),
                is_punctuation=False,
            )
        db.add(aw)

    # Record import
    record = ImportRecord(
        source_path=data.source_path or "",
        source_type=data.source_type,
        sha256_hash=data.sha256_hash,
        article_id=article.id,
        import_status="success",
        imported_at=datetime.now(),
    )
    db.add(record)
    await db.commit()

    # Run analysis
    from ..analysis.composite import CompositeAnalyzer
    analyzer = CompositeAnalyzer()
    await analyzer.analyze_and_persist(article.id, db)

    return article.id, True
