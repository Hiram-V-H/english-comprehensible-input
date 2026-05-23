from __future__ import annotations

from typing import List, Optional, Type

from ..providers.importer import BaseImporter, BookImporter, ContentImporter
from .epub_importer import EpubImporter
from .markdown_importer import MarkdownImporter
from .txt_importer import TxtImporter


class ImporterRegistry:
    def __init__(self):
        self._content_importers: List[Type[ContentImporter]] = [TxtImporter, MarkdownImporter]
        self._book_importers: List[Type[BookImporter]] = [EpubImporter]

    def register_content(self, importer_cls: Type[ContentImporter]) -> None:
        self._content_importers.append(importer_cls)

    def register_book(self, importer_cls: Type[BookImporter]) -> None:
        self._book_importers.append(importer_cls)

    def find(self, extension: str) -> Optional[Type[ContentImporter]]:
        for imp in self._content_importers:
            if imp.can_handle(extension):
                return imp
        return None

    def find_book(self, extension: str) -> Optional[Type[BookImporter]]:
        for imp in self._book_importers:
            if imp.can_handle(extension):
                return imp
        return None

    def is_book_format(self, extension: str) -> bool:
        return any(imp.can_handle(extension) for imp in self._book_importers)
