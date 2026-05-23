from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..services import annotation_service
from .deps import get_db

router = APIRouter(tags=["annotations"])


class HighlightCreate(BaseModel):
    start_char_offset: Optional[int] = None
    end_char_offset: Optional[int] = None
    start_word_position: Optional[int] = None
    end_word_position: Optional[int] = None
    selected_text: str
    highlight_type: str = "word"
    anchor_type: str = "text_offset"
    color: str = "#FFEB3B"


class HighlightUpdate(BaseModel):
    color: Optional[str] = None
    highlight_type: Optional[str] = None


class AnnotationCreate(BaseModel):
    annotation_type: str = "note"
    content: str
    word_id: Optional[int] = None


class AnnotationUpdate(BaseModel):
    annotation_type: Optional[str] = None
    content: Optional[str] = None


# Highlights
@router.get("/articles/{article_id}/highlights")
async def get_highlights(article_id: int, db: AsyncSession = Depends(get_db)):
    highlights = await annotation_service.get_highlights(db, article_id)
    return {
        "status": "ok",
        "data": [
            {
                "id": h.id,
                "highlight_type": h.highlight_type,
                "start_char_offset": h.start_char_offset,
                "end_char_offset": h.end_char_offset,
                "start_word_position": h.start_word_position,
                "end_word_position": h.end_word_position,
                "selected_text": h.selected_text,
                "color": h.color,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in highlights
        ],
    }


@router.post("/articles/{article_id}/highlights")
async def create_highlight(article_id: int, data: HighlightCreate, db: AsyncSession = Depends(get_db)):
    h = await annotation_service.create_highlight(db, article_id, data.model_dump())
    return {"status": "ok", "data": {"id": h.id}}


@router.patch("/articles/{article_id}/highlights/{highlight_id}")
async def update_highlight(article_id: int, highlight_id: int, data: HighlightUpdate, db: AsyncSession = Depends(get_db)):
    h = await annotation_service.update_highlight(db, highlight_id, data.model_dump(exclude_unset=True))
    return {"status": "ok", "data": {"id": h.id}}


@router.delete("/articles/{article_id}/highlights/{highlight_id}")
async def delete_highlight(article_id: int, highlight_id: int, db: AsyncSession = Depends(get_db)):
    await annotation_service.delete_highlight(db, highlight_id)
    return {"status": "ok", "data": None}


# Annotations
@router.get("/highlights/{highlight_id}/annotations")
async def get_annotations(highlight_id: int, db: AsyncSession = Depends(get_db)):
    annotations = await annotation_service.get_annotations(db, highlight_id)
    return {
        "status": "ok",
        "data": [
            {
                "id": a.id,
                "annotation_type": a.annotation_type,
                "content": a.content,
                "word_id": a.word_id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in annotations
        ],
    }


@router.post("/highlights/{highlight_id}/annotations")
async def create_annotation(highlight_id: int, data: AnnotationCreate, db: AsyncSession = Depends(get_db)):
    a = await annotation_service.create_annotation(db, highlight_id, data.model_dump())
    return {"status": "ok", "data": {"id": a.id}}


@router.patch("/annotations/{annotation_id}")
async def update_annotation(annotation_id: int, data: AnnotationUpdate, db: AsyncSession = Depends(get_db)):
    a = await annotation_service.update_annotation(db, annotation_id, data.model_dump(exclude_unset=True))
    return {"status": "ok", "data": {"id": a.id}}


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(annotation_id: int, db: AsyncSession = Depends(get_db)):
    await annotation_service.delete_annotation(db, annotation_id)
    return {"status": "ok", "data": None}
