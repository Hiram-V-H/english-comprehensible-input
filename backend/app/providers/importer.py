"""Unified Import System

Architecture:
    BaseImporter (ABC)
        ├── ContentImporter (single-article: txt, md)
        └── BookImporter   (multi-chapter: EPUB, PDF, etc.)

Import flow:
    1. Preview: parse file → return TOC/Chapter list
    2. Confirm: user selects chapters → system imports

Data contracts:
    ImportedArticle — single article (existing)
    ChapterInfo       — chapter metadata for preview
    BookImportResult  — TOC + chapter list for preview
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .base import BaseProvider


# ── Data contracts ──────────────────────────────────────────

@dataclass
class ImportedArticle:
    """Normalized result from any ContentImporter."""
    title: str
    content_text: str
    content_html: Optional[str] = None
    source_path: Optional[str] = None
    source_type: str = "import"
    sha256_hash: str = ""
    frontmatter: Optional[Dict] = None


@dataclass
class TocItem:
    """Recursive table-of-contents node."""
    title: str
    href: str
    children: List[TocItem] = field(default_factory=list)


@dataclass
class ChapterInfo:
    """Metadata for one chapter in a book during preview phase."""
    index: int                      # 0-based chapter index
    title: str                      # chapter title from TOC
    source_path: str                # internal path within the book (e.g. "chapter1.xhtml")
    word_count: int = 0             # estimated word count (filled after parsing)
    selected: bool = True           # user wants to import this chapter
    text_content: str = ""          # populated after import_chapters() for selected chapters


@dataclass
class BookImportResult:
    """Result of previewing a book — returned to UI for chapter selection."""
    title: str
    author: str = ""
    language: str = "en"
    source_path: str = ""
    source_type: str = "epub"
    sha256_hash: str = ""
    total_chapters: int = 0
    chapters: List[ChapterInfo] = field(default_factory=list)
    toc_tree: List[TocItem] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


# ── Importer ABCs ───────────────────────────────────────────

class BaseImporter(BaseProvider):
    """Top-level importer ABC."""

    @classmethod
    @abstractmethod
    def can_handle(cls, file_extension: str, mime_type: Optional[str] = None) -> bool:
        ...


class ContentImporter(BaseImporter):
    """For files that produce a single Article (txt, md, etc.)."""

    @abstractmethod
    async def import_file(self, path: str) -> ImportedArticle:
        ...

    @abstractmethod
    async def import_content(self, raw_bytes: bytes, filename: str) -> ImportedArticle:
        ...


class BookImporter(BaseImporter):
    """For files that produce a Book with multiple chapters (EPUB, PDF, etc.).

    The import flow has two phases:
        1. preview(path) → BookImportResult (TOC + chapter list)
        2. import_chapters(path, selected_indices) → (Book, List[ImportedArticle])
    """

    @abstractmethod
    async def preview(self, path: str) -> BookImportResult:
        """Parse the file and return TOC/chapter metadata for user review."""
        ...

    @abstractmethod
    async def import_chapters(
        self, path: str, selected_chapter_indices: List[int],
    ) -> BookImportResult:
        """Import only the selected chapters. Returns the same result with
        chapter.text_content populated for selected chapters."""
        ...
