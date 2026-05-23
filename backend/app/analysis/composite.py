from __future__ import annotations

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.article import Article
from .base import AnalysisAlgorithm, AnalysisResult
from .coverage_analyzer import CoverageAnalyzer
from .i_plus_one_detector import IPlusOneDetector
from .unknown_word_analyzer import UnknownWordAnalyzer
from .word_counter import WordCounter


class CompositeAnalyzer:
    def __init__(self, algorithms: List[AnalysisAlgorithm] | None = None):
        self._algos = algorithms or [
            WordCounter(),
            UnknownWordAnalyzer(),
            CoverageAnalyzer(),
            IPlusOneDetector(),
        ]

    async def analyze(self, article_id: int, db: AsyncSession) -> List[AnalysisResult]:
        results = []
        for algo in self._algos:
            result = await algo.analyze(article_id, db=db)
            results.append(result)
        return results

    async def analyze_and_persist(self, article_id: int, db: AsyncSession) -> List[AnalysisResult]:
        results = await self.analyze(article_id, db)

        from sqlalchemy import select
        result = await db.execute(select(Article).where(Article.id == article_id))
        article = result.scalar_one_or_none()
        if not article:
            return results

        for r in results:
            if r.algorithm_name == "word_counter":
                pass  # word_count already set during import
            elif r.algorithm_name == "unknown_word_analyzer":
                article.unknown_word_count = r.details.get("unknown_count", 0)
            elif r.algorithm_name == "coverage_analyzer":
                article.unknown_word_density = r.details.get("density", 0.0)
            elif r.algorithm_name == "i_plus_one_detector":
                article.i_plus_one_score = r.score
                article.difficulty_score = 1.0 - r.score

        await db.commit()
        return results
