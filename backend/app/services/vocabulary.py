from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..exceptions import NotFoundError
from ..models.word import Word, WordNote
from ..schemas.word import VocabularyStats
from .lemmatizer import lemmatize


async def get_words(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 30,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
) -> Tuple[List[Word], int]:
    query = select(Word)
    count_query = select(func.count(Word.id))

    if status:
        query = query.where(Word.status == status)
        count_query = count_query.where(Word.status == status)

    if search:
        pattern = f"%{search}%"
        query = query.where(Word.word_lower.like(pattern))
        count_query = count_query.where(Word.word_lower.like(pattern))

    # Get total count
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Sort
    if sort == "encounters":
        query = query.order_by(Word.encounter_count.desc())
    elif sort == "recent":
        query = query.order_by(Word.updated_at.desc())
    else:
        query = query.order_by(Word.word_lower.asc())

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    query = query.options(selectinload(Word.word_notes))

    result = await db.execute(query)
    words = list(result.scalars().all())

    return words, total


async def get_word(db: AsyncSession, word_id: int) -> Word:
    result = await db.execute(
        select(Word).options(selectinload(Word.word_notes)).where(Word.id == word_id)
    )
    word = result.scalar_one_or_none()
    if not word:
        raise NotFoundError(f"Word with id {word_id} not found")
    return word


async def update_word(db: AsyncSession, word_id: int, data: dict) -> Word:
    word = await get_word(db, word_id)
    for key, value in data.items():
        if value is not None:
            setattr(word, key, value)
    await db.commit()
    await db.refresh(word)
    return word


async def bulk_update_status(db: AsyncSession, word_ids: List[int], new_status: str) -> int:
    result = await db.execute(
        update(Word).where(Word.id.in_(word_ids)).values(status=new_status).returning(Word.id)
    )
    await db.commit()
    return len(list(result.scalars().all()))


async def search_words(db: AsyncSession, query: str, limit: int = 10, exact: bool = False) -> List[Word]:
    q = query.lower().strip()
    if exact:
        # Lemmatize the query, then exact-match the lemma
        try:
            lemma = lemmatize(q)
        except Exception:
            lemma = q
        # Try lemma match first, then fall back to surface form
        result = await db.execute(
            select(Word).where(Word.word_lower == lemma).limit(1)
        )
        words = list(result.scalars().all())
        if words:
            return words
        # Fall back to exact surface form match
        result = await db.execute(
            select(Word).where(Word.word_lower == q).limit(1)
        )
        return list(result.scalars().all())

    # Prefix search for autocomplete (vocabulary page)
    result = await db.execute(
        select(Word)
        .where(Word.word_lower.like(f"{q}%"))
        .order_by(Word.word_lower.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_stats(db: AsyncSession) -> VocabularyStats:
    result = await db.execute(
        select(Word.status, func.count(Word.id)).group_by(Word.status)
    )
    counts = dict(result.all())

    return VocabularyStats(
        total=sum(counts.values()),
        unknown=counts.get("unknown", 0),
        learning=counts.get("learning", 0),
        familiar=counts.get("familiar", 0),
        known=counts.get("known", 0),
        mastered=counts.get("mastered", 0),
    )


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

    # Create with lemma as word_lower; store original text as word,
    # and also populate the previously-unused lemma column
    word = Word(
        word=word_text.strip(),
        word_lower=lemma,
        lemma=lemma,
        status="unknown",
        first_seen=datetime.now(),
    )
    db.add(word)
    await db.flush()
    return word


async def add_note(db: AsyncSession, word_id: int, data: dict) -> WordNote:
    await get_word(db, word_id)  # ensure word exists
    note = WordNote(word_id=word_id, **data)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def update_note(db: AsyncSession, note_id: int, data: dict) -> WordNote:
    result = await db.execute(select(WordNote).where(WordNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise NotFoundError(f"Note with id {note_id} not found")
    for key, value in data.items():
        if value is not None:
            setattr(note, key, value)
    await db.commit()
    await db.refresh(note)
    return note


async def delete_note(db: AsyncSession, note_id: int) -> None:
    result = await db.execute(select(WordNote).where(WordNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise NotFoundError(f"Note with id {note_id} not found")
    await db.delete(note)
    await db.commit()


async def increment_encounter(db: AsyncSession, word_id: int) -> None:
    word = await get_word(db, word_id)
    word.encounter_count += 1
    word.last_encountered = datetime.now()
    await db.commit()
