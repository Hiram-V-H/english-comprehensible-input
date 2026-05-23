from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.article import ArticleWord
from ..models.word import Word
from .base import AnalysisAlgorithm, AnalysisResult


class UnknownWordAnalyzer(AnalysisAlgorithm):
    @classmethod
    def name(cls) -> str:
        return "unknown_word_analyzer"

    async def analyze(self, article_id: int, *, db: AsyncSession) -> AnalysisResult:
        # Get all known word_lower values
        known_result = await db.execute(
            select(Word.word_lower).where(
                Word.status.in_(["known", "familiar", "mastered"])
            )
        )
        known_words = {row[0] for row in known_result.all()}

        # Get all article words
        aw_result = await db.execute(
            select(ArticleWord).where(ArticleWord.article_id == article_id, ArticleWord.is_punctuation == False)
        )
        article_words = list(aw_result.scalars().all())

        unknown_count = 0
        unknown_list = []
        unknown_positions = []

        for aw in article_words:
            is_unknown = aw.word_lower not in known_words
            if is_unknown:
                unknown_count += 1
                unknown_list.append(aw.word_text)
                unknown_positions.append(aw.position)
            # Update the is_unknown_at_import flag
            aw.is_unknown_at_import = is_unknown

        await db.commit()

        return AnalysisResult(
            algorithm_name=self.name(),
            score=min(unknown_count / 50.0, 1.0),
            label=f"{unknown_count} unknown words",
            details={
                "unknown_count": unknown_count,
                "unknown_words": list(set(unknown_list)),
                "unknown_positions": unknown_positions,
            },
        )
