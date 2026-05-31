from __future__ import annotations

import hashlib
import math
from typing import Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..analysis.composite import CompositeAnalyzer
from ..exceptions import NotFoundError
from ..models.annotation import Highlight
from ..models.article import Article, ArticleWord
from ..models.import_record import ImportRecord
from ..models.word import Word
from ..services.tokenizer import tokenize


async def get_articles(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
    sort: Optional[str] = None,
    tag: Optional[str] = None,
    exam_type: Optional[str] = None,
    exam_year: Optional[int] = None,
    question_type: Optional[str] = None,
) -> Tuple[List[Article], int]:
    conditions = [Article.is_archived == False, Article.book_id == None]
    if exam_type is not None:
        conditions.append(Article.exam_type == exam_type)
    if exam_year is not None:
        conditions.append(Article.exam_year == exam_year)
    if question_type is not None:
        conditions.append(Article.question_type == question_type)

    query = select(Article).where(*conditions)
    count_query = select(func.count(Article.id)).where(*conditions)

    # Sort
    if sort == "difficulty":
        query = query.order_by(Article.difficulty_score.asc().nullslast())
    elif sort == "recent":
        query = query.order_by(Article.last_read_at.desc().nullslast())
    elif sort == "exam_year":
        query = query.order_by(Article.exam_year.desc(), Article.question_type.asc())
    else:
        query = query.order_by(Article.created_at.desc())

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    articles = list(result.scalars().all())
    return articles, total


async def get_article(db: AsyncSession, article_id: int) -> Article:
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise NotFoundError(f"Article with id {article_id} not found")
    return article


async def update_article(db: AsyncSession, article_id: int, data: dict) -> Article:
    article = await get_article(db, article_id)
    for key, value in data.items():
        if value is not None:
            setattr(article, key, value)
    await db.commit()
    await db.refresh(article)
    return article


def _word_char_offset(article_words: List[ArticleWord], position: int) -> int:
    """Compute char_offset for a single word position by walking tokens in order."""
    offset = 0
    for i, aw in enumerate(article_words):
        if aw.position == position:
            return offset
        offset += len(aw.word_text)
        if i < len(article_words) - 1:
            next_aw = article_words[i + 1]
            if not next_aw.is_punctuation:
                offset += 1
    return 0


async def _remap_highlights(
    db: AsyncSession,
    old_highlights: List[Highlight],
    new_text: str,
    new_article_words: List[ArticleWord],
) -> None:
    """Remap highlight character offsets and word positions after content edit."""
    for hl in old_highlights:
        old_start = hl.start_char_offset or 0
        old_end = hl.end_char_offset or 0
        selected = hl.selected_text

        # Search window: 50 chars around old position
        window_start = max(0, old_start - 50)
        window_end = min(len(new_text), old_end + 50)
        search_region = new_text[window_start:window_end]

        found_at = search_region.find(selected)

        if found_at == -1:
            # Selected text is gone — delete the highlight (cascade deletes annotations)
            await db.delete(hl)
            continue

        new_start = window_start + found_at
        new_end = new_start + len(selected)

        # Find word positions that overlap [new_start, new_end)
        start_pos = None
        end_pos = None
        for aw in new_article_words:
            aw_start = _word_char_offset(new_article_words, aw.position)
            aw_end = aw_start + len(aw.word_text)
            if aw_start <= new_start < aw_end and start_pos is None:
                start_pos = aw.position
            if aw_start < new_end <= aw_end:
                end_pos = aw.position
                break

        if start_pos is None:
            start_pos = hl.start_word_position
        if end_pos is None:
            end_pos = hl.end_word_position

        hl.start_char_offset = new_start
        hl.end_char_offset = new_end
        hl.start_word_position = start_pos
        hl.end_word_position = end_pos


async def update_content(db: AsyncSession, article_id: int, new_text: str) -> Dict[str, object]:
    """Replace article content_text, re-tokenize, remap highlights, re-analyze."""
    from ..services.reader_service import assemble_reader_payload

    article = await get_article(db, article_id)

    # Validate
    if not new_text or not new_text.strip():
        raise ValueError("Content text cannot be empty")

    # Dedup check
    new_hash = hashlib.sha256(new_text.encode()).hexdigest()
    existing = await db.execute(
        select(Article).where(Article.sha256_hash == new_hash, Article.id != article_id)
    )
    if existing.scalar_one_or_none():
        raise ValueError("Another article with identical content already exists")

    # Save old highlights before deleting ArticleWords
    old_highlights = list((await db.execute(
        select(Highlight).where(Highlight.article_id == article_id)
    )).scalars().all())

    # Update article
    article.content_text = new_text
    article.sha256_hash = new_hash
    article.annotated_html = None  # fall back to ArticleDisplay rendering

    # Delete old ArticleWords using bulk delete
    await db.execute(
        delete(ArticleWord).where(ArticleWord.article_id == article_id)
    )
    await db.flush()

    # Re-tokenize and insert new ArticleWords
    tokens = tokenize(new_text)
    word_count = 0
    for tok in tokens:
        # Look up word in vocabulary
        word_result = await db.execute(
            select(Word).where(Word.word_lower == tok.text.lower())
        )
        word = word_result.scalar_one_or_none()

        aw = ArticleWord(
            article_id=article_id,
            word_id=word.id if word else None,
            word_text=tok.text,
            word_lower=tok.text.lower(),
            position=tok.position,
            sentence_index=tok.sentence_index,
            is_punctuation=tok.is_punctuation,
            is_unknown_at_import=None,
        )
        db.add(aw)
        if not tok.is_punctuation:
            word_count += 1

    article.word_count = word_count
    await db.flush()

    # Remap highlights
    new_article_words = list((await db.execute(
        select(ArticleWord).where(ArticleWord.article_id == article_id).order_by(ArticleWord.position)
    )).scalars().all())
    await _remap_highlights(db, old_highlights, new_text, new_article_words)

    await db.flush()

    # Re-run analysis
    analyzer = CompositeAnalyzer()
    await analyzer.analyze_and_persist(article_id, db)

    await db.commit()

    # Return fresh reader payload
    return await assemble_reader_payload(db, article_id)


async def delete_article(db: AsyncSession, article_id: int) -> None:
    article = await get_article(db, article_id)
    await db.delete(article)
    await db.commit()


async def get_import_history(
    db: AsyncSession,
    *,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[ImportRecord], int]:
    query = select(ImportRecord).order_by(ImportRecord.imported_at.desc())
    count_query = select(func.count(ImportRecord.id))

    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    records = list(result.scalars().all())
    return records, total
