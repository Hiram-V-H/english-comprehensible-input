from __future__ import annotations

import math
from typing import List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..exceptions import NotFoundError
from ..models.article import Article
from ..models.import_record import ImportRecord


async def get_articles(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
    sort: Optional[str] = None,
    tag: Optional[str] = None,
) -> Tuple[List[Article], int]:
    query = select(Article).where(Article.is_archived == False)
    count_query = select(func.count(Article.id)).where(Article.is_archived == False)

    # Sort
    if sort == "difficulty":
        query = query.order_by(Article.difficulty_score.asc().nullslast())
    elif sort == "recent":
        query = query.order_by(Article.last_read_at.desc().nullslast())
    else:
        query = query.order_by(Article.created_at.desc())

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    articles = list(result.scalars().all())
    return articles, total


async def get_article(db: AsyncSession, article_id: int) -> Article:
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise NotFoundError(f"Article with id {article_id} not found")
    return article


async def update_article(db: AsyncSession, article_id: int, data: dict) -> Article:
    article = await get_article(db, article_id)
    for key, value in data.items():
        if value is not None:
            setattr(article, key, value)
    await db.commit()
    await db.refresh(article)
    return article


async def delete_article(db: AsyncSession, article_id: int) -> None:
    article = await get_article(db, article_id)
    await db.delete(article)
    await db.commit()


async def get_import_history(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[ImportRecord], int]:
    query = select(ImportRecord).order_by(ImportRecord.imported_at.desc())
    count_query = select(func.count(ImportRecord.id))

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    records = list(result.scalars().all())
    return records, total
