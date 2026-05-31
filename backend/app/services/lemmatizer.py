"""Lemmatization service — reduce English words to their base/dictionary form.

Uses NLTK WordNetLemmatizer with a heuristic POS sequence:
  verb → noun → adjective/adverb

Runs by default. Falls back to returning the original word on any error.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_lemmatizer: Optional[object] = None
_downloaded: bool = False


def _ensure_nltk() -> object:
    """Lazy-load the NLTK lemmatizer, downloading wordnet on first use."""
    global _lemmatizer, _downloaded
    if _lemmatizer is not None:
        return _lemmatizer

    import nltk
    from nltk.stem import WordNetLemmatizer

    if not _downloaded:
        try:
            nltk.download('wordnet', quiet=True, raise_on_error=True)
        except Exception as exc:
            logger.warning("Failed to download wordnet: %s. Lemmatization disabled.", exc)
            _lemmatizer = _NoopLemmatizer()
            return _lemmatizer
        _downloaded = True

    _lemmatizer = WordNetLemmatizer()
    return _lemmatizer


class _NoopLemmatizer:
    """Fallback lemmatizer that returns the word unchanged."""
    def lemmatize(self, word: str, pos: str = "n") -> str:
        return word


def lemmatize(word: str) -> str:
    """Return the base form of an English word.

    Heuristic: try verb first (covers -ing, -ed, irregular past),
    then noun (covers plurals, irregular plurals), then adjective.
    Unknown words are returned unchanged.

    Examples:
        running → run      (verb)
        ran     → run      (verb, irregular)
        went    → go       (verb, irregular)
        stores  → store    (noun)
        feet    → foot     (noun, irregular)
        better  → good     (adjective)
        quickly → quickly  (adverb; returns as-is)
    """
    wl = word.lower().strip()
    if not wl:
        return wl

    lemmatizer_obj = _ensure_nltk()

    # 1. Try verb (handles -ing, -ed, irregular past/past-participle)
    verb_lemma = lemmatizer_obj.lemmatize(wl, pos="v")
    if verb_lemma != wl:
        return verb_lemma

    # 2. Try noun (handles plurals, irregular plurals)
    noun_lemma = lemmatizer_obj.lemmatize(wl, pos="n")
    if noun_lemma != wl:
        return noun_lemma

    # 3. Try adjective (handles comparatives/superlatives)
    adj_lemma = lemmatizer_obj.lemmatize(wl, pos="a")
    return adj_lemma
