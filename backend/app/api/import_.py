from __future__ import annotations

import hashlib
import math
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..importers.registry import ImporterRegistry
from ..schemas.import_ import FolderImportRequest, ImportRecordOut, ImportResult, PathCheckRequest
from ..services import article as article_service
from ..services.import_service import (
    import_book_chapters,
    import_content,
    import_file,
    import_folder,
    preview_book,
)
from .deps import get_db

router = APIRouter(prefix="/import", tags=["import"])


class EpubConfirmBody(BaseModel):
    temp_file_path: str
    selected_chapter_indices: List[int]


class TextImportBody(BaseModel):
    title: str
    content: str


@router.post("/file")
async def upload_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    registry = ImporterRegistry()
    raw_bytes = await file.read()
    filename = file.filename or "untitled"
    extension = Path(filename).suffix.lower()

    # Check if it's a book format (EPUB etc.)
    if registry.is_book_format(extension):
        # Save to temp file for two-step preview+confirm flow
        tmp = tempfile.NamedTemporaryFile(suffix=extension, delete=False)
        tmp.write(raw_bytes)
        tmp.close()

        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        return {
            "status": "ok",
            "data": {
                "type": "book",
                "temp_file_path": tmp.name,
                "sha256_hash": sha256,
            },
        }

    # Single article import
    article_id, is_new = await import_content(db, raw_bytes, filename, registry)

    from ..models.article import Article
    from sqlalchemy import select
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one()

    return {
        "status": "ok",
        "data": ImportResult(
            article_id=article.id,
            title=article.title,
            status="imported" if is_new else "duplicate",
            word_count=article.word_count or 0,
        ),
    }


@router.post("/epub/preview")
async def epub_preview(file: UploadFile = File(...)):
    """Parse EPUB and return TOC for user to select chapters."""
    registry = ImporterRegistry()
    raw_bytes = await file.read()

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".epub", delete=False)
    tmp.write(raw_bytes)
    tmp.close()

    try:
        result = await preview_book(tmp.name, registry)
        return {
            "status": "ok",
            "data": {
                "temp_file_path": tmp.name,
                "title": result.title,
                "author": result.author,
                "sha256_hash": result.sha256_hash,
                "total_chapters": result.total_chapters,
                "chapters": [
                    {
                        "index": ch.index,
                        "title": ch.title,
                        "source_path": ch.source_path,
                        "selected": ch.selected,
                    }
                    for ch in result.chapters
                ],
                "toc_tree": [asdict(item) for item in result.toc_tree],
            },
        }
    except Exception as e:
        Path(tmp.name).unlink(missing_ok=True)
        return {"status": "error", "detail": str(e), "code": "epub_parse_error"}


@router.post("/epub/confirm")
async def epub_confirm(data: EpubConfirmBody, db: AsyncSession = Depends(get_db)):
    """Import selected chapters from a previewed EPUB."""
    registry = ImporterRegistry()

    if not Path(data.temp_file_path).exists():
        return {"status": "error", "detail": "Temp file expired. Please re-upload.", "code": "file_not_found"}

    try:
        result = await import_book_chapters(
            db, data.temp_file_path, data.selected_chapter_indices, registry,
        )
        return {"status": "ok", "data": result}
    finally:
        Path(data.temp_file_path).unlink(missing_ok=True)


@router.post("/folder")
async def scan_and_import(data: FolderImportRequest, db: AsyncSession = Depends(get_db)):
    registry = ImporterRegistry()
    result = await import_folder(db, data.folder_path, data.recursive, registry)
    return {"status": "ok", "data": result}


@router.post("/text")
async def import_text(data: TextImportBody, db: AsyncSession = Depends(get_db)):
    """Import article from pasted text."""
    registry = ImporterRegistry()
    raw_bytes = data.content.encode("utf-8")
    filename = data.title + ".txt"
    article_id, is_new = await import_content(db, raw_bytes, filename, registry, title=data.title)

    from ..models.article import Article
    from sqlalchemy import select
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one()

    return {
        "status": "ok",
        "data": ImportResult(
            article_id=article.id,
            title=article.title,
            status="imported" if is_new else "duplicate",
            word_count=article.word_count or 0,
        ),
    }


@router.get("/history")
async def import_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    records, total = await article_service.get_import_history(db, page=page, per_page=per_page)
    return {
        "status": "ok",
        "data": {
            "items": [ImportRecordOut.model_validate(r) for r in records],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, math.ceil(total / per_page)),
        },
    }


@router.post("/check")
async def check_path(data: PathCheckRequest, db: AsyncSession = Depends(get_db)):
    p = Path(data.path)
    if not p.exists():
        return {"status": "ok", "data": {"exists": False, "imported": False}}

    content = p.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()

    from sqlalchemy import select
    from ..models.article import Article
    result = await db.execute(select(Article.id).where(Article.sha256_hash == sha256))
    article_id = result.scalar_one_or_none()

    return {"status": "ok", "data": {"exists": True, "imported": article_id is not None, "article_id": article_id}}
