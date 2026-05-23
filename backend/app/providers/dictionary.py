"""Dictionary Provider Interface

Defines the contract for dictionary backends. Future implementations:
- StarDictProvider (local StarDict dictionaries)
- MDictProvider (local MDict/MDX dictionaries)
- JSONDictionaryProvider (local JSON-based word lists)
- OnlineDictionaryProvider (Merriam-Webster, Oxford, etc. APIs)

Not implemented in current phase.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from .base import BaseProvider


class DictionaryProvider(BaseProvider):
    """Interface for dictionary backends — local or online."""

    @abstractmethod
    async def lookup(self, word: str) -> Optional[Dict[str, Any]]:
        """Look up a word in the dictionary.

        Returns None if the word is not found.

        Structured response:
        {
            "word": str,
            "pronunciation": {"uk": str, "us": str},
            "definitions": [
                {
                    "pos": str,           # part of speech (noun, verb, etc.)
                    "meaning": str,       # definition text
                    "examples": [str],    # usage examples
                    "synonyms": [str],
                }
            ],
            "etymology": str,
            "level": str,                 # CEFR level if available
        }
        """
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Fuzzy/stemmed search for auto-complete.

        Returns a list of matching headwords with basic info.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the dictionary files/indexes are accessible on disk."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Human-readable dictionary name, e.g. 'Oxford Advanced Learner's'."""
        ...
