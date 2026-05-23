"""Word Lookup Provider Interface

A Facade that aggregates AI, dictionary, and local DB into a unified word lookup.
This is the single entry point for "click a word" in the reader.

Future implementation will:
1. Check local DB for personal notes and vocab status
2. Query DictionaryProvider for formal definitions
3. Fall back to AIProvider for AI-generated explanations
4. Merge results into a unified response

Not implemented in current phase.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from .base import BaseProvider


class WordLookupProvider(BaseProvider):
    """Facade aggregating all word lookup sources.

    When instantiated, receives references to:
    - DictionaryProvider (optional)
    - AIProvider (optional)
    - Database session for local notes/status
    """

    @abstractmethod
    async def lookup(
        self,
        word: str,
        *,
        context_sentence: Optional[str] = None,
        article_id: Optional[int] = None,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """Unified word lookup.

        Priority: local notes > dictionary > AI

        Returns:
        {
            "word": str,
            "lemma": str,
            "pronunciation": str,
            "definitions": [
                {
                    "source": "dictionary" | "ai" | "local",
                    "pos": str,
                    "text": str,
                    "examples": [str],
                }
            ],
            "personal_notes": [
                {"id": int, "note_type": str, "content": str, "created_at": str}
            ],
            "vocab_status": str,
            "encounter_count": int,
            "articles_containing": [
                {"article_id": int, "title": str, "difficulty_score": float}
            ],
        }
        """
        ...

    @abstractmethod
    async def quick_lookup(self, word: str) -> Dict[str, Any]:
        """Fast lookup returning only the most essential info for popup display.

        Returns:
        {
            "word": str,
            "status": str,
            "definition": str,       # single best definition
            "personal_notes": [str], # brief note summaries
        }
        """
        ...
