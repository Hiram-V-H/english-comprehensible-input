from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..exceptions import NotFoundError
from ..models.annotation import Annotation, Highlight


async def get_highlights(db: AsyncSession, article_id: int) -> List[Highlight]:
    result = await db.execute(
        select(Highlight).where(Highlight.article_id == article_id).order_by(Highlight.start_char_offset)
    )
    return list(result.scalars().all())


async def create_highlight(db: AsyncSession, article_id: int, data: dict) -> Highlight:
    highlight = Highlight(article_id=article_id, **data)
    db.add(highlight)
    await db.commit()
    await db.refresh(highlight)
    return highlight


async def update_highlight(db: AsyncSession, highlight_id: int, data: dict) -> Highlight:
    result = await db.execute(select(Highlight).where(Highlight.id == highlight_id))
    h = result.scalar_one_or_none()
    if not h:
        raise NotFoundError(f"Highlight with id {highlight_id} not found")
    for key, value in data.items():
        if value is not None:
            setattr(h, key, value)
    await db.commit()
    await db.refresh(h)
    return h


async def delete_highlight(db: AsyncSession, highlight_id: int) -> None:
    result = await db.execute(select(Highlight).where(Highlight.id == highlight_id))
    h = result.scalar_one_or_none()
    if not h:
        raise NotFoundError(f"Highlight with id {highlight_id} not found")
    await db.delete(h)
    await db.commit()


async def get_annotations(db: AsyncSession, highlight_id: int) -> List[Annotation]:
    result = await db.execute(
        select(Annotation).where(Annotation.highlight_id == highlight_id).order_by(Annotation.created_at)
    )
    return list(result.scalars().all())


async def create_annotation(db: AsyncSession, highlight_id: int, data: dict) -> Annotation:
    # Get the highlight to know the article_id
    hl_result = await db.execute(select(Highlight).where(Highlight.id == highlight_id))
    highlight = hl_result.scalar_one_or_none()
    if not highlight:
        raise NotFoundError(f"Highlight with id {highlight_id} not found")

    annotation = Annotation(
        highlight_id=highlight_id,
        article_id=highlight.article_id,
        **data,
    )
    db.add(annotation)
    await db.commit()
    await db.refresh(annotation)
    return annotation


async def update_annotation(db: AsyncSession, annotation_id: int, data: dict) -> Annotation:
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    a = result.scalar_one_or_none()
    if not a:
        raise NotFoundError(f"Annotation with id {annotation_id} not found")
    for key, value in data.items():
        if value is not None:
            setattr(a, key, value)
    await db.commit()
    await db.refresh(a)
    return a


async def delete_annotation(db: AsyncSession, annotation_id: int) -> None:
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    a = result.scalar_one_or_none()
    if not a:
        raise NotFoundError(f"Annotation with id {annotation_id} not found")
    await db.delete(a)
    await db.commit()
