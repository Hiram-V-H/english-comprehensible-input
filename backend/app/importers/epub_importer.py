from __future__ import annotations

import hashlib
import html as html_mod
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from ebooklib import epub

from ..providers.importer import BookImportResult, BookImporter, ChapterInfo


class EpubImporter(BookImporter):
    """Import EPUB books as structured chapter collections."""

    @classmethod
    def provider_name(cls) -> str:
        return "epub_importer"

    @classmethod
    def can_handle(cls, file_extension: str, mime_type: Optional[str] = None) -> bool:
        return file_extension.lower() == ".epub"

    async def validate(self) -> bool:
        return True

    async def preview(self, path: str) -> BookImportResult:
        """Parse EPUB metadata and TOC without importing content."""
        book = epub.read_epub(path)
        sha256 = hashlib.sha256(Path(path).read_bytes()).hexdigest()

        title = self._get_metadata(book, "title") or Path(path).stem
        author = self._get_metadata(book, "creator") or ""

        # Build chapter list from TOC
        chapters = self._extract_toc(book)

        return BookImportResult(
            title=title,
            author=author,
            language=self._get_metadata(book, "language") or "en",
            source_path=str(Path(path).resolve()),
            source_type="epub",
            sha256_hash=sha256,
            total_chapters=len(chapters),
            chapters=chapters,
            metadata={
                "publisher": self._get_metadata(book, "publisher"),
                "description": self._get_metadata(book, "description"),
            },
        )

    async def import_chapters(
        self, path: str, selected_chapter_indices: List[int],
    ) -> BookImportResult:
        """Parse EPUB and populate text content for selected chapters."""
        result = await self.preview(path)
        book = epub.read_epub(path)

        selected_set = set(selected_chapter_indices)

        for ch in result.chapters:
            if ch.index not in selected_set:
                ch.selected = False
                continue
            ch.selected = True

            # Extract text from the chapter
            text = self._extract_chapter_text(book, ch.source_path)
            ch.text_content = text
            ch.word_count = len(text.split()) if text else 0

        return result

    # ── Private helpers ─────────────────────────────────────

    def _get_metadata(self, book, key: str) -> Optional[str]:
        """Safely extract Dublin Core metadata."""
        items = book.get_metadata("DC", key)
        if items:
            return str(items[0][0])
        return None

    def _extract_toc(self, book) -> List[ChapterInfo]:
        """Walk the EPUB table of contents and return chapter entries."""
        chapters: List[ChapterInfo] = []
        toc = book.toc

        def walk(items, depth=0):
            for item in items:
                if isinstance(item, tuple) and len(item) >= 1:
                    # (section, children) tuple — epub3 style
                    walk(item, depth + 1)
                elif isinstance(item, epub.Link):
                    title = item.title or f"Chapter {len(chapters) + 1}"
                    href = item.href or ""
                    chapters.append(ChapterInfo(
                        index=len(chapters),
                        title=title,
                        source_path=href.split("#")[0] if "#" in href else href,
                    ))
                    walk(item.children if hasattr(item, 'children') else [], depth + 1)
                elif isinstance(item, list):
                    walk(item, depth)

        try:
            walk(toc)
        except Exception:
            pass

        # If TOC is empty, try to find chapters from spine
        if not chapters:
            chapters = self._extract_from_spine(book)

        return chapters

    def _extract_from_spine(self, book) -> List[ChapterInfo]:
        """Fallback: build chapter list from spine items."""
        chapters = []
        spine_items = []
        for item_id, _ in book.spine:
            try:
                item = book.get_item_with_id(item_id)
                if item:
                    spine_items.append(item)
            except Exception:
                continue

        for i, item in enumerate(spine_items):
            chapters.append(ChapterInfo(
                index=i,
                title=f"Chapter {i + 1}",
                source_path=item.file_name,
            ))
        return chapters

    def _extract_chapter_text(self, book, file_path: str) -> str:
        """Extract clean plain text from an EPUB chapter XHTML file."""
        try:
            # Find the document item
            for item in book.get_items_of_type(9):  # ITEM_DOCUMENT = 9
                if item.file_name == file_path or item.file_name.endswith(file_path):
                    content = item.get_content().decode("utf-8", errors="replace")
                    return self._html_to_text(content)

            # Try by matching partial path
            for item in book.get_items_of_type(9):
                if file_path in item.file_name or item.file_name in file_path:
                    content = item.get_content().decode("utf-8", errors="replace")
                    return self._html_to_text(content)

            return ""
        except Exception:
            return ""

    def _html_to_text(self, html_content: str) -> str:
        """Strip HTML tags and return clean plain text."""
        # Remove script and style blocks
        html_content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL)
        # Replace block-level tags with newlines
        html_content = re.sub(r'</?(?:p|div|br|h[1-6]|li|tr)[^>]*>', '\n', html_content, flags=re.IGNORECASE)
        # Remove remaining tags
        html_content = re.sub(r'<[^>]+>', '', html_content)
        # Decode HTML entities
        html_content = html_mod.unescape(html_content)
        # Clean up whitespace
        html_content = re.sub(r'\n{3,}', '\n\n', html_content)
        html_content = re.sub(r'[ \t]+', ' ', html_content)
        return html_content.strip()

    def _get_all_text(self, book) -> str:
        """Get concatenated text from all spine items (for word count estimation)."""
        parts = []
        for item_id, _ in book.spine:
            try:
                item = book.get_item_with_id(item_id)
                if item:
                    content = item.get_content().decode("utf-8", errors="replace")
                    parts.append(self._html_to_text(content))
            except Exception:
                continue
        return "\n\n".join(parts)
