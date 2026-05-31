from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.article import ArticleWord
from ..models.word import Word
from ..services.lemmatizer import lemmatize
from .base import AnalysisAlgorithm, AnalysisResult


class UnknownWordAnalyzer(AnalysisAlgorithm):
    @classmethod
    def name(cls) -> str:
        return "unknown_word_analyzer"

    async def analyze(self, article_id: int, *, db: AsyncSession) -> AnalysisResult:
        # Get all known word_lower values (which are lemmas for new imports).
        # For legacy data, we lemmatize the stored word_lower to build a
        # known-lemma set, ensuring compatibility with pre-lemmatization data.
        known_result = await db.execute(
            select(Word.word_lower).where(
                Word.status.in_(["known", "familiar", "mastered"])
            )
        )
        # Build a set of known LEMMAS.
        # For post-migration data, word_lower IS the lemma.
        # For legacy data, word_lower is a surface form — lemmatize it too.
        known_lemmas: set[str] = set()
        for row in known_result.all():
            raw = row[0]
            known_lemmas.add(lemmatize(raw))

        # Get all article words (non-punctuation)
        aw_result = await db.execute(
            select(ArticleWord).where(
                ArticleWord.article_id == article_id,
                ArticleWord.is_punctuation == False,
            )
        )
        article_words = list(aw_result.scalars().all())

        unknown_count = 0
        unknown_list: list[str] = []
        unknown_positions: list[int] = []

        for aw in article_words:
            # Check if the LEMMA of this surface form is in the known set
            aw_lemma = lemmatize(aw.word_lower)
            is_unknown = aw_lemma not in known_lemmas
            if is_unknown:
                unknown_count += 1
                unknown_list.append(aw.word_text)
                unknown_positions.append(aw.position)
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
