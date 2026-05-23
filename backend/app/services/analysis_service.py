from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..analysis.base import AnalysisResult
from ..analysis.composite import CompositeAnalyzer
from ..exceptions import NotFoundError
from ..models.article import Article


async def get_analysis(db: AsyncSession, article_id: int) -> dict:
    article_result = await db.execute(select(Article).where(Article.id == article_id))
    article = article_result.scalar_one_or_none()
    if not article:
        raise NotFoundError(f"Article with id {article_id} not found")

    return {
        "article_id": article.id,
        "title": article.title,
        "word_count": article.word_count,
        "unknown_word_count": article.unknown_word_count,
        "unknown_word_density": article.unknown_word_density,
        "i_plus_one_score": article.i_plus_one_score,
        "difficulty_score": article.difficulty_score,
    }


async def reanalyze(db: AsyncSession, article_id: int) -> List[AnalysisResult]:
    article_result = await db.execute(select(Article).where(Article.id == article_id))
    article = article_result.scalar_one_or_none()
    if not article:
        raise NotFoundError(f"Article with id {article_id} not found")

    analyzer = CompositeAnalyzer()
    results = await analyzer.analyze_and_persist(article_id, db)
    return results
