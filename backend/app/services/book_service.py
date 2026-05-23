from __future__ import annotations

import math
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..exceptions import NotFoundError
from ..models.article import Article
from ..models.book import Book


async def get_books(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[Book], int]:
    query = select(Book).order_by(Book.created_at.desc())
    count_query = select(func.count(Book.id))

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    books = list(result.scalars().all())
    return books, total


async def get_book(db: AsyncSession, book_id: int) -> Book:
    result = await db.execute(
        select(Book)
        .options(selectinload(Book.articles))
        .where(Book.id == book_id)
    )
    book = result.scalar_one_or_none()
    if not book:
        raise NotFoundError(f"Book with id {book_id} not found")
    return book


async def delete_book(db: AsyncSession, book_id: int) -> None:
    book = await get_book(db, book_id)
    await db.delete(book)
    await db.commit()
