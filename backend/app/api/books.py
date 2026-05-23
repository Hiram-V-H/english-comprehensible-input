from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.article import ArticleSummary
from ..services import book_service
from .deps import get_db

router = APIRouter(prefix="/books", tags=["books"])


@router.get("")
async def list_books(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    books, total = await book_service.get_books(db, page=page, per_page=per_page)
    return {
        "status": "ok",
        "data": {
            "items": [
                {
                    "id": b.id,
                    "title": b.title,
                    "author": b.author,
                    "source_type": b.source_type,
                    "total_chapters": b.total_chapters,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
                for b in books
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, math.ceil(total / per_page)),
        },
    }


@router.get("/{book_id}")
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await book_service.get_book(db, book_id)
    return {
        "status": "ok",
        "data": {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "source_type": book.source_type,
            "total_chapters": book.total_chapters,
            "created_at": book.created_at.isoformat() if book.created_at else None,
            "chapters": [
                {
                    "id": a.id,
                    "title": a.title,
                    "chapter_index": a.chapter_index,
                    "word_count": a.word_count,
                    "unknown_word_count": a.unknown_word_count,
                    "difficulty_score": a.difficulty_score,
                }
                for a in (book.articles or [])
            ],
        },
    }


@router.delete("/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    await book_service.delete_book(db, book_id)
    return {"status": "ok", "data": None}
