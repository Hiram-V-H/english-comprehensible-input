# Lemmatization & Contraction Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add contraction expansion and lemmatization to the import pipeline so inflected forms (runs/running/ran) map to base words (run) and contractions (we're/don't) are expanded before tokenization.

**Architecture:** Two new service modules (`contractions.py`, `lemmatizer.py`) are added. The tokenizer calls contraction expansion as a pre-processing step. `get_or_create_word()` lemmatizes before Word lookup. The analysis layer uses lemmas instead of surface forms. A data migration merges existing duplicate Word records.

**Tech Stack:** NLTK (WordNetLemmatizer + wordnet data), Python regex, SQLAlchemy async

**Design Spec:** `docs/superpowers/specs/2026-05-31-lemmatization-contractions-design.md`

---

### Task 1: Add NLTK dependency and download wordnet

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add nltk to requirements.txt**

Append to `backend/requirements.txt`:
```
nltk>=3.9.0
```

- [ ] **Step 2: Install nltk and download wordnet data**

```bash
pip install nltk>=3.9.0
python -c "import nltk; nltk.download('wordnet')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add nltk dependency for lemmatization"
```

---

### Task 2: Create contractions.py service module

**Files:**
- Create: `backend/app/services/contractions.py`

- [ ] **Step 1: Create the contractions module with mapping and expand function**

```python
"""Contraction expansion — pre-processing step before tokenization.

Expands English contractions so each component word is tokenized separately.
e.g., "we're" → "we are", "don't" → "do not"
"""

from __future__ import annotations

import re

# Ordered longest-first so "they're" matches before "we're" as a substring issue.
# The regex uses word-boundary-aware replacement to avoid partial matches.
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
    "I'm": "I am",
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

    "I've": "I have",
    "i've": "i have",
    "we've": "we have",
    "you've": "you have",
    "they've": "they have",

    "I'll": "I will",
    "i'll": "i will",
    "we'll": "we will",
    "you'll": "you will",
    "they'll": "they will",
    "he'll": "he will",
    "she'll": "she will",
    "it'll": "it will",
    "there'll": "there will",

    "I'd": "I would",
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

# Build a single regex that matches any contraction key, longest-first
_PATTERN_STR = '|'.join(
    re.escape(k) for k in sorted(_CONTRACTION_MAP.keys(), key=len, reverse=True)
)
# Word-boundary-aware: match only when the contraction is a standalone token
_CONTRACTION_RE = re.compile(r'\b(' + _PATTERN_STR + r')\b', re.IGNORECASE)


def expand(text: str) -> str:
    """Expand contractions in text, preserving original casing pattern."""
    def _replace(m: re.Match) -> str:
        original = m.group(0)
        replacement = _CONTRACTION_MAP.get(original.lower(), original)
        # Preserve capitalization of first letter
        if original[0].isupper():
            return replacement[0].upper() + replacement[1:]
        return replacement

    return _CONTRACTION_RE.sub(_replace, text)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/contractions.py
git commit -m "feat: add contraction expansion service module"
```

---

### Task 3: Create lemmatizer.py service module

**Files:**
- Create: `backend/app/services/lemmatizer.py`

- [ ] **Step 1: Create the lemmatizer module with NLTK WordNetLemmatizer wrapper**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/lemmatizer.py
git commit -m "feat: add NLTK-based lemmatization service module"
```

---

### Task 4: Modify tokenizer.py to integrate contraction expansion

**Files:**
- Modify: `backend/app/services/tokenizer.py`

- [ ] **Step 1: Add contraction expansion call at the start of tokenize()**

Add the import at line 6 and call `expand_contractions` at the start of `tokenize()`:

```python
# After line 5: from typing import List
# Insert:
from .contractions import expand as expand_contractions

# In tokenize(), at line 29, after the docstring, add:
def tokenize(text: str) -> List[Token]:
    """Split English text into word and punctuation tokens.

    Every token (word, number, punctuation mark) gets its own entry,
    preserving character offsets for accurate text reconstruction.

    Contractions are expanded before tokenization (e.g., "we're" → "we are").
    """
    # Expand contractions first so component words are individual tokens
    text = expand_contractions(text)
    
    tokens: List[Token] = []
    # ... rest unchanged
```

The full modified tokenizer.py becomes:

```python
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
    r"[a-zA-Z]+(?:'[a-zA-Z]+)?|\d+(?:\.\d+)?|"  # words, contractions, numbers
    r"[.,!?;:]+|"   # clause/sentence punctuation
    r"[()\[\]{}\"']|"  # brackets and quotes
    r"--?"  # dashes
)

_PUNCT_SET = set(".,!?;:()[]{}'\"-")


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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/tokenizer.py
git commit -m "feat: integrate contraction expansion into tokenizer"
```

---

### Task 5: Modify vocabulary.py to lemmatize before Word lookup

**Files:**
- Modify: `backend/app/services/vocabulary.py`

- [ ] **Step 1: Modify get_or_create_word() to lemmatize before lookup**

Add the import and modify the function (lines 114-132):

```python
# Add at top, after existing imports:
from .lemmatizer import lemmatize

# Replace the existing get_or_create_word function:
async def get_or_create_word(db: AsyncSession, word_text: str) -> Word:
    """Find existing word by lemma, or create a new one.

    Uses lemmatization so inflected forms map to the base word.
    e.g., "running" → lemma "run" → Word("run").
    ArticleWord still stores the original surface form.
    """
    word_lower = word_text.lower().strip()
    lemma = lemmatize(word_lower)

    # Look up by lemma — all inflected forms share one Word record
    result = await db.execute(
        select(Word).where(Word.word_lower == lemma)
    )
    word = result.scalar_one_or_none()
    if word:
        return word

    # Create with lemma as word_lower; store original text as word
    word = Word(
        word=word_text.strip(),
        word_lower=lemma,
        status="unknown",
        first_seen=datetime.now(),
    )
    db.add(word)
    await db.flush()
    return word
```

- [ ] **Step 2: Also update lemma field on the Word record for backward compat**

In the same function, when creating a new Word, also set the `lemma` field:
```python
    word = Word(
        word=word_text.strip(),
        word_lower=lemma,
        lemma=lemma,  # populate the previously-unused lemma column
        status="unknown",
        first_seen=datetime.now(),
    )
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/vocabulary.py
git commit -m "feat: lemmatize words during vocabulary lookup"
```

---

### Task 6: Modify import_service.py to expand contractions in content_text

**Files:**
- Modify: `backend/app/services/import_service.py`

- [ ] **Step 1: Add contraction expansion to _save_article()**

In `_save_article()`, expand contractions in `content_text` before tokenization (the tokenizer now also does this, but we need the expanded text stored in the Article). Add import at top:

```python
# Add after line 21 (from .tokenizer import tokenize):
from .contractions import expand as expand_contractions
```

In `_save_article()`, after line 133 (`tokens = tokenize(data.content_text)`), change to expand the text first and use the expanded text for both tokenization and storage:

Replace lines 132-136:
```python
    # Tokenize
    tokens = tokenize(data.content_text)

    # Count only real words (exclude punctuation and non-letter tokens)
    real_word_count = sum(1 for t in tokens if not t.is_punctuation and _has_letter(t.text))
```

With:
```python
    # Expand contractions in the raw text before tokenization.
    # The tokenizer also calls expand_contractions internally, but we expand
    # here too because the Article stores the expanded content_text.
    expanded_text = expand_contractions(data.content_text)

    # Tokenize
    tokens = tokenize(expanded_text)

    # Count only real words (exclude punctuation and non-letter tokens)
    real_word_count = sum(1 for t in tokens if not t.is_punctuation and _has_letter(t.text))
```

And update the Article creation (line 143) to use `expanded_text`:
```python
    article = Article(
        title=data.title,
        source_path=data.source_path,
        source_type=data.source_type,
        content_text=expanded_text,  # store expanded version
        content_html=data.content_html,
        ...
    )
```

Similarly update `_save_book_chapter()` (around line 325-326):
```python
    expanded_text = expand_contractions(data.content_text)
    tokens = tokenize(expanded_text)
    real_word_count = sum(1 for t in tokens if not t.is_punctuation and _has_letter(t.text))
```

And use `expanded_text` in the Article creation at line 332 (`content_text=expanded_text`).

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/import_service.py
git commit -m "feat: expand contractions in imported text before storage"
```

---

### Task 7: Modify epub_importer.py to expand contractions in clean HTML

**Files:**
- Modify: `backend/app/importers/epub_importer.py`

- [ ] **Step 1: Add contraction expansion to clean HTML text nodes**

In `_CleanHTMLParser.handle_data()` and `_html_to_clean_html()`, expand contractions in text nodes so span injection matches the expanded tokens.

Add import at top:
```python
# After existing imports:
from ..services.contractions import expand as expand_contractions
```

Modify `_html_to_clean_html()` (line 523-529):
```python
def _html_to_clean_html(raw_html: str) -> str:
    """Strip CSS, images, scripts from EPUB XHTML. Keep semantic structure.
    Contractions are expanded so span injection aligns with tokenized text."""
    parser = _CleanHTMLParser()
    parser.feed(raw_html)
    parser.close()
    clean = html_mod.unescape(parser.get_html())
    # Expand contractions in the clean HTML so that <span> injection
    # matches the tokens produced by the (now-expanded) tokenizer output.
    return expand_contractions(clean)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/importers/epub_importer.py
git commit -m "feat: expand contractions in EPUB clean HTML output"
```

---

### Task 8: Modify unknown_word_analyzer.py to use lemma-based matching

**Files:**
- Modify: `backend/app/analysis/unknown_word_analyzer.py`

- [ ] **Step 1: Add lemma-aware known-word lookup**

Replace the analyze method to compare word lemmas instead of surface forms:

```python
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
        # Get all known word_lower values (which are now lemmas for new imports).
        # For legacy data (pre-lemmatization), also lemmatize them to build
        # a known-lemma set instead of raw surface forms.
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

        # Get all article words
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/analysis/unknown_word_analyzer.py
git commit -m "feat: use lemma comparison in unknown word analysis"
```

---

### Task 9: Create Alembic migration to clean legacy Word data

**Files:**
- Create: `backend/migrations/versions/009_merge_lemma_words.py`

- [ ] **Step 1: Generate migration skeleton**

```bash
cd backend && alembic revision --autogenerate -m "merge_lemma_words"
```

The autogenerate step won't detect the data migration logic — it's a data-only migration.

- [ ] **Step 2: Write the data migration**

Replace the generated migration content with:

```python
"""merge duplicate Word records by lemma, update ArticleWord references

Revision ID: 009
Revises: 008
Create Date: 2026-05-31
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge existing Word records that share the same lemma.

    For each lemma group, keep the record with the highest encounter_count,
    sum all encounter_counts, update ArticleWord.word_id to point to the
    survivor, then delete the redundant records.

    Runs in raw SQL because the operation spans multiple tables and needs
    careful ordering.
    """
    conn = op.get_bind()

    # Step 1: Find groups of words that share the same word_lower after
    # lemmatization. Since word_lower is unique, we can't have exact
    # duplicates there — but pre-lemmatization, "run", "runs", "running"
    # all have different word_lower values. We need Python lemmatization
    # to group them.

    # Try to import the lemmatizer. If NLTK not available, skip merge.
    try:
        from app.services.lemmatizer import lemmatize
    except Exception:
        # NLTK not available during migration — skip data merge.
        # The analysis layer will still work correctly for future imports.
        return

    # Fetch all Word records
    result = conn.execute(
        sa.text("SELECT id, word, word_lower, status, encounter_count, notes FROM words")
    )
    rows = list(result.mappings().all())

    if not rows:
        return

    # Group by lemma
    lemma_groups: dict[str, list[dict]] = {}
    for row in rows:
        lemma = lemmatize(row["word_lower"])
        lemma_groups.setdefault(lemma, []).append(dict(row))

    # Process groups with >1 member
    merged = 0
    for lemma, group in lemma_groups.items():
        if len(group) <= 1:
            continue

        # Sort: keep the one with highest encounter_count, then oldest id
        group.sort(key=lambda r: (-r["encounter_count"], r["id"]))
        survivor = group[0]

        for duplicate in group[1:]:
            dup_id = duplicate["id"]

            # Update ArticleWord references to point to survivor
            conn.execute(
                sa.text(
                    "UPDATE article_words SET word_id = :new_id "
                    "WHERE word_id = :old_id"
                ),
                {"new_id": survivor["id"], "old_id": dup_id},
            )

            # Sum encounter counts into survivor
            conn.execute(
                sa.text(
                    "UPDATE words SET encounter_count = encounter_count + :dup_encounters "
                    "WHERE id = :survivor_id"
                ),
                {"dup_encounters": duplicate["encounter_count"], "survivor_id": survivor["id"]},
            )

            # If duplicate has notes and survivor doesn't, copy them
            if duplicate.get("notes") and not survivor.get("notes"):
                conn.execute(
                    sa.text("UPDATE words SET notes = :notes WHERE id = :sid"),
                    {"notes": duplicate["notes"], "sid": survivor["id"]},
                )

            # Delete the duplicate WordNote records first (CASCADE would handle
            # this, but be explicit)
            conn.execute(
                sa.text("DELETE FROM word_notes WHERE word_id = :wid"),
                {"wid": dup_id},
            )

            # Delete the duplicate Word record
            conn.execute(
                sa.text("DELETE FROM words WHERE id = :wid"),
                {"wid": dup_id},
            )
            merged += 1

    # Also update the lemma column for all remaining words
    conn.execute(
        sa.text(
            "UPDATE words SET lemma = word_lower WHERE lemma IS NULL"
        )
    )

    if merged:
        print(f"Merged {merged} duplicate Word records across {len(lemma_groups)} lemma groups")


def downgrade() -> None:
    """Cannot unmerge — this is a data compaction migration."""
    pass
```

- [ ] **Step 3: Apply the migration**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/009_merge_lemma_words.py
git commit -m "feat: add migration to merge duplicate Word records by lemma"
```

---

### Task 10: Write unit tests

**Files:**
- Create: `backend/tests/test_contractions.py`
- Create: `backend/tests/test_lemmatizer.py`

- [ ] **Step 1: Create test_contractions.py**

```python
from __future__ import annotations

import pytest
from app.services.contractions import expand


@pytest.mark.parametrize("input_text, expected", [
    # Standard negations
    ("don't", "do not"),
    ("doesn't", "does not"),
    ("can't", "cannot"),
    ("won't", "will not"),
    ("shouldn't", "should not"),
    # Person + be
    ("we're", "we are"),
    ("I'm", "I am"),
    ("he's", "he is"),
    ("it's", "it is"),
    # Person + have
    ("I've", "I have"),
    ("we've", "we have"),
    # Person + will
    ("I'll", "I will"),
    ("they'll", "they will"),
    # Full sentences
    ("We're going to the store.", "We are going to the store."),
    ("I don't know what it's about.", "I do not know what it is about."),
    # No contraction
    ("hello world", "hello world"),
    # Empty
    ("", ""),
])
def test_expand_contractions(input_text, expected):
    assert expand(input_text) == expected


def test_expand_preserves_whitespace():
    result = expand("  don't  ")
    # The regex uses \b, so whitespace around the contraction is kept
    assert "do not" in result
```

- [ ] **Step 2: Create test_lemmatizer.py**

```python
from __future__ import annotations

import pytest
from app.services.lemmatizer import lemmatize


@pytest.mark.parametrize("word, expected", [
    # Verbs: -ing
    ("running", "run"),
    ("walking", "walk"),
    ("swimming", "swim"),
    # Verbs: -ed / past
    ("walked", "walk"),
    ("played", "play"),
    # Verbs: irregular past
    ("ran", "run"),
    ("went", "go"),
    ("was", "be"),
    ("were", "be"),
    # Nouns: plurals
    ("stores", "store"),
    ("cats", "cat"),
    ("boxes", "box"),
    # Nouns: irregular plurals
    ("feet", "foot"),
    ("mice", "mouse"),
    ("children", "child"),
    # Adjectives: comparatives
    ("better", "good"),
    ("bigger", "big"),
    # Words that are already base form
    ("run", "run"),
    ("store", "store"),
    ("go", "go"),
    # Contractions (already expanded by the time lemmatizer sees them)
    ("we", "we"),
    ("are", "be"),
    ("do", "do"),
    ("not", "not"),
])
def test_lemmatize(word, expected):
    assert lemmatize(word) == expected


def test_lemmatize_case_insensitive():
    assert lemmatize("Running") == "run"
    assert lemmatize("WENT") == "go"


def test_lemmatize_empty():
    assert lemmatize("") == ""
    assert lemmatize("  ") == ""
```

- [ ] **Step 3: Run the new tests**

```bash
cd backend && pytest tests/test_contractions.py tests/test_lemmatizer.py -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_contractions.py backend/tests/test_lemmatizer.py
git commit -m "test: add tests for contraction expansion and lemmatization"
```

---

### Task 11: Run full test suite and verify

**Files:**
- (all modified files)

- [ ] **Step 1: Run the full test suite**

```bash
cd backend && pytest -v
```

Expected: All existing tests continue to pass.

- [ ] **Step 2: Verify with a manual import test**

Start the dev server and import a text with contractions and inflected forms:
```
Input text: "We're running to the stores. I don't know what he's thinking."
Expected behavior:
- "We're" → tokens "We" + "are"
- "running" → lemma "run"
- "stores" → lemma "store"
- "don't" → tokens "do" + "not"
- "he's" → tokens "he" + "is"
- "thinking" → lemma "think"
- All words map to 8 Word records instead of 6 (plus punctuation)
- If "run", "store", "we", "are", "do", "not", "he", "be", "think" are known, 0 unknown words
```

- [ ] **Step 3: Run re-analysis on existing articles**

To update `is_unknown_at_import` for existing articles:
```bash
cd backend && python -c "
import asyncio
from app.database import async_session
from app.analysis.composite import CompositeAnalyzer

async def reanalyze():
    async with async_session() as db:
        from sqlalchemy import select
        from app.models.article import Article
        result = await db.execute(select(Article.id))
        ids = [row[0] for row in result.all()]
        analyzer = CompositeAnalyzer()
        for aid in ids:
            await analyzer.analyze_and_persist(aid, db)
        print(f'Re-analyzed {len(ids)} articles')

asyncio.run(reanalyze())
"
```

- [ ] **Step 5: Final commit if any cleanup needed**

```bash
git status
# If no changes needed, done.
```

---

## Implementation Order

Tasks should be executed **sequentially in numeric order** (1→11). Each task depends on the previous one. Task 9 (migration) must come after tasks 1-3 (NLTK setup, contractions, lemmatizer) because it imports from app.services.lemmatizer.

The only tasks that can run in parallel:
- Tasks 2 and 3 (contractions.py and lemmatizer.py) can be created simultaneously — they don't depend on each other
- Task 10 (tests) can be written alongside tasks 4-9
