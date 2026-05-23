from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..exceptions import NotFoundError
from ..models.article import Article, ArticleWord
from ..models.annotation import Annotation, Highlight
from ..models.book import Book
from ..models.reading_session import ReadingSession
from ..models.word import Word, WordNote


async def assemble_reader_payload(db: AsyncSession, article_id: int) -> Dict[str, Any]:
    """Assemble the full reader data for an article: paragraphs, words, highlights, annotations."""
    article_result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = article_result.scalar_one_or_none()
    if not article:
        raise NotFoundError(f"Article with id {article_id} not found")

    # Get all article_words with joined word data
    aw_result = await db.execute(
        select(ArticleWord)
        .options(selectinload(ArticleWord.word))
        .where(ArticleWord.article_id == article_id)
        .order_by(ArticleWord.position)
    )
    article_words = list(aw_result.scalars().all())

    # Get highlights
    hl_result = await db.execute(
        select(Highlight).where(Highlight.article_id == article_id)
    )
    highlights = list(hl_result.scalars().all())

    # Get annotations for this article
    ann_result = await db.execute(
        select(Annotation).where(Annotation.article_id == article_id)
    )
    annotations = list(ann_result.scalars().all())

    # Build highlight-annotation mapping
    hl_annotations: Dict[int, List[dict]] = {}
    for ann in annotations:
        if ann.highlight_id:
            hl_annotations.setdefault(ann.highlight_id, []).append({
                "id": ann.id,
                "annotation_type": ann.annotation_type,
                "content": ann.content,
            })

    # Group article_words by sentence
    paragraphs = _build_paragraphs(article_words, highlights, hl_annotations)

    # Calculate stats (exclude punctuation)
    real_words = [aw for aw in article_words if not aw.is_punctuation]
    known_count = sum(1 for aw in real_words if aw.word and aw.word.status in ("known", "familiar", "mastered"))
    unknown_count = sum(1 for aw in real_words if not aw.word or aw.word.status in ("unknown", "learning"))
    total = len(real_words)
    coverage = known_count / total if total > 0 else 1.0

    # Build book/chapter navigation context
    book_context = None
    if article.book_id:
        book_result = await db.execute(select(Book).where(Book.id == article.book_id))
        book = book_result.scalar_one_or_none()
        if book:
            # Get sibling chapters
            siblings_result = await db.execute(
                select(Article.id, Article.title, Article.chapter_index, Article.chapter_path)
                .where(Article.book_id == book.id)
                .order_by(Article.chapter_index)
            )
            chapters = [
                {"id": r[0], "title": r[1], "chapter_index": r[2], "chapter_path": r[3]}
                for r in siblings_result.all()
            ]
            current_idx = next((i for i, c in enumerate(chapters) if c["id"] == article.id), -1)

            toc_tree = None
            if book.toc_json:
                try:
                    toc_tree = json.loads(book.toc_json)
                except (json.JSONDecodeError, TypeError):
                    toc_tree = None

            book_context = {
                "book_id": book.id,
                "book_title": book.title,
                "total_chapters": book.total_chapters,
                "current_chapter_index": article.chapter_index,
                "prev_chapter": chapters[current_idx - 1] if current_idx > 0 else None,
                "next_chapter": chapters[current_idx + 1] if current_idx + 1 < len(chapters) else None,
                "all_chapters": chapters,
                "toc_tree": toc_tree,
            }

    return {
        "article": {
            "id": article.id,
            "title": article.title,
            "word_count": article.word_count,
            "difficulty_score": article.difficulty_score,
            "unknown_word_count": article.unknown_word_count,
            "i_plus_one_score": article.i_plus_one_score,
        },
        "book": book_context,
        "paragraphs": paragraphs,
        "highlights": [
            {
                "id": h.id,
                "highlight_type": h.highlight_type,
                "start_char_offset": h.start_char_offset,
                "end_char_offset": h.end_char_offset,
                "start_word_position": h.start_word_position,
                "end_word_position": h.end_word_position,
                "selected_text": h.selected_text,
                "color": h.color,
                "annotation_count": len(hl_annotations.get(h.id, [])),
            }
            for h in highlights
        ],
        "annotations": [
            {
                "id": a.id,
                "highlight_id": a.highlight_id,
                "word_id": a.word_id,
                "annotation_type": a.annotation_type,
                "content": a.content,
            }
            for a in annotations
        ],
        "stats": {
            "total_words": total,
            "known_words": known_count,
            "unknown_words": unknown_count,
            "coverage": coverage,
        },
    }


def _build_paragraphs(
    article_words: List[ArticleWord],
    highlights: List[Highlight],
    hl_annotations: Dict[int, List[dict]],
) -> List[dict]:
    """Group words into paragraphs by sentence boundaries, adding per-word metadata."""
    # Build highlight lookup by position
    hl_by_pos: Dict[int, dict] = {}
    for h in highlights:
        if h.start_word_position is not None:
            for pos in range(h.start_word_position, (h.end_word_position or h.start_word_position) + 1):
                hl_by_pos[pos] = {"color": h.color, "highlight_id": h.id}

    # Reconstruct character offsets from word positions and text
    # We assume words are in order and separated by single spaces
    char_offset_map = _compute_char_offsets(article_words)

    paragraphs: List[dict] = []
    current_para: List[dict] = []

    for aw in article_words:
        is_punct = aw.is_punctuation or False
        word_data = {
            "position": aw.position,
            "text": aw.word_text,
            "word_id": aw.word_id,
            "word_lower": aw.word_lower,
            "status": "punct" if is_punct else (aw.word.status if aw.word else "unknown"),
            "has_notes": False if is_punct else bool(aw.word and aw.word.notes),
            "is_highlighted": aw.position in hl_by_pos,
            "highlight_color": hl_by_pos[aw.position]["color"] if aw.position in hl_by_pos else None,
            "char_offset": char_offset_map.get(aw.position, 0),
        }
        current_para.append(word_data)

    if current_para:
        paragraphs.append({"index": 0, "words": current_para})

    return paragraphs


def _compute_char_offsets(article_words: List[ArticleWord]) -> Dict[int, int]:
    """Reconstruct character offsets by walking tokens in position order.
    No space is added before punctuation tokens."""
    offsets = {}
    char_pos = 0
    for i, aw in enumerate(article_words):
        offsets[aw.position] = char_pos
        char_pos += len(aw.word_text)
        if i < len(article_words) - 1:
            next_aw = article_words[i + 1]
            if not next_aw.is_punctuation:
                char_pos += 1  # space between words
    return offsets


async def record_encounter(db: AsyncSession, article_id: int, word_id: int) -> None:
    word_result = await db.execute(select(Word).where(Word.id == word_id))
    word = word_result.scalar_one_or_none()
    if word:
        word.encounter_count += 1
        word.last_encountered = datetime.now()
        await db.commit()


async def start_session(db: AsyncSession, article_id: int) -> ReadingSession:
    session = ReadingSession(article_id=article_id, started_at=datetime.now())
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Update article read stats
    article_result = await db.execute(select(Article).where(Article.id == article_id))
    article = article_result.scalar_one_or_none()
    if article:
        article.read_count += 1
        article.last_read_at = datetime.now()
        await db.commit()

    return session


async def end_session(
    db: AsyncSession,
    session_id: int,
    word_position: Optional[int] = None,
) -> ReadingSession:
    result = await db.execute(select(ReadingSession).where(ReadingSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError(f"Session with id {session_id} not found")

    session.ended_at = datetime.now()
    if word_position is not None:
        session.word_position_stopped = word_position
    if session.started_at:
        session.duration_seconds = int((datetime.now() - session.started_at).total_seconds())
    await db.commit()
    await db.refresh(session)
    return session
