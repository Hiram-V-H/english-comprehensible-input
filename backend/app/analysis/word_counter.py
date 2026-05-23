from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.article import Article, ArticleWord
from .base import AnalysisAlgorithm, AnalysisResult


class WordCounter(AnalysisAlgorithm):
    @classmethod
    def name(cls) -> str:
        return "word_counter"

    async def analyze(self, article_id: int, *, db: AsyncSession) -> AnalysisResult:
        result = await db.execute(
            select(func.count(ArticleWord.id)).where(ArticleWord.article_id == article_id, ArticleWord.is_punctuation == False)
        )
        total = result.scalar() or 0

        result = await db.execute(
            select(func.count(func.distinct(ArticleWord.word_lower))).where(
                ArticleWord.article_id == article_id, ArticleWord.is_punctuation == False
            )
        )
        unique = result.scalar() or 0

        return AnalysisResult(
            algorithm_name=self.name(),
            score=min(total / 2000.0, 1.0),
            label=f"{total} words ({unique} unique)",
            details={"total_words": total, "unique_words": unique},
        )
