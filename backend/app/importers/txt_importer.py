from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from ..providers.importer import ContentImporter, ImportedArticle


class TxtImporter(ContentImporter):
    @classmethod
    def provider_name(cls) -> str:
        return "txt_importer"

    @classmethod
    def can_handle(cls, file_extension: str, mime_type: Optional[str] = None) -> bool:
        return file_extension.lower() in (".txt", ".text")

    async def validate(self) -> bool:
        return True

    async def import_file(self, path: str) -> ImportedArticle:
        p = Path(path)
        content = p.read_text(encoding="utf-8-sig")
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        first_line = content.strip().split("\n")[0].strip().lstrip("#").strip()
        title = first_line[:200] if first_line else p.stem

        return ImportedArticle(
            title=title,
            content_text=content,
            source_path=str(p.resolve()),
            source_type="txt",
            sha256_hash=sha256,
        )

    async def import_content(self, raw_bytes: bytes, filename: str) -> ImportedArticle:
        try:
            content = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = raw_bytes.decode("latin-1")

        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        first_line = content.strip().split("\n")[0].strip()
        title = first_line[:200] if first_line else Path(filename).stem

        return ImportedArticle(
            title=title,
            content_text=content,
            source_path=filename,
            source_type="txt",
            sha256_hash=sha256,
        )
