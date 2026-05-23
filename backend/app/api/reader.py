from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..services import reader_service
from .deps import get_db

router = APIRouter(tags=["reader"])


class EndSessionBody(BaseModel):
    word_position: Optional[int] = None


@router.get("/reader/{article_id}")
async def get_reader_data(article_id: int, db: AsyncSession = Depends(get_db)):
    data = await reader_service.assemble_reader_payload(db, article_id)
    return {"status": "ok", "data": data}


@router.post("/reader/{article_id}/word/{word_id}/encounter")
async def record_encounter(article_id: int, word_id: int, db: AsyncSession = Depends(get_db)):
    await reader_service.record_encounter(db, article_id, word_id)
    return {"status": "ok", "data": None}


@router.post("/reader/{article_id}/session/start")
async def start_reading_session(article_id: int, db: AsyncSession = Depends(get_db)):
    session = await reader_service.start_session(db, article_id)
    return {"status": "ok", "data": {"session_id": session.id}}


@router.post("/reader/{article_id}/session/{session_id}/end")
async def end_reading_session(
    article_id: int,
    session_id: int,
    body: EndSessionBody = EndSessionBody(),
    db: AsyncSession = Depends(get_db),
):
    session = await reader_service.end_session(db, session_id, body.word_position)
    return {
        "status": "ok",
        "data": {
            "session_id": session.id,
            "duration_seconds": session.duration_seconds,
        },
    }
