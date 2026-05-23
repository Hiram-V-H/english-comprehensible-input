from __future__ import annotations

import hashlib
import html as html_mod
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ebooklib import epub

from ..providers.importer import BookImportResult, BookImporter, ChapterInfo, TocItem


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

        # Build chapter list and TOC tree from direct XML parsing
        chapters, toc_tree = self._extract_toc(path)

        return BookImportResult(
            title=title,
            author=author,
            language=self._get_metadata(book, "language") or "en",
            source_path=str(Path(path).resolve()),
            source_type="epub",
            sha256_hash=sha256,
            total_chapters=len(chapters),
            chapters=chapters,
            toc_tree=toc_tree,
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

    # ── TOC extraction (direct ZIP/XML parsing) ──────────────

    def _extract_toc(self, path: str) -> Tuple[List[ChapterInfo], List[TocItem]]:
        """Parse EPUB TOC directly from NCX/NAV XML inside the ZIP.
        Returns (flat_chapters, toc_tree)."""
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                # Step 1: META-INF/container.xml → OPF path
                container_root = ET.fromstring(zf.read('META-INF/container.xml'))
                opf_path = self._find_opf_path(container_root)
                if not opf_path:
                    raise ValueError("No rootfile in container.xml")

                # Step 2: Parse OPF → find NCX or NAV
                opf_root = ET.fromstring(zf.read(opf_path))
                opf_dir = Path(opf_path).parent

                # EPUB 3 NAV
                nav_href = self._find_nav_href(opf_root)
                if nav_href:
                    nav_full = (opf_dir / nav_href).as_posix()
                    return self._parse_nav(zf.read(nav_full), opf_dir)

                # EPUB 2 NCX
                ncx_href = self._find_ncx_href(opf_root)
                if ncx_href:
                    ncx_full = (opf_dir / ncx_href).as_posix()
                    return self._parse_ncx(zf.read(ncx_full), opf_dir)

                # Fallback: build from manifest spine
                return self._build_from_manifest(opf_root, opf_dir, zf)

        except Exception:
            pass

        # Final fallback: use ebooklib spine
        return self._extract_from_spine_fallback(path)

    def _find_opf_path(self, container_root: ET.Element) -> str:
        """Extract the OPF full-path from container.xml."""
        ns = 'urn:oasis:names:tc:opendocument:xmlns:container'
        rootfile = container_root.find(f'{{{ns}}}rootfile')
        if rootfile is None:
            # Try without namespace
            for el in container_root.iter():
                if el.tag.endswith('rootfile'):
                    rootfile = el
                    break
        return rootfile.attrib.get('full-path', '') if rootfile is not None else ''

    def _find_nav_href(self, opf_root: ET.Element) -> Optional[str]:
        """Find the EPUB 3 nav document href in OPF manifest."""
        for item in opf_root.iter():
            if not item.tag.endswith('}item') and not item.tag.endswith('item'):
                continue
            if item.attrib.get('properties') == 'nav':
                return item.attrib.get('href')
        return None

    def _find_ncx_href(self, opf_root: ET.Element) -> Optional[str]:
        """Find the EPUB 2 NCX href in OPF manifest."""
        for item in opf_root.iter():
            if not item.tag.endswith('}item') and not item.tag.endswith('item'):
                continue
            if item.attrib.get('media-type') == 'application/x-dtbncx+xml':
                return item.attrib.get('href')
        return None

    def _get_ns(self, root: ET.Element) -> str:
        """Extract namespace URI from root element tag."""
        tag = root.tag
        if tag.startswith('{'):
            return tag[1:tag.index('}')]
        return ''

    def _resolve_path(self, src: str, opf_dir: Path) -> str:
        """Normalize an NCX/NAV src/href to be relative to the EPUB root."""
        if not src:
            return ''
        # Resolve relative to OPF directory
        if opf_dir != Path('.'):
            resolved = (opf_dir / src).as_posix()
        else:
            resolved = src
        return resolved

    # ── EPUB 2 NCX parser ────────────────────────────────────

    def _parse_ncx(
        self, xml_bytes: bytes, opf_dir: Path
    ) -> Tuple[List[ChapterInfo], List[TocItem]]:
        """Recursively parse EPUB 2 NCX navMap."""
        root = ET.fromstring(xml_bytes)
        ns = self._get_ns(root)

        nav_map = root.find(f'{{{ns}}}navMap') if ns else root.find('navMap')
        if nav_map is None:
            return [], []

        chapters: List[ChapterInfo] = []

        def parse_nav_points(parent_el, parent_source_path: str = '') -> List[TocItem]:
            items: List[TocItem] = []
            tag = f'{{{ns}}}navPoint' if ns else 'navPoint'

            for np in parent_el.findall(tag):
                # Title
                title = 'Untitled'
                label = np.find(f'{{{ns}}}navLabel') if ns else np.find('navLabel')
                if label is not None:
                    text = label.find(f'{{{ns}}}text') if ns else label.find('text')
                    if text is not None and text.text:
                        title = text.text.strip()

                # Source
                content = np.find(f'{{{ns}}}content') if ns else np.find('content')
                src = content.attrib.get('src', '') if content is not None else ''
                href = self._resolve_path(src, opf_dir)
                source_path = href.split('#')[0] if '#' in href else href
                if not source_path and parent_source_path:
                    source_path = parent_source_path

                chapters.append(ChapterInfo(
                    index=len(chapters),
                    title=title,
                    source_path=source_path,
                ))

                children = parse_nav_points(np, source_path)
                items.append(TocItem(title=title, href=href, children=children))

            return items

        toc_tree = parse_nav_points(nav_map)
        return chapters, toc_tree

    # ── EPUB 3 NAV (XHTML) parser ────────────────────────────

    def _parse_nav(
        self, xml_bytes: bytes, opf_dir: Path
    ) -> Tuple[List[ChapterInfo], List[TocItem]]:
        """Recursively parse EPUB 3 nav.xhtml toc."""
        root = ET.fromstring(xml_bytes)
        ns = self._get_ns(root)

        # Find <nav epub:type="toc">
        toc_nav = None
        for nav in root.iter():
            if not nav.tag.endswith('}nav') and not nav.tag.endswith('nav'):
                continue
            epub_type = (
                nav.attrib.get('{http://www.idpf.org/2007/ops}type')
                or nav.attrib.get('epub:type', '')
            )
            if epub_type == 'toc':
                toc_nav = nav
                break

        if toc_nav is None:
            return [], []

        chapters: List[ChapterInfo] = []

        def parse_ol(parent_el, parent_source_path: str = '') -> List[TocItem]:
            items: List[TocItem] = []
            ol_tag = f'{{{ns}}}ol' if ns else 'ol'

            for ol_el in parent_el.findall(ol_tag):
                for li_el in ol_el:
                    if not (li_el.tag.endswith('}li') or li_el.tag == 'li'):
                        continue

                    # Find <a> element
                    a_el = li_el.find(f'{{{ns}}}a') if ns else li_el.find('a')
                    title = 'Untitled'
                    href = ''
                    if a_el is not None:
                        title = ''.join(a_el.itertext()).strip() or 'Untitled'
                        href = self._resolve_path(a_el.attrib.get('href', ''), opf_dir)

                    source_path = href.split('#')[0] if '#' in href else href
                    if not source_path and parent_source_path:
                        source_path = parent_source_path

                    chapters.append(ChapterInfo(
                        index=len(chapters),
                        title=title,
                        source_path=source_path,
                    ))

                    children = parse_ol(li_el, source_path)
                    items.append(TocItem(title=title, href=href, children=children))

            return items

        toc_tree = parse_ol(toc_nav)
        return chapters, toc_tree

    # ── Fallback: build from OPF manifest spine ──────────────

    def _build_from_manifest(
        self, opf_root: ET.Element, opf_dir: Path, zf: zipfile.ZipFile
    ) -> Tuple[List[ChapterInfo], List[TocItem]]:
        """Build flat chapter list from OPF spine when no NCX/NAV found."""
        chapters: List[ChapterInfo] = []
        toc_items: List[TocItem] = []

        # Find all itemrefs in spine
        spine_refs = []
        for el in opf_root.iter():
            if el.tag.endswith('}itemref') or el.tag.endswith('itemref'):
                spine_refs.append(el.attrib.get('idref', ''))

        # Build id→href lookup from manifest
        manifest: Dict[str, str] = {}
        for el in opf_root.iter():
            if el.tag.endswith('}item') or el.tag.endswith('item'):
                item_id = el.attrib.get('id', '')
                href = el.attrib.get('href', '')
                if item_id and href:
                    manifest[item_id] = href

        for i, idref in enumerate(spine_refs):
            href = manifest.get(idref, '')
            source_path = self._resolve_path(href, opf_dir)
            title = f'Chapter {i + 1}'
            chapters.append(ChapterInfo(
                index=i,
                title=title,
                source_path=source_path,
            ))
            toc_items.append(TocItem(title=title, href=source_path))

        return chapters, toc_items

    def _extract_from_spine_fallback(
        self, path: str
    ) -> Tuple[List[ChapterInfo], List[TocItem]]:
        """Last-resort fallback using ebooklib spine."""
        try:
            book = epub.read_epub(path)
            chapters: List[ChapterInfo] = []
            toc_items: List[TocItem] = []

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
                    title=f'Chapter {i + 1}',
                    source_path=item.file_name,
                ))
                toc_items.append(TocItem(
                    title=f'Chapter {i + 1}',
                    href=item.file_name,
                ))

            return chapters, toc_items
        except Exception:
            return [], []

    # ── Metadata helpers ─────────────────────────────────────

    def _get_metadata(self, book, key: str) -> Optional[str]:
        """Safely extract Dublin Core metadata."""
        items = book.get_metadata("DC", key)
        if items:
            return str(items[0][0])
        return None

    # ── Text extraction helpers ──────────────────────────────

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
