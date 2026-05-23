from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.article import ArticleWord
from .base import AnalysisAlgorithm, AnalysisResult


class IPlusOneDetector(AnalysisAlgorithm):
    """Determines if an article is at the right i+1 level for the learner.

    Based on the coverage ratio:
    - >= 98% coverage: too easy (score 0.5, not ideal)
    - 95-98%: ideal i+1 (score 1.0)
    - 90-95%: challenging but doable (score 0.7)
    - 80-90%: hard (score 0.4)
    - < 80%: too hard (score 0.1)
    """

    @classmethod
    def name(cls) -> str:
        return "i_plus_one_detector"

    async def analyze(self, article_id: int, *, db: AsyncSession) -> AnalysisResult:
        total_result = await db.execute(
            select(func.count(ArticleWord.id)).where(ArticleWord.article_id == article_id, ArticleWord.is_punctuation == False)
        )
        total = total_result.scalar() or 1

        unknown_result = await db.execute(
            select(func.count(ArticleWord.id)).where(
                ArticleWord.article_id == article_id, ArticleWord.is_punctuation == False,
                ArticleWord.is_unknown_at_import == True,
            )
        )
        unknown = unknown_result.scalar() or 0

        coverage = 1.0 - (unknown / total)

        if coverage >= 0.98:
            score, label = 0.5, "Too easy"
        elif coverage >= 0.95:
            score, label = 1.0, "Ideal i+1"
        elif coverage >= 0.90:
            score, label = 0.7, "Challenging"
        elif coverage >= 0.80:
            score, label = 0.4, "Hard"
        else:
            score, label = 0.1, "Too hard"

        return AnalysisResult(
            algorithm_name=self.name(),
            score=score,
            label=label,
            details={
                "coverage": coverage,
                "unknown_count": unknown,
                "total_words": total,
            },
        )
