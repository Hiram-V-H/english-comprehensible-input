from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.common import PaginatedResponse
from ..schemas.word import (
    BulkStatusUpdate,
    VocabularyStats,
    WordNoteCreate,
    WordNoteOut,
    WordNoteUpdate,
    WordOut,
    WordSummary,
    WordUpdate,
)
from ..services import vocabulary as vocab_service
from .deps import get_db

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


@router.get("")
async def list_words(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=200),
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    words, total = await vocab_service.get_words(
        db, page=page, per_page=per_page, status=status, search=search, sort=sort,
    )
    return {
        "status": "ok",
        "data": {
            "items": [WordSummary.model_validate(w) for w in words],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, math.ceil(total / per_page)),
        },
    }


@router.get("/stats")
async def vocabulary_stats(db: AsyncSession = Depends(get_db)):
    stats = await vocab_service.get_stats(db)
    return {"status": "ok", "data": stats.model_dump()}


@router.get("/search")
async def search_vocabulary(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    words = await vocab_service.search_words(db, q, limit)
    return {"status": "ok", "data": [WordSummary.model_validate(w) for w in words]}


@router.get("/{word_id}")
async def get_word(word_id: int, db: AsyncSession = Depends(get_db)):
    word = await vocab_service.get_word(db, word_id)
    return {"status": "ok", "data": WordOut.model_validate(word)}


@router.patch("/{word_id}")
async def update_word(word_id: int, data: WordUpdate, db: AsyncSession = Depends(get_db)):
    word = await vocab_service.update_word(db, word_id, data.model_dump(exclude_unset=True))
    return {"status": "ok", "data": WordOut.model_validate(word)}


@router.post("/bulk-status")
async def bulk_update(data: BulkStatusUpdate, db: AsyncSession = Depends(get_db)):
    count = await vocab_service.bulk_update_status(db, data.word_ids, data.new_status)
    return {"status": "ok", "data": {"updated": count}}


@router.post("/{word_id}/notes")
async def add_note(word_id: int, data: WordNoteCreate, db: AsyncSession = Depends(get_db)):
    note = await vocab_service.add_note(db, word_id, data.model_dump())
    return {"status": "ok", "data": WordNoteOut.model_validate(note)}


@router.patch("/{word_id}/notes/{note_id}")
async def update_note(word_id: int, note_id: int, data: WordNoteUpdate, db: AsyncSession = Depends(get_db)):
    note = await vocab_service.update_note(db, note_id, data.model_dump(exclude_unset=True))
    return {"status": "ok", "data": WordNoteOut.model_validate(note)}


@router.delete("/{word_id}/notes/{note_id}")
async def delete_note(word_id: int, note_id: int, db: AsyncSession = Depends(get_db)):
    await vocab_service.delete_note(db, note_id)
    return {"status": "ok", "data": None}
