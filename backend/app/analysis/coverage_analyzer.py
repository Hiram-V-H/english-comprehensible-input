from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.article import ArticleWord
from .base import AnalysisAlgorithm, AnalysisResult


class CoverageAnalyzer(AnalysisAlgorithm):
    @classmethod
    def name(cls) -> str:
        return "coverage_analyzer"

    async def analyze(self, article_id: int, *, db: AsyncSession) -> AnalysisResult:
        total_result = await db.execute(
            select(func.count(ArticleWord.id)).where(ArticleWord.article_id == article_id, ArticleWord.is_punctuation == False)
        )
        total = total_result.scalar() or 0

        unknown_result = await db.execute(
            select(func.count(ArticleWord.id)).where(
                ArticleWord.article_id == article_id, ArticleWord.is_punctuation == False,
                ArticleWord.is_unknown_at_import == True,
            )
        )
        unknown = unknown_result.scalar() or 0

        coverage = 1.0 - (unknown / total) if total > 0 else 1.0
        density = unknown / total if total > 0 else 0.0

        return AnalysisResult(
            algorithm_name=self.name(),
            score=coverage,
            label=f"{coverage:.1%} coverage",
            details={
                "total_words": total,
                "unknown_words": unknown,
                "coverage": coverage,
                "density": density,
            },
        )
