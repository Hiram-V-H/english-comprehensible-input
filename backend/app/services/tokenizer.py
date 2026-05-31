from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from .contractions import expand as expand_contractions


@dataclass
class Token:
    text: str
    position: int
    sentence_index: int
    char_offset: int
    is_punctuation: bool = False


# Pattern: words/contractions/numbers OR punctuation sequences
_TOKEN_RE = re.compile(
    r"[a-zA-Z]+(?:'[a-zA-Z]+)?|\d+s|\d+(?:\.\d+)?|"  # words, contractions, 40s/50s, numbers
    r"[.,!?;:%]+|"   # clause/sentence punctuation (incl. %)
    r"[()\[\]{}\"']|"  # brackets and quotes
    r"--?"  # dashes
)

_PUNCT_SET = set(".,!?;:()[]{}'\"-%")


def tokenize(text: str) -> List[Token]:
    """Split English text into word and punctuation tokens.

    Every token (word, number, punctuation mark) gets its own entry,
    preserving character offsets for accurate text reconstruction.

    Contractions are expanded before tokenization (e.g., "we're" → "we are").
    """
    # Expand contractions first so component words are individual tokens
    text = expand_contractions(text)

    tokens: List[Token] = []
    sent_idx = 0

    for m in _TOKEN_RE.finditer(text):
        raw_text = m.group()
        is_punct = all(c in _PUNCT_SET for c in raw_text)

        tokens.append(Token(
            text=raw_text,
            position=len(tokens),
            sentence_index=sent_idx,
            char_offset=m.start(),
            is_punctuation=is_punct,
        ))

        # Advance sentence index AFTER sentence-ending punctuation
        if raw_text in ('.', '!', '?'):
            sent_idx += 1

    return tokens
