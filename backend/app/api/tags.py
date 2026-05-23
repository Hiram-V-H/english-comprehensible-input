from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..services import tag_service
from .deps import get_db

router = APIRouter(prefix="/tags", tags=["tags"])


class TagCreate(BaseModel):
    name: str
    color: str | None = None


class AnnotationTagBody(BaseModel):
    tag_id: int


@router.get("")
async def get_tags(db: AsyncSession = Depends(get_db)):
    tags = await tag_service.get_all_tags(db)
    return {
        "status": "ok",
        "data": [
            {"id": t.id, "name": t.name, "color": t.color} for t in tags
        ],
    }


@router.post("")
async def create_tag(data: TagCreate, db: AsyncSession = Depends(get_db)):
    tag = await tag_service.create_tag(db, data.model_dump())
    return {"status": "ok", "data": {"id": tag.id, "name": tag.name}}


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    await tag_service.delete_tag(db, tag_id)
    return {"status": "ok", "data": None}


@router.post("/annotations/{annotation_id}/tags")
async def add_annotation_tag(annotation_id: int, data: AnnotationTagBody, db: AsyncSession = Depends(get_db)):
    await tag_service.add_annotation_tag(db, annotation_id, data.tag_id)
    return {"status": "ok", "data": None}


@router.delete("/annotations/{annotation_id}/tags/{tag_id}")
async def remove_annotation_tag(annotation_id: int, tag_id: int, db: AsyncSession = Depends(get_db)):
    await tag_service.remove_annotation_tag(db, annotation_id, tag_id)
    return {"status": "ok", "data": None}
