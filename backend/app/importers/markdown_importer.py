from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Optional

from markdown_it import MarkdownIt

from ..providers.importer import ContentImporter, ImportedArticle

md = MarkdownIt()


class MarkdownImporter(ContentImporter):
    @classmethod
    def provider_name(cls) -> str:
        return "markdown_importer"

    @classmethod
    def can_handle(cls, file_extension: str, mime_type: Optional[str] = None) -> bool:
        return file_extension.lower() in (".md", ".markdown")

    async def validate(self) -> bool:
        return True

    async def import_file(self, path: str) -> ImportedArticle:
        p = Path(path)
        raw = p.read_text(encoding="utf-8")
        return self._parse(raw, str(p.resolve()))

    async def import_content(self, raw_bytes: bytes, filename: str) -> ImportedArticle:
        try:
            raw = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raw = raw_bytes.decode("latin-1")
        return self._parse(raw, filename)

    def _parse(self, raw: str, source_path: str) -> ImportedArticle:
        sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        # Parse frontmatter (YAML between --- markers)
        frontmatter = {}
        content_body = raw
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                frontmatter = self._parse_frontmatter(parts[1])
                content_body = parts[2]

        # Extract title
        title = frontmatter.get("title", "")
        if not title:
            match = re.search(r"^#\s+(.+)", content_body, re.MULTILINE)
            title = match.group(1).strip() if match else Path(source_path).stem

        # Render HTML
        content_html = md.render(content_body)
        # Strip HTML tags for plain text
        plain_text = re.sub(r"<[^>]+>", "", content_html)
        plain_text = html.unescape(plain_text)

        return ImportedArticle(
            title=title,
            content_text=plain_text,
            content_html=content_html,
            source_path=source_path,
            source_type="markdown",
            sha256_hash=sha256,
            frontmatter=frontmatter,
        )

    def _parse_frontmatter(self, yaml_text: str) -> dict:
        """Minimal YAML frontmatter parser. Handles string, number, and list values."""
        result = {}
        for line in yaml_text.strip().split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
        return result
