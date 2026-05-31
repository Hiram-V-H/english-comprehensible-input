"""Contraction expansion — pre-processing step before tokenization.

Expands English contractions so each component word is tokenized separately.
e.g., "we're" → "we are", "don't" → "do not"
"""

from __future__ import annotations

import re

# Ordered longest-first so "they're" matches before "we're" as a substring issue.
# All keys are lowercase — IGNORECASE and the _replace function handle
# capitalization at match time, so uppercase-only variants are redundant.
# Entries starting with "'" (archaic forms like 'tis, 'twas) use (?<!\w)
# as their leading boundary since \b does not work before a non-\w character.
_CONTRACTION_MAP: dict[str, str] = {
    # ── Negations ──
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "can't": "cannot",
    "cannot": "can not",
    "won't": "will not",
    "wouldn't": "would not",
    "shouldn't": "should not",
    "couldn't": "could not",
    "mustn't": "must not",
    "needn't": "need not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "haven't": "have not",
    "hasn't": "has not",
    "hadn't": "had not",
    "mightn't": "might not",
    "oughtn't": "ought not",
    "daren't": "dare not",
    "shan't": "shall not",

    # ── to-be / to-have / will / would ──
    "i'm": "i am",
    "we're": "we are",
    "you're": "you are",
    "they're": "they are",
    "he's": "he is",
    "she's": "she is",
    "it's": "it is",
    "that's": "that is",
    "who's": "who is",
    "what's": "what is",
    "where's": "where is",
    "when's": "when is",
    "why's": "why is",
    "how's": "how is",
    "there's": "there is",
    "here's": "here is",

    "i've": "i have",
    "we've": "we have",
    "you've": "you have",
    "they've": "they have",

    "i'll": "i will",
    "we'll": "we will",
    "you'll": "you will",
    "they'll": "they will",
    "he'll": "he will",
    "she'll": "she will",
    "it'll": "it will",
    "there'll": "there will",

    "i'd": "i would",
    "we'd": "we would",
    "you'd": "you would",
    "they'd": "they would",
    "he'd": "he would",
    "she'd": "she would",
    "it'd": "it would",

    # ── Special forms ──
    "let's": "let us",
    "ain't": "is not",
    "ma'am": "madam",
    "y'all": "you all",
    "gonna": "going to",
    "gotta": "got to",
    "wanna": "want to",
    "lemme": "let me",
    "gimme": "give me",
    "kinda": "kind of",
    "sorta": "sort of",
    "outta": "out of",
    "dunno": "do not know",

    # ── 'tis etc ──
    "'tis": "it is",
    "'twas": "it was",
    "'twere": "it were",
    "'twill": "it will",
    "'twould": "it would",
}

# Separate entries that start with apostrophe (archaic forms like 'tis)
# from regular entries.  \b does not work before a leading apostrophe
# because ' is not a \w character, so we use (?<!\w) instead.
_apostrophe_keys: list[str] = sorted(
    (k for k in _CONTRACTION_MAP if k.startswith("'")),
    key=len, reverse=True,
)
_regular_keys: list[str] = sorted(
    (k for k in _CONTRACTION_MAP if not k.startswith("'")),
    key=len, reverse=True,
)

_ApostrophePattern = '|'.join(re.escape(k) for k in _apostrophe_keys)
_RegularPattern = '|'.join(re.escape(k) for k in _regular_keys)

# For apostrophe entries: (?<!\w) matches after non-word boundary (space,
# punctuation, or start-of-string).  For regular entries: standard \b.
_CONTRACTION_RE = re.compile(
    rf'(?<!\w)(?:{_ApostrophePattern})\b'
    rf'|\b(?:{_RegularPattern})\b',
    re.IGNORECASE,
)


def expand(text: str) -> str:
    """Expand contractions in text, preserving original casing pattern."""
    def _replace(m: re.Match) -> str:
        original = m.group(0)
        replacement = _CONTRACTION_MAP.get(original.lower(), original)
        # Find the first alphabetic character for capitalization check,
        # since archaic forms like 'Tis start with a non-letter apostrophe.
        first_alpha_idx = next(
            (i for i, c in enumerate(original) if c.isalpha()), 0
        )
        if first_alpha_idx < len(original) and original[first_alpha_idx].isupper():
            return replacement[0].upper() + replacement[1:]
        return replacement

    return _CONTRACTION_RE.sub(_replace, text)
