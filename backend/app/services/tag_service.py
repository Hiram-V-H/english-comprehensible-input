from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..exceptions import NotFoundError
from ..models.tag import AnnotationTag, Tag


async def get_all_tags(db: AsyncSession) -> List[Tag]:
    result = await db.execute(select(Tag).order_by(Tag.name))
    return list(result.scalars().all())


async def create_tag(db: AsyncSession, data: dict) -> Tag:
    tag = Tag(**data)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag_id: int) -> None:
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise NotFoundError(f"Tag with id {tag_id} not found")
    await db.delete(tag)
    await db.commit()


async def add_annotation_tag(db: AsyncSession, annotation_id: int, tag_id: int) -> None:
    existing = await db.execute(
        select(AnnotationTag).where(
            AnnotationTag.annotation_id == annotation_id,
            AnnotationTag.tag_id == tag_id,
        )
    )
    if existing.scalar_one_or_none():
        return
    at = AnnotationTag(annotation_id=annotation_id, tag_id=tag_id)
    db.add(at)
    await db.commit()


async def remove_annotation_tag(db: AsyncSession, annotation_id: int, tag_id: int) -> None:
    result = await db.execute(
        select(AnnotationTag).where(
            AnnotationTag.annotation_id == annotation_id,
            AnnotationTag.tag_id == tag_id,
        )
    )
    at = result.scalar_one_or_none()
    if at:
        await db.delete(at)
        await db.commit()
