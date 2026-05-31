from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.article import ArticleContentUpdate, ArticleDetail, ArticleSummary, ArticleUpdate
from ..services import article as article_service
from .deps import get_db

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("")
async def list_articles(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: Optional[str] = None,
    tag: Optional[str] = None,
    exam_type: Optional[str] = None,
    exam_year: Optional[int] = None,
    question_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    articles, total = await article_service.get_articles(
        db, page=page, per_page=per_page, sort=sort, tag=tag,
        exam_type=exam_type, exam_year=exam_year, question_type=question_type,
    )
    return {
        "status": "ok",
        "data": {
            "items": [ArticleSummary.model_validate(a) for a in articles],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, math.ceil(total / per_page)),
        },
    }


@router.get("/{article_id}")
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await article_service.get_article(db, article_id)
    return {"status": "ok", "data": ArticleDetail.model_validate(article)}


@router.patch("/{article_id}")
async def update_article(article_id: int, data: ArticleUpdate, db: AsyncSession = Depends(get_db)):
    article = await article_service.update_article(db, article_id, data.model_dump(exclude_unset=True))
    return {"status": "ok", "data": ArticleDetail.model_validate(article)}


@router.put("/{article_id}/content")
async def update_article_content(article_id: int, data: ArticleContentUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await article_service.update_content(db, article_id, data.content_text)
        return {"status": "ok", "data": result}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{article_id}")
async def delete_article(article_id: int, db: AsyncSession = Depends(get_db)):
    await article_service.delete_article(db, article_id)
    return {"status": "ok", "data": None}
